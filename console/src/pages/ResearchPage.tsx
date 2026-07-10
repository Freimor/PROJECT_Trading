import { useCallback, useState } from "react";
import { apiGet, apiPost } from "../api";
import PortfolioCard from "../components/PortfolioCard";
import { POLL } from "../config/polling";
import { useErrorNotifications } from "../context/ErrorNotifications";
import { useI18n } from "../i18n/LanguageContext";
import { usePolling } from "../hooks/usePolling";

type PaperCandidate = {
  id: string;
  source?: string;
  title?: string;
  summary?: string;
  published?: string;
  url?: string;
  relevance_score?: number;
  citation_count?: number | null;
  status?: string;
  discovered_at?: string;
  draft_path?: string | null;
};

type LeaderboardRow = {
  model?: string;
  avg_score?: number;
  runs?: number;
  passes?: number;
  fixture_pass_rate?: number | null;
  avg_latency_ms?: number | null;
};

type ModelRecommendation = {
  model?: string;
  fixture_pass_rate?: number;
  avg_latency_ms?: number;
  reason?: string;
};

type ResearchDashboard = {
  papers?: {
    pending_count?: number;
    approved_count?: number;
    by_source?: Record<string, number>;
    inbox_path?: string;
  };
  neuratrade?: {
    leaderboard?: LeaderboardRow[];
    recommended?: ModelRecommendation | null;
  };
};

type IngestResult = {
  new_count?: number;
  by_source?: Record<string, number>;
};

export default function ResearchPage() {
  const { t } = useI18n();
  const { report } = useErrorNotifications();
  const [statusFilter, setStatusFilter] = useState<"pending" | "all" | "approved" | "rejected">("pending");
  const [busy, setBusy] = useState(false);
  const [actionLog, setActionLog] = useState("");

  const fetchDashboard = useCallback(() => apiGet<ResearchDashboard>("/api/research/dashboard"), []);
  const { data: dashboard, refresh: refreshDashboard } = usePolling(fetchDashboard, POLL.OPS, true, {
    staggerKey: "research-dashboard",
  });

  const fetchCandidates = useCallback(
    () => apiGet<PaperCandidate[]>(`/api/papers/monitor/candidates?status=${statusFilter}&limit=50`),
    [statusFilter],
  );
  const { data: candidates, refresh: refreshCandidates } = usePolling(fetchCandidates, POLL.OPS, true, {
    staggerKey: "research-candidates",
  });

  const refreshAll = () => {
    refreshDashboard();
    refreshCandidates();
  };

  const runAction = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(true);
    report("research/action", null);
    setActionLog(`${label}…`);
    try {
      const result = await fn();
      setActionLog(JSON.stringify(result, null, 2));
      refreshAll();
    } catch (err) {
      report("research/action", String(err));
      setActionLog(String(err));
    } finally {
      setBusy(false);
    }
  };

  const approveDraft = (id: string) =>
    runAction(t("research.approveDraft"), () => apiPost(`/api/papers/monitor/${id}/draft`));

  const rejectCandidate = (id: string) =>
    runAction(t("research.reject"), () =>
      apiPost(`/api/papers/monitor/${id}/status`, { status: "rejected" }),
    );

  const list = candidates ?? [];
  const leaderboard = dashboard?.neuratrade?.leaderboard ?? [];
  const recommended = dashboard?.neuratrade?.recommended ?? null;

  return (
    <div className="page">
      <div className="page-title">
        <h2>{t("research.title")}</h2>
        <p className="muted">{t("research.subtitle")}</p>
      </div>

      <div className="grid cards-2">
        <PortfolioCard title={t("research.papersCard")} subtitle={dashboard?.papers?.inbox_path}>
          <div className="metric-row">
            <span>{t("research.pending")}</span>
            <strong>{dashboard?.papers?.pending_count ?? 0}</strong>
          </div>
          <div className="metric-row">
            <span>{t("research.approved")}</span>
            <strong>{dashboard?.papers?.approved_count ?? 0}</strong>
          </div>
          {dashboard?.papers?.by_source && (
            <pre className="small-pre">{JSON.stringify(dashboard.papers.by_source, null, 2)}</pre>
          )}
          <div className="btn-row" style={{ marginTop: "0.75rem" }}>
            <button type="button" disabled={busy} onClick={() => runAction(t("research.ingest"), () => apiPost<IngestResult>("/api/papers/monitor/ingest"))}>
              {t("research.ingest")}
            </button>
            <button type="button" disabled={busy} onClick={refreshAll}>
              {t("header.refresh")}
            </button>
          </div>
        </PortfolioCard>

        <PortfolioCard title={t("research.neuratradeCard")}>
          <p className="muted small">{t("research.neuratradeHint")}</p>
          {recommended?.model ? (
            <p className="small" style={{ marginBottom: "0.5rem" }}>
              {t("research.recommendedModel")}: <strong>{recommended.model}</strong>
              {recommended.fixture_pass_rate != null
                ? ` · ${t("research.fixturePassRate")} ${(recommended.fixture_pass_rate * 100).toFixed(0)}%`
                : ""}
            </p>
          ) : null}
          {leaderboard.length === 0 ? (
            <p className="muted">{t("research.noLeaderboard")}</p>
          ) : (
            <table className="simple-table">
              <thead>
                <tr>
                  <th>{t("research.model")}</th>
                  <th>{t("research.avgScore")}</th>
                  <th>{t("research.fixturePassRate")}</th>
                  <th>{t("research.latency")}</th>
                  <th>{t("research.runs")}</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((row) => (
                  <tr key={row.model}>
                    <td>{row.model}</td>
                    <td>{row.avg_score != null ? row.avg_score.toFixed(3) : "—"}</td>
                    <td>
                      {row.fixture_pass_rate != null ? `${(row.fixture_pass_rate * 100).toFixed(0)}%` : "—"}
                    </td>
                    <td>{row.avg_latency_ms != null ? `${row.avg_latency_ms} ms` : "—"}</td>
                    <td>{row.runs ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="btn-row" style={{ marginTop: "0.75rem" }}>
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                runAction(t("research.runHarness"), () => apiPost("/api/neuratrade/cycle", { equity: 10000, mode: "fixtures" }))
              }
            >
              {t("research.runHarness")}
            </button>
          </div>
        </PortfolioCard>
      </div>

      <PortfolioCard title={t("research.candidatesTitle")}>
        <div className="btn-row" style={{ marginBottom: "0.75rem" }}>
          {(["pending", "approved", "rejected", "all"] as const).map((s) => (
            <button
              key={s}
              type="button"
              className={statusFilter === s ? "active" : ""}
              onClick={() => setStatusFilter(s)}
            >
              {t(`research.filter.${s}`)}
            </button>
          ))}
        </div>

        {list.length === 0 ? (
          <p className="muted">{t("research.noCandidates")}</p>
        ) : (
          <div className="research-list">
            {list.map((c) => (
              <article key={c.id} className="research-item">
                <header>
                  <span className="badge">{c.source}</span>
                  {c.published && <span className="muted small">{c.published}</span>}
                  {c.citation_count != null && (
                    <span className="muted small">cite: {c.citation_count}</span>
                  )}
                  <span className="muted small">rel: {c.relevance_score ?? 0}</span>
                </header>
                <h4>
                  {c.url ? (
                    <a href={c.url} target="_blank" rel="noreferrer">
                      {c.title}
                    </a>
                  ) : (
                    c.title
                  )}
                </h4>
                {c.summary && (
                  <p className="muted small">
                    {c.summary.length > 280 ? `${c.summary.slice(0, 280)}…` : c.summary}
                  </p>
                )}
                {c.draft_path && (
                  <p className="small muted">
                    {t("research.draft")}: <code>{c.draft_path}</code>
                  </p>
                )}
                {c.status === "pending" && (
                  <div className="btn-row">
                    <button type="button" disabled={busy} onClick={() => approveDraft(c.id)}>
                      {t("research.approveDraft")}
                    </button>
                    <button type="button" disabled={busy} onClick={() => rejectCandidate(c.id)}>
                      {t("research.reject")}
                    </button>
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </PortfolioCard>

      {actionLog && (
        <PortfolioCard title={t("research.log")}>
          <pre className="small-pre">{actionLog}</pre>
        </PortfolioCard>
      )}

      <p className="muted small">{t("research.sourcesNote")}</p>
    </div>
  );
}
