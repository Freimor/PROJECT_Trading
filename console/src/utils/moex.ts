const RUB_TICKERS = new Set(["RUB000UTSTOM", "RUB", "SUR"]);

export function isRubCash(ticker?: string): boolean {
  if (!ticker) return false;
  return RUB_TICKERS.has(ticker.toUpperCase());
}

export function formatMoexPosition(
  ticker: string | undefined,
  quantity: number | undefined,
  avgPrice: number | undefined,
  labels: { cashRub: string; pieces: string },
): { label: string; value: string } {
  if (isRubCash(ticker)) {
    const rub = quantity ?? 0;
    return {
      label: labels.cashRub,
      value: `${rub.toLocaleString("ru-RU", { maximumFractionDigits: 2 })} ₽`,
    };
  }
  return {
    label: ticker ?? "?",
    value: `${quantity ?? 0} ${labels.pieces}${avgPrice != null ? ` @ ${avgPrice.toFixed(2)}` : ""}`,
  };
}

export function formatMoexNextOpen(
  t: (key: string, vars?: Record<string, string | number>) => string,
  nextOpen?: { kind?: string; time_msk?: string; weekday?: number },
  weekdays?: readonly string[],
): string | null {
  if (!nextOpen?.time_msk) return null;
  const weekdayName =
    nextOpen.weekday != null && weekdays ? weekdays[nextOpen.weekday] ?? "" : "";
  if (nextOpen.kind === "today") {
    return t("overview.moexOpensToday", { time: nextOpen.time_msk });
  }
  if (nextOpen.kind === "tomorrow") {
    return t("overview.moexOpensTomorrow", { time: nextOpen.time_msk });
  }
  if (nextOpen.kind === "weekday" && weekdayName) {
    return t("overview.moexOpensWeekday", { weekday: weekdayName, time: nextOpen.time_msk });
  }
  return null;
}
