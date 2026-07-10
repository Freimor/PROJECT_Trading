import { useCallback, useState } from "react";
import { apiGet, apiPost, formatOperatorFacingError } from "../api";
import ModeChangeConfirmModal from "./ModeChangeConfirmModal";
import PortfolioCard from "./PortfolioCard";
import StatusDot from "./StatusDot";
import { POLL } from "../config/polling";
import { useErrorNotifications } from "../context/ErrorNotifications";
import { useI18n } from "../i18n/LanguageContext";
import { usePolling } from "../hooks/usePolling";

type Market = "crypto" | "securities";
type TargetMode = "demo" | "live";

type MarketControl = {
  market?: string;
  operation_mode?: string;
  operation_detail?: string;
  trading_mode?: string;
  live_flag?: boolean;
  workflows?: Array<{ id: string; name: string; active: boolean }>;
  n8n?: { status?: string; message?: string };
};

type Props = {
  market: Market;
  title: string;
  variant?: "card" | "toolbar";
  onModeApplied?: () => void;
};

export default function MarketOperationMode({
  market,
  title,
  variant = "toolbar",
  onModeApplied,
}: Props) {
  const { t } = useI18n();
  const { report } = useErrorNotifications();
  const [busy, setBusy] = useState(false);
  const [pendingMode, setPendingMode] = useState<TargetMode | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);

  const { data, refresh } = usePolling<MarketControl>(
    () => apiGet(`/api/automation/control/${market}`),
    POLL.OPS,
    true,
    { staggerKey: `market-mode-${market}` },
  );

  const current = data?.operation_mode ?? "demo";

  const applyMode = useCallback(
    async (mode: TargetMode, password: string) => {
      setBusy(true);
      setModalError(null);
      report(`workspace/mode-${market}`, null);
      try {
        await apiPost(
          `/api/admin/markets/${market}/mode`,
          {
            mode,
            operator: "web:operator",
            apply_workflows: true,
          },
          { operatorPassword: password },
        );
        setPendingMode(null);
        refresh();
        onModeApplied?.();
      } catch (err) {
        const message = formatOperatorFacingError(err, t);
        setModalError(message);
        report(`workspace/mode-${market}`, message);
      } finally {
        setBusy(false);
      }
    },
    [market, onModeApplied, refresh, report],
  );

  const requestMode = useCallback(
    (mode: TargetMode) => {
      if (mode === current) return;
      if (mode === "live" && !data?.live_flag) return;
      setModalError(null);
      setPendingMode(mode);
    },
    [current, data?.live_flag],
  );

  const modeLabel = t(`workspace.mode${current === "live" ? "Live" : "Demo"}` as "workspace.modeDemo");

  const controls = (
    <div className={`market-mode-controls ${variant}`}>
      <span className="market-mode-label">{t("workspace.operationMode")}</span>
      <span className="pill">{modeLabel}</span>
      <button
        type="button"
        disabled={busy}
        className={current === "demo" ? "primary tiny" : "tiny"}
        onClick={() => requestMode("demo")}
      >
        {t("workspace.modeDemo")}
      </button>
      <button
        type="button"
        disabled={busy || !data?.live_flag}
        className={current === "live" ? "primary danger tiny" : "danger tiny"}
        onClick={() => requestMode("live")}
        title={!data?.live_flag ? t("workspace.liveDisabled") : undefined}
      >
        {t("workspace.modeLive")}
      </button>
    </div>
  );

  const modal = (
    <ModeChangeConfirmModal
      open={pendingMode !== null}
      marketTitle={title}
      targetMode={pendingMode ?? "demo"}
      busy={busy}
      error={modalError}
      onCancel={() => {
        if (!busy) {
          setPendingMode(null);
          setModalError(null);
        }
      }}
      onConfirm={(password) => {
        if (pendingMode) applyMode(pendingMode, password);
      }}
    />
  );

  if (variant === "toolbar") {
    return (
      <>
        <div className="market-mode-toolbar" aria-label={t("workspace.operationMode")}>
          {controls}
          {data?.workflows?.length ? (
            <div className="market-mode-workflows muted small">
              {data.workflows.map((wf) => (
                <span key={wf.id} className="market-mode-wf">
                  <StatusDot tone={wf.active ? "ok" : "off"} />
                  {wf.name}
                </span>
              ))}
            </div>
          ) : null}
        </div>
        {modal}
      </>
    );
  }

  return (
    <>
      <PortfolioCard title={t("workspace.operationMode")} subtitle={title}>
        {controls}
        {data?.workflows?.length ? (
          <ul className="event-list" style={{ marginTop: "0.75rem" }}>
            {data.workflows.map((wf) => (
              <li key={wf.id}>
                <StatusDot tone={wf.active ? "ok" : "off"} />
                <span className="mono-small">{wf.name}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </PortfolioCard>
      {modal}
    </>
  );
}
