import { useI18n } from "../i18n/LanguageContext";
import type { ChartMarker } from "../types";

export type MarkerFilters = {
  orders: boolean;
  fills: boolean;
  news: boolean;
};

export const DEFAULT_MARKER_FILTERS: MarkerFilters = {
  orders: true,
  fills: true,
  news: true,
};

export function filterChartMarkers(markers: ChartMarker[], filters: MarkerFilters): ChartMarker[] {
  return markers.filter((m) => {
    const kind = m.kind ?? "";
    const stage = m.stage ?? "";
    if (kind === "news" || stage === "news") return filters.news;
    if (kind.startsWith("order") || stage === "order") return filters.orders;
    if (kind.startsWith("fill") || stage === "fill") return filters.fills;
    if (stage === "guardrails" && m.decision !== "approve") return filters.orders;
    if (stage === "filter" && m.decision === "reject") return filters.orders;
    return false;
  });
}

type Props = {
  filters: MarkerFilters;
  onChange: (next: MarkerFilters) => void;
};

export default function ChartMarkerMenu({ filters, onChange }: Props) {
  const { t } = useI18n();

  const toggle = (key: keyof MarkerFilters) => {
    onChange({ ...filters, [key]: !filters[key] });
  };

  const items: { key: keyof MarkerFilters; label: string }[] = [
    { key: "orders", label: t("workspace.markersOrders") },
    { key: "fills", label: t("workspace.markersFills") },
    { key: "news", label: t("workspace.markersNews") },
  ];

  return (
    <div className="chart-marker-menu">
      {items.map(({ key, label }) => (
        <label key={key}>
          <input type="checkbox" checked={filters[key]} onChange={() => toggle(key)} />
          {label}
        </label>
      ))}
    </div>
  );
}
