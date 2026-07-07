import { useState } from "react";
import { apiGet, apiPost } from "../api";
import PortfolioCard from "../components/PortfolioCard";
import StatusDot from "../components/StatusDot";
import { POLL } from "../config/polling";
import { useErrorNotifications } from "../context/ErrorNotifications";
import { usePolling } from "../hooks/usePolling";
import { useI18n } from "../i18n/LanguageContext";

type ControlWorkflow = {
  id: string;
  name: string;
  active: boolean;
  expected_for_mode: boolean;
};

type AutomationControl = {
  trading_mode?: string;
  yaml_trading_mode?: string;
  runtime_override?: boolean;
  valid_modes?: string[];
  live_flag?: boolean;
  schedules?: {
    crypto?: { interval?: string; pairs?: string[]; summary_ru?: string; summary_en?: string };
    securities_swing?: { cron?: string; universe?: string[]; summary_ru?: string; summary_en?: string };
  };
  workflows?: ControlWorkflow[];
  n8n?: { status?: string; message?: string };
};

const MODES = ["dry_run", "paper", "shadow", "live"] as const;

export default function ControlPage() {
  const { t } = useI18n();
  const [log, setLog] = useState("");
  const [busy, setBusy] = useState(false);
  const { report } = useErrorNotifications();

  const { data: control, refresh: refreshControl } = usePolling<AutomationControl>(
    () => apiGet("/api/automation/control"),
    POLL.OPS,
    true,
    { staggerKey: "automation-control" },
  );

  const { data: checklist, refresh: refreshChecklist } = usePolling<{
    ready_for_live?: boolean;
    checks?: Record<string, boolean>;
  }>(() => apiGet("/api/live/checklist"), POLL.OPS, true, {
    staggerKey: "control-checklist",
  });

  const { data: pending, refresh: refreshPending } = usePolling<
    Array<{ id: string; title: string; action_type: string }>
  >(() => apiGet("/api/admin/confirmations/pending"), POLL.PENDING, true, {
    staggerKey: "control-pending",
  });

  const run = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(true);
    report("control/action", null);
    setLog(`${label}…`);
    try {
      const r = await fn();
      setLog(JSON.stringify(r, null, 2));
      refreshControl();
      refreshChecklist();
    } catch (err) {
      report("control/action", String(err));
    } finally {
      setBusy(false);
    }
  };

  const killSwitch = async (enabled: boolean) => {
    if (!confirm(t("control.killConfirm", { state: enabled ? "ON" : "OFF" }))) return;
    await run("kill-switch", () =>
      apiPost("/api/admin/kill-switch", {
        enabled,
        operator: "web:operator",
        source: "web",
      }),
    );
  };

  const setMode = async (mode: string) => {
    if (mode === "live" && !confirm(t("control.liveConfirm"))) return;
    if (!confirm(t("control.modeConfirm", { mode }))) return;
    await run(`mode:${mode}`, () =>
      apiPost("/api/admin/trading-mode", {
        mode,
        operator: "web:operator",
        apply_workflows: true,
      }),
    );
  };

  const resetMode = async () => {
    if (!confirm(t("control.resetModeConfirm"))) return;
    await run("reset-mode", () => apiPost("/api/admin/trading-mode/reset"));
  };

  const toggleWorkflow = async (wf: ControlWorkflow) => {
    await run(`wf:${wf.name}`, () =>
      apiPost(`/api/admin/workflows/${encodeURIComponent(wf.name)}/toggle`, {
        active: !wf.active,
        operator: "web:operator",
      }),
    );
  };

  const smoke = async () => {
    await run("smoke", () => apiPost("/api/admin/smoke-test"));
  };

  const resolve = async (id: string, decision: string) => {
    report("control/confirm", null);
    try {
      await apiPost(`/api/admin/confirmations/${id}/resolve`, {
        decision,
        operator: "web:operator",
      });
      refreshPending();
      refreshChecklist();
    } catch (err) {
      report("control/confirm", String(err));
    }
  };

  const currentMode = control?.trading_mode ?? "—";
  const cryptoSchedule = control?.schedules?.crypto;
  const swingSchedule = control?.schedules?.securities_swing;

  return (
    <div className="page">
      <div className="page-title">
        <h2>{t("control.title")}</h2>
        <p className="muted">{t("control.subtitle")}</p>
      </div>

      <div className="grid cards-2">
        <PortfolioCard
          title={t("control.modeTitle")}
          subtitle={
            control?.runtime_override
              ? t("control.runtimeOverride", { yaml: control.yaml_trading_mode ?? "—" })
              : t("control.fromYaml")
          }
        >
          <div className="metric-row">
            <span>{t("control.currentMode")}</span>
            <strong>{currentMode}</strong>
          </div>
          <div className="btn-row" style={{ marginTop: "0.75rem" }}>
            {MODES.map((mode) => (
              <button
                key={mode}
                type="button"
                disabled={busy || (mode === "live" && !control?.live_flag)}
                className={currentMode === mode ? "primary" : ""}
                onClick={() => setMode(mode)}
                title={mode === "live" && !control?.live_flag ? t("control.liveDisabled") : undefined}
              >
                {mode}
              </button>
            ))}
          </div>
          <div className="btn-row" style={{ marginTop: "0.5rem" }}>
            <button type="button" disabled={busy || !control?.runtime_override} onClick={resetMode}>
              {t("control.resetYaml")}
            </button>
          </div>
        </PortfolioCard>

        <PortfolioCard title={t("control.llmSchedule")}>
          <div className="metric-row">
            <span>Crypto</span>
            <strong>{cryptoSchedule?.interval ?? "4h"}</strong>
          </div>
          <p className="muted small">
            {t("control.cryptoSchedule", {
              pairs: (cryptoSchedule?.pairs ?? ["BTCUSDT", "ETHUSDT"]).join(", "),
            })}
          </p>
          <div className="metric-row" style={{ marginTop: "0.75rem" }}>
            <span>MOEX swing</span>
            <strong>{swingSchedule?.cron ?? "15 18 * * 1-5"}</strong>
          </div>
          <p className="muted small">
            {t("control.moexSchedule", {
              tickers: (swingSchedule?.universe ?? ["SBER"]).join(", "),
            })}
          </p>
        </PortfolioCard>
      </div>

      <PortfolioCard
        title={t("control.automationsTitle")}
        subtitle={
          control?.n8n?.status === "error"
            ? control.n8n.message
            : t("control.automationsHint")
        }
      >
        {!control?.workflows?.length ? (
          <p className="muted">{t("control.noWorkflows")}</p>
        ) : (
          <div className="workflow-list compact">
            {control.workflows.map((wf) => (
              <div key={wf.id} className="confirm-row">
                <div>
                  <strong>{wf.name}</strong>
                  <div className="muted" style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                    <StatusDot tone={wf.active ? "ok" : "off"} />
                    {wf.active ? t("common.statusOn") : t("common.statusOff")}
                    {wf.expected_for_mode ? ` · ${t("control.expectedForMode")}` : ""}
                  </div>
                </div>
                <button type="button" disabled={busy} onClick={() => toggleWorkflow(wf)}>
                  {wf.active ? t("control.deactivate") : t("control.activate")}
                </button>
              </div>
            ))}
          </div>
        )}
      </PortfolioCard>

      <div className="grid cards-2">
        <PortfolioCard title={t("control.riskTitle")}>
          <div className="btn-row">
            <button type="button" className="danger" disabled={busy} onClick={() => killSwitch(true)}>
              Kill ON
            </button>
            <button type="button" className="primary" disabled={busy} onClick={() => killSwitch(false)}>
              Kill OFF
            </button>
            <button type="button" disabled={busy} onClick={smoke}>
              Smoke test
            </button>
          </div>
        </PortfolioCard>

        <PortfolioCard
          title={t("control.checklistTitle")}
          subtitle={checklist?.ready_for_live ? "READY" : "NOT READY"}
        >
          <ul className="checklist">
            {Object.entries(checklist?.checks ?? {}).map(([k, v]) => (
              <li key={k} className={v ? "ok" : "warn"}>
                {v ? "✓" : "✗"} {k}
              </li>
            ))}
          </ul>
        </PortfolioCard>
      </div>

      {pending && pending.length > 0 && (
        <PortfolioCard title={t("control.pendingTitle")}>
          {pending.map((p) => (
            <div key={p.id} className="confirm-row">
              <div>
                <strong>{p.title}</strong>
                <div className="muted">{p.action_type}</div>
              </div>
              <div className="btn-row">
                <button type="button" onClick={() => resolve(p.id, "approved")}>
                  Approve
                </button>
                <button type="button" onClick={() => resolve(p.id, "rejected")}>
                  Reject
                </button>
              </div>
            </div>
          ))}
        </PortfolioCard>
      )}

      {log && (
        <PortfolioCard title={t("control.output")}>
          <pre>{log}</pre>
        </PortfolioCard>
      )}
    </div>
  );
}
