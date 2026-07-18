/** Parse API ISO timestamp (UTC with offset or naive UTC). */
export function parseApiIso(iso: string): Date | null {
  if (!iso) return null;
  try {
    const normalized = iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`;
    const d = new Date(normalized);
    return Number.isNaN(d.getTime()) ? null : d;
  } catch {
    return null;
  }
}

/** Display API timestamp in the user's local timezone. */
export function formatIsoLocal(iso: string, locale = "ru-RU"): string {
  const d = parseApiIso(iso);
  if (!d) return iso.slice(0, 19).replace("T", " ");
  return d.toLocaleString(locale, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}
