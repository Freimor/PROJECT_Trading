import { useEffect, useRef } from "react";
import {
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type UTCTimestamp,
} from "lightweight-charts";

export type EquityCurvePoint = {
  time: number;
  equity: number;
  cash?: number;
  position_value?: number;
  event?: string;
  side?: string;
  notional?: number | null;
  symbol?: string;
};

export type AutomationEquityCurve = {
  status: string;
  currency?: string;
  session_capital?: number | null;
  current_equity?: number;
  pnl_abs?: number;
  pnl_pct?: number | null;
  points?: EquityCurvePoint[];
  trades?: Array<{
    event_at?: string;
    side?: string;
    notional?: number | null;
    symbol?: string;
    currency?: string;
  }>;
};

type Props = {
  data: AutomationEquityCurve | null;
  loading?: boolean;
  height?: number;
  t: (key: string, vars?: Record<string, string | number>) => string;
};

function fmtMoney(value: number | null | undefined, currency: string): string {
  if (value == null || Number.isNaN(value)) return "—";
  const unit = currency === "RUB" ? "₽" : currency;
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${unit}`;
}

export default function AutomationEquityChart({ data, loading, height = 150, t }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const baselineRef = useRef<ISeriesApi<"Line"> | null>(null);

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
      timeScale: { borderColor: "#243044", timeVisible: true, secondsVisible: false },
      handleScroll: { mouseWheel: false, pressedMouseMove: true },
      handleScale: { mouseWheel: false, pinch: false },
    });

    const series = chart.addLineSeries({
      color: "#3dd68c",
      lineWidth: 2,
      priceLineVisible: true,
      lastValueVisible: true,
      title: t("workspace.equitySeries"),
    });

    const baseline = chart.addLineSeries({
      color: "#6e7681",
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    chartRef.current = chart;
    seriesRef.current = series;
    baselineRef.current = baseline;

    const onResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    onResize();
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      baselineRef.current = null;
    };
  }, [height, t]);

  useEffect(() => {
    const series = seriesRef.current;
    const baseline = baselineRef.current;
    const chart = chartRef.current;
    if (!series || !baseline || !chart) return;

    const points = data?.points ?? [];
    if (!points.length) {
      series.setData([]);
      baseline.setData([]);
      return;
    }

    const lineData: LineData[] = points.map((p) => ({
      time: p.time as UTCTimestamp,
      value: p.equity,
    }));
    series.setData(lineData);

    const cap = data?.session_capital;
    if (cap != null && cap > 0) {
      baseline.setData(
        points.map((p) => ({
          time: p.time as UTCTimestamp,
          value: cap,
        })),
      );
    } else {
      baseline.setData([]);
    }

    chart.timeScale().fitContent();
  }, [data]);

  if (loading) {
    return <p className="muted small automation-equity-empty">{t("common.loading")}</p>;
  }

  if (!data || data.status === "inactive" || !(data.points?.length ?? 0)) {
    return (
      <p className="muted small automation-equity-empty">{t("workspace.equityEmpty")}</p>
    );
  }

  const currency = data.currency ?? "USDT";
  const pnl = data.pnl_abs ?? 0;
  const pnlPct = data.pnl_pct;
  const pnlClass = pnl > 0 ? "pnl-up" : pnl < 0 ? "pnl-down" : "pnl-flat";
  const pnlText =
    pnlPct != null
      ? `${pnl >= 0 ? "+" : ""}${fmtMoney(pnl, currency)} (${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(2)}%)`
      : `${pnl >= 0 ? "+" : ""}${fmtMoney(pnl, currency)}`;

  return (
    <div className="automation-equity-wrap">
      <div className="automation-equity-head">
        <div>
          <span className="automation-equity-title">{t("workspace.equityTitle")}</span>
          <span className="muted small automation-equity-hint">{t("workspace.equityHint")}</span>
        </div>
        <div className="automation-equity-summary">
          <strong>{fmtMoney(data.current_equity, currency)}</strong>
          <span className={pnlClass}>{pnlText}</span>
        </div>
      </div>
      <div ref={containerRef} className="automation-equity-chart" style={{ height }} />
      {data.trades?.length ? (
        <ul className="automation-equity-trades muted small">
          {[...data.trades].reverse().slice(0, 5).map((tr, i) => (
            <li key={`${tr.event_at}-${i}`}>
              {tr.side === "SELL" ? t("workspace.equitySell") : t("workspace.equityBuy")}{" "}
              {tr.symbol}
              {tr.notional != null ? ` · ${fmtMoney(tr.notional, tr.currency ?? currency)}` : ""}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
