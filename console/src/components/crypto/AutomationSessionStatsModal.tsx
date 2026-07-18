import { useEffect } from "react";
import ModalPortal from "../../ui/ModalPortal";
import type { CryptoInstanceSessionReport } from "../../types/cryptoAutomation";

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

function pnlClass(dir?: string): string {
  if (dir === "up") return "pnl-up";
  if (dir === "down") return "pnl-down";
  return "pnl-flat";
}

export default function AutomationSessionStatsModal({
  report,
  onClose,
  t,
}: {
  report: CryptoInstanceSessionReport | null;
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

  const stats = report.statistics ?? {};
  const pnlPct =
    report.pnl_pct != null ? `${report.pnl_pct >= 0 ? "+" : ""}${report.pnl_pct.toFixed(2)}%` : "—";
  const pnlSum =
    report.pnl_sum != null
      ? `${report.pnl_sum >= 0 ? "+" : ""}${report.pnl_sum} ${report.currency ?? "USDT"}`
      : "—";

  return (
    <ModalPortal>
      <div className="modal-overlay" role="presentation" onClick={onClose}>
        <div
          className="modal-dialog workflow-report-modal automation-session-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="automation-session-title"
          onClick={(e) => e.stopPropagation()}
        >
          <h3 id="automation-session-title">{t("cryptoAutomation.sessionReportTitle")}</h3>
          <p className="workflow-report-headline">{report.name ?? report.symbol}</p>
          <p className="muted workflow-report-meta">
            {report.symbol} · {fmtTime(report.started_at)} → {fmtTime(report.ended_at)} ·{" "}
            {fmtDuration(report.duration_sec)}
          </p>

          <div className="workflow-report-body">
            <section className="workflow-report-section">
              <h4>{t("cryptoAutomation.sessionPnl")}</h4>
              <div className="automation-session-pnl-row">
                <strong className={pnlClass(report.pnl_direction)}>{pnlPct}</strong>
                <span className="muted">{pnlSum}</span>
                {report.session_capital != null ? (
                  <span className="muted small">
                    {t("cryptoAutomation.sessionBudget")}: {report.session_capital} USDT
                  </span>
                ) : null}
              </div>
            </section>

            <section className="workflow-report-section">
              <h4>{t("workflowReport.statistics")}</h4>
              <div className="workflow-report-stats-grid">
                <span>
                  {t("workflowReport.signals")}: {stats.signals ?? 0}
                </span>
                <span>
                  {t("cryptoAutomation.filterFunnel")}: {stats.filter_approve ?? 0} /{" "}
                  {stats.filter_skip ?? 0} / {stats.filter_reject ?? 0}
                </span>
                <span>
                  {t("workflowReport.orders")}: {stats.orders_ok ?? 0} / {stats.orders_failed ?? 0}
                </span>
                <span>
                  {t("cryptoAutomation.investedNotional")}: {stats.invested_notional ?? "—"} USDT
                </span>
                <span>
                  {t("cryptoAutomation.guardrailsReject")}: {stats.guardrails_reject ?? 0}
                </span>
              </div>
            </section>

            <section className="workflow-report-section">
              <h4>{t("workflowReport.accountActions")}</h4>
              {!report.trades?.length ? (
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
                      {report.trades.map((a, i) => (
                        <tr key={`${a.event_at}-${a.symbol}-${i}`}>
                          <td>{fmtTime(a.event_at)}</td>
                          <td>{a.side ?? "—"}</td>
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
