import { useEffect, useMemo, useState } from "react";
import { apiGet } from "../api";
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
]);

const SECURITIES_NAMES = new Set([
  "securities-swing-dry-run",
  "securities-swing-paper",
  "securities-dca-sandbox",
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

  const renderList = (items: Workflow[]) => (
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
        {grouped.crypto.length ? renderList(grouped.crypto) : (
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
        {grouped.securities.length ? renderList(grouped.securities) : (
          <p className="muted">{t("control.noWorkflows")}</p>
        )}
      </PortfolioCard>

      {grouped.other.length ? (
        <PortfolioCard title={t("workflowsPage.groupOther")}>{renderList(grouped.other)}</PortfolioCard>
      ) : null}
    </div>
  );
}
