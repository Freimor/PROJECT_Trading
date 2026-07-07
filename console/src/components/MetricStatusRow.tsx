import StatusDot from "./StatusDot";

type Props = {
  label: string;
  tone?: "ok" | "warn" | "danger" | "neutral" | "off";
  children?: React.ReactNode;
};

/** Metric row with optional status dot on the right. */
export default function MetricStatusRow({ label, tone, children }: Props) {
  return (
    <div className="metric-row metric-row-dot">
      <span>{label}</span>
      {children ?? (tone ? <StatusDot tone={tone} /> : <span>—</span>)}
    </div>
  );
}
