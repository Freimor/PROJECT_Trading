import { useEffect } from "react";
import ModalPortal from "../ui/ModalPortal";
import type { WorkflowSessionReport } from "../types";

type TFn = (k: string, vars?: Record<string, string | number>) => string;

function fmtTime(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? String(iso) : d.toLocaleString();
}

function fmtDuration(sec?: number | null): string {
  if (sec == null || sec < 0) return "—";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  if (h > 0) return `${h}ч ${m}м`;
  return `${m}м`;
}

export default function WorkflowSessionReportModal({
  report,
  onClose,
  t,
}: {
  report: WorkflowSessionReport | null;
  onClose: () => void;
  t: TFn;
}) {
  useEffect(() => {
    if (!report) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [report, onClose]);

  if (!report) return null;

  const data = report.report ?? {};
  const stats = data.statistics ?? {};
  const narr = report.llm_narrative ?? data.llm_narrative ?? {};
  const actions = data.account_actions ?? [];
  const session = data.session_stats ?? {};

  return (
    <ModalPortal>
      <div className="modal-overlay" role="presentation" onClick={onClose}>
        <div
          className="modal-dialog workflow-report-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="workflow-report-title"
          onClick={(e) => e.stopPropagation()}
        >
          <h3 id="workflow-report-title">{t("workflowReport.title")}</h3>
          <p className="workflow-report-headline">{narr.headline ?? report.workflow_name}</p>
          <p className="muted workflow-report-meta">
            {report.workflow_name} · {fmtTime(report.started_at)} → {fmtTime(report.ended_at)} ·{" "}
            {fmtDuration(data.duration_sec as number | undefined)}
          </p>

          <div className="workflow-report-body">
            <section className="workflow-report-section">
              <h4>{t("workflowReport.llmSummary")}</h4>
              {narr.success_rating ? (
                <p>
                  {t("workflowReport.rating")}: <strong>{narr.success_rating}</strong>
                  {report.llm_model ? ` · ${report.llm_model}` : ""}
                </p>
              ) : null}
              {narr.reject_analysis ? <p>{narr.reject_analysis}</p> : null}
              {narr.risk_notes ? <p className="muted">{narr.risk_notes}</p> : null}
              {Array.isArray(narr.recommendations) && narr.recommendations.length > 0 ? (
                <ul>
                  {narr.recommendations.map((r: string) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              ) : null}
            </section>

            <section className="workflow-report-section">
              <h4>{t("workflowReport.statistics")}</h4>
              <div className="workflow-report-stats-grid">
                <span>
                  {t("workflowReport.signals")}: {stats.signals ?? 0}
                </span>
                <span>
                  {t("workflowReport.filter")}: {stats.filter_approve ?? 0} / {stats.filter_skip ?? 0} /{" "}
                  {stats.filter_reject ?? 0}
                </span>
                <span>
                  {t("workflowReport.llm")}: {stats.llm_approve ?? 0} / {stats.llm_reject ?? 0}
                </span>
                <span>
                  {t("workflowReport.orders")}: {stats.orders_ok ?? 0} / {stats.orders_failed ?? 0}
                </span>
                <span>
                  {t("workflowReport.sessionPnl")}: {session.pnl_delta ?? "—"} {session.currency ?? ""}
                </span>
              </div>
            </section>

            <section className="workflow-report-section">
              <h4>{t("workflowReport.accountActions")}</h4>
              {actions.length === 0 ? (
                <p className="muted">{t("workflowReport.noTrades")}</p>
              ) : (
                <div className="table-wrap">
                  <table className="data-table compact">
                    <thead>
                      <tr>
                        <th>{t("workflowReport.time")}</th>
                        <th>{t("workflowReport.side")}</th>
                        <th>{t("workflowReport.symbol")}</th>
                        <th>{t("workflowReport.qty")}</th>
                        <th>{t("workflowReport.notional")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {actions.map((a, i) => (
                        <tr key={`${a.event_at}-${a.symbol}-${i}`}>
                          <td>{fmtTime(a.event_at)}</td>
                          <td>{a.side}</td>
                          <td>{a.symbol}</td>
                          <td>{a.quantity ?? "—"}</td>
                          <td>
                            {a.notional ?? "—"} {a.currency ?? ""}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            {Array.isArray(stats.reject_reasons) && stats.reject_reasons.length > 0 ? (
              <section className="workflow-report-section">
                <h4>{t("workflowReport.rejectReasons")}</h4>
                <ul className="workflow-report-rejects">
                  {stats.reject_reasons.slice(0, 8).map((r: { reject_reason?: string; cnt?: number }) => (
                    <li key={r.reject_reason}>
                      <code>{r.reject_reason}</code> — {r.cnt}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
          </div>

          <div className="modal-actions">
            <button type="button" onClick={onClose}>
              {t("workflowReport.close")}
            </button>
          </div>
        </div>
      </div>
    </ModalPortal>
  );
}
