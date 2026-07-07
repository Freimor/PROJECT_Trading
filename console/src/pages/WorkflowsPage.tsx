import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../api";
import PortfolioCard from "../components/PortfolioCard";
import { POLL } from "../config/polling";
import { useErrorNotifications } from "../context/ErrorNotifications";
import { usePolling } from "../hooks/usePolling";

type Workflow = { id: string; name: string; active: boolean };

const CRON_PRESETS = [
  { label: "15m", expr: "*/15 * * * *" },
  { label: "1h", expr: "0 * * * *" },
  { label: "4h", expr: "0 */4 * * *" },
];

export default function WorkflowsPage() {
  const [log, setLog] = useState("");
  const { report } = useErrorNotifications();

  const { data, refresh } = usePolling<{ status: string; workflows?: Workflow[]; message?: string }>(
    () => apiGet("/api/n8n/workflows"),
    POLL.OPS,
    true,
    {
      errorSource: "GET /api/n8n/workflows",
      staggerKey: "n8n-workflows",
    },
  );

  useEffect(() => {
    if (data?.status === "error" && data.message) {
      report("GET /api/n8n/workflows", data.message);
    } else if (data?.status !== "error") {
      report("GET /api/n8n/workflows", null);
    }
  }, [data, report]);

  const toggle = async (wf: Workflow) => {
    report("n8n/toggle", null);
    const path = wf.active
      ? `/api/n8n/workflows/${wf.id}/deactivate`
      : `/api/n8n/workflows/${wf.id}/activate`;
    try {
      const r = await apiPost(path);
      setLog(JSON.stringify(r, null, 2));
      refresh();
    } catch (err) {
      report("n8n/toggle", String(err));
    }
  };

  const setCron = async (wf: Workflow, expr: string) => {
    report("n8n/cron", null);
    try {
      const r = await apiPost(`/api/n8n/workflows/${wf.id}/cron`, { cron_expression: expr });
      setLog(JSON.stringify(r, null, 2));
    } catch (err) {
      report("n8n/cron", String(err));
    }
  };

  if (data?.status === "error") {
    return (
      <div className="page">
        <h2>🧩 n8n Workflows</h2>
        <p className="muted">
          Создайте API key в n8n (Settings → API keys) и задайте N8N_API_KEY в .env
        </p>
      </div>
    );
  }

  const workflows = data?.workflows ?? [];

  return (
    <div className="page">
      <div className="page-title">
        <h2>🧩 n8n Workflows</h2>
        <p className="muted">Включение и расписание (как в Telegram)</p>
      </div>

      <div className="workflow-list">
        {workflows.map((wf) => (
          <PortfolioCard key={wf.id} title={wf.name} subtitle={wf.id}>
            <div className="btn-row">
              <button type="button" onClick={() => toggle(wf)}>
                {wf.active ? "⏸ Выключить" : "▶️ Включить"}
              </button>
              <span className={`pill ${wf.active ? "ok" : ""}`}>
                {wf.active ? "active" : "off"}
              </span>
            </div>
            <div className="btn-row" style={{ marginTop: "0.5rem" }}>
              {CRON_PRESETS.map((p) => (
                <button key={p.expr} type="button" className="tiny" onClick={() => setCron(wf, p.expr)}>
                  {p.label}
                </button>
              ))}
            </div>
          </PortfolioCard>
        ))}
      </div>

      {log && (
        <PortfolioCard title="Ответ API">
          <pre>{log}</pre>
        </PortfolioCard>
      )}
    </div>
  );
}
