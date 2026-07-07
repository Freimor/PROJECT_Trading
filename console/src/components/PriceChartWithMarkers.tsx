import { useEffect, useRef } from "react";
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

type Props = {
  candles: Candle[];
  markers: ChartMarker[];
  height?: number;
  interval?: string;
  symbol?: string;
  onMarkerClick?: (marker: ChartMarker) => void;
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
  const fitKeyRef = useRef("");

  markersRef.current = markers;

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
      }
    };
    onResize();
    window.addEventListener("resize", onResize);

    chart.subscribeClick((param) => {
      if (!onMarkerClick || !param.time) return;
      const t = param.time as number;
      const hit = markersRef.current.find((m) => m.time === t);
      if (hit) onMarkerClick(hit);
    });

    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [height, onMarkerClick, interval]);

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
    seriesRef.current.setMarkers(markers.map(toSeriesMarker));

    const fitKey = `${symbol ?? ""}:${interval ?? ""}`;
    if (fitKey !== fitKeyRef.current && candles.length > 0) {
      fitKeyRef.current = fitKey;
      chartRef.current?.timeScale().fitContent();
    }
  }, [candles, markers, symbol, interval]);

  return <div ref={containerRef} className="price-chart" />;
}
