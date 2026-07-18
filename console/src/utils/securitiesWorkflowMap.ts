import type { ChartOverlays } from "../types";

export type OperationMode = "dry_run" | "paper" | "live";

const SWING_CHART_OVERLAYS: ChartOverlays = {
  price: ["ema50", "ema200"],
  panels: [
    { id: "rsi", series: ["rsi_14"], levels: ["rsi_oversold", "rsi_overbought"] },
    { id: "macd", series: ["macd", "macd_signal"], histogram: "macd_histogram" },
  ],
};

export const SECURITIES_CHART_OVERLAYS: Record<string, ChartOverlays | undefined> = {
  swing_signals: SWING_CHART_OVERLAYS,
};

export function chartOverlaysForStrategy(strategyId: string): ChartOverlays | undefined {
  return SECURITIES_CHART_OVERLAYS[strategyId];
}

export const SECURITIES_STRATEGY_WORKFLOW: Record<string, Partial<Record<OperationMode, string>>> = {
  swing_signals: {
    dry_run: "securities-swing-dry-run",
    paper: "securities-swing-paper",
    live: "securities-swing-paper",
  },
  index_dca: { paper: "securities-dca-sandbox" },
  factor_sleeve: { paper: "securities-factor-sleeve" },
  bond_ladder: { paper: "bond-ladder-flow" },
};

export const SECURITIES_STRATEGY_MODES: Record<string, OperationMode[]> = {
  swing_signals: ["dry_run", "paper", "live"],
  index_dca: ["paper"],
  factor_sleeve: ["paper"],
  bond_ladder: ["paper"],
};

export const MULTI_SYMBOL_STRATEGIES = new Set(["swing_signals", "factor_sleeve"]);

export const ISS_SCAN_STRATEGIES = new Set(["swing_signals", "factor_sleeve"]);

export function supportsIssScan(strategyId: string): boolean {
  return ISS_SCAN_STRATEGIES.has(strategyId);
}

export const SECURITIES_STRATEGY_INTERVAL: Record<string, string> = {
  swing_signals: "1d",
  index_dca: "1d",
  factor_sleeve: "1d",
  bond_ladder: "1d",
};

export function chartIntervalForStrategy(strategyId: string): string {
  return SECURITIES_STRATEGY_INTERVAL[strategyId] ?? "1d";
}

export function resolveSecuritiesWorkflow(strategyId: string, operationMode: OperationMode): string {
  return SECURITIES_STRATEGY_WORKFLOW[strategyId]?.[operationMode] ?? "";
}

export function supportsMultiSymbol(strategyId: string): boolean {
  return MULTI_SYMBOL_STRATEGIES.has(strategyId);
}

export function instanceSymbols(inst: { symbols?: string[]; symbol: string }): string[] {
  if (inst.symbols?.length) return inst.symbols.map((s) => s.toUpperCase());
  return inst.symbol ? [inst.symbol.toUpperCase()] : [];
}

export function symbolsShortLabel(inst: { symbol: string; symbols?: string[] }): string {
  const syms = instanceSymbols(inst);
  if (syms.length === 0) return "—";
  if (syms.length === 1) return syms[0];
  if (syms.length <= 3) return syms.join(", ");
  return `${syms[0]} +${syms.length - 1}`;
}

export function strategyTabLabel(strategyId: string, t: (key: string) => string): string {
  const full = t(`strategies.${strategyId}.label` as "strategies.swing_signals.label");
  return full.replace(/\s*\(MOEX\)\s*/i, "").trim();
}

export function automationTabLabel(
  inst: { name?: string; symbol: string; symbols?: string[]; strategy_id: string },
  t: (key: string) => string,
): string {
  return `${strategyTabLabel(inst.strategy_id, t)} · ${symbolsShortLabel(inst)}`;
}

export function symbolsFingerprint(symbols: string[]): string {
  return [...new Set(symbols.map((s) => s.toUpperCase()))].sort().join("|");
}

export function isDuplicateAutomationInstance(
  instances: Array<{ strategy_id: string; symbols?: string[]; symbol: string }>,
  strategyId: string,
  symbols: string[],
): boolean {
  const fp = symbolsFingerprint(symbols);
  return instances.some(
    (i) => i.strategy_id === strategyId && symbolsFingerprint(instanceSymbols(i)) === fp,
  );
}
