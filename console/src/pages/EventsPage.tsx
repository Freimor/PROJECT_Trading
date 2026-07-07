import { useCallback, useState } from "react";
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
          status={selected ? { label: selected.stage, tone: "neutral" } : undefined}
        >
          {!selected && <p className="muted">{t("events.clickRow")}</p>}
          {selected && (
            <div className="detail-block">
              {selected.summary && <p className="event-summary">{selected.summary}</p>}
              <div className="muted small">id: {selected.id}</div>
              <div>
                {selected.stage} / {selected.decision}
              </div>
              <div>
                {t("events.confidence")}: {selected.confidence ?? "—"}
              </div>
              {selected.reject_reason && <div className="warn">{selected.reject_reason}</div>}
              {selected.stage === "llm" && (
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
