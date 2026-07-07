import { useI18n } from "../i18n/LanguageContext";
import type { AutomationOverview } from "../types";

type Props = {
  overview: AutomationOverview | null;
};

export default function StatusBar({ overview }: Props) {
  const { t } = useI18n();
  const last = overview?.last_event;
  const ollama = overview?.ollama;

  return (
    <div className="status-bar">
      <div className="status-item">
        <span className="status-label">{t("status.kill")}</span>
        <span className={overview?.kill_switch ? "pill danger" : "pill ok"}>
          {overview?.kill_switch ? "ON" : "OFF"}
        </span>
      </div>
      <div className="status-item">
        <span className="status-label">{t("status.mode")}</span>
        <span className="pill">{overview?.trading_mode ?? "—"}</span>
      </div>
      <div className="status-item">
        <span className="status-label">{t("status.live")}</span>
        <span className={overview?.live_flag ? "pill warn" : "pill"}>
          {overview?.live_flag ? "enabled" : "off"}
        </span>
      </div>
      <div className="status-item">
        <span className="status-label">{t("status.ollama")}</span>
        <span className={`pill ${ollama?.status === "ok" ? "ok" : "warn"}`}>
          {ollama?.status ?? "—"} {ollama?.latency_ms != null ? `(${ollama.latency_ms}ms)` : ""}
        </span>
      </div>
      <div className="status-item status-last">
        <span className="status-label">{t("status.last")}</span>
        <span className="status-value">
          {last
            ? `${String(last.event_at).slice(0, 16)} · ${last.workflow_name ?? "?"} · ${last.stage}/${last.decision} · ${last.symbol ?? ""}`
            : "—"}
        </span>
      </div>
    </div>
  );
}
