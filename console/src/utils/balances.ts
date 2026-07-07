export type BalanceRow = { asset: string; free: number; locked: number; total?: number };

export type BalancesResponse = {
  status?: string;
  message?: string;
  balances?: BalanceRow[];
  total_assets?: number;
  testnet?: boolean;
};

/** API may return legacy raw array or structured object. */
export function normalizeBalances(data: BalancesResponse | BalanceRow[] | null | undefined): {
  rows: BalanceRow[];
  status: string;
  message?: string;
} {
  if (!data) return { rows: [], status: "loading" };
  if (Array.isArray(data)) {
    const rows = data
      .map((b) => ({
        asset: b.asset,
        free: Number(b.free),
        locked: Number(b.locked ?? 0),
        total: Number(b.free) + Number(b.locked ?? 0),
      }))
      .filter((b) => b.free > 0 || b.locked > 0);
    return { rows, status: rows.length ? "ok" : "empty" };
  }
  if (data.status === "empty" || data.status === "error") {
    return { rows: [], status: data.status, message: data.message };
  }
  return {
    rows: data.balances ?? [],
    status: data.status ?? "ok",
    message: data.message,
  };
}

export function fmtAmount(value: number | undefined, digits = 4): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (value >= 1000) return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
  return value.toFixed(digits);
}
