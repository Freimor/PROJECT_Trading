import { useI18n } from "../i18n/LanguageContext";

export type TradingProductBadge = {
  market_type?: string;
  is_futures?: boolean;
  allow_short?: boolean;
  leverage?: number;
  margin_mode?: string;
};

export default function TradingProductPill({ product }: { product: TradingProductBadge }) {
  const { t } = useI18n();
  const isFutures = Boolean(product.is_futures);
  const parts: string[] = [
    isFutures ? t("strategySubsettings.productFutures") : t("strategySubsettings.productSpot"),
  ];
  if (isFutures) {
    parts.push(`${product.leverage ?? 1}x`);
    parts.push(product.margin_mode === "cross" ? "Cross" : "Isolated");
  }
  if (product.allow_short) parts.push("Short");
  return (
    <span className={`automation-product-pill ${isFutures ? "futures" : "spot"}`}>
      {parts.join(" · ")}
    </span>
  );
}
