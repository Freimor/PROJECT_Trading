import { useEffect, useMemo, useState } from "react";
import { apiGet } from "../api";
import { AUX_WORKFLOW_META } from "../config/auxWorkflows";
import PortfolioCard from "../components/PortfolioCard";
import StatusDot from "../components/StatusDot";
import { POLL } from "../config/polling";
import { useErrorNotifications } from "../context/ErrorNotifications";
import { useI18n } from "../i18n/LanguageContext";
import { usePolling } from "../hooks/usePolling";

type Workflow = { id: string; name: string; active: boolean };

type MarketControl = {
  operation_mode?: string;
  trading_mode?: string;
  workflows?: Workflow[];
  n8n?: { status?: string; message?: string };
};

type ControlState = {
  crypto?: MarketControl;
  securities?: MarketControl;
};

const CRYPTO_NAMES = new Set([
  "crypto-signal-dry-run",
  "crypto-signal-paper",
  "crypto-monitor-testnet",
  "crypto-scalp-hybrid-dry-run",
  "crypto-scalp-hybrid-paper",
  "crypto-execute-testnet",
]);

const SECURITIES_NAMES = new Set([
  "securities-swing-dry-run",
  "securities-swing-paper",
  "securities-dca-sandbox",
  "securities-factor-sleeve",
  "bond-ladder-flow",
]);

export default function WorkflowsPage() {
  const { t } = useI18n();
  const { report } = useErrorNotifications();

  const { data } = usePolling<{ status: string; workflows?: Workflow[]; message?: string }>(
    () => apiGet("/api/n8n/workflows"),
    POLL.OPS,
    true,
    {
      errorSource: "GET /api/n8n/workflows",
      staggerKey: "n8n-workflows",
    },
  );

  const { data: control } = usePolling<ControlState>(
    () => apiGet("/api/automation/control"),
    POLL.OPS,
    true,
    { staggerKey: "n8n-control" },
  );

  useEffect(() => {
    if (data?.status === "error" && data.message) {
      report("GET /api/n8n/workflows", data.message);
    } else if (data?.status !== "error") {
      report("GET /api/n8n/workflows", null);
    }
  }, [data, report]);

  const workflows = data?.workflows ?? [];

  const grouped = useMemo(() => {
    const crypto: Workflow[] = [];
    const securities: Workflow[] = [];
    const other: Workflow[] = [];
    for (const wf of workflows) {
      if (CRYPTO_NAMES.has(wf.name)) crypto.push(wf);
      else if (SECURITIES_NAMES.has(wf.name)) securities.push(wf);
      else other.push(wf);
    }
    return { crypto, securities, other };
  }, [workflows]);

  const renderTradingList = (items: Workflow[]) => (
    <ul className="workflow-status-list">
      {items.map((wf) => (
        <li key={wf.id}>
          <StatusDot tone={wf.active ? "ok" : "off"} />
          <span className="mono-small">{wf.name}</span>
          <span className={`pill tiny ${wf.active ? "ok" : ""}`}>
            {wf.active ? t("workflowPanel.running") : t("workflowPanel.stopped")}
          </span>
        </li>
      ))}
    </ul>
  );

  const renderOtherList = (items: Workflow[]) => (
    <ul className="workflow-other-list">
      {items.map((wf) => {
        const meta = AUX_WORKFLOW_META[wf.name];
        return (
          <li key={wf.id} className="workflow-other-item">
            <div className="workflow-other-head">
              <StatusDot tone={wf.active ? "ok" : "off"} />
              <span className="mono-small">{wf.name}</span>
              <span className={`pill tiny ${wf.active ? "ok" : ""}`}>
                {wf.active ? t("workflowPanel.running") : t("workflowPanel.stopped")}
              </span>
            </div>
            {meta ? (
              <div className="workflow-other-meta muted small">
                <div>
                  <strong>{t("workflowsPage.otherSchedule")}:</strong> {t(meta.scheduleKey)}
                </div>
                <div>
                  <strong>{t("workflowsPage.otherPurpose")}:</strong> {t(meta.purposeKey)}
                </div>
              </div>
            ) : (
              <p className="muted small">{t("workflowsPage.otherManual")}</p>
            )}
          </li>
        );
      })}
    </ul>
  );

  if (data?.status === "error") {
    return (
      <div className="page">
        <h2>{t("workflowsPage.title")}</h2>
        <p className="muted">{t("workflowsPage.n8nSetup")}</p>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-title">
        <h2>{t("workflowsPage.title")}</h2>
        <p className="muted">{t("workflowsPage.subtitleTechnical")}</p>
      </div>

      <div className="workflow-alert">
        <p className="small">{t("workflowsPage.manageOnMarkets")}</p>
      </div>

      <PortfolioCard title={t("workflowsPage.groupCrypto")}>
        <p className="muted small">
          {t("workflowsPage.modeLine", {
            mode: control?.crypto?.operation_mode ?? "—",
            trading: control?.crypto?.trading_mode ?? "—",
          })}
        </p>
        <p className="muted small">{t("workflowsPage.cryptoSyncHint")}</p>
        {grouped.crypto.length ? renderTradingList(grouped.crypto) : (
          <p className="muted">{t("control.noWorkflows")}</p>
        )}
      </PortfolioCard>

      <PortfolioCard title={t("workflowsPage.groupMoex")}>
        <p className="muted small">
          {t("workflowsPage.modeLine", {
            mode: control?.securities?.operation_mode ?? "—",
            trading: control?.securities?.trading_mode ?? "—",
          })}
        </p>
        <p className="muted small">{t("workflowsPage.moexSyncHint")}</p>
        {grouped.securities.length ? renderTradingList(grouped.securities) : (
          <p className="muted">{t("control.noWorkflows")}</p>
        )}
      </PortfolioCard>

      {grouped.other.length ? (
        <PortfolioCard title={t("workflowsPage.groupOther")}>
          <p className="muted small">{t("workflowsPage.otherIntro")}</p>
          {renderOtherList(grouped.other)}
        </PortfolioCard>
      ) : null}
    </div>
  );
}
