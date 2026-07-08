export type StrategyInfo = {
  id: string;
  label: string;
  description?: string;
  workflow?: string;
  symbols?: string[];
  chart_default?: string;
  chart_interval?: string;
  uses_llm?: boolean;
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
};

export type AutomationOverview = {
  kill_switch: boolean;
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
    active_mode?: string;
    strategy_label?: string;
    tinvest_api?: string;
    workflow?: string;
    funnel_signal?: { passed?: number; total?: number };
  };
  dry_run_signals_7d?: number;
};
