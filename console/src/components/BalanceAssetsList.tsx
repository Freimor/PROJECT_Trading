import { fmtAmount, type BalanceRow } from "../utils/balances";
import { formatMoexPosition } from "../utils/moex";

type MoexPosition = { ticker?: string; quantity?: number; avg_price?: number };

type Props = {
  title?: string;
  balances?: BalanceRow[];
  positions?: MoexPosition[];
  cashRubLabel?: string;
  piecesLabel?: string;
  maxHeight?: string;
};

export default function BalanceAssetsList({
  title,
  balances,
  positions,
  cashRubLabel = "рубли на счёте",
  piecesLabel = "шт.",
  maxHeight = "11rem",
}: Props) {
  const balanceRows = balances ?? [];
  const moexRows =
    positions?.filter((p) => p.ticker !== "RUB000UTSTOM" || (p.quantity ?? 0) > 0) ?? [];

  const count = balanceRows.length || moexRows.length;
  if (count === 0) return null;

  return (
    <div className="balance-assets-block">
      {title ? <div className="balance-assets-title">{title}</div> : null}
      <ul className="balance-list compact balance-list-scroll" style={{ maxHeight }}>
        {balanceRows.map((b) => (
          <li key={b.asset}>
            <span>{b.asset}</span>
            <span>{fmtAmount(b.total ?? b.free, b.asset === "USDT" ? 2 : 4)}</span>
          </li>
        ))}
        {moexRows.map((p) => {
          const row = formatMoexPosition(p.ticker, p.quantity, p.avg_price, {
            cashRub: cashRubLabel,
            pieces: piecesLabel,
          });
          return (
            <li key={p.ticker}>
              <span>{row.label}</span>
              <span>{row.value}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
