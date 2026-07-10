import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { apiPost, formatOperatorFacingError } from "../api";
import OperatorConfirmModal from "./OperatorConfirmModal";
import { useErrorNotifications } from "../context/ErrorNotifications";
import { useI18n } from "../i18n/LanguageContext";
import type { AutomationOverview } from "../types";

type Props = {
  overview: AutomationOverview | null;
  onRefresh?: () => void;
};

type WorkflowVisual = "off" | "demo" | "live";

function formatUptime(iso?: string): string {
  if (!iso) return "—";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "—";
  const sec = Math.max(0, Math.floor((Date.now() - t) / 1000));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  if (h > 0) return `${h}ч ${m}м`;
  return `${m}м`;
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

function formatPnl(pnl?: { pnl_pct?: number | null; direction?: string } | null) {
  if (pnl?.pnl_pct == null || Number.isNaN(pnl.pnl_pct)) return null;
  const sign = pnl.pnl_pct > 0 ? "+" : "";
  const direction = pnl.direction === "up" ? "up" : pnl.direction === "down" ? "down" : "flat";
  return { text: `${sign}${pnl.pnl_pct.toFixed(1)}%`, direction };
}

export default function StatusBar({ overview, onRefresh }: Props) {
  const { t } = useI18n();
  const { report } = useErrorNotifications();
  const [busy, setBusy] = useState(false);
  const [killModal, setKillModal] = useState<"enable" | "disable" | null>(null);
  const [killError, setKillError] = useState<string | null>(null);

  const killOn = Boolean(overview?.kill_switch);
  const ollama = overview?.ollama;
  const cryptoState = workflowState(killOn, overview?.crypto);
  const moexState = workflowState(killOn, overview?.securities);
  const cryptoPnl = cryptoState !== "off" ? formatPnl(overview?.crypto?.workflow_pnl) : null;
  const moexPnl = moexState !== "off" ? formatPnl(overview?.securities?.workflow_pnl) : null;

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
    [killModal, onRefresh, report],
  );

  return (
    <>
      <div className="control-strip" role="toolbar" aria-label={t("controlStrip.aria")}>
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

        <Link to="/crypto" className={`control-strip-workflow wf-${cryptoState}`}>
          <div className="control-strip-wf-body">
            <span className="control-strip-wf-title">{t("controlStrip.cryptoWorkflow")}</span>
            <span className="control-strip-wf-mode">{workflowLabel(cryptoState, t)}</span>
            <span className="control-strip-wf-uptime">
              {t("controlStrip.uptime")}: {formatUptime(
                overview?.crypto?.workflow_started_at ?? overview?.crypto?.mode_updated_at,
              )}
            </span>
          </div>
          {cryptoPnl ? (
            <span className={`control-strip-wf-pnl pnl-${cryptoPnl.direction}`} aria-label="PNL">
              {cryptoPnl.text}
            </span>
          ) : null}
        </Link>

        <Link to="/moex" className={`control-strip-workflow wf-${moexState}`}>
          <div className="control-strip-wf-body">
            <span className="control-strip-wf-title">{t("controlStrip.moexWorkflow")}</span>
            <span className="control-strip-wf-mode">{workflowLabel(moexState, t)}</span>
            <span className="control-strip-wf-uptime">
              {t("controlStrip.uptime")}: {formatUptime(
                overview?.securities?.workflow_started_at ?? overview?.securities?.mode_updated_at,
              )}
            </span>
          </div>
          {moexPnl ? (
            <span className={`control-strip-wf-pnl pnl-${moexPnl.direction}`} aria-label="PNL">
              {moexPnl.text}
            </span>
          ) : null}
        </Link>

        <div className={`control-strip-ollama ${ollama?.status === "ok" ? "ok" : "warn"}`}>
          <span className="control-strip-wf-title">Ollama</span>
          <span className="control-strip-wf-mode">
            {ollama?.status ?? "—"}
            {ollama?.latency_ms != null ? ` · ${ollama.latency_ms} ms` : ""}
          </span>
          {ollama?.model ? (
            <span className="control-strip-wf-uptime mono-small">{ollama.model}</span>
          ) : null}
        </div>
      </div>

      <OperatorConfirmModal
        open={killModal !== null}
        title={
          killModal === "enable"
            ? t("controlStrip.killEnableTitle")
            : t("controlStrip.killDisableTitle")
        }
        lead={
          killModal === "enable"
            ? t("controlStrip.killEnableLead")
            : t("controlStrip.killDisableLead")
        }
        risk={
          killModal === "enable"
            ? t("controlStrip.killEnableRisk")
            : t("controlStrip.killDisableRisk")
        }
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
