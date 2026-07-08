import type { Candle, ChartMarker } from "../types";

export type SignalHighlight = {
  id: string;
  time: number;
  low: number;
  high: number;
  label: string;
  side: "buy" | "sell";
  marker: ChartMarker;
};

const HIGHLIGHT_KINDS = new Set([
  "order_buy",
  "order_sell",
  "fill_buy",
  "fill_sell",
]);

function envLabel(env: string): string {
  return /live/i.test(env) ? "Live" : "Demo";
}

function sideFromMarker(marker: ChartMarker): "buy" | "sell" | null {
  if (marker.kind.includes("sell")) return "sell";
  if (marker.kind.includes("buy")) return "buy";
  return null;
}

function candleAtTime(candles: Candle[], time: number): Candle | undefined {
  return candles.find((c) => c.time === time);
}

export function buildSignalHighlights(
  markers: ChartMarker[],
  candles: Candle[],
): SignalHighlight[] {
  const highlights: SignalHighlight[] = [];

  for (const marker of markers) {
    if (!HIGHLIGHT_KINDS.has(marker.kind)) continue;
    const side = sideFromMarker(marker);
    if (!side) continue;

    const candle = candleAtTime(candles, marker.time);
    if (!candle) continue;

    const label =
      marker.text && marker.text.includes("|")
        ? marker.text
        : `${envLabel(marker.env)} | ${side === "buy" ? "BUY" : "SELL"}`;

    highlights.push({
      id: marker.id,
      time: marker.time,
      low: candle.low,
      high: candle.high,
      label,
      side,
      marker,
    });
  }

  return highlights;
}

export function markersForSeries(markers: ChartMarker[]): ChartMarker[] {
  return markers
    .filter((m) => !HIGHLIGHT_KINDS.has(m.kind))
    .map((m) => ({
      ...m,
      text: m.text || m.stage,
      shape: m.shape === "circle" && m.kind.startsWith("llm") ? "square" : m.shape,
    }));
}
