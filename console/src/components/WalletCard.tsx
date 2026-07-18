import PortfolioCard from "./PortfolioCard";
import { normalizeBalances, type BalancesResponse } from "../utils/balances";
import BalanceAssetsList from "./BalanceAssetsList";
import { useI18n } from "../i18n/LanguageContext";

type Props = {
  data: BalancesResponse | null;
  loading?: boolean;
};

export default function WalletCard({ data, loading }: Props) {
  const { t } = useI18n();
  const { rows, status, message } = normalizeBalances(data ?? undefined);

  return (
    <PortfolioCard title="Кошелёк Binance testnet">
      {loading && !data && <p className="muted small">{t("common.loading")}</p>}
      {status === "empty" && (
        <p className="muted small">{message ?? t("overview.emptyTestnet")}</p>
      )}
      {status === "ok" && (
        <>
          <BalanceAssetsList title={t("overview.allAssets")} balances={rows} />
          <p className="muted small">
            {t("overview.assetsWithBalance")}: {rows.length}
          </p>
        </>
      )}
    </PortfolioCard>
  );
}
