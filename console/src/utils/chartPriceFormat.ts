import type { Candle } from "../types";

export type ChartPriceFormat = {
  type: "price";
  precision: number;
  minMove: number;
};

/** Match lightweight-charts price scale to asset price (avoids 0.00 on sub-dollar alts). */
export function priceFormatForCandles(candles: Candle[]): ChartPriceFormat {
  const closes = candles.map((c) => c.close).filter((c) => Number.isFinite(c) && c > 0);
  if (!closes.length) {
    return { type: "price", precision: 2, minMove: 0.01 };
  }
  const sorted = [...closes].sort((a, b) => a - b);
  const median = sorted[Math.floor(sorted.length / 2)];

  if (median >= 1000) return { type: "price", precision: 2, minMove: 0.01 };
  if (median >= 100) return { type: "price", precision: 3, minMove: 0.001 };
  if (median >= 10) return { type: "price", precision: 3, minMove: 0.001 };
  if (median >= 1) return { type: "price", precision: 4, minMove: 0.0001 };
  if (median >= 0.1) return { type: "price", precision: 5, minMove: 0.00001 };
  if (median >= 0.01) return { type: "price", precision: 6, minMove: 0.000001 };
  if (median >= 0.001) return { type: "price", precision: 7, minMove: 0.0000001 };
  return { type: "price", precision: 8, minMove: 0.00000001 };
}

/** Drop invalid OHLC rows that break autoscale. */
export function sanitizeCandles(candles: Candle[]): Candle[] {
  const out: Candle[] = [];
  let prevTime = -1;
  for (const c of candles) {
    if (!Number.isFinite(c.time) || c.time <= 0) continue;
    const { open, high, low, close } = c;
    if (![open, high, low, close].every((v) => Number.isFinite(v) && v > 0)) continue;
    if (high < low) continue;
    if (c.time <= prevTime) continue;
    out.push(c);
    prevTime = c.time;
  }
  return out;
}
