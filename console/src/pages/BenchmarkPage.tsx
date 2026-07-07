import { useState } from "react";
import { apiGet, apiPost } from "../api";
import PortfolioCard from "../components/PortfolioCard";
import { POLL } from "../config/polling";
import { useErrorNotifications } from "../context/ErrorNotifications";
import { usePolling } from "../hooks/usePolling";

export default function BenchmarkPage() {
  const [log, setLog] = useState("");
  const [busy, setBusy] = useState(false);
  const { report } = useErrorNotifications();

  const { data: reportData, refresh: refreshReport } = usePolling(
    () => apiGet("/api/benchmark/report?days=30"),
    POLL.OPS,
    true,
    { staggerKey: "benchmark-report" },
  );
  const { data: calib } = usePolling(
    () => apiGet("/api/benchmark/calibrate/last-snapshot"),
    POLL.OPS * 2,
    true,
    { staggerKey: "benchmark-calib" },
  );
  const { data: plan } = usePolling(() => apiGet("/api/benchmark/calibrate/plan"), POLL.STATIC, true, {
    staggerKey: "benchmark-plan",
  });

  const runReport = async () => {
    setBusy(true);
    report("benchmark/outcome", null);
    try {
      await apiPost("/api/benchmark/sample?days=30", {});
      await apiPost("/api/benchmark/label", {});
      refreshReport();
      setLog("Outcome sample + label выполнены");
    } catch (err) {
      report("benchmark/outcome", String(err));
    } finally {
      setBusy(false);
    }
  };

  const rep = reportData as Record<string, unknown> | null;
  const byMarket = (rep?.by_market ?? {}) as Record<string, { outcome?: Record<string, unknown> }>;
  const cal = calib as Record<string, unknown> | null;
  const rec = cal?.recommended as Record<string, unknown> | undefined;

  return (
    <div className="page">
      <div className="page-title">
        <h2>📊 LLM Benchmark</h2>
        <p className="muted">Outcome metrics + калибровка</p>
      </div>

      <div className="btn-row" style={{ marginBottom: "1rem" }}>
        <button type="button" disabled={busy} onClick={runReport}>
          Обновить outcome
        </button>
        <span className="muted">
          Калибровка: {String((plan as { llm_calls?: number })?.llm_calls ?? "?")} LLM-вызовов — через Telegram
        </span>
      </div>

      <div className="grid cards-2">
        <PortfolioCard title="Outcome (30д)">
          <div className="metric-row">
            <span>Кейсов</span>
            <strong>{String(rep?.total_cases ?? 0)}</strong>
          </div>
          <div className="metric-row">
            <span>Размечено</span>
            <strong>{String(rep?.labeled_cases ?? 0)}</strong>
          </div>
          {Object.entries(byMarket).map(([mkt, block]) => (
            <div key={mkt} className="market-block">
              <strong>{mkt}</strong>
              <div className="muted">
                precision: {String(block.outcome?.precision_approve ?? "—")} · recall:{" "}
                {String(block.outcome?.recall ?? "—")}
              </div>
            </div>
          ))}
        </PortfolioCard>

        <PortfolioCard title="Последняя калибровка">
          {cal?.status === "ok" && rec ? (
            <>
              <div className="metric-row">
                <span>Рекомендация</span>
                <strong>
                  T={String(rec.temperature)} conf={String(rec.min_confidence)}
                </strong>
              </div>
              <div className="metric-row">
                <span>Score</span>
                <strong>{String(rec.composite_score)}</strong>
              </div>
              <p className="muted small">{String(cal.recommendation_note ?? "")}</p>
            </>
          ) : (
            <p className="muted">Калибровка ещё не запускалась (Telegram → 🎛 Калибровка)</p>
          )}
        </PortfolioCard>
      </div>

      {log && (
        <PortfolioCard title="Log">
          <pre>{log}</pre>
        </PortfolioCard>
      )}
    </div>
  );
}
