import type { ChartOverlays } from "../types";

export type OperationMode = "dry_run" | "paper" | "live";

const SWING_CHART_OVERLAYS: ChartOverlays = {
  price: ["ema50", "ema200"],
  panels: [
    { id: "rsi", series: ["rsi_14"], levels: ["rsi_oversold", "rsi_overbought"] },
    { id: "macd", series: ["macd", "macd_signal"], histogram: "macd_histogram" },
  ],
};

const SCALP_CHART_OVERLAYS: ChartOverlays = {
  price: ["ema50"],
  panels: [{ id: "rsi", series: ["rsi_14"], levels: ["rsi_oversold", "rsi_overbought"] }],
};

export const CRYPTO_CHART_OVERLAYS: Record<string, ChartOverlays | undefined> = {
  llm_swing: SWING_CHART_OVERLAYS,
  crypto_scalp_hybrid: SCALP_CHART_OVERLAYS,
  deepfund_paper: SWING_CHART_OVERLAYS,
};

export function chartOverlaysForStrategy(strategyId: string): ChartOverlays | undefined {
  return CRYPTO_CHART_OVERLAYS[strategyId];
}

export const CRYPTO_STRATEGY_WORKFLOW: Record<string, Partial<Record<OperationMode, string>>> = {
  llm_swing: {
    dry_run: "crypto-signal-dry-run",
    paper: "crypto-signal-paper",
    live: "crypto-signal-paper",
  },
  crypto_scalp_hybrid: {
    dry_run: "crypto-scalp-hybrid-dry-run",
    paper: "crypto-scalp-hybrid-paper",
  },
  deepfund_paper: {
    paper: "deepfund-live-paper",
  },
};

export const CRYPTO_STRATEGY_MODES: Record<string, OperationMode[]> = {
  llm_swing: ["dry_run", "paper", "live"],
  crypto_scalp_hybrid: ["dry_run", "paper"],
  deepfund_paper: ["paper"],
};

export const CRYPTO_STRATEGY_INTERVAL: Record<string, string> = {
  llm_swing: "4h",
  crypto_scalp_hybrid: "5m",
  deepfund_paper: "4h",
};

export function chartIntervalForStrategy(strategyId: string): string {
  return CRYPTO_STRATEGY_INTERVAL[strategyId] ?? "4h";
}

export function resolveCryptoWorkflow(strategyId: string, operationMode: OperationMode): string {
  return CRYPTO_STRATEGY_WORKFLOW[strategyId]?.[operationMode] ?? "";
}

export function supportsScalpPreScan(strategyId: string): boolean {
  return strategyId === "crypto_scalp_hybrid";
}
