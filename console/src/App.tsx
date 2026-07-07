import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost } from "./api";

type Tab = "overview" | "events" | "stats" | "risk" | "checklist";

export default function App() {
  const [tab, setTab] = useState<Tab>("overview");
  const [adminKey, setAdminKey] = useState(localStorage.getItem("adminKey") || "");
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [checklist, setChecklist] = useState<Record<string, unknown> | null>(null);
  const [pending, setPending] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState("");
  const [log, setLog] = useState("");

  const refresh = useCallback(async () => {
    setError("");
    try {
      const [s, e, st, cl, p] = await Promise.all([
        apiGet("/api/system/status"),
        apiGet("/api/events?limit=30"),
        apiGet("/api/stats/digest?days=7"),
        apiGet("/api/live/checklist"),
        apiGet("/api/admin/confirmations/pending"),
      ]);
      setStatus(s as Record<string, unknown>);
      setEvents(e as Record<string, unknown>[]);
      setStats(st as Record<string, unknown>);
      setChecklist(cl as Record<string, unknown>);
      setPending(p as Record<string, unknown>[]);
    } catch (err) {
      setError(String(err));
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 30000);
    return () => clearInterval(id);
  }, [refresh]);

  const saveAdminKey = () => {
    localStorage.setItem("adminKey", adminKey);
    refresh();
  };

  const killSwitch = async (enabled: boolean) => {
    if (!confirm(`Kill switch ${enabled ? "ON" : "OFF"}?`)) return;
    try {
      const r = await apiPost("/api/admin/kill-switch", {
        enabled,
        operator: "web:operator",
        source: "web",
      });
      setLog(JSON.stringify(r, null, 2));
      refresh();
    } catch (err) {
      setError(String(err));
    }
  };

  const smoke = async () => {
    setLog("Running smoke test…");
    try {
      const r = await apiPost("/api/admin/smoke-test");
      setLog((r as { output?: string }).output || JSON.stringify(r, null, 2));
    } catch (err) {
      setError(String(err));
    }
  };

  const resolve = async (id: string, decision: string) => {
    try {
      await apiPost(`/api/admin/confirmations/${id}/resolve`, {
        decision,
        operator: "web:operator",
      });
      refresh();
    } catch (err) {
      setError(String(err));
    }
  };

  return (
    <div className="layout">
      <header>
        <div>
          <h1>Trading Console</h1>
          <p className="muted">Dry-run control panel</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <input
            type="password"
            placeholder="Admin API key"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            style={{ padding: "0.5rem", borderRadius: 8, border: "1px solid #243044", background: "#0b1017", color: "inherit" }}
          />
          <button onClick={saveAdminKey}>Save</button>
          <button onClick={refresh}>Refresh</button>
        </div>
      </header>

      {error && <p className="error">{error}</p>}

      <nav>
        {(["overview", "events", "stats", "risk", "checklist"] as Tab[]).map((t) => (
          <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </nav>

      {tab === "overview" && status && (
        <section className="grid">
          <div className="card">
            <h3>Kill Switch</h3>
            <div className={`value ${status.kill_switch ? "error" : "ok"}`}>
              {status.kill_switch ? "ON" : "OFF"}
            </div>
          </div>
          <div className="card">
            <h3>Mode</h3>
            <div className="value">{String(status.trading_mode)}</div>
          </div>
          <div className="card">
            <h3>Ollama</h3>
            <div className="value">{(status.ollama as { status?: string })?.status}</div>
          </div>
          <div className="card">
            <h3>Live flag</h3>
            <div className="value">{status.live_enabled ? "true" : "false"}</div>
          </div>
        </section>
      )}

      {tab === "events" && (
        <table>
          <thead>
            <tr>
              <th>Time</th><th>Env</th><th>Stage</th><th>Decision</th><th>Symbol</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={String(e.id)}>
                <td>{String(e.event_at).slice(0, 19)}</td>
                <td>{String(e.env)}</td>
                <td>{String(e.stage)}</td>
                <td>{String(e.decision)}</td>
                <td>{String(e.symbol || "")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {tab === "stats" && stats && (
        <div className="card">
          <h3>7-day digest</h3>
          <pre>{JSON.stringify(stats, null, 2)}</pre>
        </div>
      )}

      {tab === "risk" && (
        <section>
          <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
            <button className="danger" onClick={() => killSwitch(true)}>Kill ON</button>
            <button className="primary" onClick={() => killSwitch(false)}>Kill OFF</button>
            <button onClick={smoke}>Smoke test</button>
          </div>
          {pending.length > 0 && (
            <div className="card">
              <h3>Pending confirmations</h3>
              {pending.map((p) => (
                <div key={String(p.id)} style={{ marginBottom: "0.75rem" }}>
                  <div>{String(p.title)}</div>
                  <div className="muted">{String(p.action_type)}</div>
                  <button onClick={() => resolve(String(p.id), "approved")}>Approve</button>{" "}
                  <button onClick={() => resolve(String(p.id), "rejected")}>Reject</button>
                </div>
              ))}
            </div>
          )}
          {log && <pre>{log}</pre>}
        </section>
      )}

      {tab === "checklist" && checklist && (
        <div className="card">
          <h3>Live readiness: {checklist.ready_for_live ? "READY" : "NOT READY"}</h3>
          <ul>
            {Object.entries(checklist.checks as Record<string, boolean>).map(([k, v]) => (
              <li key={k} className={v ? "ok" : "warn"}>{k}: {v ? "ok" : "fail"}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
