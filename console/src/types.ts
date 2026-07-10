export type StrategyInfo = {
  id: string;
  label: string;
  description?: string;
  description_en?: string;
  rationale_ru?: string;
  rationale_en?: string;
  paper_ref?: string;
  kind?: string;
  workflow?: string;
  symbols?: string[];
  chart_default?: string;
  chart_interval?: string;
  uses_llm?: boolean;
  chart_overlays?: ChartOverlays;
};

export type ChartOverlayPanel = {
  id: string;
  series: string[];
  levels?: string[];
  histogram?: string;
};

export type ChartOverlays = {
  price?: string[];
  panels?: ChartOverlayPanel[];
};

export type IndicatorPoint = {
  time: number;
  value: number;
};

export type ChartIndicators = {
  series: Record<string, IndicatorPoint[]>;
  levels: Record<string, number>;
};

export type StrategyState = {
  market: string;
  active: string;
  strategy: StrategyInfo;
  strategies: StrategyInfo[];
};

export type ActivityFeedItem = {
  id: string;
  occurred_at: string;
  message: string;
  category?: string;
  level?: "info" | "success" | "warn" | "error";
  ref_type?: string;
  ref_id?: string;
};

export type Candle = {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
};

export type ChartMarker = {
  id: string;
  time: number;
  event_at: string;
  env: string;
  stage: string;
  decision?: string;
  confidence?: number;
  reject_reason?: string;
  workflow_name?: string;
  inputs_hash?: string;
  model?: string;
  latency_ms?: number;
  counter_thesis?: string;
  kind: string;
  shape: string;
  position: string;
  color: string;
  text: string;
};

export type TradeEvent = {
  id: string;
  event_at: string;
  market: string;
  env: string;
  stage: string;
  symbol?: string;
  decision?: string;
  confidence?: number;
  reject_reason?: string;
  inputs_hash?: string;
  summary?: string;
  workflow_name?: string;
  model?: string;
  context?: {
    explanation?: string | null;
    reject_hint?: string | null;
    missing_llm_stage?: boolean;
    pipeline?: Array<{
      id: string;
      stage: string;
      decision?: string;
      reject_reason?: string;
      event_at?: string;
      payload?: Record<string, unknown>;
    }>;
    llm_audit?: {
      parsed_action?: string;
      confidence?: number;
      counter_thesis?: string;
      reject_reason?: string;
      model?: string;
      raw_response?: string;
    } | null;
  };
};

export type WorkflowPnl = {
  status?: string;
  pnl_pct?: number | null;
  direction?: "up" | "down" | "flat";
  current_total?: number | null;
  baseline_total?: number | null;
  currency?: string;
};

export type AutomationOverview = {
  kill_switch: boolean;
  kill_switch_updated_at?: string;
  trading_mode: string;
  operation_mode?: string;
  operation_detail?: string;
  live_flag: boolean;
  ollama?: { status?: string; latency_ms?: number; model?: string };
  last_event?: {
    event_at?: string;
    workflow_name?: string;
    stage?: string;
    decision?: string;
    env?: string;
    symbol?: string;
  };
  crypto?: {
    env?: string;
    mode?: string;
    operation_mode?: string;
    operation_detail?: string;
    mode_updated_at?: string;
    workflow_started_at?: string | null;
    workflow_pnl?: WorkflowPnl | null;
    workflows_active?: boolean;
    active_workflows?: string[];
    pairs?: string[];
    active_strategy?: string;
    strategy_label?: string;
    workflow?: string;
    funnel_signal?: { passed?: number; total?: number };
  };
  securities?: {
    env?: string;
    mode?: string;
    operation_mode?: string;
    operation_detail?: string;
    mode_updated_at?: string;
    workflow_started_at?: string | null;
    workflow_pnl?: WorkflowPnl | null;
    workflows_active?: boolean;
    active_workflows?: string[];
    active_mode?: string;
    strategy_label?: string;
    tinvest_api?: string;
    workflow?: string;
    funnel_signal?: { passed?: number; total?: number };
  };
  dry_run_signals_7d?: number;
};
