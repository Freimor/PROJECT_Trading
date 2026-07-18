import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ColorType,
  createChart,
  TickMarkType,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { Candle, ChartIndicators, ChartMarker, ChartOverlays } from "../types";
import { buildMarkerPins, type MarkerPin } from "../utils/chartSignals";
import { priceFormatForCandles, sanitizeCandles } from "../utils/chartPriceFormat";

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

type MarkerPinBox = MarkerPin;

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

function layoutMarkerPins(
  chart: IChartApi,
  series: ISeriesApi<"Candlestick">,
  markers: ChartMarker[],
  candles: Candle[],
  interval?: string,
): MarkerPinBox[] {
  const timeScale = chart.timeScale();
  return buildMarkerPins(
    markers,
    candles,
    {
      timeToX: (time) => timeScale.timeToCoordinate(time as UTCTimestamp),
      priceToY: (price) => series.priceToCoordinate(price),
    },
    interval,
  );
}

function bindChartSync(leader: IChartApi, followers: IChartApi[]) {
  const handler = (range: Parameters<Parameters<IChartApi["timeScale"]["subscribeVisibleLogicalRangeChange"]>[0]>[0]) => {
    if (!range) return;
    for (const chart of followers) {
      try {
        chart.timeScale().setVisibleLogicalRange(range);
      } catch {
        // Panel may have fewer bars than main — ignore invalid range.
      }
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
  const markerPinsRef = useRef<MarkerPinBox[]>([]);
  const fitKeyRef = useRef("");
  const [markerPins, setMarkerPins] = useState<MarkerPinBox[]>([]);

  const panels = overlays?.panels ?? [];
  const priceOverlays = overlays?.price ?? [];
  const safeCandles = useMemo(() => sanitizeCandles(candles), [candles]);
  const priceFormat = useMemo(() => priceFormatForCandles(safeCandles), [safeCandles]);

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
  markerPinsRef.current = markerPins;

  const refreshOverlays = useCallback(() => {
    const chart = chartRef.current;
    const series = seriesRef.current;
    if (!chart || !series || markersRef.current.length === 0) {
      setMarkerPins([]);
      return;
    }
    setMarkerPins(layoutMarkerPins(chart, series, markersRef.current, safeCandles, interval));
  }, [safeCandles, interval]);

  useEffect(() => {
    if (!mainContainerRef.current) return;

    const mainChart = createChart(mainContainerRef.current, chartBaseOptions(height, interval));
    const candleSeries = mainChart.addCandlestickSeries({
      upColor: "#3dd68c",
      downColor: "#ff6b6b",
      borderVisible: false,
      wickUpColor: "#3dd68c",
      wickDownColor: "#ff6b6b",
      priceFormat,
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
        markerPinsRef.current.find((p) => p.time === t)?.marker;
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
  }, [height, onMarkerClick, refreshOverlays, interval, priceFormat]);

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
    chartRef.current?.applyOptions({
      timeScale: timeScaleOptions(interval),
      localization: {
        timeFormatter: crosshairTimeFormatter(interval),
      },
    });
  }, [interval]);

  useEffect(() => {
    if (!seriesRef.current) return;

    seriesRef.current.applyOptions({ priceFormat });
    seriesRef.current.setData(
      safeCandles.map((c) => ({
        time: c.time as UTCTimestamp,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      })),
    );
    seriesRef.current.setMarkers([]);

    const fitKey = `${symbol ?? ""}:${interval ?? ""}`;
    if (fitKey !== fitKeyRef.current && safeCandles.length > 0) {
      fitKeyRef.current = fitKey;
      const mainChart = chartRef.current;
      if (mainChart) {
        fitMainAndSyncPanels(mainChart, panelChartsRef.current);
      }
    }

    refreshOverlays();
  }, [safeCandles, symbol, interval, refreshOverlays, priceFormat]);

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
        priceFormat,
      });
      line.setData(
        points.map((p) => ({
          time: p.time as UTCTimestamp,
          value: p.value,
        })),
      );
      priceOverlaySeriesRef.current.push(line);
    }
  }, [indicators, priceOverlays, priceFormat]);

  useEffect(() => {
    refreshOverlays();
  }, [markers, safeCandles, refreshOverlays]);

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
      <div className="price-chart-main-wrap" style={{ position: "relative", height }}>
        <div ref={mainContainerRef} className="price-chart" style={{ height }} />
        {markerPins.length > 0 ? (
          <div className="chart-marker-pins" aria-hidden="true">
            {markerPins.map((pin) => (
              <button
                key={pin.id}
                type="button"
                className={`chart-marker-pin tone-${pin.tone}`}
                style={{
                  left: `${pin.left}px`,
                  top: `${pin.top}px`,
                }}
                onClick={() => onMarkerClick?.(pin.marker)}
              >
                <span className="chart-marker-pin-label">{pin.label}</span>
                <span className="chart-marker-tooltip" role="tooltip">
                  {pin.summary}
                </span>
              </button>
            ))}
          </div>
        ) : null}
      </div>
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
    </div>
  );
}
