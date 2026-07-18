import PortfolioCard from "./PortfolioCard";
import TradingProductPill, { type TradingProductBadge } from "./TradingProductPill";
import { useI18n } from "../i18n/LanguageContext";

type FunnelStage = { passed?: number; total?: number };

type Props = {
  title: string;
  mode?: string;
  env?: string;
  workflow?: string;
  funnel?: Record<string, FunnelStage>;
  llmEval?: { count?: number; approve_rate?: number; avg_latency_ms?: number };
  ollama?: { status?: string; latency_ms?: number };
  connectionWarning?: string;
  tradingProduct?: TradingProductBadge | null;
};

function stageLine(label: string, stage?: FunnelStage) {
  if (!stage || stage.total == null) return null;
  const pct = stage.total ? Math.round(((stage.passed ?? 0) / stage.total) * 100) : 0;
  return (
    <div className="metric-row compact" key={label}>
      <span>{label}</span>
      <strong>
        {stage.passed ?? 0}/{stage.total} ({pct}%)
      </strong>
    </div>
  );
}

export default function AutomationPanel({
  title,
  mode,
  env,
  workflow,
  funnel,
  llmEval,
  ollama,
  connectionWarning,
  tradingProduct,
}: Props) {
  const nested = funnel?.funnel as Record<string, FunnelStage> | undefined;
  const stages = nested ?? funnel;

  return (
    <PortfolioCard
      title={title}
      subtitle={[env, mode].filter(Boolean).join(" · ") || undefined}
      headBadge={tradingProduct ? <TradingProductPill product={tradingProduct} /> : undefined}
      collapsible={false}
    >
      {connectionWarning ? <p className="warn small">{connectionWarning}</p> : null}
      {workflow && (
        <div className="metric-row compact muted">
          <span className="small">n8n</span>
          <strong className="mono-small">{workflow}</strong>
        </div>
      )}
      {stageLine("signal", stages?.signal)}
      {stageLine("filter", stages?.filter)}
      {stageLine("llm", stages?.llm)}
      {stageLine("guardrails", stages?.guardrails)}
      {stageLine("order", stages?.order)}
      <div className="metric-row compact">
        <span>LLM (7д)</span>
        <strong>
          {llmEval?.count
            ? `${llmEval.count} выз., approve ${llmEval.approve_rate != null ? `${(llmEval.approve_rate * 100).toFixed(0)}%` : "—"}`
            : "нет вызовов"}
        </strong>
      </div>
      <div className="metric-row compact">
        <span>Ollama</span>
        <strong className={ollama?.status === "ok" ? "ok" : ""}>
          {ollama?.status ?? "—"}
          {ollama?.latency_ms != null ? ` (${ollama.latency_ms}ms)` : ""}
        </strong>
      </div>
    </PortfolioCard>
  );
}
