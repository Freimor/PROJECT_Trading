import { fmtAmount } from "../../utils/balances";
import type { CryptoInstanceWallet, CryptoInstanceWalletRow } from "../../types/cryptoAutomation";

type TFn = (k: string, vars?: Record<string, string | number>) => string;

function rowLabel(row: CryptoInstanceWalletRow, t: TFn): string {
  switch (row.label) {
    case "session_budget":
      return t("cryptoAutomation.walletSessionBudget");
    case "futures_margin":
      return t("cryptoAutomation.walletFuturesMargin");
    case "futures_position":
      return t("cryptoAutomation.walletFuturesPosition");
    case "session_position":
      return t("cryptoAutomation.walletSessionPosition");
    case "session_quote_available":
      return t("cryptoAutomation.walletQuoteAvailable");
    default:
      return row.asset;
  }
}

function fmtRowValue(row: CryptoInstanceWalletRow): string {
  const qty = fmtAmount(row.quantity, row.asset.includes("USDT") ? 2 : 4);
  if (row.label === "futures_position" && row.entry_price != null) {
    return `${qty} @ ${Number(row.entry_price).toFixed(4)}`;
  }
  return qty;
}

type Props = {
  wallet?: CryptoInstanceWallet | null;
  loading?: boolean;
  t: TFn;
};

export default function AutomationWalletPanel({ wallet, loading, t }: Props) {
  const rows = wallet?.rows ?? [];

  return (
    <div className="automation-wallet-panel">
      <h4 className="automation-wallet-title">{t("cryptoAutomation.localWallet")}</h4>
      {loading && !wallet ? <p className="muted small">{t("common.loading")}</p> : null}
      {!loading && rows.length === 0 ? (
        <p className="muted small">{t("cryptoAutomation.walletEmpty")}</p>
      ) : (
        <ul className="balance-list compact balance-list-scroll automation-wallet-list">
          {rows.map((row) => (
            <li key={`${row.asset}-${row.label ?? "x"}`}>
              <span>{rowLabel(row, t)}</span>
              <span>
                {fmtRowValue(row)}
                {row.usdt_value != null && row.label !== "session_budget" ? (
                  <span className="muted small"> · ≈{fmtAmount(row.usdt_value, 2)} USDT</span>
                ) : null}
                {row.unrealized_pnl != null ? (
                  <span className="muted small"> · PnL {fmtAmount(Number(row.unrealized_pnl), 2)}</span>
                ) : null}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
