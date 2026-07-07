type Tone = "ok" | "warn" | "danger" | "neutral" | "off";

type Props = {
  tone?: Tone;
  title?: string;
};

/** Colored status indicator (replaces OK / online / подключён text). */
export default function StatusDot({ tone = "neutral", title }: Props) {
  return <span className={`status-dot dot-${tone}`} title={title} aria-hidden={title ? undefined : true} />;
}

export function isPositiveStatusLabel(label: string): boolean {
  const n = label.trim().toLowerCase();
  return ["ok", "online", "подключён", "подключен", "connected", "open", "открыта"].includes(n);
}

export function labelToDotTone(label: string, explicit?: Tone): Tone {
  if (explicit) return explicit;
  const n = label.trim().toLowerCase();
  if (isPositiveStatusLabel(n)) return "ok";
  if (["closed", "закрыта", "error", "empty", "off", "выключен"].includes(n)) return "warn";
  if (["critical", "fail", "failed"].includes(n)) return "danger";
  return "neutral";
}
