import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet } from "../api";
import PortfolioCard from "../components/PortfolioCard";
import { POLL } from "../config/polling";
import { useI18n } from "../i18n/LanguageContext";
import { usePolling } from "../hooks/usePolling";
import type { TradeEvent } from "../types";

export default function EventsPage() {
  const { t } = useI18n();
  const [market, setMarket] = useState("");
  const [env, setEnv] = useState("");
  const [stage, setStage] = useState("");
  const [selected, setSelected] = useState<TradeEvent | null>(null);
  const [detail, setDetail] = useState<TradeEvent | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetcher = useCallback(() => {
    const q = new URLSearchParams({ limit: "80" });
    if (market) q.set("market", market);
    if (env) q.set("env", env);
    if (stage) q.set("stage", stage);
    return apiGet<TradeEvent[]>(`/api/events?${q}`);
  }, [market, env, stage]);

  const { data: events, loading } = usePolling(fetcher, POLL.EVENTS, true, {
    errorSource: "GET /api/events",
    staggerKey: "events-list",
  });

  useEffect(() => {
    if (!selected?.id) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    apiGet<TradeEvent>(`/api/events/${selected.id}`)
      .then((row) => {
        if (!cancelled) setDetail(row);
      })
      .catch(() => {
        if (!cancelled) setDetail(selected);
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selected]);

  const view = detail ?? selected;
  const ctx = view?.context;

  return (
    <div className="page">
      <div className="page-title">
        <h2>{t("events.title")}</h2>
        <div className="toolbar-controls">
          <label>
            {t("events.market")}
            <select value={market} onChange={(e) => setMarket(e.target.value)}>
              <option value="">{t("common.all")}</option>
              <option value="crypto">crypto</option>
              <option value="securities">securities</option>
            </select>
          </label>
          <label>
            Env
            <select value={env} onChange={(e) => setEnv(e.target.value)}>
              <option value="">{t("common.all")}</option>
              <option value="dry_run">dry_run</option>
              <option value="paper">paper</option>
              <option value="live">live</option>
            </select>
          </label>
          <label>
            {t("events.stage")}
            <select value={stage} onChange={(e) => setStage(e.target.value)}>
              <option value="">{t("common.all")}</option>
              <option value="signal">signal</option>
              <option value="filter">filter</option>
              <option value="llm">llm</option>
              <option value="guardrails">guardrails</option>
              <option value="order">order</option>
              <option value="fill">fill</option>
            </select>
          </label>
        </div>
      </div>

      {loading && <p className="muted">{t("common.loading")}</p>}

      <div className="grid cards-2">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("events.time")}</th>
                <th>{t("events.market")}</th>
                <th>Env</th>
                <th>{t("events.stage")}</th>
                <th>{t("events.decision")}</th>
                <th>{t("events.symbol")}</th>
              </tr>
            </thead>
            <tbody>
              {(events ?? []).map((e) => (
                <tr
                  key={e.id}
                  className={selected?.id === e.id ? "row-selected" : "row-clickable"}
                  onClick={() => setSelected(e)}
                >
                  <td>{String(e.event_at).slice(0, 19)}</td>
                  <td>{e.market}</td>
                  <td>{e.env}</td>
                  <td>{e.stage}</td>
                  <td>{e.decision}</td>
                  <td>{e.symbol ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <PortfolioCard
          title={t("events.details")}
          status={view ? { label: view.stage, tone: "neutral" } : undefined}
        >
          {!view && <p className="muted">{t("events.clickRow")}</p>}
          {view && (
            <div className="detail-block">
              {detailLoading && <p className="muted small">{t("common.loading")}</p>}
              {view.summary && <p className="event-summary">{view.summary}</p>}
              {ctx?.explanation && (
                <div className="info-block" style={{ marginTop: "0.75rem" }}>
                  <strong>{t("events.explanation")}</strong>
                  <p>{ctx.explanation}</p>
                </div>
              )}
              <div className="muted small">id: {view.id}</div>
              <div>
                {view.stage} / {view.decision}
                {view.workflow_name ? ` · ${view.workflow_name}` : ""}
              </div>
              <div>
                {t("events.confidence")}: {view.confidence ?? "—"}
                {view.model ? ` · ${view.model}` : ""}
              </div>
              {view.reject_reason && (
                <div className="warn">
                  {t("events.rejectCode")}: {view.reject_reason}
                </div>
              )}
              {ctx?.llm_audit?.counter_thesis && (
                <div className="muted small" style={{ marginTop: "0.5rem" }}>
                  <strong>{t("events.counterThesis")}:</strong> {ctx.llm_audit.counter_thesis}
                </div>
              )}
              {ctx?.llm_audit?.raw_response && (
                <details className="small" style={{ marginTop: "0.5rem" }}>
                  <summary>{t("events.llmRaw")}</summary>
                  <pre className="mono-small">{ctx.llm_audit.raw_response}</pre>
                </details>
              )}
              {(ctx?.pipeline?.length ?? 0) > 1 && (
                <div style={{ marginTop: "0.75rem" }}>
                  <strong className="small">{t("events.pipeline")}</strong>
                  <ul className="muted small" style={{ margin: "0.35rem 0 0", paddingLeft: "1.1rem" }}>
                    {(ctx?.pipeline ?? []).map((step) => (
                      <li key={step.id}>
                        {step.stage} → {step.decision}
                        {step.reject_reason ? ` (${step.reject_reason})` : ""}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {(view.stage === "llm" || ctx?.llm_audit) && (
                <Link to="/llm" className="card-link">
                  {t("events.openLlm")}
                </Link>
              )}
            </div>
          )}
        </PortfolioCard>
      </div>
    </div>
  );
}
