/** Единые интервалы опроса API (мс). Консоль — мониторинг, не тикер. */
export const POLL = {
  /** Один раз при монтировании (справочники, план калибровки). */
  STATIC: 0,
  /** Статус-бар, automation overview. */
  OVERVIEW: 120_000,
  /** Дашборды crypto / host / funnel. */
  DASHBOARD: 120_000,
  /** Binance balances. */
  WALLET: 180_000,
  /** T-Invest portfolio / status. */
  PORTFOLIO: 180_000,
  /** Свечи на графике. */
  CHART: 120_000,
  /** Маркеры на графике. */
  MARKERS: 60_000,
  /** Журнал событий, LLM audit. */
  EVENTS: 60_000,
  /** Лента системных уведомлений. */
  ACTIVITY: 60_000,
  /** Equity curve. */
  EQUITY: 180_000,
  /** n8n workflows, paper, benchmark. */
  OPS: 120_000,
  /** Активный автомат в работе — сводка, stats, кошелёк. */
  TICK: 20_000,
  /** Ожидающие подтверждения админа. */
  PENDING: 60_000,
} as const;

export function staggerMs(key: string, maxMs = 4_000): number {
  let hash = 0;
  for (let i = 0; i < key.length; i += 1) {
    hash = (hash * 31 + key.charCodeAt(i)) | 0;
  }
  return Math.abs(hash) % maxMs;
}
