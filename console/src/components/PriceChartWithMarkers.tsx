import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import type { Candle, ChartMarker } from "../types";
import {
  buildSignalHighlights,
  markersForSeries,
  type SignalHighlight,
} from "../utils/chartSignals";

type Props = {
  candles: Candle[];
  markers: ChartMarker[];
  height?: number;
  interval?: string;
  symbol?: string;
  onMarkerClick?: (marker: ChartMarker) => void;
};

type OverlayBox = {
  id: string;
  left: number;
  top: number;
  width: number;
  height: number;
  label: string;
  side: "buy" | "sell";
  marker: ChartMarker;
};

function toSeriesMarker(m: ChartMarker): SeriesMarker<Time> {
  return {
    time: m.time as UTCTimestamp,
    position: m.position as SeriesMarker<Time>["position"],
    shape: m.shape as SeriesMarker<Time>["shape"],
    color: m.color,
    text: m.text,
    id: m.id,
  };
}

function showSeconds(interval?: string): boolean {
  return ["1m", "5m", "15m"].includes(interval ?? "");
}

function isHourlyOrFiner(interval?: string): boolean {
  return ["1m", "5m", "15m", "30m", "1h", "2h"].includes(interval ?? "");
}

function layoutHighlights(
  chart: IChartApi,
  series: ISeriesApi<"Candlestick">,
  highlights: SignalHighlight[],
): OverlayBox[] {
  const timeScale = chart.timeScale();
  const barSpacing = timeScale.options().barSpacing ?? 6;
  const boxWidth = Math.max(barSpacing * 2.4, 18);
  const boxes: OverlayBox[] = [];

  for (const h of highlights) {
    const x = timeScale.timeToCoordinate(h.time as UTCTimestamp);
    const yTop = series.priceToCoordinate(h.high);
    const yBottom = series.priceToCoordinate(h.low);
    if (x === null || yTop === null || yBottom === null) continue;

    const top = Math.min(yTop, yBottom);
    const height = Math.max(Math.abs(yBottom - yTop), 12);

    boxes.push({
      id: h.id,
      left: x - boxWidth / 2,
      top: top - 18,
      width: boxWidth,
      height: height + 18,
      label: h.label,
      side: h.side,
      marker: h.marker,
    });
  }

  return boxes;
}

export default function PriceChartWithMarkers({
  candles,
  markers,
  height = 420,
  interval,
  symbol,
  onMarkerClick,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const markersRef = useRef(markers);
  const highlightsRef = useRef<SignalHighlight[]>([]);
  const fitKeyRef = useRef("");
  const [overlayBoxes, setOverlayBoxes] = useState<OverlayBox[]>([]);

  const highlights = useMemo(() => buildSignalHighlights(markers, candles), [markers, candles]);
  const seriesMarkers = useMemo(() => markersForSeries(markers), [markers]);

  markersRef.current = markers;
  highlightsRef.current = highlights;

  const refreshOverlays = useCallback(() => {
    const chart = chartRef.current;
    const series = seriesRef.current;
    if (!chart || !series || highlightsRef.current.length === 0) {
      setOverlayBoxes([]);
      return;
    }
    setOverlayBoxes(layoutHighlights(chart, series, highlightsRef.current));
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: "#0b1017" },
        textColor: "#9fb0c7",
      },
      grid: {
        vertLines: { color: "#1e2a3a" },
        horzLines: { color: "#1e2a3a" },
      },
      rightPriceScale: { borderColor: "#243044" },
      timeScale: {
        borderColor: "#243044",
        timeVisible: true,
        secondsVisible: showSeconds(interval),
      },
      localization: {
        timeFormatter: (time: number) => {
          const d = new Date(time * 1000);
          if (showSeconds(interval)) {
            return d.toLocaleString(undefined, {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            });
          }
          if (isHourlyOrFiner(interval)) {
            return d.toLocaleString(undefined, {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            });
          }
          return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
        },
      },
      handleScale: {
        axisPressedMouseMove: { time: true, price: true },
        mouseWheel: true,
        pinch: true,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
      },
    });

    const series = chart.addCandlestickSeries({
      upColor: "#3dd68c",
      downColor: "#ff6b6b",
      borderVisible: false,
      wickUpColor: "#3dd68c",
      wickDownColor: "#ff6b6b",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const onResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
        refreshOverlays();
      }
    };
    onResize();
    window.addEventListener("resize", onResize);

    const onRange = () => refreshOverlays();
    chart.timeScale().subscribeVisibleLogicalRangeChange(onRange);

    chart.subscribeClick((param) => {
      if (!onMarkerClick || !param.time) return;
      const t = param.time as number;
      const hit =
        markersRef.current.find((m) => m.time === t) ??
        highlightsRef.current.find((h) => h.time === t)?.marker;
      if (hit) onMarkerClick(hit);
    });

    return () => {
      window.removeEventListener("resize", onResize);
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(onRange);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [height, onMarkerClick, interval, refreshOverlays]);

  useEffect(() => {
    chartRef.current?.applyOptions({
      timeScale: {
        timeVisible: true,
        secondsVisible: showSeconds(interval),
      },
      localization: {
        timeFormatter: (time: number) => {
          const d = new Date(time * 1000);
          if (showSeconds(interval)) {
            return d.toLocaleString(undefined, {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            });
          }
          if (isHourlyOrFiner(interval)) {
            return d.toLocaleString(undefined, {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            });
          }
          return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
        },
      },
    });
  }, [interval]);

  useEffect(() => {
    if (!seriesRef.current) return;
    seriesRef.current.setData(
      candles.map((c) => ({
        time: c.time as UTCTimestamp,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      })),
    );
    seriesRef.current.setMarkers(seriesMarkers.map(toSeriesMarker));

    const fitKey = `${symbol ?? ""}:${interval ?? ""}`;
    if (fitKey !== fitKeyRef.current && candles.length > 0) {
      fitKeyRef.current = fitKey;
      chartRef.current?.timeScale().fitContent();
    }

    refreshOverlays();
  }, [candles, seriesMarkers, symbol, interval, refreshOverlays]);

  useEffect(() => {
    refreshOverlays();
  }, [highlights, refreshOverlays]);

  return (
    <div className="price-chart-wrap">
      <div ref={containerRef} className="price-chart" />
      {overlayBoxes.length > 0 ? (
        <div className="chart-signal-overlays" aria-hidden="true">
          {overlayBoxes.map((box) => (
            <button
              key={box.id}
              type="button"
              className={`chart-signal-box ${box.side}`}
              style={{
                left: `${box.left}px`,
                top: `${box.top}px`,
                width: `${box.width}px`,
                height: `${box.height}px`,
              }}
              title={box.label}
              onClick={() => onMarkerClick?.(box.marker)}
            >
              <span className="chart-signal-label">{box.label}</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
