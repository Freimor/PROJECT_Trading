import { useState } from "react";
import { apiGet, apiPost } from "../api";
import PortfolioCard from "../components/PortfolioCard";
import { POLL } from "../config/polling";
import { useErrorNotifications } from "../context/ErrorNotifications";
import { usePolling } from "../hooks/usePolling";

export default function PaperPage() {
  const [log, setLog] = useState("");
  const [busy, setBusy] = useState(false);
  const { report } = useErrorNotifications();

  const { data: status } = usePolling(() => apiGet("/api/paper/status"), POLL.OPS, true, {
    staggerKey: "paper-status",
  });
  const { data: eff, refresh: refreshEff } = usePolling(
    () => apiGet("/api/paper/effectiveness?days=7"),
    POLL.OPS,
    true,
    { staggerKey: "paper-effectiveness" },
  );

  const run = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(true);
    report("paper/action", null);
    setLog(`${label}…`);
    try {
      const r = await fn();
      setLog(JSON.stringify(r, null, 2));
      refreshEff();
    } catch (err) {
      report("paper/action", String(err));
    } finally {
      setBusy(false);
    }
  };

  const paper = eff as Record<string, unknown> | null;
  const session = paper?.session as Record<string, unknown> | undefined;
  const deltas = paper?.deltas as Record<string, number> | undefined;

  return (
    <div className="page">
      <div className="page-title">
        <h2>🧪 Paper тест</h2>
        <p className="muted">Виртуальные сделки на testnet / sandbox</p>
      </div>

      <div className="grid cards-2">
        <PortfolioCard title="Конфиг" subtitle={String((status as { global_mode?: string })?.global_mode)}>
          <pre className="small-pre">{JSON.stringify(status, null, 2)}</pre>
        </PortfolioCard>

        <PortfolioCard title="Эффективность (7д)">
          {session ? (
            <>
              <div className="metric-row">
                <span>Сессия</span>
                <strong>{String(session.label ?? session.id).slice(0, 20)}</strong>
              </div>
              {deltas && (
                <>
                  <div className="metric-row">
                    <span>Δ USDT</span>
                    <strong>{deltas.usdt_delta?.toFixed(2) ?? "—"}</strong>
                  </div>
                  <div className="metric-row">
                    <span>Δ RUB</span>
                    <strong>{deltas.rub_delta?.toFixed(0) ?? "—"}</strong>
                  </div>
                </>
              )}
            </>
          ) : (
            <p className="muted">Нет активной paper-сессии</p>
          )}
        </PortfolioCard>
      </div>

      <PortfolioCard title="Действия">
        <div className="btn-row">
          <button
            type="button"
            disabled={busy}
            onClick={() => run("Snapshot", () => apiPost("/api/paper/snapshot"))}
          >
            📸 Snapshot
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => run("Reset MOEX", () => apiPost("/api/paper/session/reset"))}
          >
            🔄 Сброс sandbox
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() =>
              run("Crypto paper", () => apiPost("/api/paper/crypto/run", { symbol: "BTCUSDT" }))
            }
          >
            ▶️ Crypto BTC
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() =>
              run("MOEX swing", () => apiPost("/api/paper/securities/swing", { ticker: "SBER" }))
            }
          >
            ▶️ MOEX SBER
          </button>
        </div>
      </PortfolioCard>

      {log && (
        <PortfolioCard title="Результат">
          <pre>{log}</pre>
        </PortfolioCard>
      )}
    </div>
  );
}
