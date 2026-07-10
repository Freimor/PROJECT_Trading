import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost } from "../api";
import PortfolioCard from "../components/PortfolioCard";
import { POLL } from "../config/polling";
import { useErrorNotifications } from "../context/ErrorNotifications";
import { usePolling } from "../hooks/usePolling";
import { useI18n } from "../i18n/LanguageContext";
import Hint from "../ui/Hint";
import type { TradeEvent } from "../types";

const PIPELINE_STAGES = ["signal", "filter", "llm", "guardrails", "risk", "order", "fill"] as const;

function formatEventTime(iso: string, locale: string): string {
  try {
    const normalized = iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`;
    const d = new Date(normalized);
    return d.toLocaleString(locale, {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso.slice(0, 16);
  }
}

function stageTone(stage: string, decision?: string): string {
  if (stage === "filter" && decision === "approve") return "ok";
  if (stage === "llm" && decision === "approve") return "ok";
  if (decision === "reject" || decision === "skip") return "warn";
  return "";
}

export default function LlmAuditPage() {
  const { t, lang } = useI18n();
  const locale = lang === "en" ? "en-US" : "ru-RU";
  const [market, setMarket] = useState("");
  const [stage, setStage] = useState("");
  const [action, setAction] = useState("");
  const [selected, setSelected] = useState<TradeEvent | null>(null);
  const [detail, setDetail] = useState<TradeEvent | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [replay, setReplay] = useState<Record<string, unknown> | null>(null);
  const [replayBusy, setReplayBusy] = useState(false);
  const { report } = useErrorNotifications();

  const fetcher = useCallback(() => {
    const q = new URLSearchParams({
      limit: "100",
      days: "365",
      stages: PIPELINE_STAGES.join(","),
    });
    if (market) q.set("market", market);
    if (stage) q.set("stage", stage);
    if (action) q.set("decision", action);
    return apiGet<TradeEvent[]>(`/api/events?${q}`);
  }, [market, stage, action]);

  const { data: events, loading } = usePolling(fetcher, POLL.EVENTS, true, {
    errorSource: "GET /api/events?pipeline",
    staggerKey: "llm-audit",
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

  const selectRow = (row: TradeEvent) => {
    setSelected(row);
    setReplay(null);
  };

  const view = detail ?? selected;
  const ctx = view?.context;
  const canReplay = view?.stage === "llm" && Boolean(view?.inputs_hash);

  const runReplay = async () => {
    if (!view?.inputs_hash) return;
    setReplayBusy(true);
    report("POST /api/evaluation/replay", null);
    setReplay(null);
    try {
      const r = await apiPost<Record<string, unknown>>(
        "/api/evaluation/replay",
        { inputs_hash: view.inputs_hash },
        { timeoutMs: 600_000 },
      );
      setReplay(r);
    } catch (err) {
      report("POST /api/evaluation/replay", String(err));
    } finally {
      setReplayBusy(false);
    }
  };

  const replayChanged = Boolean(replay?.changed);

  return (
    <div className="page llm-audit-page">
      <div className="page-title">
        <h2>{t("llmAudit.title")}</h2>
        <p className="muted">{t("llmAudit.subtitle")}</p>
      </div>

      <div className="toolbar-controls llm-audit-filters">
        <label>
          {t("llmAudit.market")}
          <select value={market} onChange={(e) => setMarket(e.target.value)}>
            <option value="">{t("llmAudit.allMarkets")}</option>
            <option value="crypto">{t("nav.crypto")}</option>
            <option value="securities">{t("nav.moex")}</option>
          </select>
        </label>
        <label>
          {t("llmAudit.stage")}
          <select value={stage} onChange={(e) => setStage(e.target.value)}>
            <option value="">{t("llmAudit.allStages")}</option>
            {PIPELINE_STAGES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("llmAudit.action")}
          <select value={action} onChange={(e) => setAction(e.target.value)}>
            <option value="">{t("llmAudit.allActions")}</option>
            <option value="approve">approve</option>
            <option value="reject">reject</option>
            <option value="skip">skip</option>
          </select>
        </label>
      </div>

      <div className="llm-audit-grid">
        <PortfolioCard title={`${t("llmAudit.events")} (${events?.length ?? 0})`}>
          {loading && !events?.length ? (
            <p className="muted">{t("common.loading")}</p>
          ) : (
            <div className="llm-decisions-scroll table-wrap">
              <table className="llm-decisions-table">
                <thead>
                  <tr>
                    <th>{t("llmAudit.time")}</th>
                    <th>{t("llmAudit.stage")}</th>
                    <th>{t("llmAudit.symbol")}</th>
                    <th>{t("llmAudit.summary")}</th>
                  </tr>
                </thead>
                <tbody>
                  {(events ?? []).map((row) => (
                    <tr
                      key={row.id}
                      className={`llm-decision-row${selected?.id === row.id ? " row-selected" : ""}`}
                      onClick={() => selectRow(row)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          selectRow(row);
                        }
                      }}
                      tabIndex={0}
                      role="button"
                    >
                      <td className="llm-event-time">
                        {formatEventTime(String(row.event_at), locale)}
                      </td>
                      <td>
                        <span className={`pill tiny ${stageTone(row.stage ?? "", row.decision)}`}>
                          {row.stage}
                        </span>
                      </td>
                      <td>{row.symbol ?? "—"}</td>
                      <td className="llm-event-summary">
                        {row.summary ?? `${row.stage}/${row.decision}`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!events?.length && !loading ? (
                <p className="muted llm-decisions-empty">{t("common.statusEmpty")}</p>
              ) : null}
            </div>
          )}
        </PortfolioCard>

        <PortfolioCard
          title={t("llmAudit.detailsTitle")}
          status={view ? { label: view.stage ?? "—", tone: "neutral" } : undefined}
          subtitle={view?.symbol}
        >
          {!view ? (
            <p className="muted">{t("llmAudit.selectRow")}</p>
          ) : (
            <div className="detail-block">
              {detailLoading ? <p className="muted small">{t("common.loading")}</p> : null}
              {view.summary ? <p className="event-summary">{view.summary}</p> : null}
              <div>
                {view.stage} / {view.decision}
                {view.workflow_name ? ` · ${view.workflow_name}` : ""}
              </div>
              <div>
                {t("llmAudit.env")}: {view.env ?? "—"}
              </div>
              {view.stage === "llm" ? (
                <>
                  <div>
                    {t("llmAudit.model")}: {view.model ?? "—"}
                  </div>
                  <div>
                    {t("llmAudit.latency")}: {view.latency_ms ?? "—"} ms
                  </div>
                  <div>
                    {t("llmAudit.conf")}: {view.confidence?.toFixed(2) ?? "—"}
                  </div>
                </>
              ) : null}
              {ctx?.explanation ? (
                <p className="thesis">
                  <strong>{t("events.explanation")}: </strong>
                  {ctx.explanation}
                </p>
              ) : null}
              {ctx?.llm_audit?.counter_thesis ? (
                <p className="thesis">
                  <strong>{t("llmAudit.counterThesis")}: </strong>
                  {ctx.llm_audit.counter_thesis.slice(0, 500)}
                </p>
              ) : null}
              {view.reject_reason ? (
                <p className="warn">
                  <strong>{t("llmAudit.rejectReason")}: </strong>
                  {view.reject_reason}
                </p>
              ) : null}
              {view.inputs_hash ? (
                <>
                  <div className="muted small">{t("llmAudit.inputsHash")}</div>
                  <code className="hash">{view.inputs_hash}</code>
                </>
              ) : null}
            </div>
          )}

          {canReplay ? (
            <div className="btn-row llm-replay-row">
              <Hint label={t("llmAudit.replayHint")}>
                <button type="button" className="tiny" disabled={replayBusy} onClick={() => void runReplay()}>
                  {replayBusy ? t("llmAudit.replayBusy") : t("llmAudit.replay")}
                </button>
              </Hint>
            </div>
          ) : null}

          {replay ? (
            <div className="replay-out-block">
              <div className={`pill tiny ${replayChanged ? "warn" : "ok"}`}>
                {replayChanged ? t("llmAudit.replayChanged") : t("llmAudit.replayUnchanged")}
              </div>
              <pre className="replay-out small-pre">
                {JSON.stringify(
                  {
                    [t("llmAudit.was")]: (replay.original as { parsed_action?: string })?.parsed_action,
                    [t("llmAudit.now")]: (replay.replay as { action?: string })?.action,
                    confidence: (replay.replay as { confidence?: number })?.confidence,
                  },
                  null,
                  2,
                )}
              </pre>
            </div>
          ) : null}
        </PortfolioCard>
      </div>
    </div>
  );
}
