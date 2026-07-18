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

export type MarkerPinTone = "buy" | "sell" | "block" | "skip" | "info" | "neutral";

export type MarkerPin = {
  id: string;
  time: number;
  left: number;
  top: number;
  label: string;
  summary: string;
  tone: MarkerPinTone;
  marker: ChartMarker;
};

const ORDER_KINDS = new Set([
  "order_buy",
  "order_sell",
  "order_fail",
  "fill_buy",
  "fill_sell",
]);

const IMPORTANT_STAGES = new Set(["order", "fill", "llm", "guardrails", "news"]);

/** Pipeline noise — hidden from the price chart (shown on the activity strip instead). */
export function isPriceChartMarker(marker: ChartMarker): boolean {
  const stage = marker.stage ?? "";
  const decision = marker.decision ?? "";
  const kind = marker.kind ?? "";
  const label = marker.short_label || marker.text || "";

  if (kind === "news" || stage === "news") return true;
  if (stage === "order" || stage === "fill") return true;
  if (stage === "guardrails" && decision !== "approve") return true;
  if (stage === "filter" && decision === "reject") return true;
  if (label === "FAIL" || kind.includes("fail")) return true;

  if (stage === "signal" || stage === "risk" || stage === "llm") return false;
  if (stage === "filter" && decision !== "reject") return false;
  if (stage === "guardrails" && decision === "approve") return false;
  if (label === "OK" || label === "SKIP" || label === "PASS" || label === "LLM+" || label === "LLM-") {
    return false;
  }
  if (label.startsWith("SKIP×") || label.startsWith("PASS×") || label.startsWith("SIG×")) return false;

  return false;
}

export function filterPriceChartMarkers(markers: ChartMarker[]): ChartMarker[] {
  return markers.filter(isPriceChartMarker);
}

const PIN_HEIGHT = 18;
const PIN_GAP = 3;
const PIN_MIN_WIDTH = 34;
const CHAR_WIDTH = 6.5;

function markerLabel(marker: ChartMarker): string {
  return marker.short_label || marker.text || marker.stage.toUpperCase();
}

function markerSummary(marker: ChartMarker): string {
  const parts: string[] = [];
  if (marker.summary) parts.push(marker.summary);
  if (marker.reject_reason && !marker.summary?.includes(marker.reject_reason)) {
    parts.push(marker.reject_reason);
  }
  if (marker.counter_thesis) parts.push(marker.counter_thesis);
  const stage = marker.stage ? `${marker.stage}/${marker.decision ?? "—"}` : "";
  if (!parts.length && stage) parts.push(stage);
  return parts.join(" · ") || stage || markerLabel(marker);
}

export function markerPinTone(marker: ChartMarker): MarkerPinTone {
  const label = markerLabel(marker);
  const kind = marker.kind ?? "";
  if (label === "BUY" || kind.includes("buy")) return "buy";
  if (label === "SOLD" || kind.includes("sell")) return "sell";
  if (label === "BLOCK" || label === "LLM-" || kind.includes("guardrails")) return "block";
  if (label === "SKIP" || label === "REJECT" || marker.decision === "skip" || marker.decision === "reject") {
    return "skip";
  }
  if (label.startsWith("SKIP×") || label.startsWith("PASS×")) return "skip";
  if (label === "NEWS" || label === "SIGNAL" || label === "SIZE" || label === "LLM+" || kind === "news") {
    return "info";
  }
  return "neutral";
}

function intervalToSeconds(interval?: string): number {
  switch (interval?.toLowerCase()) {
    case "1m":
      return 60;
    case "5m":
      return 300;
    case "15m":
      return 900;
    case "30m":
      return 1800;
    case "1h":
      return 3600;
    case "2h":
      return 7200;
    case "4h":
      return 14400;
    case "1d":
      return 86400;
    default:
      return 300;
  }
}

function isRoutineMarker(marker: ChartMarker): boolean {
  if (IMPORTANT_STAGES.has(marker.stage)) return false;
  if (marker.stage === "filter" && marker.decision === "reject") return false;
  return marker.stage === "signal" || marker.stage === "filter" || marker.stage === "risk";
}

function stagePriority(marker: ChartMarker): number {
  switch (marker.stage) {
    case "fill":
      return 100;
    case "order":
      return 90;
    case "llm":
      return 80;
    case "guardrails":
      return 70;
    case "filter":
      return marker.decision === "reject" ? 65 : 40;
    case "risk":
      return 50;
    case "signal":
      return 10;
    default:
      return 30;
  }
}

function nearestCandle(candles: Candle[], time: number): Candle | undefined {
  if (!candles.length) return undefined;
  let best = candles[0];
  let bestDist = Math.abs(time - best.time);
  for (const c of candles) {
    const dist = Math.abs(time - c.time);
    if (dist < bestDist) {
      best = c;
      bestDist = dist;
    }
  }
  return best;
}

/** Align event time to nearest candle (fixes testnet events vs mainnet OHLC mismatch). */
export function snapMarkerTime(
  time: number,
  candles: Candle[],
  interval?: string,
  maxSnapSec = 86400 * 14,
): number {
  if (!candles.length) return time;
  if (candles.some((c) => c.time === time)) return time;
  const nearest = nearestCandle(candles, time);
  if (!nearest) return time;
  if (Math.abs(time - nearest.time) > maxSnapSec) return nearest.time;
  return nearest.time;
}

function collapseBucket(group: ChartMarker[]): ChartMarker[] {
  const important = group.filter((m) => !isRoutineMarker(m));
  if (important.length) {
    const routine = group.filter((m) => isRoutineMarker(m));
    const rejects = routine.filter((m) => m.stage === "filter" && m.decision === "reject");
    return [...important, ...rejects];
  }

  const filters = group.filter((m) => m.stage === "filter");
  if (filters.length) {
    const rep = filters[0];
    if (filters.length === 1) return [rep];
    const label = markerLabel(rep);
    const suffix = label === "REJECT" ? "REJECT" : "SKIP";
    return [
      {
        ...rep,
        id: `${rep.id}-bucket`,
        short_label: `${suffix}×${filters.length}`,
        text: `${suffix}×${filters.length}`,
        summary: `${markerSummary(rep)} · ${filters.length} ticks`,
      },
    ];
  }

  const signals = group.filter((m) => m.stage === "signal");
  if (signals.length === 1) return [signals[0]];
  if (signals.length > 1) {
    const rep = signals[0];
    return [
      {
        ...rep,
        id: `${rep.id}-bucket`,
        short_label: `SIG×${signals.length}`,
        text: `SIG×${signals.length}`,
        summary: `${signals.length} signal checks`,
      },
    ];
  }

  return group.slice(0, 1);
}

function aggregateSameCandle(markers: ChartMarker[]): ChartMarker[] {
  const byTime = new Map<number, ChartMarker[]>();
  for (const m of markers) {
    const list = byTime.get(m.time) ?? [];
    list.push(m);
    byTime.set(m.time, list);
  }

  const out: ChartMarker[] = [];
  for (const [, group] of byTime) {
    const important = group.filter((m) => !isRoutineMarker(m));
    const routine = group.filter((m) => isRoutineMarker(m));

    out.push(...important);

    if (routine.length === 0) continue;
    if (routine.length === 1) {
      out.push(routine[0]);
      continue;
    }

    const rejects = routine.filter((m) => m.stage === "filter" && m.decision === "reject");
    const skips = routine.filter((m) => !(m.stage === "filter" && m.decision === "reject"));

    if (rejects.length) out.push(...rejects);

    if (skips.length === 1) {
      out.push(skips[0]);
    } else if (skips.length > 1) {
      const rep = skips.find((m) => m.stage === "filter") ?? skips[0];
      const label = markerLabel(rep) === "REJECT" ? "SKIP" : markerLabel(rep);
      const short = label.startsWith("SKIP") || label === "PASS" ? `SKIP×${skips.length}` : `×${skips.length}`;
      out.push({
        ...rep,
        id: `${rep.id}-agg`,
        short_label: short,
        text: short,
        summary: `${markerSummary(rep)} · ${skips.length} no-entry checks`,
      });
    }
  }

  return out.sort((a, b) => a.time - b.time);
}

/** Snap, dedupe pipeline noise, aggregate crowded bars. */
export function prepareChartMarkers(
  markers: ChartMarker[],
  candles: Candle[],
  interval?: string,
): ChartMarker[] {
  if (!markers.length) return [];

  const bucketSec = intervalToSeconds(interval);
  const snapped = markers.map((m) => ({
    ...m,
    time: snapMarkerTime(m.time, candles, interval),
  }));

  const bucketMap = new Map<number, ChartMarker[]>();
  for (const m of snapped) {
    const bucket = Math.round(m.time / bucketSec) * bucketSec;
    const list = bucketMap.get(bucket) ?? [];
    list.push(m);
    bucketMap.set(bucket, list);
  }

  const collapsed: ChartMarker[] = [];
  for (const [, group] of bucketMap) {
    collapsed.push(...collapseBucket(group));
  }

  return aggregateSameCandle(collapsed);
}

function pinWidth(label: string): number {
  return Math.max(PIN_MIN_WIDTH, label.length * CHAR_WIDTH + 12);
}

function rectsOverlap(
  a: { left: number; top: number; right: number; bottom: number },
  b: { left: number; top: number; right: number; bottom: number },
  pad = 2,
): boolean {
  return !(
    a.right + pad < b.left ||
    a.left - pad > b.right ||
    a.bottom + pad < b.top ||
    a.top - pad > b.bottom
  );
}

export function layoutMarkerPinsAvoidOverlap(pins: MarkerPin[]): MarkerPin[] {
  if (pins.length <= 1) return pins;

  const sorted = [...pins].sort((a, b) => a.left - b.left || stagePriority(b.marker) - stagePriority(a.marker));
  const placed: Array<{ left: number; top: number; right: number; bottom: number }> = [];
  const laid: MarkerPin[] = [];

  for (const pin of sorted) {
    const w = pinWidth(pin.label);
    const h = PIN_HEIGHT;
    let left = pin.left;
    let top = pin.top;

    for (let attempt = 0; attempt < 32; attempt += 1) {
      const rect = {
        left: left - w / 2,
        top: top - h / 2,
        right: left + w / 2,
        bottom: top + h / 2,
      };
      const hit = placed.some((p) => rectsOverlap(p, rect));
      if (!hit) {
        placed.push(rect);
        laid.push({ ...pin, left, top });
        break;
      }
      if (attempt % 4 === 0) top -= h + PIN_GAP;
      else if (attempt % 4 === 1) top += h + PIN_GAP;
      else if (attempt % 4 === 2) left += w * 0.55;
      else left -= w * 0.55;
    }
  }

  return laid;
}

function candleAtTime(candles: Candle[], time: number): Candle | undefined {
  return candles.find((c) => c.time === time) ?? nearestCandle(candles, time);
}

/** @deprecated use buildMarkerPins */
export function buildSignalHighlights(
  markers: ChartMarker[],
  candles: Candle[],
): SignalHighlight[] {
  const highlights: SignalHighlight[] = [];
  for (const marker of markers) {
    if (!ORDER_KINDS.has(marker.kind)) continue;
    const side = markerPinTone(marker) === "sell" ? "sell" : "buy";
    const candle = candleAtTime(candles, marker.time);
    if (!candle) continue;
    highlights.push({
      id: marker.id,
      time: marker.time,
      low: candle.low,
      high: candle.high,
      label: markerLabel(marker),
      side,
      marker,
    });
  }
  return highlights;
}

export function buildMarkerPins(
  markers: ChartMarker[],
  candles: Candle[],
  coords: {
    timeToX: (time: number) => number | null;
    priceToY: (price: number) => number | null;
  },
  interval?: string,
): MarkerPin[] {
  const prepared = prepareChartMarkers(markers, candles, interval);
  const byTime = new Map<number, ChartMarker[]>();

  for (const m of prepared) {
    const list = byTime.get(m.time) ?? [];
    list.push(m);
    byTime.set(m.time, list);
  }

  const rawPins: MarkerPin[] = [];

  for (const [time, group] of byTime) {
    const candle = candleAtTime(candles, time);
    if (!candle) continue;
    const x = coords.timeToX(time);
    if (x == null) continue;

    const sorted = [...group].sort((a, b) => stagePriority(b) - stagePriority(a));

    sorted.forEach((marker, index) => {
      const preferBelow =
        marker.position === "belowBar" ||
        markerPinTone(marker) === "buy" ||
        (marker.position !== "aboveBar" && index % 2 === 0);

      const lane = Math.floor(index / 2);
      const stackOffset = lane * (PIN_HEIGHT + PIN_GAP);

      let anchorY: number | null = null;
      if (preferBelow) {
        anchorY = coords.priceToY(candle.low);
        if (anchorY != null) anchorY += 10 + stackOffset;
      } else {
        anchorY = coords.priceToY(candle.high);
        if (anchorY != null) anchorY -= 12 + stackOffset;
      }
      if (anchorY == null) return;

      rawPins.push({
        id: `${marker.id}-${index}`,
        time,
        left: x,
        top: anchorY,
        label: markerLabel(marker),
        summary: markerSummary(marker),
        tone: markerPinTone(marker),
        marker,
      });
    });
  }

  return layoutMarkerPinsAvoidOverlap(rawPins);
}

/** No native chart dots — labels rendered as HTML pins only. */
export function markersForSeries(_markers: ChartMarker[]): ChartMarker[] {
  return [];
}
