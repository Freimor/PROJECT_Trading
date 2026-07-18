type Props = {
  min: number;
  max: number;
  recommended?: number | null;
  value?: number | null;
  recLabel: string;
  formatValue: (value: number | null | undefined) => string;
};

export default function ScanParamScale({ min, max, recommended, value, recLabel, formatValue }: Props) {
  const span = max - min;
  if (!Number.isFinite(span) || span <= 0) return null;
  const clampPct = (n: number) => Math.max(0, Math.min(100, ((n - min) / span) * 100));
  const valNum = value != null && Number.isFinite(Number(value)) ? Number(value) : null;
  const recNum = recommended != null && Number.isFinite(Number(recommended)) ? Number(recommended) : null;

  return (
    <div className="scalp-param-scale" aria-hidden>
      <div className="scalp-param-scale-track">
        {recNum != null ? (
          <span
            className="scalp-param-scale-rec"
            style={{ left: `${clampPct(recNum)}%` }}
            title={`${recLabel}: ${formatValue(recNum)}`}
          />
        ) : null}
        {valNum != null ? (
          <span className="scalp-param-scale-val" style={{ left: `${clampPct(valNum)}%` }} />
        ) : null}
      </div>
      <div className="scalp-param-scale-labels">
        <span>{formatValue(min)}</span>
        {recNum != null ? (
          <span className="scalp-param-scale-rec-label">
            {recLabel}: {formatValue(recNum)}
          </span>
        ) : (
          <span />
        )}
        <span>{formatValue(max)}</span>
      </div>
    </div>
  );
}
