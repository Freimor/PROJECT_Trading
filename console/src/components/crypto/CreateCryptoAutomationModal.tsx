import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiPost, formatOperatorFacingError } from "../../api";
import { useI18n } from "../../i18n/LanguageContext";
import OperatorConfirmModal from "../OperatorConfirmModal";
import ModalPortal from "../../ui/ModalPortal";
import ScalpPairPickerPanel from "../ScalpPairPickerPanel";
import type { StrategyState } from "../../types";
import type { CryptoAutomationInstance } from "../../types/cryptoAutomation";
import {
  CRYPTO_STRATEGY_MODES,
  resolveCryptoWorkflow,
  supportsScalpPreScan,
} from "../../utils/cryptoWorkflowMap";
import type { MarginMode, MarketType } from "../../utils/tradingProduct";
import {
  instanceMarketType,
  isDuplicateAutomationInstance,
  marketTypeLabel,
} from "../../utils/tradingProduct";
import LlmAssistCreateSection, { type LlmAssistMode, type LlmAssistCreateProfile } from "./LlmAssistCreateSection";
import { fmtAmount, normalizeBalances, type BalancesResponse } from "../../utils/balances";

type SessionVolumeMode = "stablecoin" | "existing_holdings" | "combined";
type HoldingsUnit = "percent" | "absolute";
type PairSource = "list" | "prescan";

type WorkflowSettingsResp = {
  status?: string;
  trading_product?: {
    market_type?: MarketType;
    allow_short?: boolean;
    leverage?: number;
    max_leverage?: number;
    margin_mode?: MarginMode;
  };
};

type Props = {
  open: boolean;
  pairOptions: string[];
  existingInstances?: CryptoAutomationInstance[];
  onClose: () => void;
  onCreated: (instanceId?: string) => void;
};

const DEFAULT_CAPITAL = 10_000;

function baseAssetFromPair(pair: string): string {
  const upper = pair.toUpperCase();
  if (upper.endsWith("USDT")) return upper.slice(0, -4);
  if (upper.endsWith("USDC")) return upper.slice(0, -4);
  if (upper.endsWith("BUSD")) return upper.slice(0, -4);
  return upper;
}

export default function CreateCryptoAutomationModal({
  open,
  pairOptions,
  existingInstances = [],
  onClose,
  onCreated,
}: Props) {
  const { t, lang } = useI18n();
  const [strategies, setStrategies] = useState<StrategyState["strategies"]>([]);
  const [strategyId, setStrategyId] = useState("");
  const [operationMode, setOperationMode] = useState<"dry_run" | "paper" | "live">("paper");
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [sessionCapital, setSessionCapital] = useState(String(DEFAULT_CAPITAL));
  const [useStablecoinBudget, setUseStablecoinBudget] = useState(true);
  const [useBaseAssetBudget, setUseBaseAssetBudget] = useState(false);
  const [holdingsUnit, setHoldingsUnit] = useState<HoldingsUnit>("percent");
  const [existingHoldingsPct, setExistingHoldingsPct] = useState("100");
  const [existingHoldingsQty, setExistingHoldingsQty] = useState("");
  const [walletBalances, setWalletBalances] = useState<BalancesResponse | null>(null);
  const [liquidateOnStop, setLiquidateOnStop] = useState(false);
  const [marketType, setMarketType] = useState<MarketType>("spot");
  const [allowShort, setAllowShort] = useState(false);
  const [leverage, setLeverage] = useState(3);
  const [marginMode, setMarginMode] = useState<MarginMode>("isolated");
  const [maxLeverage, setMaxLeverage] = useState(5);
  const [pairSource, setPairSource] = useState<PairSource>("list");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [formSession, setFormSession] = useState(0);
  const [symbolPickedByUser, setSymbolPickedByUser] = useState(false);
  const [llmAssistEnabled, setLlmAssistEnabled] = useState(false);
  const [llmAssistMode, setLlmAssistMode] = useState<LlmAssistMode>("validate_only");
  const [llmAssistSamplePct, setLlmAssistSamplePct] = useState(15);

  useEffect(() => {
    if (!open) return;
    setFormSession((n) => n + 1);
    setError(null);
    setConfirmOpen(false);
    setSymbol("");
    setSymbolPickedByUser(false);
    setMarketType("spot");
    setAllowShort(false);
    setUseStablecoinBudget(true);
    setUseBaseAssetBudget(false);
    setHoldingsUnit("percent");
    setExistingHoldingsPct("100");
    setExistingHoldingsQty("");
    apiGet<StrategyState>("/api/strategies/crypto")
      .then((data) => {
        const list = (data.strategies ?? []).filter((s) =>
          Object.prototype.hasOwnProperty.call(CRYPTO_STRATEGY_MODES, s.id),
        );
        setStrategies(list);
        const first = list[0]?.id ?? "llm_swing";
        setStrategyId(first);
        const modes = CRYPTO_STRATEGY_MODES[first] ?? ["paper"];
        setOperationMode(modes.includes("paper") ? "paper" : modes[0]);
      })
      .catch(() => {});
  }, [open]);

  useEffect(() => {
    if (!strategyId) return;
    apiGet<LlmAssistCreateProfile>(
      `/api/crypto/llm-assist-profile?strategy_id=${encodeURIComponent(strategyId)}`,
    )
      .then((p) => {
        if (!p.supports_assist) {
          setLlmAssistEnabled(false);
          return;
        }
        setLlmAssistEnabled(Boolean(p.default_enabled));
        setLlmAssistMode((p.default_mode as LlmAssistMode) ?? "validate_only");
        setLlmAssistSamplePct(p.default_sample_pct ?? 15);
      })
      .catch(() => setLlmAssistEnabled(false));
  }, [strategyId]);

  const modes = useMemo(
    () => CRYPTO_STRATEGY_MODES[strategyId] ?? ["paper"],
    [strategyId],
  );

  useEffect(() => {
    if (!modes.includes(operationMode)) {
      setOperationMode(modes[0] ?? "paper");
    }
  }, [modes, operationMode]);

  const prescanAvailable = supportsScalpPreScan(strategyId);

  useEffect(() => {
    if (!prescanAvailable && pairSource === "prescan") {
      setPairSource("list");
    }
  }, [prescanAvailable, pairSource]);

  useEffect(() => {
    if (prescanAvailable && open) {
      setPairSource("prescan");
    }
  }, [prescanAvailable, strategyId, open]);

  const scalpWorkflow = useMemo(
    () => resolveCryptoWorkflow(strategyId, operationMode),
    [strategyId, operationMode],
  );

  const strategyOptions = useMemo(() => {
    return strategies.map((s) => ({
      id: s.id,
      label: lang === "en" ? s.label_en ?? s.label : s.label,
    }));
  }, [strategies, lang]);

  const takenPairsForStrategy = useMemo(() => {
    return new Set(
      existingInstances
        .filter(
          (i) => i.strategy_id === strategyId && instanceMarketType(i.session_config) === marketType,
        )
        .map((i) => i.symbol.toUpperCase()),
    );
  }, [existingInstances, strategyId, marketType]);

  const symbolUpper = symbol.toUpperCase();
  const isDuplicate = isDuplicateAutomationInstance(
    existingInstances,
    strategyId,
    symbolUpper,
    marketType,
  );

  useEffect(() => {
    if (!open) return;
    apiGet<BalancesResponse>("/api/binance/balances?testnet=true&top=0")
      .then(setWalletBalances)
      .catch(() => setWalletBalances(null));
  }, [open]);

  const walletRows = useMemo(() => normalizeBalances(walletBalances).rows, [walletBalances]);

  const baseAsset = useMemo(() => baseAssetFromPair(symbolUpper || "BTCUSDT"), [symbolUpper]);

  const walletBaseQty = useMemo(() => {
    const row = walletRows.find((r) => r.asset.toUpperCase() === baseAsset);
    if (!row) return 0;
    return Number(row.total ?? row.free + (row.locked ?? 0)) || 0;
  }, [walletRows, baseAsset]);

  const sessionVolumeMode: SessionVolumeMode = useMemo(() => {
    if (useStablecoinBudget && useBaseAssetBudget) return "combined";
    if (useBaseAssetBudget) return "existing_holdings";
    return "stablecoin";
  }, [useStablecoinBudget, useBaseAssetBudget]);

  useEffect(() => {
    if (walletBaseQty <= 0 && useBaseAssetBudget) {
      setUseBaseAssetBudget(false);
    }
  }, [walletBaseQty, useBaseAssetBudget]);

  const listPairOptions = useMemo(() => {
    const base = pairOptions.length ? pairOptions : ["BTCUSDT", "ETHUSDT"];
    return base.map((p) => p.toUpperCase());
  }, [pairOptions]);

  useEffect(() => {
    if (!open) return;
    apiGet<WorkflowSettingsResp>("/api/crypto/workflow-settings")
      .then((data) => {
        if (data.status !== "ok") return;
        const tp = data.trading_product;
        setLeverage(tp?.leverage ?? 3);
        setMarginMode(tp?.margin_mode === "cross" ? "cross" : "isolated");
        setMaxLeverage(tp?.max_leverage ?? 5);
      })
      .catch(() => {});
  }, [open]);

  const firstFreeSymbol = useCallback(
    (taken: Set<string>) => listPairOptions.find((p) => !taken.has(p)) ?? "",
    [listPairOptions],
  );

  useEffect(() => {
    if (!open || !strategyId || pairSource === "prescan") return;
    const taken = takenPairsForStrategy;
    const current = symbol.toUpperCase();
    if (current && !taken.has(current)) return;
    const next = firstFreeSymbol(taken);
    if (next && next !== current) {
      setSymbol(next);
      setSymbolPickedByUser(false);
    }
  }, [open, strategyId, marketType, pairSource, takenPairsForStrategy, firstFreeSymbol, symbol]);

  useEffect(() => {
    if (!open || pairSource !== "prescan" || !symbolPickedByUser) return;
    const current = symbol.toUpperCase();
    if (!current) return;
    if (takenPairsForStrategy.has(current)) {
      setSymbol("");
      setSymbolPickedByUser(false);
    }
  }, [open, pairSource, marketType, takenPairsForStrategy, symbol, symbolPickedByUser]);

  const prescanReady = pairSource !== "prescan" || symbolPickedByUser;

  const submit = useCallback(
    async (password: string) => {
      setBusy(true);
      setError(null);
      try {
        const cap = parseFloat(sessionCapital.replace(",", "."));
        const pct = parseFloat(existingHoldingsPct.replace(",", "."));
        const qty = parseFloat(existingHoldingsQty.replace(/\s/g, "").replace(",", "."));

        if (!useStablecoinBudget && !useBaseAssetBudget) {
          setError(t("cryptoAutomation.budgetRequiresOne"));
          setBusy(false);
          return;
        }
        if (useStablecoinBudget && (!Number.isFinite(cap) || cap <= 0)) {
          setError(t("workflowPanel.sessionCapitalInvalid"));
          setBusy(false);
          return;
        }
        if (useBaseAssetBudget) {
          if (holdingsUnit === "percent") {
            if (!Number.isFinite(pct) || pct <= 0 || pct > 100) {
              setError(t("workflowPanel.existingHoldingsPctInvalid"));
              setBusy(false);
              return;
            }
          } else if (!Number.isFinite(qty) || qty <= 0) {
            setError(t("workflowPanel.existingHoldingsQtyInvalid"));
            setBusy(false);
            return;
          }
        }

        const resp = await apiPost<{ instance?: { id?: string } }>(
          "/api/crypto/automations",
          {
            strategy_id: strategyId,
            symbol: symbol.toUpperCase(),
            operation_mode: operationMode,
            session_capital:
              useStablecoinBudget && Number.isFinite(cap) && cap > 0 ? cap : undefined,
            session_volume_mode: sessionVolumeMode,
            use_existing_holdings: useBaseAssetBudget,
            existing_holdings_unit: holdingsUnit,
            existing_holdings_use_pct: Number.isFinite(pct) ? pct : 100,
            existing_holdings_use_qty:
              useBaseAssetBudget && holdingsUnit === "absolute" && Number.isFinite(qty) ? qty : undefined,
            liquidate_on_stop: liquidateOnStop,
            market_type: marketType,
            allow_short: marketType === "usdt_futures" ? allowShort : false,
            leverage,
            margin_mode: marginMode,
            llm_assist_enabled: llmAssistEnabled,
            llm_assist_mode: llmAssistEnabled ? llmAssistMode : "disabled",
            llm_assist_sample_pct: llmAssistSamplePct,
            operator: "web:operator",
          },
          { operatorPassword: password },
        );
        setConfirmOpen(false);
        onCreated(resp.instance?.id);
        onClose();
      } catch (err) {
        const raw = err instanceof Error ? err.message : String(err);
        if (raw.includes("duplicate_automation")) {
          setError(
            t("cryptoAutomation.duplicateError", {
              symbol: symbolUpper,
              market: marketTypeLabel(marketType, t),
            }),
          );
        } else {
          setError(formatOperatorFacingError(err, t));
        }
      } finally {
        setBusy(false);
      }
    },
    [
      strategyId,
      symbol,
      operationMode,
      sessionCapital,
      sessionVolumeMode,
      useStablecoinBudget,
      useBaseAssetBudget,
      holdingsUnit,
      existingHoldingsPct,
      existingHoldingsQty,
      liquidateOnStop,
      marketType,
      allowShort,
      leverage,
      marginMode,
      llmAssistEnabled,
      llmAssistMode,
      llmAssistSamplePct,
      onClose,
      onCreated,
      marketType,
      t,
    ],
  );

  const strategyLabel =
    strategyOptions.find((s) => s.id === strategyId)?.label ?? strategyId;
  const modeLabel = t(
    `operationModes.${operationMode === "dry_run" ? "dryRun" : operationMode}` as "operationModes.paper",
  );

  const budgetSummary = useMemo(() => {
    const parts: string[] = [];
    if (useStablecoinBudget) {
      parts.push(`${sessionCapital || "—"} USDT`);
    }
    if (useBaseAssetBudget) {
      if (holdingsUnit === "percent") {
        parts.push(`${existingHoldingsPct}% ${baseAsset}`);
      } else {
        parts.push(`${existingHoldingsQty || "—"} ${baseAsset}`);
      }
    }
    return parts.length ? parts.join(" + ") : "—";
  }, [
    useStablecoinBudget,
    useBaseAssetBudget,
    sessionCapital,
    holdingsUnit,
    existingHoldingsPct,
    existingHoldingsQty,
    baseAsset,
  ]);

  if (!open) return null;

  return (
    <>
      <ModalPortal>
        <div className="modal-overlay" role="presentation" onClick={onClose}>
          <div
            className={`modal-dialog modal-dialog-scroll modal-dialog-create-auto${pairSource === "prescan" ? " modal-dialog-create-auto--prescan" : ""}`}
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-dialog-body">
              <header className="create-auto-header">
                <h3>{t("cryptoAutomation.createTitle")}</h3>
                <p className="muted small">{t("cryptoAutomation.createLead")}</p>
              </header>

              <div className="create-auto-layout">
                <div className="create-auto-main">
                  <section className="create-auto-section">
                    <h4 className="create-auto-section-title">{t("createAutomation.sectionBasics")}</h4>
                    <div className="create-auto-field-grid">
                      <label className="modal-field">
                        <span>{t("cryptoAutomation.strategyLabel")}</span>
                        <select
                          className="input"
                          value={strategyId}
                          onChange={(e) => setStrategyId(e.target.value)}
                        >
                          {strategyOptions.map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.label}
                            </option>
                          ))}
                        </select>
                      </label>

                      <fieldset className="workflow-mode-list compact create-auto-mode-field">
                        <legend className="muted small">{t("workflowPanel.modeSection")}</legend>
                        {(["dry_run", "paper", "live"] as const)
                          .filter((m) => modes.includes(m))
                          .map((m) => (
                            <label key={m} className="workflow-mode-option">
                              <input
                                type="radio"
                                name="create-auto-mode"
                                checked={operationMode === m}
                                onChange={() => setOperationMode(m)}
                              />
                              <span>
                                {t(`operationModes.${m === "dry_run" ? "dryRun" : m}` as "operationModes.paper")}
                              </span>
                            </label>
                          ))}
                      </fieldset>
                    </div>
                  </section>

                  <section className="create-auto-section">
                    <h4 className="create-auto-section-title">{t("cryptoAutomation.pairLabel")}</h4>
                    <fieldset className="workflow-mode-list compact crypto-pair-source">
                      <legend className="muted small">{t("cryptoAutomation.pairSourceLegend")}</legend>
                      <label className="workflow-mode-option">
                        <input
                          type="radio"
                          name="create-pair-source"
                          checked={pairSource === "list"}
                          onChange={() => {
                            setPairSource("list");
                            setSymbolPickedByUser(false);
                          }}
                        />
                        <span>{t("cryptoAutomation.pairSourceList")}</span>
                      </label>
                      <label
                        className={`workflow-mode-option${prescanAvailable ? "" : " disabled"}`}
                        title={prescanAvailable ? undefined : t("cryptoAutomation.pairPrescanScalpOnly")}
                      >
                        <input
                          type="radio"
                          name="create-pair-source"
                          checked={pairSource === "prescan"}
                          disabled={!prescanAvailable}
                          onChange={() => {
                            setPairSource("prescan");
                            setSymbol("");
                            setSymbolPickedByUser(false);
                          }}
                        />
                        <span>{t("cryptoAutomation.pairSourcePrescan")}</span>
                      </label>
                    </fieldset>

                    {pairSource === "prescan" && prescanAvailable && scalpWorkflow ? (
                      <div className="crypto-create-prescan">
                        <ScalpPairPickerPanel
                          key={`prescan-${formSession}`}
                          workflow={scalpWorkflow}
                          marketType={marketType}
                          singleSelect
                          selectedSymbol={symbol}
                          disabledSymbols={takenPairsForStrategy}
                          onPickSymbol={(sym) => {
                            setSymbol(sym.toUpperCase());
                            setSymbolPickedByUser(true);
                          }}
                        />
                        {symbolPickedByUser && symbol ? (
                          <p className="crypto-create-pair-selected">
                            {t("cryptoAutomation.pairPrescanSelected", { symbol: symbolUpper })}
                            {" · "}
                            {marketTypeLabel(marketType, t)}
                          </p>
                        ) : (
                          <p className="warn small">{t("cryptoAutomation.pairPrescanMustPick")}</p>
                        )}
                      </div>
                    ) : (
                      <>
                        <select
                          className="input"
                          value={symbol}
                          onChange={(e) => {
                            setSymbol(e.target.value);
                            setSymbolPickedByUser(true);
                          }}
                        >
                          {listPairOptions.map((p) => {
                            const taken = takenPairsForStrategy.has(p);
                            return (
                              <option key={p} value={p} disabled={taken}>
                                {taken
                                  ? t("cryptoAutomation.duplicatePairOption", { symbol: p })
                                  : p}
                              </option>
                            );
                          })}
                        </select>
                        <span className="muted small">{t("cryptoAutomation.singlePairHint")}</span>
                      </>
                    )}
                  </section>

                  <section className="create-auto-section">
                    <h4 className="create-auto-section-title">{t("cryptoAutomation.marketLabel")}</h4>
                    <p className="muted small">{t("cryptoAutomation.marketHint")}</p>
                    <div className="create-auto-field-grid create-auto-field-grid--market">
                      <label className="modal-field">
                        <span>{t("strategySubsettings.tradingProductTitle")}</span>
                        <select
                          className="input"
                          value={marketType}
                          onChange={(e) => {
                            const next = e.target.value as MarketType;
                            setMarketType(next);
                            if (next === "spot") setAllowShort(false);
                          }}
                        >
                          <option value="spot">{t("strategySubsettings.marketTypeSpot")}</option>
                          <option value="usdt_futures">{t("strategySubsettings.marketTypeFutures")}</option>
                        </select>
                      </label>
                      <label className="modal-field">
                        <span>{t("strategySubsettings.leverage")}</span>
                        <select
                          className="input"
                          value={leverage}
                          disabled={marketType !== "usdt_futures"}
                          onChange={(e) => setLeverage(Number(e.target.value))}
                        >
                          {Array.from({ length: maxLeverage }, (_, i) => i + 1).map((lev) => (
                            <option key={lev} value={lev}>
                              {lev}x
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="modal-field">
                        <span>{t("strategySubsettings.marginMode")}</span>
                        <select
                          className="input"
                          value={marginMode}
                          disabled={marketType !== "usdt_futures"}
                          onChange={(e) => setMarginMode(e.target.value as MarginMode)}
                        >
                          <option value="isolated">{t("strategySubsettings.marginIsolated")}</option>
                          <option value="cross">{t("strategySubsettings.marginCross")}</option>
                        </select>
                      </label>
                    </div>
                    <label className="checkbox-row">
                      <input
                        type="checkbox"
                        checked={allowShort}
                        disabled={marketType !== "usdt_futures"}
                        onChange={(e) => setAllowShort(e.target.checked)}
                      />
                      <span>{t("strategySubsettings.allowShort")}</span>
                    </label>
                    {marketType === "usdt_futures" ? (
                      <p className="warn small">{t("strategySubsettings.applyTradingProductFuturesDanger")}</p>
                    ) : null}
                  </section>

                  <section className="create-auto-section">
                    <h4 className="create-auto-section-title">{t("createAutomation.sectionBudget")}</h4>
                    <fieldset className="modal-field session-volume-mode">
                      <legend>{t("cryptoAutomation.budgetSourcesLabel")}</legend>
                      <label className="checkbox-field">
                        <input
                          type="checkbox"
                          checked={useStablecoinBudget}
                          onChange={(e) => setUseStablecoinBudget(e.target.checked)}
                        />
                        <span>{t("cryptoAutomation.budgetStablecoinOption")}</span>
                      </label>
                      {walletBaseQty > 0 ? (
                        <label className="checkbox-field">
                          <input
                            type="checkbox"
                            checked={useBaseAssetBudget}
                            onChange={(e) => setUseBaseAssetBudget(e.target.checked)}
                          />
                          <span>
                            {t("cryptoAutomation.budgetBaseAssetOption", {
                              asset: baseAsset,
                              qty: fmtAmount(walletBaseQty),
                            })}
                          </span>
                        </label>
                      ) : (
                        <p className="muted small">
                          {t("cryptoAutomation.budgetBaseAssetUnavailable", { asset: baseAsset })}
                        </p>
                      )}
                    </fieldset>

                    {useStablecoinBudget ? (
                      <label className="modal-field">
                        <span>{t("workflowPanel.sessionCapitalStablecoinLabel")}</span>
                        <input
                          type="number"
                          className="input"
                          min={100}
                          step={100}
                          value={sessionCapital}
                          onChange={(e) => setSessionCapital(e.target.value)}
                        />
                        <span className="muted small">{t("workflowPanel.sessionCapitalStablecoinHint")}</span>
                      </label>
                    ) : null}

                    {useBaseAssetBudget ? (
                      <>
                        <fieldset className="modal-field session-volume-mode">
                          <legend>{t("workflowPanel.holdingsUnitLabel")}</legend>
                          <label className="checkbox-field">
                            <input
                              type="radio"
                              name="crypto-holdings-unit"
                              checked={holdingsUnit === "percent"}
                              onChange={() => setHoldingsUnit("percent")}
                            />
                            <span>{t("workflowPanel.holdingsUnitPercent")}</span>
                          </label>
                          <label className="checkbox-field">
                            <input
                              type="radio"
                              name="crypto-holdings-unit"
                              checked={holdingsUnit === "absolute"}
                              onChange={() => setHoldingsUnit("absolute")}
                            />
                            <span>{t("moexAutomation.holdingsUnitAbsolute")}</span>
                          </label>
                        </fieldset>
                        {holdingsUnit === "percent" ? (
                          <label className="modal-field">
                            <span>{t("workflowPanel.existingHoldingsPctLabel")}</span>
                            <input
                              type="number"
                              className="input"
                              min={1}
                              max={100}
                              value={existingHoldingsPct}
                              onChange={(e) => setExistingHoldingsPct(e.target.value)}
                            />
                            <span className="muted small">
                              {t("cryptoAutomation.baseAssetPctHint", { asset: baseAsset })}
                            </span>
                          </label>
                        ) : (
                          <label className="modal-field">
                            <span>{t("cryptoAutomation.baseAssetQtyLabel", { asset: baseAsset })}</span>
                            <input
                              type="number"
                              className="input"
                              min={0}
                              step="any"
                              value={existingHoldingsQty}
                              onChange={(e) => setExistingHoldingsQty(e.target.value)}
                            />
                            <span className="muted small">
                              {t("cryptoAutomation.baseAssetQtyHint", { asset: baseAsset })}
                            </span>
                          </label>
                        )}
                      </>
                    ) : null}

                    {useStablecoinBudget && useBaseAssetBudget ? (
                      <p className="muted small">{t("cryptoAutomation.budgetCombinedHint", { asset: baseAsset })}</p>
                    ) : null}

                    <label className="modal-field checkbox-field">
                      <input
                        type="checkbox"
                        checked={liquidateOnStop}
                        onChange={(e) => setLiquidateOnStop(e.target.checked)}
                      />
                      <span>{t("workflowPanel.liquidateOnStopLabel")}</span>
                      {marketType === "usdt_futures" ? (
                        <span className="muted small block">{t("workflowPanel.liquidateFuturesNote")}</span>
                      ) : null}
                    </label>
                  </section>
                </div>

                <aside className="create-auto-aside">
                  <div className="create-auto-summary-card">
                    <h4>{t("createAutomation.summaryTitle")}</h4>
                    <dl className="create-auto-summary-dl">
                      <dt>{t("cryptoAutomation.strategyLabel")}</dt>
                      <dd>{strategyLabel}</dd>
                      <dt>{t("workflowPanel.modeSection")}</dt>
                      <dd>{modeLabel}</dd>
                      <dt>{t("cryptoAutomation.pairLabel")}</dt>
                      <dd>{symbolUpper || "—"}</dd>
                      <dt>{t("cryptoAutomation.marketLabel")}</dt>
                      <dd>{marketTypeLabel(marketType, t)}</dd>
                      <dt>{t("cryptoAutomation.sessionCapital")}</dt>
                      <dd>{budgetSummary}</dd>
                      <dt>{t("createAutomation.llmAssistShort")}</dt>
                      <dd>
                        {llmAssistEnabled
                          ? t("createAutomation.llmAssistOn")
                          : t("createAutomation.llmAssistOff")}
                      </dd>
                    </dl>
                  </div>

                  <LlmAssistCreateSection
                    strategyId={strategyId}
                    enabled={llmAssistEnabled}
                    mode={llmAssistMode}
                    samplePct={llmAssistSamplePct}
                    onEnabledChange={setLlmAssistEnabled}
                    onModeChange={setLlmAssistMode}
                    onSamplePctChange={setLlmAssistSamplePct}
                  />
                </aside>
              </div>

              {isDuplicate ? (
                <p className="warn small">
                  {t("cryptoAutomation.duplicateError", {
                    symbol: symbolUpper,
                    market: marketTypeLabel(marketType, t),
                  })}
                </p>
              ) : null}

              {error ? <p className="warn small">{error}</p> : null}
            </div>

            <div className="modal-dialog-foot">
              <div className="modal-actions">
                <button type="button" className="tiny" onClick={onClose}>
                  {t("common.close")}
                </button>
                <button
                  type="button"
                  className="primary"
                  disabled={
                    !symbol.trim() ||
                    isDuplicate ||
                    !prescanReady ||
                    (!useStablecoinBudget && !useBaseAssetBudget)
                  }
                  onClick={() => {
                    if (isDuplicate || !prescanReady) return;
                    setError(null);
                    setConfirmOpen(true);
                  }}
                >
                  {t("cryptoAutomation.createSubmit")}
                </button>
              </div>
            </div>
          </div>
        </div>
      </ModalPortal>

      <OperatorConfirmModal
        open={confirmOpen}
        title={t("cryptoAutomation.createTitle")}
        lead={t("cryptoAutomation.createConfirmDetail", {
          symbol: symbolUpper,
          market: marketTypeLabel(marketType, t),
        })}
        risk={
          marketType === "usdt_futures"
            ? `${t("workflowsPage.operatorRisk")}\n\n${t("strategySubsettings.applyTradingProductFuturesDanger")}`
            : t("workflowsPage.operatorRisk")
        }
        riskTone={marketType === "usdt_futures" ? "danger" : undefined}
        busy={busy}
        error={error}
        onConfirm={submit}
        onCancel={() => setConfirmOpen(false)}
      />
    </>
  );
}
