import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost, formatOperatorFacingError } from "../api";
import OperatorConfirmModal from "./OperatorConfirmModal";
import WorkflowUniversePanel from "./WorkflowUniversePanel";
import { useI18n } from "../i18n/LanguageContext";

type RiskLimits = {
  risk_per_trade_pct?: number;
  daily_loss_limit_pct?: number;
  max_open_positions?: number;
  max_notional_pct_equity?: number;
  min_stop_distance_pct?: number;
};

type RiskOption = {
  id: string;
  label_ru?: string;
  label_en?: string;
  description_ru?: string;
  description_en?: string;
  limits?: RiskLimits;
};

type SwingSignalSummary = {
  rule_filter?: { rsi_oversold?: number; rsi_overbought?: number; require_macd_cross?: boolean };
  llm?: { min_confidence?: number };
  notes_ru?: string;
  notes_en?: string;
};

type RiskProfileState = {
  profile_id?: string;
  profile_label_ru?: string;
  profile_label_en?: string;
  runtime_override?: boolean;
  options?: RiskOption[];
  effective_limits?: RiskLimits;
  effective_swing_signals?: SwingSignalSummary;
  can_change?: boolean;
  change_blocked_reason?: string | null;
};

type Props = {
  workflow: string;
  market: "crypto" | "securities";
  onChange?: () => void;
};

function pctLabel(value: number | undefined): string {
  if (value == null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function EffectiveLimitsGrid({
  limits,
  title,
  highlight,
}: {
  limits: RiskLimits;
  title: string;
  highlight?: boolean;
}) {
  const { t } = useI18n();
  const items = [
    { label: t("strategySubsettings.riskPerTrade"), value: pctLabel(limits.risk_per_trade_pct) },
    { label: t("strategySubsettings.dailyLimit"), value: pctLabel(limits.daily_loss_limit_pct) },
    {
      label: t("strategySubsettings.maxPositions"),
      value: limits.max_open_positions != null ? String(limits.max_open_positions) : "—",
    },
    {
      label: t("strategySubsettings.maxNotional"),
      value: pctLabel(limits.max_notional_pct_equity),
    },
    {
      label: t("strategySubsettings.minStop"),
      value: pctLabel(limits.min_stop_distance_pct),
    },
  ];

  return (
    <div className={`risk-effective-panel${highlight ? " active" : ""}`}>
      <div className="risk-effective-title">{title}</div>
      <dl className="risk-effective-grid">
        {items.map((item) => (
          <div key={item.label} className="risk-effective-item">
            <dt>{item.label}</dt>
            <dd>{item.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

type CryptoTradingProduct = {
  market_type?: "spot" | "usdt_futures";
  is_futures?: boolean;
  allow_short?: boolean;
  leverage?: number;
  max_leverage?: number;
  margin_mode?: "isolated" | "cross";
  runtime_override?: boolean;
  yaml_default?: {
    market_type?: string;
    allow_short?: boolean;
    leverage?: number;
    margin_mode?: string;
  };
};

type CryptoWorkflowSettings = {
  quote_asset?: string;
  allowed_quote_assets?: string[];
  yaml_default?: string;
  runtime_override?: boolean;
  trading_product?: CryptoTradingProduct;
};

export default function StrategySubsettingsPanel({ workflow, market, onChange }: Props) {
  const { t, lang } = useI18n();
  const [risk, setRisk] = useState<RiskProfileState | null>(null);
  const [selectedProfile, setSelectedProfile] = useState("");
  const [riskBusy, setRiskBusy] = useState(false);
  const [riskMsg, setRiskMsg] = useState<string | null>(null);
  const [pendingApply, setPendingApply] = useState(false);
  const [opBusy, setOpBusy] = useState(false);
  const [opError, setOpError] = useState<string | null>(null);
  const [universeOpen, setUniverseOpen] = useState(true);
  const [cryptoSettings, setCryptoSettings] = useState<CryptoWorkflowSettings | null>(null);
  const [selectedQuote, setSelectedQuote] = useState("USDT");
  const [pendingQuoteApply, setPendingQuoteApply] = useState(false);
  const [marketType, setMarketType] = useState<"spot" | "usdt_futures">("spot");
  const [allowShort, setAllowShort] = useState(false);
  const [leverage, setLeverage] = useState(3);
  const [marginMode, setMarginMode] = useState<"isolated" | "cross">("isolated");
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

  const savedProduct = cryptoSettings?.trading_product;
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

  const marketLabel = market === "crypto" ? t("strategySubsettings.marketCrypto") : t("strategySubsettings.marketMoex");

  const loadRisk = useCallback(async () => {
    const data = await apiGet<{ status: string } & RiskProfileState>(
      `/api/strategy/risk-profile/${market}`,
    );
    if (data.status === "ok") {
      setRisk(data);
      setSelectedProfile(data.profile_id ?? "balanced");
    }
  }, [market]);

  const loadCryptoSettings = useCallback(async () => {
    if (market !== "crypto") return;
    const data = await apiGet<{ status: string } & CryptoWorkflowSettings>(
      "/api/crypto/workflow-settings",
    );
    if (data.status === "ok") {
      setCryptoSettings(data);
      setSelectedQuote(data.quote_asset ?? "USDT");
      syncTradingProduct(data.trading_product);
    }
  }, [market]);

  useEffect(() => {
    loadRisk().catch(() => {});
    loadCryptoSettings().catch(() => {});
  }, [loadRisk, loadCryptoSettings]);

  const applyRiskProfile = async (password: string) => {
    setOpBusy(true);
    setOpError(null);
    try {
      const resp = await apiPost<{ status: string } & RiskProfileState>(
        `/api/strategy/risk-profile/${market}`,
        { profile_id: selectedProfile, operator: "web:operator" },
        { operatorPassword: password },
      );
      if (resp.status === "ok") {
        setRisk(resp);
        setRiskMsg(null);
        setPendingApply(false);
        onChange?.();
      }
    } catch (err) {
      setOpError(formatOperatorFacingError(err, t));
    } finally {
      setOpBusy(false);
    }
  };

  const applyQuoteAsset = async (password: string) => {
    setOpBusy(true);
    setOpError(null);
    try {
      const resp = await apiPost<{ status: string } & CryptoWorkflowSettings>(
        "/api/crypto/workflow-settings/quote-asset",
        { quote_asset: selectedQuote, operator: "web:operator" },
        { operatorPassword: password },
      );
      if (resp.status === "ok") {
        setCryptoSettings(resp);
        syncTradingProduct(resp.trading_product);
        setPendingQuoteApply(false);
        onChange?.();
      }
    } catch (err) {
      setOpError(formatOperatorFacingError(err, t));
    } finally {
      setOpBusy(false);
    }
  };

  const applyTradingProduct = async (password: string) => {
    setOpBusy(true);
    setOpError(null);
    try {
      const resp = await apiPost<{ status: string } & CryptoWorkflowSettings>(
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
        setCryptoSettings(resp);
        syncTradingProduct(resp.trading_product);
        setPendingProductApply(false);
        setProductModalKind("params");
        setOpError(null);
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
      const resp = await apiPost<{ status: string } & CryptoWorkflowSettings>(
        "/api/crypto/workflow-settings/trading-product/reset",
        {},
        { operatorPassword: password },
      );
      if (resp.status === "ok") {
        setCryptoSettings(resp);
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

  const optionLabel = (opt: RiskOption) =>
    lang === "en" ? opt.label_en ?? opt.id : opt.label_ru ?? opt.id;

  const optionDesc = (opt: RiskOption) =>
    lang === "en" ? opt.description_en : opt.description_ru;

  const activeLabel =
    lang === "en" ? risk?.profile_label_en ?? risk?.profile_id : risk?.profile_label_ru ?? risk?.profile_id;

  const blockHint =
    risk?.change_blocked_reason === "daily_loss_halt_active"
      ? t("strategySubsettings.riskBlockedHalt")
      : risk?.change_blocked_reason === "futures_margin_halt_active"
        ? t("strategySubsettings.riskBlockedMarginCall")
        : risk?.change_blocked_reason === "open_positions"
          ? t("strategySubsettings.riskBlockedPositions")
          : null;

  return (
    <div className="strategy-subsettings">
      <section className="strategy-subsection">
        <div className="strategy-subsection-head">
          <h4>{t("strategySubsettings.riskTitle")}</h4>
          <span className="muted small">
            {marketLabel}
            {" · "}
            {risk?.runtime_override ? t("strategySubsettings.runtime") : t("strategySubsettings.defaultPreset")}
          </span>
        </div>
        <p className="muted small">{t("strategySubsettings.riskHint")}</p>

        {risk?.effective_swing_signals ? (
          <div className="swing-thresholds-info">
            <div className="info-panel-label">{t("strategySubsettings.swingSignalsTitle")}</div>
            <dl className="risk-effective-grid">
              <div className="risk-effective-item">
                <dt>{t("strategySubsettings.rsiBand")}</dt>
                <dd>
                  &lt; {risk.effective_swing_signals.rule_filter?.rsi_oversold ?? "—"} / &gt;{" "}
                  {risk.effective_swing_signals.rule_filter?.rsi_overbought ?? "—"}
                </dd>
              </div>
              <div className="risk-effective-item">
                <dt>{t("strategySubsettings.minConfidence")}</dt>
                <dd>
                  {risk.effective_swing_signals.llm?.min_confidence != null
                    ? `${(risk.effective_swing_signals.llm.min_confidence * 100).toFixed(0)}%`
                    : "—"}
                </dd>
              </div>
              <div className="risk-effective-item">
                <dt>{t("strategySubsettings.macdCross")}</dt>
                <dd>
                  {risk.effective_swing_signals.rule_filter?.require_macd_cross
                    ? t("strategySubsettings.required")
                    : t("strategySubsettings.optional")}
                </dd>
              </div>
            </dl>
            <p className="muted small">
              {lang === "en"
                ? risk.effective_swing_signals.notes_en
                : risk.effective_swing_signals.notes_ru}
            </p>
            <p className="muted small">{t("strategySubsettings.onchainNote")}</p>
          </div>
        ) : null}

        {risk?.effective_limits ? (
          <EffectiveLimitsGrid
            limits={risk.effective_limits}
            title={t("strategySubsettings.effectiveTitle", { profile: activeLabel ?? "—", market: marketLabel })}
            highlight
          />
        ) : null}

        <div className="risk-profile-options">
          {(risk?.options ?? []).map((opt) => {
            const isActive = opt.id === risk?.profile_id;
            const isSelected = selectedProfile === opt.id;
            const lim = opt.limits ?? {};
            return (
              <label
                key={opt.id}
                className={`risk-profile-card${isSelected ? " selected" : ""}${isActive ? " active-preset" : ""}${
                  !risk?.can_change && !isActive ? " disabled" : ""
                }`}
              >
                <input
                  type="radio"
                  name={`risk-${market}`}
                  value={opt.id}
                  checked={isSelected}
                  disabled={riskBusy || (!risk?.can_change && !isActive)}
                  onChange={() => {
                    setSelectedProfile(opt.id);
                    setRiskMsg(null);
                  }}
                />
                <div>
                  <div className="risk-profile-card-head">
                    <strong>{optionLabel(opt)}</strong>
                    {isActive ? <span className="pill tiny ok">{t("strategySubsettings.activeBadge")}</span> : null}
                  </div>
                  {optionDesc(opt) ? <p className="muted small">{optionDesc(opt)}</p> : null}
                  <ul className="risk-profile-metrics small muted">
                    <li>
                      {t("strategySubsettings.riskPerTrade")}: {pctLabel(lim.risk_per_trade_pct)}
                    </li>
                    <li>
                      {t("strategySubsettings.dailyLimit")}: {pctLabel(lim.daily_loss_limit_pct)}
                    </li>
                    <li>
                      {t("strategySubsettings.maxPositions")}: {lim.max_open_positions ?? "—"}
                    </li>
                  </ul>
                </div>
              </label>
            );
          })}
        </div>

        {blockHint ? <p className="warn-text small">{blockHint}</p> : null}

        <div className="btn-row">
          <button
            type="button"
            className="tiny primary"
            disabled={
              riskBusy ||
              !risk?.can_change ||
              selectedProfile === risk?.profile_id ||
              !selectedProfile
            }
            onClick={() => {
              setOpError(null);
              setPendingApply(true);
            }}
          >
            {t("strategySubsettings.applyRisk")}
          </button>
        </div>
        {riskMsg ? <p className="modal-error small">{riskMsg}</p> : null}
      </section>

      {market === "crypto" ? (
        <>
        <section className="strategy-subsection">
          <div className="strategy-subsection-head">
            <h4>{t("strategySubsettings.quoteAssetTitle")}</h4>
            <span className="muted small">
              {cryptoSettings?.runtime_override
                ? t("strategySubsettings.runtime")
                : t("strategySubsettings.defaultPreset")}
            </span>
          </div>
          <p className="muted small">{t("strategySubsettings.quoteAssetHint")}</p>
          <label className="modal-field">
            <span>{t("strategySubsettings.quoteAssetLabel")}</span>
            <select
              className="input"
              value={selectedQuote}
              disabled={opBusy}
              onChange={(e) => setSelectedQuote(e.target.value)}
            >
              {(cryptoSettings?.allowed_quote_assets ?? ["USDT"]).map((asset) => (
                <option key={asset} value={asset}>
                  {asset}
                </option>
              ))}
            </select>
          </label>
          <div className="btn-row">
            <button
              type="button"
              className="tiny primary"
              disabled={opBusy || selectedQuote === cryptoSettings?.quote_asset}
              onClick={() => {
                setOpError(null);
                setPendingQuoteApply(true);
              }}
            >
              {t("strategySubsettings.applyQuoteAsset")}
            </button>
          </div>
        </section>

        <section className="strategy-subsection">
          <div className="strategy-subsection-head">
            <h4>{t("strategySubsettings.tradingProductTitle")}</h4>
            <span className="muted small">
              {cryptoSettings?.trading_product?.runtime_override
                ? t("strategySubsettings.runtime")
                : t("strategySubsettings.defaultPreset")}
            </span>
          </div>
          <p className="muted small">{t("strategySubsettings.tradingProductHint")}</p>
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
                  {Array.from(
                    { length: cryptoSettings?.trading_product?.max_leverage ?? 5 },
                    (_, i) => i + 1,
                  ).map((lev) => (
                    <option key={lev} value={lev}>
                      {lev}x
                    </option>
                  ))}
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
            {cryptoSettings?.trading_product?.runtime_override ? (
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
        </section>
        </>
      ) : null}

      <section className="strategy-subsection">
        <button
          type="button"
          className="strategy-subsection-toggle"
          onClick={() => setUniverseOpen((v) => !v)}
          aria-expanded={universeOpen}
        >
          <h4>{t("strategySubsettings.universeTitle")}</h4>
          <span className="muted small">{universeOpen ? "▾" : "▸"}</span>
        </button>
        {universeOpen ? (
          <WorkflowUniversePanel workflow={workflow} market={market} onChange={onChange} compact />
        ) : null}
      </section>

      <OperatorConfirmModal
        open={pendingApply}
        title={t("strategySubsettings.applyRisk")}
        lead={t("workflowsPage.operatorLead")}
        risk={t("strategySubsettings.applyRiskRisk")}
        confirmLabel={t("strategySubsettings.applyRisk")}
        busy={opBusy}
        error={opError}
        onCancel={() => {
          if (!opBusy) {
            setPendingApply(false);
            setOpError(null);
          }
        }}
        onConfirm={applyRiskProfile}
      />
      <OperatorConfirmModal
        open={pendingQuoteApply}
        title={t("strategySubsettings.applyQuoteAsset")}
        lead={t("workflowsPage.operatorLead")}
        risk={t("strategySubsettings.applyQuoteAssetRisk")}
        confirmLabel={t("strategySubsettings.applyQuoteAsset")}
        busy={opBusy}
        error={opError}
        onCancel={() => {
          if (!opBusy) {
            setPendingQuoteApply(false);
            setOpError(null);
          }
        }}
        onConfirm={applyQuoteAsset}
      />
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
        onCancel={() => {
          if (!opBusy) {
            setPendingProductReset(false);
            setOpError(null);
          }
        }}
        onConfirm={resetTradingProduct}
      />
    </div>
  );
}
