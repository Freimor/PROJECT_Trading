export type SecuritiesAutomationStatus = "stopped" | "running" | "error";

export type SecuritiesAutomationInstance = {
  id: string;
  name: string;
  strategy_id: string;
  symbol: string;
  symbols?: string[];
  workflow_name: string;
  operation_mode: string;
  status: SecuritiesAutomationStatus;
  session_config: Record<string, unknown>;
  collapsed: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  stopped_at?: string | null;
};

export type SecuritiesAutomationStats = {
  instance_id: string;
  symbol: string;
  symbols?: string[];
  workflow_name: string;
  days: number;
  events: number;
  orders: number;
  pnl_sum: number;
  pnl_pct: number | null;
  status: SecuritiesAutomationStatus;
};

export type SecuritiesAutomationsListResponse = {
  status: string;
  items: SecuritiesAutomationInstance[];
  count: number;
};
