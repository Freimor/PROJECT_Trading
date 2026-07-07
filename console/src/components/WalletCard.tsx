import PortfolioCard from "./PortfolioCard";
import { fmtAmount, normalizeBalances, type BalancesResponse } from "../utils/balances";

type Props = {
  data: BalancesResponse | null;
  loading?: boolean;
  highlightAssets?: string[];
};

export default function WalletCard({
  data,
  loading,
  highlightAssets = ["USDT", "BTC", "ETH", "BNB"],
}: Props) {
  const { rows, status, message } = normalizeBalances(data ?? undefined);

  return (
    <PortfolioCard title="Кошелёк Binance testnet">
      {loading && !data && <p className="muted small">Загрузка баланса…</p>}
      {status === "empty" && (
        <p className="muted small">{message ?? "Пусто или нет API-ключей testnet в .env"}</p>
      )}
      {status === "ok" && (
        <>
          {highlightAssets.map((asset) => {
            const row = rows.find((b) => b.asset === asset);
            return (
              <div className="metric-row" key={asset}>
                <span>{asset}</span>
                <strong>{fmtAmount(row?.free, asset === "USDT" ? 2 : 6)}</strong>
              </div>
            );
          })}
          {rows.length > highlightAssets.length && (
            <ul className="balance-list compact">
              {rows
                .filter((b) => !highlightAssets.includes(b.asset))
                .slice(0, 5)
                .map((b) => (
                  <li key={b.asset}>
                    <span>{b.asset}</span>
                    <span>{fmtAmount(b.free)}</span>
                  </li>
                ))}
            </ul>
          )}
          <p className="muted small">Активов с балансом: {rows.length}</p>
        </>
      )}
    </PortfolioCard>
  );
}
