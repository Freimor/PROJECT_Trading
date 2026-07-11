import type { WorkflowSessionStats } from "../types";

type TFn = (k: string, vars?: Record<string, string | number>) => string;

function formatMoneyDelta(delta: number | null | undefined, currency?: string): string | null {
  if (delta == null || Number.isNaN(delta)) return null;
  const sign = delta > 0 ? "+" : "";
  const abs = Math.abs(delta);
  const compact =
    abs >= 1_000_000
      ? `${(delta / 1_000_000).toFixed(1)}M`
      : abs >= 10_000
        ? `${(delta / 1_000).toFixed(1)}k`
        : abs >= 100
          ? `${sign}${Math.round(delta)}`
          : `${sign}${delta.toFixed(1)}`;
  const cur = currency === "RUB" ? "₽" : currency === "USDT" ? "USDT" : currency ?? "";
  return cur ? `${compact} ${cur}` : compact;
}

function formatPct(pct: number | null | undefined): string | null {
  if (pct == null || Number.isNaN(pct)) return null;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

function formatAgo(sec: number | null | undefined, t: TFn): string | null {
  if (sec == null || sec < 0) return null;
  if (sec < 60) return t("controlStrip.agoSeconds", { s: Math.max(1, Math.round(sec)) });
  if (sec < 3600) return t("controlStrip.agoMinutes", { m: Math.floor(sec / 60) });
  return t("controlStrip.agoHours", { h: Math.floor(sec / 3600) });
}

function pnlDirection(session?: WorkflowSessionStats | null): "up" | "down" | "flat" {
  const d = session?.pnl_direction;
  if (d === "up" || d === "down") return d;
  return "flat";
}

export function WorkflowSessionMetrics({
  session,
  t,
}: {
  session?: WorkflowSessionStats | null;
  t: TFn;
}) {
  if (!session || session.status === "inactive") return null;

  const direction = pnlDirection(session);
  const money = formatMoneyDelta(session.pnl_delta, session.currency);
  const pct = formatPct(session.pnl_pct);
  const ordersOk = session.orders_ok ?? 0;
  const ordersFailed = session.orders_failed ?? 0;
  const signals = session.signals ?? 0;
  const openPos = session.open_positions ?? 0;
  const maxPos = session.max_open_positions;
  const ago = formatAgo(session.last_event_ago_sec, t);

  const midParts: string[] = [];
  if (session.pnl_source === "session_trades") {
    midParts.push(t("controlStrip.sessionPnlTrades"));
  }
  if (session.session_capital != null && session.session_capital > 0) {
    const cur = session.currency === "RUB" ? "₽" : session.currency === "USDT" ? "USDT" : "";
    midParts.push(
      t("controlStrip.sessionCapital", {
        amount: Math.round(session.session_capital),
        currency: cur,
      }),
    );
  }
  if (pct) midParts.push(pct);
  if (ordersOk > 0 || ordersFailed > 0) {
    midParts.push(
      ordersFailed > 0
        ? t("controlStrip.ordersMixed", { ok: ordersOk, fail: ordersFailed })
        : t("controlStrip.ordersOk", { n: ordersOk }),
    );
  } else {
    midParts.push(t("controlStrip.ordersNone"));
  }
  if (maxPos != null && maxPos > 0) {
    midParts.push(t("controlStrip.positions", { n: openPos, max: maxPos }));
  }

  const bottomParts: string[] = [t("controlStrip.signals", { n: signals })];
  if (ago) bottomParts.push(ago);
  if (session.last_event_symbol && session.last_event_stage) {
    const sym = String(session.last_event_symbol).replace("USDT", "");
    bottomParts.push(`${sym} · ${session.last_event_stage}`);
  }

  return (
    <div className="control-strip-wf-metrics" aria-label={t("controlStrip.sessionMetrics")}>
      <div className={`control-strip-wf-pnl-primary pnl-${direction}`}>
        {money ?? (pct ?? "—")}
      </div>
      <div className="control-strip-wf-pnl-sub">{midParts.join(" · ")}</div>
      <div className="control-strip-wf-pnl-sub muted">{bottomParts.join(" · ")}</div>
    </div>
  );
}
