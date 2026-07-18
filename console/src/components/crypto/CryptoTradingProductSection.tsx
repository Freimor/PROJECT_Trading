import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost, formatOperatorFacingError } from "../../api";
import { useI18n } from "../../i18n/LanguageContext";
import OperatorConfirmModal from "../OperatorConfirmModal";
import PortfolioCard from "../PortfolioCard";
import TradingProductPill from "../TradingProductPill";

type CryptoTradingProduct = {
  market_type?: "spot" | "usdt_futures";
  is_futures?: boolean;
  allow_short?: boolean;
  leverage?: number;
  max_leverage?: number;
  margin_mode?: "isolated" | "cross";
  runtime_override?: boolean;
};

type CryptoWorkflowSettings = {
  status?: string;
  trading_product?: CryptoTradingProduct;
};

type Props = {
  onChange?: () => void;
  /** When true, skip outer PortfolioCard (e.g. inside settings). */
  bare?: boolean;
};

export default function CryptoTradingProductSection({ onChange, bare = false }: Props) {
  const { t } = useI18n();
  const [settings, setSettings] = useState<CryptoWorkflowSettings | null>(null);
  const [marketType, setMarketType] = useState<"spot" | "usdt_futures">("spot");
  const [allowShort, setAllowShort] = useState(false);
  const [leverage, setLeverage] = useState(3);
  const [marginMode, setMarginMode] = useState<"isolated" | "cross">("isolated");
  const [opBusy, setOpBusy] = useState(false);
  const [opError, setOpError] = useState<string | null>(null);
  const [pendingProductApply, setPendingProductApply] = useState(false);
  const [pendingProductReset, setPendingProductReset] = useState(false);
  const [productModalKind, setProductModalKind] = useState<"market_type" | "params">("params");

  const syncTradingProduct = (tp?: CryptoTradingProduct) => {
    if (!tp) return;
    setMarketType(tp.market_type === "usdt_futures" ? "usdt_futures" : "spot");
    setAllowShort(Boolean(tp.allow_short));
    setLeverage(tp.leverage ?? 3);
    setMarginMode(tp.margin_mode === "cross" ? "cross" : "isolated");
  };

  const savedProduct = settings?.trading_product;
  const savedMarketType =
    savedProduct?.market_type === "usdt_futures" ? "usdt_futures" : "spot";

  const productParamsDirty = (() => {
    if (!savedProduct || marketType !== savedMarketType) return false;
    return (
      allowShort !== Boolean(savedProduct.allow_short) ||
      leverage !== (savedProduct.leverage ?? 3) ||
      marginMode !== (savedProduct.margin_mode === "cross" ? "cross" : "isolated")
    );
  })();

  const loadSettings = useCallback(async () => {
    const data = await apiGet<CryptoWorkflowSettings>("/api/crypto/workflow-settings");
    if (data.status === "ok") {
      setSettings(data);
      syncTradingProduct(data.trading_product);
    }
  }, []);

  useEffect(() => {
    loadSettings().catch(() => {});
  }, [loadSettings]);

  const cancelProductModal = () => {
    if (opBusy) return;
    syncTradingProduct(savedProduct);
    setPendingProductApply(false);
    setProductModalKind("params");
    setOpError(null);
  };

  const productModalRisk = (() => {
    const lines = [t("strategySubsettings.applyTradingProductRisk")];
    if (marketType === "usdt_futures") {
      lines.push(t("strategySubsettings.applyTradingProductFuturesDanger"));
    } else if (savedMarketType === "usdt_futures" && productModalKind === "market_type") {
      lines.push(t("strategySubsettings.switchToSpotWarning"));
    }
    return lines.join("\n\n");
  })();

  const applyTradingProduct = async (password: string) => {
    setOpBusy(true);
    setOpError(null);
    try {
      const resp = await apiPost<CryptoWorkflowSettings>(
        "/api/crypto/workflow-settings/trading-product",
        {
          market_type: marketType,
          allow_short: marketType === "usdt_futures" ? allowShort : false,
          leverage,
          margin_mode: marginMode,
          operator: "web:operator",
        },
        { operatorPassword: password },
      );
      if (resp.status === "ok") {
        setSettings(resp);
        syncTradingProduct(resp.trading_product);
        setPendingProductApply(false);
        setProductModalKind("params");
        onChange?.();
      }
    } catch (err) {
      setOpError(formatOperatorFacingError(err, t));
    } finally {
      setOpBusy(false);
    }
  };

  const resetTradingProduct = async (password: string) => {
    setOpBusy(true);
    setOpError(null);
    try {
      const resp = await apiPost<CryptoWorkflowSettings>(
        "/api/crypto/workflow-settings/trading-product/reset",
        {},
        { operatorPassword: password },
      );
      if (resp.status === "ok") {
        setSettings(resp);
        syncTradingProduct(resp.trading_product);
        setPendingProductReset(false);
        onChange?.();
      }
    } catch (err) {
      setOpError(formatOperatorFacingError(err, t));
    } finally {
      setOpBusy(false);
    }
  };

  const body = (
    <div className="crypto-trading-product-section">
      <div className="strategy-subsection-head">
        <p className="muted small">{t("strategySubsettings.tradingProductHint")}</p>
        {savedProduct ? (
          <div className="crypto-trading-product-current">
            <TradingProductPill product={savedProduct} />
            <span className="muted small">
              {savedProduct.runtime_override
                ? t("strategySubsettings.runtime")
                : t("strategySubsettings.defaultPreset")}
            </span>
          </div>
        ) : null}
      </div>

      <label className="modal-field">
        <span>{t("strategySubsettings.tradingProductTitle")}</span>
        <select
          className="input"
          value={marketType}
          disabled={opBusy}
          onChange={(e) => {
            const next = e.target.value as "spot" | "usdt_futures";
            if (next === savedMarketType) return;
            setMarketType(next);
            if (next === "spot") setAllowShort(false);
            setOpError(null);
            setProductModalKind("market_type");
            setPendingProductApply(true);
          }}
        >
          <option value="spot">{t("strategySubsettings.marketTypeSpot")}</option>
          <option value="usdt_futures">{t("strategySubsettings.marketTypeFutures")}</option>
        </select>
      </label>
      <p className="muted small field-hint">{t("strategySubsettings.marketTypePasswordHint")}</p>

      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={allowShort}
          disabled={opBusy || marketType !== "usdt_futures"}
          onChange={(e) => setAllowShort(e.target.checked)}
        />
        <span>{t("strategySubsettings.allowShort")}</span>
      </label>

      <div className="strategy-product-grid">
        <div className="strategy-product-field">
          <label className="modal-field">
            <span>{t("strategySubsettings.leverage")}</span>
            <select
              className="input"
              value={leverage}
              disabled={opBusy || marketType !== "usdt_futures"}
              onChange={(e) => setLeverage(Number(e.target.value))}
            >
              {Array.from({ length: savedProduct?.max_leverage ?? 5 }, (_, i) => i + 1).map(
                (lev) => (
                  <option key={lev} value={lev}>
                    {lev}x
                  </option>
                ),
              )}
            </select>
          </label>
          <p className="muted small field-hint">{t("strategySubsettings.leverageHint")}</p>
        </div>
        <div className="strategy-product-field">
          <label className="modal-field">
            <span>{t("strategySubsettings.marginMode")}</span>
            <select
              className="input"
              value={marginMode}
              disabled={opBusy || marketType !== "usdt_futures"}
              onChange={(e) => setMarginMode(e.target.value as "isolated" | "cross")}
            >
              <option value="isolated">{t("strategySubsettings.marginIsolated")}</option>
              <option value="cross">{t("strategySubsettings.marginCross")}</option>
            </select>
          </label>
          <p className="muted small field-hint">
            {marginMode === "cross"
              ? t("strategySubsettings.marginCrossHint")
              : t("strategySubsettings.marginIsolatedHint")}
          </p>
        </div>
      </div>

      {marketType === "usdt_futures" && productParamsDirty ? (
        <div className="btn-row">
          <button
            type="button"
            className="tiny primary"
            disabled={opBusy}
            onClick={() => {
              setOpError(null);
              setProductModalKind("params");
              setPendingProductApply(true);
            }}
          >
            {t("strategySubsettings.applyFuturesParams")}
          </button>
        </div>
      ) : null}

      <div className="btn-row">
        {savedProduct?.runtime_override ? (
          <button
            type="button"
            className="tiny"
            disabled={opBusy}
            onClick={() => {
              setOpError(null);
              setPendingProductReset(true);
            }}
          >
            {t("strategySubsettings.resetTradingProduct")}
          </button>
        ) : null}
      </div>

      <OperatorConfirmModal
        open={pendingProductApply}
        title={
          productModalKind === "market_type"
            ? t("strategySubsettings.confirmMarketType")
            : t("strategySubsettings.applyFuturesParams")
        }
        lead={t("workflowsPage.operatorLead")}
        risk={productModalRisk}
        riskTone={marketType === "usdt_futures" ? "danger" : "warn"}
        confirmLabel={
          productModalKind === "market_type"
            ? t("strategySubsettings.confirmMarketTypeApply")
            : t("strategySubsettings.applyFuturesParams")
        }
        busy={opBusy}
        error={opError}
        onCancel={cancelProductModal}
        onConfirm={applyTradingProduct}
      />
      <OperatorConfirmModal
        open={pendingProductReset}
        title={t("strategySubsettings.resetTradingProduct")}
        lead={t("workflowsPage.operatorLead")}
        risk={t("strategySubsettings.resetTradingProductRisk")}
        confirmLabel={t("strategySubsettings.resetTradingProduct")}
        busy={opBusy}
        error={opError}
        onCancel={() => !opBusy && setPendingProductReset(false)}
        onConfirm={resetTradingProduct}
      />
    </div>
  );

  if (bare) return body;

  return (
    <PortfolioCard
      title={t("cryptoFutures.sectionTitle")}
      subtitle={t("cryptoFutures.sectionHint")}
      collapsible
      defaultCollapsed={false}
    >
      {body}
    </PortfolioCard>
  );
}
