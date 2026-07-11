import { useEffect, useState, type RefObject } from "react";

export type AutoChartLayout = {
  chartHeight: number;
  panelHeight: number;
  needsScroll: boolean;
};

const CHART_MIN = 300;
const PANEL_MIN = 72;
const PANEL_MAX = 132;
const LEGEND_OVERHEAD = 48;

function clamp(n: number, min: number, max: number): number {
  if (!Number.isFinite(n)) return min;
  return Math.max(min, Math.min(max, Math.round(n)));
}

function viewportChartFallback(panelCount: number): number {
  if (typeof window === "undefined") return 480;
  return Math.round(window.innerHeight * (panelCount > 0 ? 0.5 : 0.42));
}

export function computeAutoChartLayout(
  availableHeight: number,
  panelCount: number,
): AutoChartLayout {
  let slotHeight = availableHeight;
  if (slotHeight <= 0) {
    slotHeight = viewportChartFallback(panelCount);
  }

  const usable = slotHeight - LEGEND_OVERHEAD;
  const minContent = CHART_MIN + panelCount * PANEL_MIN;

  if (usable < minContent) {
    return { chartHeight: CHART_MIN, panelHeight: PANEL_MIN, needsScroll: true };
  }

  const panelsBudget = panelCount > 0 ? Math.round(usable * 0.34) : 0;
  const panelHeight =
    panelCount > 0
      ? clamp(Math.round(panelsBudget / panelCount), PANEL_MIN, PANEL_MAX)
      : PANEL_MIN;
  const chartHeight = clamp(usable - panelCount * panelHeight, CHART_MIN, 960);

  return { chartHeight, panelHeight, needsScroll: false };
}

/** Fit chart + indicator panels to the chart slot; scroll when viewport is too small. */
export function useAutoChartLayout(
  slotRef: RefObject<HTMLElement | null>,
  panelCount: number,
): AutoChartLayout {
  const [layout, setLayout] = useState<AutoChartLayout>(() =>
    computeAutoChartLayout(0, panelCount),
  );

  useEffect(() => {
    const el = slotRef.current;
    if (!el) return;

    const measure = () => {
      const height = el.clientHeight;
      setLayout(computeAutoChartLayout(height, panelCount));
    };

    measure();
    const ro = new ResizeObserver(() => {
      requestAnimationFrame(measure);
    });
    ro.observe(el);
    window.addEventListener("resize", measure);

    return () => {
      ro.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [slotRef, panelCount]);

  return layout;
}
