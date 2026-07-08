import { useState } from "react";
import { apiGet, apiPost } from "../api";
import PortfolioCard from "../components/PortfolioCard";
import { POLL } from "../config/polling";
import { useErrorNotifications } from "../context/ErrorNotifications";
import { usePolling } from "../hooks/usePolling";
import { useI18n } from "../i18n/LanguageContext";

export default function ControlPage() {
  const { t } = useI18n();
  const [log, setLog] = useState("");
  const { report } = useErrorNotifications();

  const { data: control } = usePolling<{
    crypto?: { operation_mode?: string; trading_mode?: string };
    securities?: { operation_mode?: string; trading_mode?: string };
    trading_mode?: string;
  }>(() => apiGet("/api/automation/control"), POLL.OPS, true, {
    staggerKey: "automation-control",
  });

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

  const killSwitch = async (enabled: boolean) => {
    if (!confirm(t("control.killConfirm", { state: enabled ? "ON" : "OFF" }))) return;
    report("control/kill-switch", null);
    try {
      const r = await apiPost("/api/admin/kill-switch", {
        enabled,
        operator: "web:operator",
        source: "web",
      });
      setLog(JSON.stringify(r, null, 2));
    } catch (err) {
      report("control/kill-switch", String(err));
    }
  };

  const smoke = async () => {
    setLog("Running smoke test…");
    report("control/smoke", null);
    try {
      const r = await apiPost<{ output?: string }>("/api/admin/smoke-test");
      setLog(r.output || JSON.stringify(r, null, 2));
    } catch (err) {
      report("control/smoke", String(err));
    }
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

  const modeLabel = (op?: string) =>
    op === "live" ? t("workspace.modeLive") : t("workspace.modeDemo");

  return (
    <div className="page">
      <div className="page-title">
        <h2>{t("control.title")}</h2>
        <p className="muted">{t("control.subtitleRisk")}</p>
      </div>

      <PortfolioCard title={t("control.marketModesTitle")}>
        <p className="muted small">{t("control.marketModesHint")}</p>
        <div className="metric-row">
          <span>Crypto</span>
          <strong>{modeLabel(control?.crypto?.operation_mode)}</strong>
        </div>
        <div className="metric-row">
          <span>MOEX</span>
          <strong>{modeLabel(control?.securities?.operation_mode)}</strong>
        </div>
        {control?.trading_mode === "mixed" && (
          <p className="muted small">{t("control.mixedModes")}</p>
        )}
      </PortfolioCard>

      <div className="grid cards-2">
        <PortfolioCard title={t("control.riskTitle")}>
          <div className="btn-row">
            <button type="button" className="danger" onClick={() => killSwitch(true)}>
              Kill ON
            </button>
            <button type="button" className="primary" onClick={() => killSwitch(false)}>
              Kill OFF
            </button>
            <button type="button" onClick={smoke}>
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
