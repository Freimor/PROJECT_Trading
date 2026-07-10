import type { StrategyInfo } from "../types";

function formatSymbols(symbols: string[], market: "crypto" | "securities", max = 6): string {
  if (!symbols.length) return "—";
  const labels =
    market === "crypto"
      ? symbols.slice(0, max).map((s) => s.replace(/USDT$/i, ""))
      : symbols.slice(0, max);
  let text = labels.join(", ");
  if (symbols.length > max) text += ` (+${symbols.length - max})`;
  return text;
}

export function strategyRationale(
  strategy: StrategyInfo,
  lang: "ru" | "en",
): string | undefined {
  if (lang === "en" && strategy.rationale_en) return strategy.rationale_en;
  return strategy.rationale_ru;
}

export function strategyDescription(
  strategy: StrategyInfo,
  lang: "ru" | "en",
  market: "crypto" | "securities",
): string {
  if (lang === "en" && strategy.description_en) return strategy.description_en;
  if (lang === "ru" && strategy.description) return strategy.description;
  if (lang === "en" && strategy.description) return strategy.description;

  const label = formatSymbols(strategy.symbols ?? [], market);
  if (market === "crypto") {
    return lang === "en"
      ? `Looks for setups on active USDT pairs: ${label}. Edit the list in «Workflow quotes».`
      : `Ищет возможности на активных USDT-парах: ${label}. Список — в «Котировки workflow».`;
  }
  return lang === "en"
    ? `Trades stocks from the active watchlist (${label}). Tickers are managed in «Workflow quotes».`
    : `Торговля акциями из активного списка (${label}). Список — в «Котировки workflow».`;
}
