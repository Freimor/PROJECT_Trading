import type { OllamaStatus } from "../types";
import { isOllamaHealthy } from "../utils/ollamaHealth";

type TFn = (k: string, vars?: Record<string, string | number>) => string;

function formatLatency(ms: number | null | undefined): string | null {
  if (ms == null || Number.isNaN(ms)) return null;
  if (ms >= 10_000) return `${(ms / 1000).toFixed(0)}s`;
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}

function statusLabel(ollama: OllamaStatus, t: TFn): string {
  if (isOllamaHealthy(ollama)) return t("controlStrip.ollamaOnline");
  if (ollama.status === "critical" || ollama.status === "error" || ollama.error) {
    return t("controlStrip.ollamaOffline");
  }
  return ollama.status ?? "—";
}

export function OllamaStatusMetrics({ ollama, t }: { ollama?: OllamaStatus | null; t: TFn }) {
  if (!ollama) return null;

  const online = isOllamaHealthy(ollama);
  const ping = formatLatency(ollama.ping_ms ?? ollama.latency_ms);
  const avg = formatLatency(ollama.avg_latency_ms);
  const calls = ollama.llm_calls ?? 0;
  const errors = ollama.llm_errors ?? 0;
  const modelsCount = ollama.models_count ?? ollama.models?.length ?? 0;
  const loaded = ollama.loaded_count ?? 0;
  const primary = ollama.primary_models?.[0] ?? ollama.model;

  const midParts: string[] = [];
  if (avg) {
    midParts.push(t("controlStrip.ollamaAvg", { v: avg }));
  } else if (online) {
    midParts.push(t("controlStrip.ollamaNoCalls"));
  }
  if (calls > 0) {
    midParts.push(t("controlStrip.ollamaCalls", { n: calls }));
  }
  if (errors > 0) {
    midParts.push(t("controlStrip.ollamaErrors", { n: errors }));
  }

  const bottomParts: string[] = [];
  if (primary) bottomParts.push(primary);
  if (modelsCount > 0) {
    bottomParts.push(
      loaded > 0
        ? t("controlStrip.ollamaModelsLoaded", { loaded, total: modelsCount })
        : t("controlStrip.ollamaModels", { n: modelsCount }),
    );
  }

  return (
    <div className="control-strip-wf-metrics control-strip-ollama-metrics" aria-label={t("controlStrip.ollamaMetrics")}>
      <div className={`control-strip-wf-pnl-primary ${online ? "pnl-up" : "pnl-down"}`}>
        {statusLabel(ollama, t)}
        {ping ? ` · ${t("controlStrip.ollamaPing", { v: ping })}` : ""}
      </div>
      <div className="control-strip-wf-pnl-sub">{midParts.length ? midParts.join(" · ") : "—"}</div>
      <div className="control-strip-wf-pnl-sub muted">{bottomParts.join(" · ") || "—"}</div>
    </div>
  );
}
