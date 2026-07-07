import { useEffect, useRef } from "react";
import { ColorType, createChart, type UTCTimestamp } from "lightweight-charts";

type Point = { time: number; value: number };

type Props = {
  data: Point[];
  height?: number;
  color?: string;
  title?: string;
};

export default function EquityMiniChart({
  data,
  height = 140,
  color = "#5b9cf5",
  title,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || !data.length) return;

    const chart = createChart(ref.current, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: "#0b1017" },
        textColor: "#9fb0c7",
      },
      grid: { vertLines: { visible: false }, horzLines: { color: "#1e2a3a" } },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
      handleScroll: false,
      handleScale: false,
    });

    const series = chart.addLineSeries({ color, lineWidth: 2 });
    series.setData(
      data.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })),
    );
    chart.timeScale().fitContent();

    const onResize = () => {
      if (ref.current) chart.applyOptions({ width: ref.current.clientWidth });
    };
    onResize();
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
    };
  }, [data, height, color]);

  if (!data.length) {
    return <p className="muted small">Нет истории equity. Сделайте paper snapshot.</p>;
  }

  return (
    <div>
      {title && <div className="chart-mini-title muted">{title}</div>}
      <div ref={ref} className="equity-mini-chart" />
    </div>
  );
}
