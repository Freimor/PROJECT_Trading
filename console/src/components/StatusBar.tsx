import { useCallback, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { apiPost, formatOperatorFacingError } from "../api";
import OperatorConfirmModal from "./OperatorConfirmModal";
import { OllamaStatusMetrics } from "./OllamaStatusMetrics";
import { ollamaStripClass } from "../utils/ollamaHealth";
import { WorkflowSessionMetrics } from "./WorkflowSessionMetrics";
import { useErrorNotifications } from "../context/ErrorNotifications";
import { useI18n } from "../i18n/LanguageContext";
import Hint from "../ui/Hint";
import type { AutomationOverview } from "../types";

type Props = {
  overview: AutomationOverview | null;
  onRefresh?: () => void;
};

type WorkflowVisual = "off" | "demo" | "live";

function formatUptime(iso: string | undefined, t: (k: string, vars?: Record<string, string | number>) => string): string {
  if (!iso) return "—";
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) return "—";
  const sec = Math.max(0, Math.floor((Date.now() - parsed) / 1000));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  if (h > 0) return t("controlStrip.uptimeHours", { h, m });
  return t("controlStrip.uptimeMinutes", { m });
}

function workflowState(
  kill: boolean,
  block?: { operation_mode?: string; workflows_active?: boolean },
): WorkflowVisual {
  if (kill || block?.workflows_active === false) return "off";
  if (block?.operation_mode === "live") return "live";
  return "demo";
}

function workflowLabel(state: WorkflowVisual, t: (k: string) => string): string {
  if (state === "live") return t("controlStrip.workflowLive");
  if (state === "demo") return t("controlStrip.workflowDemo");
  return t("controlStrip.workflowOff");
}

export default function StatusBar({ overview, onRefresh }: Props) {
  const { t } = useI18n();
  const { report } = useErrorNotifications();
  const [busy, setBusy] = useState(false);
  const [killModal, setKillModal] = useState<"enable" | "disable" | null>(null);
  const [killError, setKillError] = useState<string | null>(null);

  const killOn = Boolean(overview?.kill_switch);
  const ollama = overview?.ollama;
  const cryptoInst = overview?.crypto?.automation_instances;
  const cryptoRunningCount = cryptoInst?.running_count ?? 0;
  const moexInst = overview?.securities?.automation_instances;
  const moexRunningCount = moexInst?.running_count ?? 0;
  const cryptoState = workflowState(killOn, overview?.crypto);
  const moexState = workflowState(killOn, overview?.securities);

  const cryptoUptimeFrom =
    cryptoRunningCount > 0
      ? cryptoInst?.earliest_started_at ?? overview?.crypto?.workflow_started_at
      : overview?.crypto?.workflow_started_at;

  const moexUptimeFrom =
    moexRunningCount > 0
      ? moexInst?.earliest_started_at ?? overview?.securities?.workflow_started_at
      : overview?.securities?.workflow_started_at;

  const moexSymbolsLabel = useMemo(() => {
    const syms = moexInst?.running_symbols ?? [];
    if (!syms.length) return null;
    return syms.join(", ");
  }, [moexInst?.running_symbols]);

  const cryptoSymbolsLabel = useMemo(() => {
    const syms = cryptoInst?.running_symbols ?? overview?.crypto?.pairs ?? [];
    if (!syms.length) return null;
    return syms.map((s) => String(s).replace("USDT", "")).join(", ");
  }, [cryptoInst?.running_symbols, overview?.crypto?.pairs]);

  const applyKill = useCallback(
    async (password: string) => {
      if (!killModal) return;
      const killEnabled = killModal === "disable";
      setBusy(true);
      setKillError(null);
      report("control/kill-switch", null);
      try {
        await apiPost(
          "/api/admin/kill-switch",
          {
            enabled: killEnabled,
            operator: "web:operator",
            source: "web",
          },
          { operatorPassword: password },
        );
        setKillModal(null);
        onRefresh?.();
      } catch (err) {
        const message = formatOperatorFacingError(err, t);
        setKillError(message);
        report("control/kill-switch", message);
      } finally {
        setBusy(false);
      }
    },
    [killModal, onRefresh, report, t],
  );

  return (
    <>
      <div className="control-strip" role="toolbar" aria-label={t("controlStrip.aria")}>
        <Hint label={killOn ? t("controlStrip.killActiveHint") : t("controlStrip.killButtonHint")}>
          <button
            type="button"
            className={`control-strip-kill ${killOn ? "active" : ""}`}
            disabled={busy}
            onClick={() => {
              setKillError(null);
              setKillModal(killOn ? "enable" : "disable");
            }}
          >
            {killOn ? t("controlStrip.killActive") : t("controlStrip.killButton")}
          </button>
        </Hint>

        <Hint label={t("controlStrip.cryptoWorkflowHint")}>
          <Link to="/crypto" className={`control-strip-workflow wf-${cryptoState}`}>
            <div className="control-strip-wf-body">
              <span className="control-strip-wf-title">{t("controlStrip.cryptoWorkflow")}</span>
              <span className="control-strip-wf-mode">
                {workflowLabel(cryptoState, t)}
                {cryptoInst?.has_instances && cryptoRunningCount > 0 ? (
                  <>
                    {" · "}
                    {t("controlStrip.cryptoInstancesRunning", { count: cryptoRunningCount })}
                  </>
                ) : cryptoInst?.has_instances && (cryptoInst.total_count ?? 0) > 0 ? (
                  <>
                    {" · "}
                    {t("controlStrip.cryptoInstancesIdle", { count: cryptoInst.total_count ?? 0 })}
                  </>
                ) : null}
              </span>
              {cryptoState !== "off" ? (
                <>
                  <span className="control-strip-wf-uptime">
                    {t("controlStrip.uptime")}: {formatUptime(cryptoUptimeFrom, t)}
                  </span>
                  {cryptoSymbolsLabel ? (
                    <span className="control-strip-wf-symbols muted small">{cryptoSymbolsLabel}</span>
                  ) : null}
                </>
              ) : cryptoInst?.has_instances && (cryptoInst.total_count ?? 0) > 0 ? (
                <span className="control-strip-wf-uptime muted small">
                  {t("controlStrip.cryptoInstancesIdle", { count: cryptoInst.total_count ?? 0 })}
                </span>
              ) : null}
            </div>
            {cryptoState !== "off" ? (
              <WorkflowSessionMetrics session={overview?.crypto?.workflow_session} t={t} />
            ) : null}
          </Link>
        </Hint>

        <Hint label={t("controlStrip.moexWorkflowHint")}>
          <Link to="/moex" className={`control-strip-workflow wf-${moexState}`}>
            <div className="control-strip-wf-body">
              <span className="control-strip-wf-title">{t("controlStrip.moexWorkflow")}</span>
              <span className="control-strip-wf-mode">
                {workflowLabel(moexState, t)}
                {moexInst?.has_instances && moexRunningCount > 0 ? (
                  <>
                    {" · "}
                    {t("controlStrip.cryptoInstancesRunning", { count: moexRunningCount })}
                  </>
                ) : moexInst?.has_instances && (moexInst.total_count ?? 0) > 0 ? (
                  <>
                    {" · "}
                    {t("controlStrip.cryptoInstancesIdle", { count: moexInst.total_count ?? 0 })}
                  </>
                ) : null}
              </span>
              {moexState !== "off" ? (
                <>
                  <span className="control-strip-wf-uptime">
                    {t("controlStrip.uptime")}: {formatUptime(moexUptimeFrom, t)}
                  </span>
                  {moexSymbolsLabel ? (
                    <span className="control-strip-wf-symbols muted small">{moexSymbolsLabel}</span>
                  ) : null}
                </>
              ) : moexInst?.has_instances && (moexInst.total_count ?? 0) > 0 ? (
                <span className="control-strip-wf-uptime muted small">
                  {t("controlStrip.cryptoInstancesIdle", { count: moexInst.total_count ?? 0 })}
                </span>
              ) : null}
            </div>
            {moexState !== "off" ? (
              <WorkflowSessionMetrics session={overview?.securities?.workflow_session} t={t} />
            ) : null}
          </Link>
        </Hint>

        <Hint
          label={
            ollama?.error
              ? `${t("controlStrip.ollamaHint")} — ${ollama.error}`
              : t("controlStrip.ollamaHint")
          }
        >
          <div className={`control-strip-ollama ${ollamaStripClass(ollama)}`}>
            <div className="control-strip-wf-body">
              <span className="control-strip-wf-title">Ollama</span>
              <span className="control-strip-wf-mode">{t("controlStrip.ollamaRole")}</span>
            </div>
            <OllamaStatusMetrics ollama={ollama} t={t} />
          </div>
        </Hint>
      </div>

      <OperatorConfirmModal
        open={killModal !== null}
        title={
          killModal === "enable" ? t("controlStrip.killEnableTitle") : t("controlStrip.killDisableTitle")
        }
        lead={killModal === "enable" ? t("controlStrip.killEnableLead") : t("controlStrip.killDisableLead")}
        risk={killModal === "enable" ? t("controlStrip.killEnableRisk") : t("controlStrip.killDisableRisk")}
        riskTone={killModal === "enable" ? "" : "danger"}
        confirmLabel={t("controlStrip.killConfirm")}
        busy={busy}
        error={killError}
        onCancel={() => !busy && setKillModal(null)}
        onConfirm={applyKill}
      />
    </>
  );
}
