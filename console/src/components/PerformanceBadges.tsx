type Metric = {
  current?: number | null;
  baseline?: number | null;
  change_all_pct?: number | null;
  change_recent_pct?: number | null;
  recent_label?: string;
  currency?: string;
};

export function fmtPct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

function pctClass(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "perf-neutral";
  if (value > 0) return "perf-up";
  if (value < 0) return "perf-down";
  return "perf-neutral";
}

type Props = {
  metric?: Metric | null;
  showAllTime?: boolean;
  showRecent?: boolean;
};

export default function PerformanceBadges({
  metric,
  showAllTime = true,
  showRecent = true,
}: Props) {
  if (!metric) return null;

  const hasAll = metric.change_all_pct != null;
  const hasRecent = metric.change_recent_pct != null;
  if (!hasAll && !hasRecent) return null;

  return (
    <div className="perf-badges">
      {showAllTime && hasAll && (
        <span className={`perf-badge ${pctClass(metric.change_all_pct)}`} title="Относительно стартового счёта">
          всё время {fmtPct(metric.change_all_pct)}
        </span>
      )}
      {showRecent && hasRecent && (
        <span
          className={`perf-badge ${pctClass(metric.change_recent_pct)}`}
          title={`За последние ${metric.recent_label ?? "2ч"}`}
        >
          {metric.recent_label ?? "2ч"} {fmtPct(metric.change_recent_pct)}
        </span>
      )}
    </div>
  );
}
