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
  short_label?: string;
  summary?: string;
  payload?: Record<string, unknown>;
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
  latency_ms?: number;
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

export type WorkflowSessionConfig = {
  session_capital?: number | null;
  session_volume_mode?: "stablecoin" | "existing_holdings" | "combined";
  use_existing_holdings?: boolean;
  existing_holdings_unit?: "percent" | "absolute";
  existing_holdings_use_pct?: number;
  existing_holdings_use_qty?: number | null;
  liquidate_on_stop?: boolean;
  liquidate_on_margin_call?: boolean;
  universe_scan_selected?: string[];
  quote_asset?: string;
  holdings_baseline?: Record<string, number>;
  baseline_captured_at?: string;
  workflow_name?: string;
};

export type WorkflowSessionStats = {
  status?: string;
  signals?: number;
  orders_ok?: number;
  orders_failed?: number;
  open_positions?: number;
  max_open_positions?: number;
  pnl_delta?: number | null;
  pnl_pct?: number | null;
  pnl_direction?: "up" | "down" | "flat";
  currency?: string;
  invested_notional?: number | null;
  pnl_source?: string;
  session_capital?: number | null;
  last_event_at?: string | null;
  last_event_ago_sec?: number | null;
  last_event_symbol?: string | null;
  last_event_stage?: string | null;
  last_event_decision?: string | null;
  last_event_reject_reason?: string | null;
  instances_running?: number;
  instances_total?: number;
  running_symbols?: string[];
};

export type CryptoAutomationInstancesSummary = {
  has_instances?: boolean;
  total_count?: number;
  running_count?: number;
  stopped_count?: number;
  running_symbols?: string[];
  active_workflows?: string[];
  earliest_started_at?: string | null;
  operation_mode?: string;
};

export type OllamaStatus = {
  status?: string;
  latency_ms?: number | null;
  ping_ms?: number | null;
  avg_latency_ms?: number | null;
  max_latency_ms?: number | null;
  llm_calls?: number;
  llm_errors?: number;
  llm_rejects?: number;
  models_count?: number;
  loaded_count?: number;
  loaded_models?: string[];
  primary_models?: string[];
  model?: string;
  models?: string[];
  window_hours?: number;
  last_latency_ms?: number | null;
  last_model?: string | null;
  error?: string | null;
};

export type ScalpPairScanProgress = {
  in_progress?: boolean;
  workflow_name?: string;
  total?: number;
  done?: number;
  current_base?: string;
  started_at?: string;
};

export type AutomationOverview = {
  kill_switch: boolean;
  kill_switch_updated_at?: string;
  trading_mode: string;
  operation_mode?: string;
  operation_detail?: string;
  live_flag: boolean;
  ollama?: OllamaStatus;
  scalp_pair_scan?: ScalpPairScanProgress;
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
    workflow_session?: WorkflowSessionStats | null;
    workflow_session_config?: WorkflowSessionConfig | null;
    workflows_active?: boolean;
    active_workflows?: string[];
    pairs?: string[];
    automation_instances?: CryptoAutomationInstancesSummary | null;
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
    workflow_session?: WorkflowSessionStats | null;
    workflow_session_config?: WorkflowSessionConfig | null;
    workflows_active?: boolean;
    active_workflows?: string[];
    active_mode?: string;
    strategy_label?: string;
    tinvest_api?: string;
    workflow?: string;
    funnel_signal?: { passed?: number; total?: number };
    automation_instances?: CryptoAutomationInstancesSummary | null;
  };
  dry_run_signals_7d?: number;
};

export type WorkflowSessionReport = {
  id?: string;
  report_id?: string;
  market?: string;
  workflow_name?: string;
  started_at?: string;
  ended_at?: string;
  reason?: string;
  llm_model?: string | null;
  llm_latency_ms?: number | null;
  llm_narrative?: {
    headline?: string;
    success_rating?: string;
    reject_analysis?: string;
    risk_notes?: string;
    recommendations?: string[];
    success_factors?: string[];
    failure_factors?: string[];
    source?: string;
  };
  report?: {
    duration_sec?: number;
    statistics?: {
      signals?: number;
      filter_approve?: number;
      filter_skip?: number;
      filter_reject?: number;
      llm_approve?: number;
      llm_reject?: number;
      orders_ok?: number;
      orders_failed?: number;
      reject_reasons?: Array<{ reject_reason?: string; cnt?: number }>;
    };
    session_stats?: WorkflowSessionStats;
    account_actions?: Array<{
      event_at?: string;
      symbol?: string;
      side?: string;
      quantity?: number | string;
      notional?: number | string;
      currency?: string;
    }>;
    llm_narrative?: WorkflowSessionReport["llm_narrative"];
  };
};
