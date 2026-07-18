import type { TradingProductBadge } from "../components/TradingProductPill";

export type MarketType = "spot" | "usdt_futures";
export type MarginMode = "isolated" | "cross";

export function instanceMarketType(cfg: Record<string, unknown> | undefined | null): MarketType {
  return cfg?.market_type === "usdt_futures" ? "usdt_futures" : "spot";
}

export function isDuplicateAutomationInstance(
  instances: Array<{ strategy_id: string; symbol: string; session_config?: Record<string, unknown> }>,
  strategyId: string,
  symbol: string,
  marketType: MarketType,
): boolean {
  const sym = symbol.toUpperCase();
  return instances.some(
    (i) =>
      i.strategy_id === strategyId &&
      i.symbol.toUpperCase() === sym &&
      instanceMarketType(i.session_config) === marketType,
  );
}

export function marketTypeLabel(marketType: MarketType, t: (k: string) => string): string {
  return marketType === "usdt_futures"
    ? t("strategySubsettings.marketTypeFutures")
    : t("strategySubsettings.marketTypeSpot");
}

export function automationTabLabel(
  instance: {
    name?: string;
    symbol: string;
    session_config?: Record<string, unknown> | null;
  },
  t: (k: string) => string,
): string {
  const base = instance.symbol.replace(/USDT$/i, "") || instance.symbol;
  const market = marketTypeLabel(instanceMarketType(instance.session_config), t);
  return `${base} · ${market}`;
}

export function tradingProductFromSessionConfig(
  cfg: Record<string, unknown> | undefined | null,
): TradingProductBadge | null {
  if (!cfg) return null;
  const mt = cfg.market_type === "usdt_futures" ? "usdt_futures" : "spot";
  return {
    market_type: mt,
    is_futures: mt === "usdt_futures",
    allow_short: Boolean(cfg.allow_short),
    leverage: typeof cfg.leverage === "number" ? cfg.leverage : Number(cfg.leverage) || 1,
    margin_mode: cfg.margin_mode === "cross" ? "cross" : "isolated",
  };
}

export function tradingProductSummaryText(
  product: TradingProductBadge | null | undefined,
  t: (k: string) => string,
): string {
  if (!product) return "—";
  const isFutures = Boolean(product.is_futures);
  const parts: string[] = [
    isFutures ? t("strategySubsettings.productFutures") : t("strategySubsettings.productSpot"),
  ];
  if (isFutures) {
    parts.push(`${product.leverage ?? 1}x`);
    parts.push(product.margin_mode === "cross" ? "Cross" : "Isolated");
  }
  if (product.allow_short) parts.push("Short");
  return parts.join(" · ");
}
