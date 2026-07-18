export type CryptoAutomationStatus = "stopped" | "running" | "error";

export type CryptoAutomationInstance = {
  id: string;
  name: string;
  strategy_id: string;
  symbol: string;
  workflow_name: string;
  operation_mode: string;
  status: CryptoAutomationStatus;
  session_config: Record<string, unknown>;
  collapsed: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  stopped_at?: string | null;
};

export type CryptoAutomationStats = {
  instance_id: string;
  symbol: string;
  workflow_name: string;
  days?: number;
  scope?: "session" | string;
  events: number;
  orders: number;
  orders_ok?: number;
  orders_failed?: number;
  signals?: number;
  filter_approve?: number;
  filter_skip?: number;
  filter_reject?: number;
  guardrails_reject?: number;
  invested_notional?: number;
  session_capital?: number | null;
  started_at?: string | null;
  stopped_at?: string | null;
  duration_sec?: number | null;
  pnl_sum: number;
  pnl_pct: number | null;
  pnl_direction?: string;
  currency?: string;
  status: CryptoAutomationStatus;
  last_event_at?: string | null;
};

export type CryptoInstanceWalletRow = {
  asset: string;
  label?: string;
  quantity: number;
  usdt_value?: number | null;
  entry_price?: number | null;
  unrealized_pnl?: number | null;
};

export type CryptoInstanceWallet = {
  status: string;
  instance_id: string;
  symbol: string;
  market_type?: string;
  session_capital?: number | null;
  rows: CryptoInstanceWalletRow[];
};

export type CryptoInstanceSessionReport = {
  instance_id: string;
  name?: string;
  strategy_id?: string;
  symbol?: string;
  workflow_name?: string;
  started_at?: string | null;
  ended_at?: string | null;
  duration_sec?: number | null;
  session_capital?: number | null;
  statistics?: {
    signals?: number;
    filter_approve?: number;
    filter_skip?: number;
    filter_reject?: number;
    guardrails_reject?: number;
    orders_ok?: number;
    orders_failed?: number;
    invested_notional?: number;
  };
  pnl_sum?: number;
  pnl_pct?: number | null;
  pnl_direction?: string;
  currency?: string;
  trades?: Array<{
    event_at?: string;
    symbol?: string;
    decision?: string;
    side?: string;
    quantity?: number | string | null;
    notional?: number | null;
    currency?: string;
  }>;
};

export type CryptoAutomationStopResponse = {
  status: string;
  instance?: CryptoAutomationInstance;
  session_report?: CryptoInstanceSessionReport;
};

export type CryptoAutomationsListResponse = {
  status: string;
  items: CryptoAutomationInstance[];
  count: number;
};
