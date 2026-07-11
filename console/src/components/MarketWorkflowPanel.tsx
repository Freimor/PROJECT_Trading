import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiPost, formatOperatorFacingError } from "../api";
import OperatorConfirmModal from "./OperatorConfirmModal";
import PortfolioCard from "./PortfolioCard";
import StrategyDetailModal from "./StrategyDetailModal";
import StrategySubsettingsPanel from "./StrategySubsettingsPanel";
import WorkflowSessionReportModal from "./WorkflowSessionReportModal";
import { POLL } from "../config/polling";
import { useErrorNotifications } from "../context/ErrorNotifications";
import { useI18n } from "../i18n/LanguageContext";
import { usePolling } from "../hooks/usePolling";
import type { StrategyState, WorkflowSessionReport } from "../types";
import { strategyDescription } from "../utils/strategyText";

type Market = "crypto" | "securities";

type N8nWorkflow = { id: string; name: string; active: boolean };

type SessionVolumeMode = "stablecoin" | "existing_holdings";
type HoldingsUnit = "percent" | "absolute";

type MarketControl = {
  trading_mode?: string;
  live_flag?: boolean;
  active_workflow?: string | null;
  workflow_started_at?: string | null;
  workflow_session_config?: {
    session_capital?: number | null;
    session_volume_mode?: SessionVolumeMode;
    use_existing_holdings?: boolean;
    existing_holdings_unit?: HoldingsUnit;
    existing_holdings_use_pct?: number;
    existing_holdings_use_qty?: number | null;
  liquidate_on_stop?: boolean;
  liquidate_on_margin_call?: boolean;
  universe_scan_selected?: string[];
    quote_asset?: string;
  } | null;
  crypto_workflow_settings?: {
    quote_asset?: string;
    allowed_quote_assets?: string[];
    runtime_override?: boolean;
    trading_product?: {
      market_type?: string;
      is_futures?: boolean;
      allow_short?: boolean;
      leverage?: number;
      margin_mode?: string;
      runtime_override?: boolean;
    };
  } | null;
  workflows?: Array<{ id: string; name: string; active: boolean }>;
  multi_automation_enabled?: boolean;
  multi_automation_max_primary?: number;
  active_workflows_primary?: string[];
  n8n?: { status?: string; message?: string };
};

const DEFAULT_SESSION_CAPITAL: Record<Market, number> = {
  crypto: 10_000,
  securities: 100_000,
};

type ScheduleResp = {
  option_id?: string;
  options?: Array<{ id: string; label_ru?: string; label_en?: string }>;
};

type DiagnosticsResp = {
  orders_executed?: number;
  orders_total?: number;
  hints?: string[];
  recent_errors?: Array<{ reject_reason?: string; symbol?: string; payload_json?: string }>;
  last_signal?: { event_at?: string; symbol?: string };
};

function formatUptime(iso?: string | null): string {
  if (!iso) return "—";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "—";
  const sec = Math.max(0, Math.floor((Date.now() - t) / 1000));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  if (h > 0) return `${h}ч ${m}м`;
  return `${m}м`;
}

type OperationMode = "dry_run" | "paper" | "live";

type OperationModeOption = { id: OperationMode; labelKey: string };

type PendingOp =
  | { kind: "start"; workflow: string; strategyId: string; operationMode: OperationMode }
  | { kind: "stop" }
  | { kind: "stop_one"; workflow: string }
  | { kind: "multi_automation"; enabled: boolean }
  | { kind: "test_run"; workflow: string }
  | { kind: "schedule"; workflow: string; optionId: string };

type Props = {
  market: Market;
  killSwitch?: boolean;
  onStrategyChange?: (state: StrategyState) => void;
  onSettingsChange?: () => void;
};

const OPERATION_MODES: OperationModeOption[] = [
  { id: "dry_run", labelKey: "operationModes.dryRun" },
  { id: "paper", labelKey: "operationModes.paper" },
  { id: "live", labelKey: "operationModes.live" },
];

const STRATEGY_OPERATION_MODES: Record<string, OperationMode[]> = {
  llm_swing: ["dry_run", "paper", "live"],
  crypto_scalp_hybrid: ["dry_run", "paper"],
  deepfund_paper: ["paper"],
  swing_signals: ["dry_run", "paper", "live"],
  index_dca: ["paper"],
  factor_sleeve: ["paper"],
  bond_ladder: ["paper"],
};

const WORKFLOW_BY_STRATEGY_MODE: Record<string, Partial<Record<OperationMode, string>>> = {
  llm_swing: {
    dry_run: "crypto-signal-dry-run",
    paper: "crypto-signal-paper",
    live: "crypto-signal-paper",
  },
  crypto_scalp_hybrid: {
    dry_run: "crypto-scalp-hybrid-dry-run",
    paper: "crypto-scalp-hybrid-paper",
  },
  deepfund_paper: {
    paper: "deepfund-live-paper",
  },
  swing_signals: {
    dry_run: "securities-swing-dry-run",
    paper: "securities-swing-paper",
    live: "securities-swing-paper",
  },
  index_dca: {
    paper: "securities-dca-sandbox",
  },
  factor_sleeve: {
    paper: "securities-factor-sleeve",
  },
  bond_ladder: {
    paper: "bond-ladder-flow",
  },
};

function resolveWorkflow(strategyId: string, operationMode: OperationMode): string {
  return WORKFLOW_BY_STRATEGY_MODE[strategyId]?.[operationMode] ?? "";
}

function tradingModeToOperationMode(tradingMode: string | undefined): OperationMode | null {
  const mode = (tradingMode ?? "").toLowerCase();
  if (mode === "dry_run") return "dry_run";
  if (mode === "live") return "live";
  if (mode === "paper" || mode === "shadow") return "paper";
  return null;
}

function workflowFallbackMode(workflowName: string): OperationMode {
  if (workflowName.includes("dry-run")) return "dry_run";
  return "paper";
}

export default function MarketWorkflowPanel({
  market,
  killSwitch = false,
  onStrategyChange,
  onSettingsChange,
}: Props) {
  const { t, lang } = useI18n();
  const { report } = useErrorNotifications();

  const [selectedStrategyId, setSelectedStrategyId] = useState("");
  const [selectedOperationMode, setSelectedOperationMode] = useState<OperationMode>("paper");
  const [pendingOp, setPendingOp] = useState<PendingOp | null>(null);
  const [opBusy, setOpBusy] = useState(false);
  const [opError, setOpError] = useState<string | null>(null);
  const [importBusy, setImportBusy] = useState(false);
  const [importMsg, setImportMsg] = useState<string | null>(null);
  const [scheduleOptionId, setScheduleOptionId] = useState("");
  const [testMsg, setTestMsg] = useState<string | null>(null);
  const [detailStrategyId, setDetailStrategyId] = useState<string | null>(null);
  const [sessionReport, setSessionReport] = useState<WorkflowSessionReport | null>(null);
  const [reportsBusy, setReportsBusy] = useState(false);
  const [sessionCapitalInput, setSessionCapitalInput] = useState("");
  const [sessionVolumeMode, setSessionVolumeMode] = useState<SessionVolumeMode>("stablecoin");
  const [holdingsUnit, setHoldingsUnit] = useState<HoldingsUnit>("percent");
  const [existingHoldingsPctInput, setExistingHoldingsPctInput] = useState("100");
  const [existingHoldingsQtyInput, setExistingHoldingsQtyInput] = useState("");
  const [liquidateOnStop, setLiquidateOnStop] = useState(false);
  const [multiAutomation, setMultiAutomation] = useState(false);

  const { data: strategyData, refresh: refreshStrategy } = usePolling<StrategyState>(
    () => apiGet(`/api/strategies/${market}`),
    POLL.DASHBOARD,
    true,
    { staggerKey: `wf-panel-strategy-${market}` },
  );

  const { data: control, refresh: refreshControl } = usePolling<MarketControl>(
    () => apiGet(`/api/automation/control/${market}`),
    POLL.OPS,
    true,
    { staggerKey: `wf-panel-${market}` },
  );

  const isFutures =
    control?.crypto_workflow_settings?.trading_product?.is_futures ?? false;
  const activePrimary = control?.active_workflows_primary ?? [];
  const maxPrimary = control?.multi_automation_max_primary ?? 2;

  useEffect(() => {
    if (control?.multi_automation_enabled != null) {
      setMultiAutomation(Boolean(control.multi_automation_enabled));
    }
  }, [control?.multi_automation_enabled]);

  const strategies = useMemo(() => strategyData?.strategies ?? [], [strategyData?.strategies]);

  const quoteAsset =
    control?.crypto_workflow_settings?.quote_asset ??
    control?.workflow_session_config?.quote_asset ??
    "USDT";
  const fiatLabel = market === "crypto" ? quoteAsset : "₽";

  const { data: n8nData, refresh: refreshN8n } = usePolling<{
    status: string;
    workflows?: N8nWorkflow[];
  }>(() => apiGet("/api/n8n/workflows"), POLL.OPS, true, { staggerKey: `wf-panel-n8n-${market}` });

  const { data: diagnostics, refresh: refreshDiagnostics } = usePolling<DiagnosticsResp>(
    () => apiGet(`/api/automation/diagnostics/${market}?days=7`),
    POLL.OPS,
    true,
    { staggerKey: `wf-diag-${market}` },
  );

  const n8nByName = useMemo(
    () => new Map((n8nData?.workflows ?? []).map((w) => [w.name, w])),
    [n8nData?.workflows],
  );

  const liveEnabled = control?.live_flag ?? false;

  const modesForStrategy = useCallback((strategyId: string) => {
    const allowed = STRATEGY_OPERATION_MODES[strategyId];
    if (!allowed) return OPERATION_MODES;
    return OPERATION_MODES.filter((m) => allowed.includes(m.id));
  }, []);

  const visibleModes = useMemo(
    () => modesForStrategy(selectedStrategyId || strategyData?.active || ""),
    [modesForStrategy, selectedStrategyId, strategyData?.active],
  );

  const selectedWorkflow = useMemo(
    () => resolveWorkflow(selectedStrategyId, selectedOperationMode),
    [selectedStrategyId, selectedOperationMode],
  );

  const scheduleFetcher = useCallback(
    () =>
      selectedWorkflow
        ? apiGet<ScheduleResp>(`/api/automation/schedule/${encodeURIComponent(selectedWorkflow)}`)
        : Promise.resolve({ option_id: "", options: [] }),
    [selectedWorkflow],
  );
  const { data: scheduleData, refresh: refreshSchedule } = usePolling<ScheduleResp>(
    scheduleFetcher,
    POLL.STATIC,
    Boolean(selectedWorkflow),
    { staggerKey: `wf-schedule-${market}-${selectedWorkflow}` },
  );

  useEffect(() => {
    if (scheduleData?.option_id) setScheduleOptionId(scheduleData.option_id);
  }, [scheduleData?.option_id, selectedWorkflow]);

  const activeWorkflow = useMemo(() => {
    const allWorkflows = new Set(
      Object.values(WORKFLOW_BY_STRATEGY_MODE).flatMap((m) => Object.values(m)),
    );
    for (const name of allWorkflows) {
      const n8n = n8nByName.get(name);
      const ctrl = control?.workflows?.find((w) => w.name === name);
      if (n8n?.active || ctrl?.active) return name;
    }
    return null;
  }, [control?.workflows, n8nByName]);

  const activeOperationMode = useMemo(() => {
    if (!activeWorkflow) return null;
    const fromTrading = tradingModeToOperationMode(control?.trading_mode);
    if (fromTrading) return fromTrading;
    return workflowFallbackMode(activeWorkflow);
  }, [activeWorkflow, control?.trading_mode]);

  const activeStrategyId = strategyData?.active ?? "";

  useEffect(() => {
    if (!strategyData) return;
    const activeId =
      strategyData.active && strategies.some((s) => s.id === strategyData.active)
        ? strategyData.active
        : strategies[0]?.id ?? "";
    setSelectedStrategyId((prev) => prev || activeId);
  }, [strategyData, strategies]);

  useEffect(() => {
    if (!selectedStrategyId) return;
    const allowed = modesForStrategy(selectedStrategyId);
    const preferred =
      activeOperationMode && allowed.some((m) => m.id === activeOperationMode)
        ? activeOperationMode
        : null;
    const fallback = allowed[0]?.id ?? "paper";
    setSelectedOperationMode((prev) => {
      if (prev && allowed.some((m) => m.id === prev)) return prev;
      return preferred ?? fallback;
    });
  }, [selectedStrategyId, activeOperationMode, modesForStrategy]);

  const isRunning =
    activeWorkflow === selectedWorkflow &&
    activeOperationMode === selectedOperationMode &&
    activeStrategyId === selectedStrategyId &&
    activeWorkflow !== null;

  const selectedExists = Boolean(selectedWorkflow) && n8nByName.has(selectedWorkflow);
  const n8nError = control?.n8n?.status === "error" || n8nData?.status === "error";
  const hasMissing = visibleModes.some((mode) => {
    const wf = resolveWorkflow(selectedStrategyId, mode.id);
    return wf && !n8nByName.has(wf);
  });

  const runImport = async () => {
    setImportBusy(true);
    setImportMsg(null);
    try {
      const r = await apiPost<{
        workflows?: Array<{ name: string; action: string }>;
        errors?: Array<{ name: string; error: string }>;
      }>(`/api/n8n/workflows/import?market=${market}&update=true`);
      const created = (r.workflows ?? []).filter((w) => w.action === "created" || w.action === "updated").length;
      const errs = r.errors?.length ?? 0;
      setImportMsg(
        errs
          ? t("workflowPanel.importPartial", { ok: String(created), err: String(errs) })
          : t("workflowPanel.importDone", { count: String(created) }),
      );
      refreshControl();
      refreshN8n();
    } catch (err) {
      setImportMsg(String(err));
      report("workflow/import", String(err));
    } finally {
      setImportBusy(false);
    }
  };

  const runPendingOp = useCallback(
    async (password: string) => {
      if (!pendingOp) return;
      setOpBusy(true);
      setOpError(null);
      try {
        if (pendingOp.kind === "start") {
          const volumeMode =
            market === "securities" ? "stablecoin" : sessionVolumeMode;
          let cap: number | undefined;
          let holdingsPct = 0;
          let holdingsQty: number | undefined;

          if (volumeMode === "stablecoin") {
            const parsed = Number(String(sessionCapitalInput).replace(/\s/g, ""));
            if (!Number.isFinite(parsed) || parsed <= 0) {
              setOpError(t("workflowPanel.sessionCapitalInvalid"));
              setOpBusy(false);
              return;
            }
            cap = parsed;
          } else {
            if (holdingsUnit === "percent") {
              holdingsPct = Number(String(existingHoldingsPctInput).replace(/\s/g, ""));
              if (!Number.isFinite(holdingsPct) || holdingsPct <= 0 || holdingsPct > 100) {
                setOpError(t("workflowPanel.existingHoldingsPctInvalid"));
                setOpBusy(false);
                return;
              }
            } else {
              const parsedQty = Number(String(existingHoldingsQtyInput).replace(/\s/g, ""));
              if (!Number.isFinite(parsedQty) || parsedQty <= 0) {
                setOpError(t("workflowPanel.existingHoldingsQtyInvalid"));
                setOpBusy(false);
                return;
              }
              holdingsQty = parsedQty;
            }
          }
          if (pendingOp.strategyId !== strategyData?.active) {
            const next = await apiPost<StrategyState>(
              `/api/strategies/${market}`,
              { strategy_id: pendingOp.strategyId, operator: "web:operator" },
              { operatorPassword: password },
            );
            onStrategyChange?.(next);
            refreshStrategy();
          }
          await apiPost(
            `/api/n8n/workflows/select?market=${market}`,
            {
              workflow_name: pendingOp.workflow,
              trading_mode: pendingOp.operationMode,
              session_volume_mode: volumeMode,
              session_capital: cap,
              use_existing_holdings: volumeMode === "existing_holdings",
              existing_holdings_unit: holdingsUnit,
              existing_holdings_use_pct: holdingsPct,
              existing_holdings_use_qty: holdingsQty,
              liquidate_on_stop: liquidateOnStop,
              liquidate_on_margin_call: liquidateOnStop,
              additive:
                multiAutomation &&
                (activePrimary.length > 0 || Boolean(activeWorkflow)) &&
                !activePrimary.includes(pendingOp.workflow),
            },
            { operatorPassword: password },
          );
        } else if (pendingOp.kind === "stop") {
          const stopResp = await apiPost<{
            session_report?: { report_id?: string } | null;
          }>(`/api/n8n/workflows/stop?market=${market}`, {}, { operatorPassword: password });
          const reportId = stopResp.session_report?.report_id;
          if (reportId) {
            const full = await apiGet<WorkflowSessionReport>(`/api/workflow/reports/${reportId}`);
            setSessionReport(full);
          }
        } else if (pendingOp.kind === "stop_one") {
          await apiPost(
            `/api/n8n/workflows/stop?market=${market}`,
            { workflow_name: pendingOp.workflow, operator: "web:operator" },
            { operatorPassword: password },
          );
        } else if (pendingOp.kind === "multi_automation") {
          await apiPost(
            `/api/automation/control/${market}/multi-automation`,
            { enabled: pendingOp.enabled, operator: "web:operator" },
            { operatorPassword: password },
          );
        } else if (pendingOp.kind === "test_run") {
          const workflow = pendingOp.workflow;
          setPendingOp(null);
          setOpBusy(false);
          setTestMsg(t("workflowPanel.testRunStarted"));
          void apiPost<{
            executed_count?: number;
            results?: Array<{ status?: string; symbol?: string; reject_reason?: string }>;
          }>(
            `/api/automation/run-once?market=${market}`,
            { workflow_name: workflow, operator: "web:operator" },
            { operatorPassword: password, timeoutMs: 900_000, retries: 0 },
          )
            .then((resp) => {
              const n = resp.executed_count ?? 0;
              setTestMsg(t("workflowPanel.testRunDone", { executed: String(n) }));
              refreshDiagnostics();
              refreshControl();
            })
            .catch((err) => {
              const message = err instanceof Error ? err.message : String(err ?? "unknown_error");
              setTestMsg(message.includes("Таймаут") ? t("workflowPanel.testRunTimeoutHint") : message);
              report("workflow/test-run", message);
              refreshDiagnostics();
            });
          return;
        } else if (pendingOp.kind === "schedule") {
          await apiPost(
            `/api/automation/schedule/${encodeURIComponent(pendingOp.workflow)}`,
            { option_id: pendingOp.optionId, operator: "web:operator" },
            { operatorPassword: password },
          );
          refreshSchedule();
        }
        setPendingOp(null);
        refreshControl();
        refreshN8n();
      } catch (err) {
        const message = formatOperatorFacingError(err, t);
        setOpError(message);
        report("workflow/panel", message);
      } finally {
        setOpBusy(false);
      }
    },
    [
      market,
      onStrategyChange,
      pendingOp,
      refreshControl,
      refreshDiagnostics,
      refreshN8n,
      refreshSchedule,
      refreshStrategy,
      report,
      strategyData?.active,
      sessionCapitalInput,
      sessionVolumeMode,
      holdingsUnit,
      existingHoldingsPctInput,
      existingHoldingsQtyInput,
      liquidateOnStop,
      multiAutomation,
      activePrimary,
      activeWorkflow,
      t,
    ],
  );

  const handleUniverseChange = useCallback(async () => {
    try {
      const next = await apiGet<StrategyState>(`/api/strategies/${market}`);
      onStrategyChange?.(next);
    } catch {
      // strategy refresh below still runs
    }
    refreshStrategy();
    refreshControl();
  }, [market, onStrategyChange, refreshStrategy, refreshControl]);

  const pendingTitle =
    pendingOp?.kind === "stop"
      ? t("workflowPanel.stop")
      : pendingOp?.kind === "stop_one"
        ? t("workflowPanel.stopOne")
        : pendingOp?.kind === "multi_automation"
          ? t("workflowPanel.multiAutomationTitle")
          : pendingOp?.kind === "test_run"
            ? t("workflowPanel.testRun")
            : pendingOp?.kind === "schedule"
              ? t("workflowPanel.scheduleApply")
              : isRunning
                ? t("workflowPanel.restart")
                : multiAutomation && activePrimary.length > 0
                  ? t("workflowPanel.addWorkflow")
                  : t("workflowPanel.start");

  const pendingRisk =
    pendingOp?.kind === "start" && pendingOp.operationMode === "live"
      ? t("workspace.modeRiskLive")
      : pendingOp?.kind === "test_run"
        ? t("workflowPanel.testRunRisk")
        : t("workflowsPage.operatorRisk");

  const pendingRiskTone =
    pendingOp?.kind === "start" && pendingOp.operationMode === "live" ? "danger" : "warn";

  return (
    <>
      <PortfolioCard title={t("workflowPanel.title")} collapsible={false}>
        {killSwitch ? <p className="warn small">{t("workflowPanel.killBlocked")}</p> : null}
        {n8nError ? <p className="warn small">{t("workflowPanel.n8nUnavailable")}</p> : null}
        {hasMissing ? (
          <div className="workflow-import-banner">
            <p className="small muted">{t("workflowPanel.importHint")}</p>
            <button type="button" className="tiny primary" disabled={importBusy} onClick={runImport}>
              {importBusy ? t("workflowPanel.importing") : t("workflowPanel.importFromRepo")}
            </button>
          </div>
        ) : null}
        {importMsg ? <p className="small muted">{importMsg}</p> : null}

        <fieldset className="workflow-mode-list">
          <legend className="muted small">{t("workflowPanel.strategySection")}</legend>
          {strategies.map((s) => (
            <div
              key={s.id}
              className={`workflow-mode-option ${selectedStrategyId === s.id ? "selected" : ""}`}
            >
              <input
                type="radio"
                name={`strategy-${market}`}
                value={s.id}
                checked={selectedStrategyId === s.id}
                onChange={() => setSelectedStrategyId(s.id)}
              />
              <div className="workflow-mode-option-body">
                <strong>{t(`strategies.${s.id}.label` as "strategies.llm_swing.label")}</strong>
                <span className="muted small block">
                  {strategyDescription(s, lang === "en" ? "en" : "ru", market)}
                </span>
                <button
                  type="button"
                  className="tiny strategy-more-btn"
                  onClick={() => setDetailStrategyId(s.id)}
                >
                  {t("workflowPanel.moreDetails")}
                </button>
              </div>
            </div>
          ))}
        </fieldset>

        <fieldset className="workflow-mode-list">
          <legend className="muted small">{t("workflowPanel.modeSection")}</legend>
          {visibleModes.map((mode) => {
            const workflow = resolveWorkflow(selectedStrategyId, mode.id);
            const imported = workflow ? n8nByName.has(workflow) : false;
            const running =
              activeOperationMode === mode.id &&
              activeWorkflow === workflow &&
              activeStrategyId === selectedStrategyId;
            const liveDisabled = mode.id === "live" && !liveEnabled;
            return (
              <label
                key={mode.id}
                className={`workflow-mode-option ${selectedOperationMode === mode.id ? "selected" : ""} ${running ? "running" : ""} ${!imported ? "missing" : ""} ${liveDisabled ? "disabled" : ""}`}
              >
                <input
                  type="radio"
                  name={`workflow-mode-${market}`}
                  value={mode.id}
                  checked={selectedOperationMode === mode.id}
                  disabled={liveDisabled}
                  title={liveDisabled ? t("workspace.liveDisabled") : undefined}
                  onChange={() => setSelectedOperationMode(mode.id)}
                />
                <span>{t(mode.labelKey as "operationModes.dryRun")}</span>
                {running ? <span className="pill tiny ok">{t("workflowPanel.running")}</span> : null}
                {!imported && workflow ? (
                  <span className="pill tiny warn">{t("workflowPanel.notImported")}</span>
                ) : null}
                {liveDisabled ? (
                  <span className="pill tiny muted">{t("workspace.liveDisabled")}</span>
                ) : null}
              </label>
            );
          })}
        </fieldset>

        <div className="workflow-multi-section">
          <label className="modal-field checkbox-field">
            <input
              type="checkbox"
              checked={multiAutomation}
              disabled={opBusy || killSwitch}
              onChange={(e) => {
                setOpError(null);
                setPendingOp({ kind: "multi_automation", enabled: e.target.checked });
              }}
            />
            <span>{t("workflowPanel.multiAutomationLabel")}</span>
            <span className="muted small block">
              {t("workflowPanel.multiAutomationHint", { max: String(maxPrimary) })}
            </span>
          </label>
          {multiAutomation && activePrimary.length > 0 ? (
            <ul className="workflow-active-list muted small">
              {activePrimary.map((wf) => (
                <li key={wf} className="workflow-active-row">
                  <span className="mono-small">{wf}</span>
                  <button
                    type="button"
                    className="tiny danger"
                    disabled={opBusy}
                    onClick={() => {
                      setOpError(null);
                      setPendingOp({ kind: "stop_one", workflow: wf });
                    }}
                  >
                    {t("workflowPanel.stopOne")}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>

        <div className="workflow-panel-actions">
          <button
            type="button"
            className={isRunning ? "primary workflow-running-btn" : "primary"}
            disabled={
              !selectedExists ||
              !selectedStrategyId ||
              (selectedOperationMode === "live" && !liveEnabled) ||
              opBusy ||
              killSwitch
            }
            onClick={() => {
              setOpError(null);
              const cfg = control?.workflow_session_config;
              const defaultCap =
                cfg?.session_capital ?? DEFAULT_SESSION_CAPITAL[market];
              setSessionCapitalInput(String(defaultCap));
              setSessionVolumeMode(
                cfg?.session_volume_mode ??
                  (cfg?.use_existing_holdings ? "existing_holdings" : "stablecoin"),
              );
              setHoldingsUnit(cfg?.existing_holdings_unit ?? "percent");
              setExistingHoldingsPctInput(String(cfg?.existing_holdings_use_pct ?? 100));
              setExistingHoldingsQtyInput(
                cfg?.existing_holdings_use_qty != null
                  ? String(cfg.existing_holdings_use_qty)
                  : "",
              );
              setLiquidateOnStop(Boolean(cfg?.liquidate_on_stop));
              setPendingOp({
                kind: "start",
                workflow: selectedWorkflow,
                strategyId: selectedStrategyId,
                operationMode: selectedOperationMode,
              });
            }}
          >
            {isRunning ? t("workflowPanel.restart") : multiAutomation && activePrimary.length > 0 ? t("workflowPanel.addWorkflow") : t("workflowPanel.start")}
          </button>
          <button
            type="button"
            className="tiny"
            disabled={reportsBusy}
            onClick={() => {
              void (async () => {
                setReportsBusy(true);
                try {
                  const list = await apiGet<{ items: Array<{ id: string }> }>(
                    `/api/workflow/reports?market=${market}&limit=1`,
                  );
                  const id = list.items?.[0]?.id;
                  if (!id) {
                    setTestMsg(t("workflowReport.none"));
                    return;
                  }
                  const full = await apiGet<WorkflowSessionReport>(`/api/workflow/reports/${id}`);
                  setSessionReport(full);
                } catch (err) {
                  report("workflow/reports", String(err));
                } finally {
                  setReportsBusy(false);
                }
              })();
            }}
          >
            {t("workflowReport.lastReport")}
          </button>
          <button
            type="button"
            className="danger"
            disabled={!activeWorkflow || opBusy}
            onClick={() => {
              setOpError(null);
              setPendingOp({ kind: "stop" });
            }}
          >
            {t("workflowPanel.stop")}
          </button>
        </div>

        {!activeWorkflow && !killSwitch ? (
          <p className="muted small">{t("workflowPanel.offHint")}</p>
        ) : null}
        {activeWorkflow && control?.workflow_started_at ? (
          <p className="muted small">
            {t("workflowPanel.uptime")}: {formatUptime(control.workflow_started_at)}
          </p>
        ) : activeWorkflow ? (
          <p className="muted small">{t("workflowPanel.uptime")}: {t("workflowPanel.uptimePending")}</p>
        ) : null}

        {activeWorkflow && control?.workflow_session_config ? (
          <div className="muted small workflow-session-config-summary">
            {control.workflow_session_config.session_volume_mode === "existing_holdings" ||
            control.workflow_session_config.use_existing_holdings ? (
              control.workflow_session_config.existing_holdings_unit === "absolute" ? (
                <p>
                  {t("workflowPanel.existingHoldingsQtyActive", {
                    qty: String(control.workflow_session_config.existing_holdings_use_qty ?? "—"),
                  })}
                </p>
              ) : (
                <p>
                  {t("workflowPanel.existingHoldingsActive", {
                    pct: String(control.workflow_session_config.existing_holdings_use_pct ?? 100),
                  })}
                </p>
              )
            ) : control.workflow_session_config.session_capital ? (
              <p>
                {t("workflowPanel.sessionCapitalActive", {
                  amount: String(control.workflow_session_config.session_capital),
                  currency: fiatLabel,
                })}
              </p>
            ) : null}
            {control.workflow_session_config.liquidate_on_stop ? (
              <p>
                {t("workflowPanel.liquidateOnStopActive", { currency: fiatLabel })}
                {isFutures ? ` · ${t("workflowPanel.liquidateFuturesNote")}` : null}
              </p>
            ) : null}
          </div>
        ) : null}

        {(scheduleData?.options?.length ?? 0) > 0 ? (
          <div className="workflow-schedule-row">
            <label className="muted small">{t("workflowPanel.scheduleLabel")}</label>
            <select
              value={scheduleOptionId}
              disabled={opBusy || !selectedWorkflow}
              onChange={(e) => {
                const optionId = e.target.value;
                setScheduleOptionId(optionId);
                setOpError(null);
                setPendingOp({ kind: "schedule", workflow: selectedWorkflow, optionId });
              }}
            >
              {(scheduleData?.options ?? []).map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {lang === "en" ? opt.label_en : opt.label_ru}
                </option>
              ))}
            </select>
          </div>
        ) : null}

        <div className="workflow-panel-actions" style={{ marginTop: "0.5rem" }}>
          <button
            type="button"
            className="tiny"
            disabled={!selectedExists || opBusy || killSwitch || selectedOperationMode === "dry_run"}
            title={selectedOperationMode === "dry_run" ? t("workflowPanel.testRunDryHint") : undefined}
            onClick={() => {
              setOpError(null);
              setTestMsg(null);
              setPendingOp({ kind: "test_run", workflow: selectedWorkflow });
            }}
          >
            {t("workflowPanel.testRun")}
          </button>
        </div>
        {testMsg ? <p className="muted small">{testMsg}</p> : null}

        {diagnostics ? (
          <div className="workflow-diagnostics muted small">
            <div>
              {t("workflowPanel.orders7d")}: {diagnostics.orders_executed ?? 0} / {diagnostics.orders_total ?? 0}
            </div>
            {diagnostics.last_signal?.event_at ? (
              <div>
                {t("workflowPanel.lastSignal")}: {String(diagnostics.last_signal.event_at).slice(0, 16)} ·{" "}
                {diagnostics.last_signal.symbol}
              </div>
            ) : null}
            {(diagnostics.hints ?? []).includes("moex_runs_once_daily_1815_weekdays") ? (
              <div className="warn-text">{t("workflowPanel.hintMoexDaily")}</div>
            ) : null}
          </div>
        ) : null}
      </PortfolioCard>

      <PortfolioCard title={t("strategySubsettings.title")}>
        <StrategySubsettingsPanel
          workflow={selectedWorkflow}
          market={market}
          onChange={() => {
            void handleUniverseChange();
            onSettingsChange?.();
          }}
        />
      </PortfolioCard>

      <OperatorConfirmModal
        open={pendingOp !== null}
        title={pendingTitle}
        lead={t("workflowsPage.operatorLead")}
        risk={pendingRisk}
        riskTone={pendingRiskTone}
        confirmLabel={pendingTitle}
        busy={opBusy}
        error={opError}
        onCancel={() => {
          if (!opBusy) {
            setPendingOp(null);
            setOpError(null);
          }
        }}
        onConfirm={runPendingOp}
      >
        {pendingOp?.kind === "start" ? (
          <>
            <fieldset className="modal-field session-volume-mode">
              <legend>{t("workflowPanel.sessionVolumeModeLabel")}</legend>
              <label className="checkbox-field">
                <input
                  type="radio"
                  name="session-volume-mode"
                  checked={sessionVolumeMode === "stablecoin"}
                  disabled={opBusy}
                  onChange={() => setSessionVolumeMode("stablecoin")}
                />
                <span>{t("workflowPanel.sessionVolumeStablecoin")}</span>
              </label>
              {market === "crypto" ? (
                <label className="checkbox-field">
                  <input
                    type="radio"
                    name="session-volume-mode"
                    checked={sessionVolumeMode === "existing_holdings"}
                    disabled={opBusy}
                    onChange={() => setSessionVolumeMode("existing_holdings")}
                  />
                  <span>{t("workflowPanel.sessionVolumeExisting")}</span>
                </label>
              ) : null}
            </fieldset>

            {sessionVolumeMode === "stablecoin" || market === "securities" ? (
              <label className="modal-field">
                <span>{t("workflowPanel.sessionCapitalLabel")}</span>
                <input
                  type="number"
                  className="input"
                  min={1}
                  step={market === "crypto" ? 100 : 1000}
                  value={sessionCapitalInput}
                  disabled={opBusy}
                  onChange={(e) => setSessionCapitalInput(e.target.value)}
                />
                <span className="muted small">
                  {t("workflowPanel.sessionCapitalHint", { currency: fiatLabel })}
                </span>
              </label>
            ) : (
              <>
                <fieldset className="modal-field session-volume-mode">
                  <legend>{t("workflowPanel.holdingsUnitLabel")}</legend>
                  <label className="checkbox-field">
                    <input
                      type="radio"
                      name="holdings-unit"
                      checked={holdingsUnit === "percent"}
                      disabled={opBusy}
                      onChange={() => setHoldingsUnit("percent")}
                    />
                    <span>{t("workflowPanel.holdingsUnitPercent")}</span>
                  </label>
                  <label className="checkbox-field">
                    <input
                      type="radio"
                      name="holdings-unit"
                      checked={holdingsUnit === "absolute"}
                      disabled={opBusy}
                      onChange={() => setHoldingsUnit("absolute")}
                    />
                    <span>{t("workflowPanel.holdingsUnitAbsolute")}</span>
                  </label>
                </fieldset>
                {holdingsUnit === "percent" ? (
                  <label className="modal-field">
                    <span>{t("workflowPanel.existingHoldingsPctLabel")}</span>
                    <input
                      type="number"
                      className="input"
                      min={1}
                      max={100}
                      step={1}
                      value={existingHoldingsPctInput}
                      disabled={opBusy}
                      onChange={(e) => setExistingHoldingsPctInput(e.target.value)}
                    />
                    <span className="muted small">{t("workflowPanel.existingHoldingsPctHint")}</span>
                  </label>
                ) : (
                  <label className="modal-field">
                    <span>{t("workflowPanel.existingHoldingsQtyLabel")}</span>
                    <input
                      type="number"
                      className="input"
                      min={0}
                      step="any"
                      value={existingHoldingsQtyInput}
                      disabled={opBusy}
                      onChange={(e) => setExistingHoldingsQtyInput(e.target.value)}
                    />
                    <span className="muted small">{t("workflowPanel.existingHoldingsQtyHint")}</span>
                  </label>
                )}
              </>
            )}

            {market === "crypto" ? (
              <label className="modal-field checkbox-field">
                <input
                  type="checkbox"
                  checked={liquidateOnStop}
                  disabled={opBusy}
                  onChange={(e) => setLiquidateOnStop(e.target.checked)}
                />
                <span>{t("workflowPanel.liquidateOnStopLabel")}</span>
                <span className="muted small block">
                  {isFutures
                    ? t("workflowPanel.liquidateOnStopHintFutures", { currency: fiatLabel })
                    : t("workflowPanel.liquidateOnStopHint", { currency: fiatLabel })}
                </span>
              </label>
            ) : null}
          </>
        ) : null}
      </OperatorConfirmModal>
      {detailStrategyId ? (
        <StrategyDetailModal strategyId={detailStrategyId} onClose={() => setDetailStrategyId(null)} />
      ) : null}
      <WorkflowSessionReportModal report={sessionReport} onClose={() => setSessionReport(null)} t={t} />
    </>
  );
}
