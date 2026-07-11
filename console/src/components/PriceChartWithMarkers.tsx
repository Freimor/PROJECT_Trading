import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ColorType,
  createChart,
  TickMarkType,
  type IChartApi,
  type ISeriesApi,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import type { Candle, ChartIndicators, ChartMarker, ChartOverlays } from "../types";
import {
  buildSignalHighlights,
  markersForSeries,
  type SignalHighlight,
} from "../utils/chartSignals";

type Props = {
  candles: Candle[];
  markers: ChartMarker[];
  height?: number;
  panelHeight?: number;
  interval?: string;
  symbol?: string;
  overlays?: ChartOverlays;
  indicators?: ChartIndicators;
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

const DEFAULT_PANEL_HEIGHT = 96;

const OVERLAY_COLORS: Record<string, string> = {
  ema50: "#f0a030",
  ema200: "#5b9cf5",
  rsi_14: "#9b7ede",
  macd: "#3dd68c",
  macd_signal: "#ff6b6b",
};

const OVERLAY_LABELS: Record<string, string> = {
  ema50: "EMA50",
  ema200: "EMA200",
  rsi_14: "RSI(14)",
  macd: "MACD",
  macd_signal: "Signal",
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
  return ["1m", "5m", "15m", "30m", "1h", "2h", "4h"].includes(interval ?? "");
}

function barSpacingForInterval(interval?: string): number {
  switch (interval) {
    case "1m":
      return 4;
    case "5m":
      return 6;
    case "15m":
      return 8;
    case "30m":
      return 9;
    case "1h":
      return 10;
    case "2h":
      return 11;
    case "4h":
      return 12;
    case "1d":
      return 14;
    default:
      return 10;
  }
}

function formatChartTime(time: number, interval?: string, tickMarkType?: TickMarkType): string {
  const d = new Date(time * 1000);
  const mark = tickMarkType ?? TickMarkType.Time;

  if (showSeconds(interval)) {
    if (mark === TickMarkType.Year || mark === TickMarkType.Month) {
      return d.toLocaleDateString(undefined, { month: "short", year: "2-digit" });
    }
    return d.toLocaleString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: showSeconds(interval) ? "2-digit" : undefined,
    });
  }

  if (isHourlyOrFiner(interval)) {
    if (mark === TickMarkType.Year) return String(d.getFullYear());
    if (mark === TickMarkType.Month) return d.toLocaleDateString(undefined, { month: "short" });
    if (mark === TickMarkType.DayOfMonth) return String(d.getDate());
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  if (mark === TickMarkType.Year) return String(d.getFullYear());
  if (mark === TickMarkType.Month) return d.toLocaleDateString(undefined, { month: "short" });
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function crosshairTimeFormatter(interval?: string) {
  return (time: number) => formatChartTime(time, interval);
}

function timeScaleOptions(interval?: string) {
  const spacing = barSpacingForInterval(interval);
  return {
    timeVisible: true,
    secondsVisible: showSeconds(interval),
    barSpacing: spacing,
    minBarSpacing: Math.max(2, spacing - 4),
    tickMarkFormatter: (time: UTCTimestamp, tickMarkType: TickMarkType) =>
      formatChartTime(time as number, interval, tickMarkType),
  };
}

function chartBaseOptions(height: number, interval?: string) {
  return {
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
    timeScale: timeScaleOptions(interval),
    localization: {
      timeFormatter: crosshairTimeFormatter(interval),
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
  };
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
    const boxHeight = Math.max(Math.abs(yBottom - yTop), 12);

    boxes.push({
      id: h.id,
      left: x - boxWidth / 2,
      top: top - 18,
      width: boxWidth,
      height: boxHeight + 18,
      label: h.label,
      side: h.side,
      marker: h.marker,
    });
  }

  return boxes;
}

function bindChartSync(leader: IChartApi, followers: IChartApi[]) {
  const handler = (range: Parameters<Parameters<IChartApi["timeScale"]["subscribeVisibleLogicalRangeChange"]>[0]>[0]) => {
    if (!range) return;
    for (const chart of followers) {
      chart.timeScale().setVisibleLogicalRange(range);
    }
  };
  leader.timeScale().subscribeVisibleLogicalRangeChange(handler);
  return () => leader.timeScale().unsubscribeVisibleLogicalRangeChange(handler);
}

/** fitContent uses candle count; indicator panels may have fewer points (e.g. MACD warmup). */
function syncPanelsToMain(mainChart: IChartApi, panels: IChartApi[]) {
  const range = mainChart.timeScale().getVisibleLogicalRange();
  if (!range) return;
  for (const chart of panels) {
    chart.timeScale().setVisibleLogicalRange(range);
  }
}

function fitMainAndSyncPanels(mainChart: IChartApi, panels: IChartApi[]) {
  mainChart.timeScale().fitContent();
  syncPanelsToMain(mainChart, panels);
}

export default function PriceChartWithMarkers({
  candles,
  markers,
  height = 420,
  panelHeight = DEFAULT_PANEL_HEIGHT,
  interval,
  symbol,
  overlays,
  indicators,
  onMarkerClick,
}: Props) {
  const mainContainerRef = useRef<HTMLDivElement>(null);
  const panelContainerRefs = useRef<(HTMLDivElement | null)[]>([]);
  const chartRef = useRef<IChartApi | null>(null);
  const panelChartsRef = useRef<IChartApi[]>([]);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const priceOverlaySeriesRef = useRef<ISeriesApi<"Line">[]>([]);
  const markersRef = useRef(markers);
  const highlightsRef = useRef<SignalHighlight[]>([]);
  const fitKeyRef = useRef("");
  const [overlayBoxes, setOverlayBoxes] = useState<OverlayBox[]>([]);

  const panels = overlays?.panels ?? [];
  const priceOverlays = overlays?.price ?? [];

  const highlights = useMemo(() => buildSignalHighlights(markers, candles), [markers, candles]);
  const seriesMarkers = useMemo(() => markersForSeries(markers), [markers]);

  const legendItems = useMemo(() => {
    const items: Array<{ key: string; label: string; color: string }> = [];
    for (const key of priceOverlays) {
      items.push({
        key,
        label: OVERLAY_LABELS[key] ?? key,
        color: OVERLAY_COLORS[key] ?? "#9fb0c7",
      });
    }
    for (const panel of panels) {
      for (const key of panel.series) {
        items.push({
          key: `${panel.id}:${key}`,
          label: OVERLAY_LABELS[key] ?? key,
          color: OVERLAY_COLORS[key] ?? "#9fb0c7",
        });
      }
      if (panel.histogram) {
        items.push({
          key: `${panel.id}:${panel.histogram}`,
          label: "Hist",
          color: "#6e7681",
        });
      }
    }
    return items;
  }, [panels, priceOverlays]);

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
    if (!mainContainerRef.current) return;

    const mainChart = createChart(mainContainerRef.current, chartBaseOptions(height, interval));
    const candleSeries = mainChart.addCandlestickSeries({
      upColor: "#3dd68c",
      downColor: "#ff6b6b",
      borderVisible: false,
      wickUpColor: "#3dd68c",
      wickDownColor: "#ff6b6b",
    });

    chartRef.current = mainChart;
    seriesRef.current = candleSeries;
    priceOverlaySeriesRef.current = [];

    const onResize = () => {
      if (mainContainerRef.current) {
        mainChart.applyOptions({ width: mainContainerRef.current.clientWidth });
      }
      refreshOverlays();
    };
    onResize();
    window.addEventListener("resize", onResize);

    const onRange = () => refreshOverlays();
    mainChart.timeScale().subscribeVisibleLogicalRangeChange(onRange);

    mainChart.subscribeClick((param) => {
      if (!onMarkerClick || !param.time) return;
      const t = param.time as number;
      const hit =
        markersRef.current.find((m) => m.time === t) ??
        highlightsRef.current.find((h) => h.time === t)?.marker;
      if (hit) onMarkerClick(hit);
    });

    return () => {
      window.removeEventListener("resize", onResize);
      mainChart.timeScale().unsubscribeVisibleLogicalRangeChange(onRange);
      mainChart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      priceOverlaySeriesRef.current = [];
    };
  }, [height, onMarkerClick, refreshOverlays, interval]);

  useEffect(() => {
    const mainChart = chartRef.current;
    if (!mainChart || panels.length === 0) {
      for (const chart of panelChartsRef.current) chart.remove();
      panelChartsRef.current = [];
      return;
    }

    const subCharts: IChartApi[] = [];
    const unsubs: Array<() => void> = [];

    for (let i = 0; i < panels.length; i++) {
      const el = panelContainerRefs.current[i];
      if (!el) continue;
      const panelChart = createChart(el, {
        ...chartBaseOptions(panelHeight, interval),
        timeScale: {
          ...timeScaleOptions(interval),
          visible: i === panels.length - 1,
        },
      });
      const panel = panels[i];

      if (indicators) {
        for (const key of panel.series) {
          const points = indicators.series[key];
          if (!points?.length) continue;
          const line = panelChart.addLineSeries({
            color: OVERLAY_COLORS[key] ?? "#9fb0c7",
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: key === panel.series[0],
            title: OVERLAY_LABELS[key] ?? key,
          });
          line.setData(
            points.map((p) => ({
              time: p.time as UTCTimestamp,
              value: p.value,
            })),
          );
          for (const levelKey of panel.levels ?? []) {
            const level = indicators.levels[levelKey];
            if (level == null) continue;
            line.createPriceLine({
              price: level,
              color: "#6e7681",
              lineWidth: 1,
              lineStyle: 2,
              axisLabelVisible: true,
              title: levelKey.includes("oversold") ? "OS" : "OB",
            });
          }
        }

        if (panel.histogram) {
          const hist = indicators.series[panel.histogram];
          if (hist?.length) {
            const histSeries = panelChart.addHistogramSeries({
              priceFormat: { type: "price", precision: 4, minMove: 0.0001 },
            });
            histSeries.setData(
              hist.map((p) => ({
                time: p.time as UTCTimestamp,
                value: p.value,
                color: p.value >= 0 ? "rgba(61, 214, 140, 0.55)" : "rgba(255, 107, 107, 0.55)",
              })),
            );
          }
        }
      }

      subCharts.push(panelChart);
    }

    panelChartsRef.current = subCharts;

    if (subCharts.length > 0) {
      unsubs.push(bindChartSync(mainChart, subCharts));
      unsubs.push(bindChartSync(subCharts[subCharts.length - 1], [mainChart, ...subCharts.slice(0, -1)]));
      fitMainAndSyncPanels(mainChart, subCharts);
    }

    const onResize = () => {
      for (let i = 0; i < subCharts.length; i++) {
        const el = panelContainerRefs.current[i];
        if (el) subCharts[i].applyOptions({ width: el.clientWidth, height: panelHeight });
      }
    };
    onResize();
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      for (const unsub of unsubs) unsub();
      for (const chart of subCharts) chart.remove();
      panelChartsRef.current = [];
    };
  }, [panels, indicators, interval, panelHeight]);

  useEffect(() => {
    fitKeyRef.current = "";
    chartRef.current?.applyOptions({
      timeScale: timeScaleOptions(interval),
      localization: {
        timeFormatter: crosshairTimeFormatter(interval),
      },
    });
    if (candles.length > 0 && chartRef.current) {
      fitMainAndSyncPanels(chartRef.current, panelChartsRef.current);
    }
  }, [interval, candles.length]);

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
      const mainChart = chartRef.current;
      if (mainChart) {
        fitMainAndSyncPanels(mainChart, panelChartsRef.current);
      }
    }

    refreshOverlays();
  }, [candles, seriesMarkers, symbol, interval, refreshOverlays]);

  useEffect(() => {
    const mainChart = chartRef.current;
    if (!mainChart || !indicators) return;

    for (const line of priceOverlaySeriesRef.current) {
      mainChart.removeSeries(line);
    }
    priceOverlaySeriesRef.current = [];

    for (const key of priceOverlays) {
      const points = indicators.series[key];
      if (!points?.length) continue;
      const line = mainChart.addLineSeries({
        color: OVERLAY_COLORS[key] ?? "#9fb0c7",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: true,
        title: OVERLAY_LABELS[key] ?? key,
      });
      line.setData(
        points.map((p) => ({
          time: p.time as UTCTimestamp,
          value: p.value,
        })),
      );
      priceOverlaySeriesRef.current.push(line);
    }
  }, [indicators, priceOverlays]);

  useEffect(() => {
    refreshOverlays();
  }, [highlights, refreshOverlays]);

  return (
    <div className="price-chart-wrap">
      {legendItems.length > 0 ? (
        <div className="chart-indicator-legend" aria-hidden="true">
          {legendItems.map((item) => (
            <span key={item.key} className="chart-legend-item">
              <span className="chart-legend-swatch" style={{ background: item.color }} />
              {item.label}
            </span>
          ))}
        </div>
      ) : null}
      <div ref={mainContainerRef} className="price-chart" style={{ height }} />
      {panels.map((panel, index) => (
        <div key={panel.id} className="chart-indicator-panel">
          <span className="chart-panel-label">{panel.id.toUpperCase()}</span>
          <div
            ref={(el) => {
              panelContainerRefs.current[index] = el;
            }}
            className="price-chart price-chart-panel"
            style={{ height: panelHeight }}
          />
        </div>
      ))}
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
