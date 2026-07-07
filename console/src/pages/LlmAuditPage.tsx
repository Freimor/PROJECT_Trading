import { useCallback, useState } from "react";
import { apiGet, apiPost } from "../api";
import PortfolioCard from "../components/PortfolioCard";
import { POLL } from "../config/polling";
import { useErrorNotifications } from "../context/ErrorNotifications";
import { usePolling } from "../hooks/usePolling";

type LlmRow = {
  id: string;
  created_at: string;
  market: string;
  symbol?: string;
  env?: string;
  model: string;
  parsed_action: string;
  confidence?: number;
  latency_ms?: number;
  inputs_hash: string;
  counter_thesis?: string;
  reject_reason?: string;
};

type ListResp = {
  total: number;
  decisions: LlmRow[];
};

export default function LlmAuditPage() {
  const [market, setMarket] = useState("");
  const [action, setAction] = useState("");
  const [selected, setSelected] = useState<LlmRow | null>(null);
  const [replay, setReplay] = useState<Record<string, unknown> | null>(null);
  const [replayBusy, setReplayBusy] = useState(false);
  const { report } = useErrorNotifications();

  const fetcher = useCallback(() => {
    const q = new URLSearchParams({ limit: "40", days: "365" });
    if (market) q.set("market", market);
    if (action) q.set("action", action);
    return apiGet<ListResp>(`/api/llm/decisions?${q}`);
  }, [market, action]);

  const { data, loading } = usePolling(fetcher, POLL.EVENTS, true, {
    errorSource: "GET /api/llm/decisions",
    staggerKey: "llm-audit",
  });

  const runReplay = async (row: LlmRow) => {
    setReplayBusy(true);
    report("POST /api/evaluation/replay", null);
    setSelected(row);
    try {
      const r = await apiPost<Record<string, unknown>>("/api/evaluation/replay", {
        inputs_hash: row.inputs_hash,
      });
      setReplay(r);
    } catch (err) {
      report("POST /api/evaluation/replay", String(err));
      setReplay(null);
    } finally {
      setReplayBusy(false);
    }
  };

  return (
    <div className="page">
      <div className="page-title">
        <h2>LLM Audit</h2>
        <p className="muted">Все решения модели · replay по inputs_hash</p>
      </div>

      <div className="toolbar-controls" style={{ marginBottom: "1rem" }}>
        <label>
          Market
          <select value={market} onChange={(e) => setMarket(e.target.value)}>
            <option value="">все</option>
            <option value="crypto">crypto</option>
            <option value="securities">securities</option>
          </select>
        </label>
        <label>
          Action
          <select value={action} onChange={(e) => setAction(e.target.value)}>
            <option value="">все</option>
            <option value="approve">approve</option>
            <option value="reject">reject</option>
          </select>
        </label>
      </div>

      {loading && <p className="muted">Загрузка…</p>}

      <div className="grid cards-2">
        <PortfolioCard title={`Решения (${data?.total ?? 0})`}>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Время</th>
                  <th>Symbol</th>
                  <th>Action</th>
                  <th>Conf</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {(data?.decisions ?? []).map((row) => (
                  <tr key={row.id} className={selected?.id === row.id ? "row-selected" : ""}>
                    <td>{row.created_at.slice(0, 16)}</td>
                    <td>{row.symbol ?? "—"}</td>
                    <td className={row.parsed_action === "approve" ? "ok" : ""}>
                      {row.parsed_action}
                    </td>
                    <td>{row.confidence?.toFixed(2) ?? ""}</td>
                    <td>
                      <button type="button" className="tiny" onClick={() => runReplay(row)}>
                        Replay
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PortfolioCard>

        <PortfolioCard title="Детали / Replay" subtitle={selected?.symbol}>
          {!selected && <p className="muted">Выберите строку и нажмите Replay</p>}
          {selected && (
            <div className="detail-block">
              <div>model: {selected.model}</div>
              <div>env: {selected.env ?? "—"}</div>
              <div>latency: {selected.latency_ms ?? "—"} ms</div>
              {selected.counter_thesis && (
                <p className="thesis">{selected.counter_thesis.slice(0, 400)}</p>
              )}
              {selected.reject_reason && <p className="warn">{selected.reject_reason}</p>}
              <code className="hash">{selected.inputs_hash}</code>
            </div>
          )}
          {replayBusy && <p className="muted">Replay… (вызов Ollama)</p>}
          {replay && (
            <pre className="replay-out">
              {JSON.stringify(
                {
                  changed: replay.changed,
                  original: (replay.original as { parsed_action?: string })?.parsed_action,
                  replay: (replay.replay as { action?: string; confidence?: number })?.action,
                  confidence: (replay.replay as { confidence?: number })?.confidence,
                },
                null,
                2,
              )}
            </pre>
          )}
        </PortfolioCard>
      </div>
    </div>
  );
}
