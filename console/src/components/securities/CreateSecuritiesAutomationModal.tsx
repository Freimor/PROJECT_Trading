import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiPost, formatOperatorFacingError } from "../../api";
import { useI18n } from "../../i18n/LanguageContext";
import OperatorConfirmModal from "../OperatorConfirmModal";
import ModalPortal from "../../ui/ModalPortal";
import type { StrategyState } from "../../types";
import type { SecuritiesAutomationInstance } from "../../types/securitiesAutomation";
import MoexTickerPickerPanel from "./MoexTickerPickerPanel";
import {
  SECURITIES_STRATEGY_MODES,
  isDuplicateAutomationInstance,
  supportsIssScan,
  supportsMultiSymbol,
} from "../../utils/securitiesWorkflowMap";

type SessionVolumeMode = "stablecoin" | "existing_holdings" | "combined";
type HoldingsUnit = "percent" | "absolute";
type TickerSource = "list" | "iss-scan";

type PortfolioPosition = { ticker?: string; quantity?: number };

type Props = {
  open: boolean;
  tickerOptions: string[];
  existingInstances?: SecuritiesAutomationInstance[];
  onClose: () => void;
  onCreated: (instanceId?: string) => void;
};

const DEFAULT_CAPITAL = 100_000;

function fmtShareQty(qty: number): string {
  if (Number.isInteger(qty)) return String(qty);
  return qty.toFixed(2).replace(/\.?0+$/, "");
}

export default function CreateSecuritiesAutomationModal({
  open,
  tickerOptions,
  existingInstances = [],
  onClose,
  onCreated,
}: Props) {
  const { t, lang } = useI18n();
  const [strategies, setStrategies] = useState<StrategyState["strategies"]>([]);
  const [strategyId, setStrategyId] = useState("swing_signals");
  const [operationMode, setOperationMode] = useState<"dry_run" | "paper" | "live">("paper");
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);
  const [sessionCapital, setSessionCapital] = useState(String(DEFAULT_CAPITAL));
  const [useRubBudget, setUseRubBudget] = useState(true);
  const [usePortfolioBudget, setUsePortfolioBudget] = useState(false);
  const [holdingsUnit, setHoldingsUnit] = useState<HoldingsUnit>("percent");
  const [existingHoldingsPct, setExistingHoldingsPct] = useState("100");
  const [existingHoldingsQty, setExistingHoldingsQty] = useState("");
  const [portfolioQtyByTicker, setPortfolioQtyByTicker] = useState<Map<string, number>>(new Map());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [formSession, setFormSession] = useState(0);
  const [tickerSource, setTickerSource] = useState<TickerSource>("list");
  const [symbolsPickedByUser, setSymbolsPickedByUser] = useState(false);

  const multi = supportsMultiSymbol(strategyId);
  const issScanAvailable = supportsIssScan(strategyId);
  const modes = useMemo(() => SECURITIES_STRATEGY_MODES[strategyId] ?? ["paper"], [strategyId]);

  useEffect(() => {
    if (!open) return;
    setFormSession((n) => n + 1);
    setError(null);
    setConfirmOpen(false);
    setSelectedSymbols([]);
    setSymbolsPickedByUser(false);
    setTickerSource("list");
    setUseRubBudget(true);
    setUsePortfolioBudget(false);
    setHoldingsUnit("percent");
    setExistingHoldingsPct("100");
    setExistingHoldingsQty("");
    apiGet<StrategyState>("/api/strategies/securities")
      .then((data) => {
        const list = data.strategies ?? [];
        setStrategies(list);
        const first = list[0]?.id ?? "swing_signals";
        setStrategyId(first);
        const allowed = SECURITIES_STRATEGY_MODES[first] ?? ["paper"];
        setOperationMode(allowed.includes("paper") ? "paper" : allowed[0]);
      })
      .catch(() => {});
    apiGet<{ positions?: PortfolioPosition[] }>("/api/tinvest/portfolio?sandbox=true", {
      timeoutMs: 45_000,
    })
      .then((data) => {
        const map = new Map<string, number>();
        for (const p of data.positions ?? []) {
          const ticker = String(p.ticker ?? "").toUpperCase();
          const qty = Number(p.quantity ?? 0);
          if (ticker && qty > 0) map.set(ticker, qty);
        }
        setPortfolioQtyByTicker(map);
      })
      .catch(() => setPortfolioQtyByTicker(new Map()));
  }, [open]);

  useEffect(() => {
    if (!modes.includes(operationMode)) setOperationMode(modes[0] ?? "paper");
  }, [modes, operationMode]);

  const tickerList = useMemo(() => {
    const base = tickerOptions.length ? tickerOptions : ["SBER", "GAZP", "LKOH"];
    return [...new Set(base.map((p) => p.toUpperCase()))];
  }, [tickerOptions]);

  useEffect(() => {
    if (!issScanAvailable && tickerSource === "iss-scan") setTickerSource("list");
  }, [issScanAvailable, tickerSource]);

  useEffect(() => {
    if (issScanAvailable && open) setTickerSource("iss-scan");
  }, [issScanAvailable, strategyId, open]);

  useEffect(() => {
    if (!open || selectedSymbols.length || tickerSource === "iss-scan") return;
    const first = tickerList[0];
    if (first) setSelectedSymbols([first]);
  }, [open, tickerList, strategyId, selectedSymbols.length, tickerSource]);

  useEffect(() => {
    if (multi) return;
    if (selectedSymbols.length > 1) setSelectedSymbols([selectedSymbols[0]]);
  }, [multi, selectedSymbols]);

  const portfolioOverlap = useMemo(
    () => selectedSymbols.filter((s) => portfolioQtyByTicker.has(s.toUpperCase())),
    [selectedSymbols, portfolioQtyByTicker],
  );

  const portfolioOverlapLabel = useMemo(
    () =>
      portfolioOverlap
        .map((sym) => {
          const qty = portfolioQtyByTicker.get(sym.toUpperCase()) ?? 0;
          return `${sym} (${fmtShareQty(qty)} ${t("moexAutomation.sharesBudgetShort")})`;
        })
        .join(", "),
    [portfolioOverlap, portfolioQtyByTicker, t],
  );

  const sessionVolumeMode: SessionVolumeMode = useMemo(() => {
    if (useRubBudget && usePortfolioBudget) return "combined";
    if (usePortfolioBudget) return "existing_holdings";
    return "stablecoin";
  }, [useRubBudget, usePortfolioBudget]);

  useEffect(() => {
    if (portfolioOverlap.length === 0 && usePortfolioBudget) {
      setUsePortfolioBudget(false);
    }
  }, [portfolioOverlap.length, usePortfolioBudget]);

  const isDuplicate = isDuplicateAutomationInstance(existingInstances, strategyId, selectedSymbols);

  const takenSymbolsForStrategy = useMemo(() => {
    const set = new Set<string>();
    for (const inst of existingInstances) {
      if (inst.strategy_id !== strategyId) continue;
      const syms = inst.symbols?.length ? inst.symbols : inst.symbol ? [inst.symbol] : [];
      syms.forEach((s) => set.add(s.toUpperCase()));
    }
    return set;
  }, [existingInstances, strategyId]);

  const issScanReady = tickerSource !== "iss-scan" || (symbolsPickedByUser && selectedSymbols.length > 0);

  const toggleSymbol = (sym: string) => {
    const upper = sym.toUpperCase();
    if (!multi) {
      setSelectedSymbols([upper]);
      return;
    }
    setSelectedSymbols((prev) => {
      const set = new Set(prev.map((s) => s.toUpperCase()));
      if (set.has(upper)) set.delete(upper);
      else set.add(upper);
      return [...set];
    });
  };

  const submit = useCallback(
    async (password: string) => {
      setBusy(true);
      setError(null);
      try {
        const cap = parseFloat(sessionCapital.replace(/\s/g, "").replace(",", "."));
        const pct = parseFloat(existingHoldingsPct.replace(",", "."));
        const qty = parseFloat(existingHoldingsQty.replace(/\s/g, "").replace(",", "."));

        if (!useRubBudget && !usePortfolioBudget) {
          setError(t("moexAutomation.budgetRequiresOne"));
          setBusy(false);
          return;
        }
        if (useRubBudget && (!Number.isFinite(cap) || cap <= 0)) {
          setError(t("workflowPanel.sessionCapitalInvalid"));
          setBusy(false);
          return;
        }
        if (usePortfolioBudget) {
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
          "/api/securities/automations",
          {
            strategy_id: strategyId,
            symbols: selectedSymbols.map((s) => s.toUpperCase()),
            operation_mode: operationMode,
            session_capital: useRubBudget && Number.isFinite(cap) && cap > 0 ? cap : undefined,
            session_volume_mode: sessionVolumeMode,
            use_existing_holdings: usePortfolioBudget,
            existing_holdings_unit: holdingsUnit,
            existing_holdings_use_pct: Number.isFinite(pct) ? pct : 100,
            existing_holdings_use_qty:
              usePortfolioBudget && holdingsUnit === "absolute" && Number.isFinite(qty) ? qty : undefined,
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
          setError(t("moexAutomation.duplicateError"));
        } else {
          setError(formatOperatorFacingError(err, t));
        }
      } finally {
        setBusy(false);
      }
    },
    [
      strategyId,
      selectedSymbols,
      operationMode,
      sessionCapital,
      sessionVolumeMode,
      useRubBudget,
      usePortfolioBudget,
      holdingsUnit,
      existingHoldingsPct,
      existingHoldingsQty,
      onClose,
      onCreated,
      t,
    ],
  );

  const strategyOptions = strategies.map((s) => ({
    id: s.id,
    label: lang === "en" ? s.label_en ?? s.label : s.label,
  }));

  const strategyLabel = strategyOptions.find((s) => s.id === strategyId)?.label ?? strategyId;
  const modeLabel = t(
    `operationModes.${operationMode === "dry_run" ? "dryRun" : operationMode}` as "operationModes.paper",
  );
  const symbolsLabel = selectedSymbols.join(", ") || "—";

  const budgetSummary = useMemo(() => {
    const parts: string[] = [];
    if (useRubBudget) parts.push(`${sessionCapital || "—"} ₽`);
    if (usePortfolioBudget) {
      if (holdingsUnit === "percent") {
        parts.push(`${existingHoldingsPct}% ${t("moexAutomation.portfolioBudgetShort")}`);
      } else {
        parts.push(`${existingHoldingsQty || "—"} ${t("moexAutomation.sharesBudgetShort")}`);
      }
    }
    return parts.length ? parts.join(" + ") : "—";
  }, [
    useRubBudget,
    usePortfolioBudget,
    sessionCapital,
    holdingsUnit,
    existingHoldingsPct,
    existingHoldingsQty,
    t,
  ]);

  if (!open) return null;

  return (
    <>
      <ModalPortal>
        <div className="modal-overlay" role="presentation" onClick={onClose}>
          <div
            className={`modal-dialog modal-dialog-scroll modal-dialog-create-auto${tickerSource === "iss-scan" && issScanAvailable ? " modal-dialog-create-auto--prescan modal-dialog-create-auto--moex-scan" : ""}`}
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-dialog-body">
              <header className="create-auto-header">
                <h3>{t("moexAutomation.createTitle")}</h3>
                <p className="muted small">{t("moexAutomation.createLead")}</p>
              </header>

              <div className="create-auto-layout">
                <div className="create-auto-main">
                  <section className="create-auto-section">
                    <h4 className="create-auto-section-title">{t("createAutomation.sectionBasics")}</h4>
                    <div className="create-auto-field-grid">
                      <label className="modal-field">
                        <span>{t("moexAutomation.strategyLabel")}</span>
                        <select className="input" value={strategyId} onChange={(e) => setStrategyId(e.target.value)}>
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
                                name="moex-auto-mode"
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

                  <section className="create-auto-section create-auto-section--tickers">
                    <h4 className="create-auto-section-title">{t("moexAutomation.tickersLabel")}</h4>
                    <fieldset className="workflow-mode-list compact crypto-pair-source">
                      <legend className="muted small">{t("moexAutomation.tickerSourceLegend")}</legend>
                      <label className="workflow-mode-option">
                        <input
                          type="radio"
                          name="moex-ticker-source"
                          checked={tickerSource === "list"}
                          onChange={() => {
                            setTickerSource("list");
                            setSymbolsPickedByUser(false);
                          }}
                        />
                        <span>{t("moexAutomation.tickerSourceList")}</span>
                      </label>
                      <label
                        className={`workflow-mode-option${issScanAvailable ? "" : " disabled"}`}
                        title={issScanAvailable ? undefined : t("moexAutomation.tickerIssScanSwingOnly")}
                      >
                        <input
                          type="radio"
                          name="moex-ticker-source"
                          checked={tickerSource === "iss-scan"}
                          disabled={!issScanAvailable}
                          onChange={() => {
                            setTickerSource("iss-scan");
                            setSelectedSymbols([]);
                            setSymbolsPickedByUser(false);
                          }}
                        />
                        <span>{t("moexAutomation.tickerSourceIssScan")}</span>
                      </label>
                    </fieldset>

                    {tickerSource === "iss-scan" && issScanAvailable ? (
                      <div className="crypto-create-prescan moex-create-scan">
                        <MoexTickerPickerPanel
                          key={`moex-iss-${formSession}`}
                          multiSelect={multi}
                          selectedSymbols={selectedSymbols}
                          disabledSymbols={takenSymbolsForStrategy}
                          onPickSymbols={(syms) => {
                            setSelectedSymbols(syms.map((s) => s.toUpperCase()));
                            setSymbolsPickedByUser(true);
                          }}
                        />
                        {symbolsPickedByUser && selectedSymbols.length ? (
                          <p className="crypto-create-pair-selected">
                            {t("moexAutomation.tickersSelected", { symbols: symbolsLabel })}
                          </p>
                        ) : (
                          <p className="warn small">{t("moexAutomation.tickerIssScanMustPick")}</p>
                        )}
                      </div>
                    ) : (
                      <>
                        <p className="muted small">
                          {multi ? t("moexAutomation.tickersMultiHint") : t("moexAutomation.tickersSingleHint")}
                        </p>
                        <div className="moex-ticker-pick-list">
                          {tickerList.map((sym) => {
                            const checked = selectedSymbols.includes(sym);
                            return (
                              <label key={sym} className={`moex-ticker-pick${checked ? " is-selected" : ""}`}>
                                <input
                                  type={multi ? "checkbox" : "radio"}
                                  name="moex-ticker-pick"
                                  checked={checked}
                                  onChange={() => toggleSymbol(sym)}
                                />
                                <span className="mono-small">{sym}</span>
                              </label>
                            );
                          })}
                        </div>
                        {selectedSymbols.length ? (
                          <p className="crypto-create-pair-selected">
                            {t("moexAutomation.tickersSelected", { symbols: symbolsLabel })}
                          </p>
                        ) : (
                          <p className="warn small">{t("moexAutomation.tickersRequired")}</p>
                        )}
                      </>
                    )}
                  </section>
                </div>

                <aside className="create-auto-aside">
                  <section className="create-auto-section">
                    <h4 className="create-auto-section-title">{t("createAutomation.sectionBudget")}</h4>
                    <fieldset className="modal-field session-volume-mode">
                      <legend>{t("moexAutomation.budgetSourcesLabel")}</legend>
                      <label className="checkbox-field">
                        <input
                          type="checkbox"
                          checked={useRubBudget}
                          onChange={(e) => setUseRubBudget(e.target.checked)}
                        />
                        <span>{t("moexAutomation.budgetRubOption")}</span>
                      </label>
                      {portfolioOverlap.length > 0 ? (
                        <label className="checkbox-field">
                          <input
                            type="checkbox"
                            checked={usePortfolioBudget}
                            onChange={(e) => setUsePortfolioBudget(e.target.checked)}
                          />
                          <span>
                            {t("moexAutomation.budgetPortfolioOption", { tickers: portfolioOverlapLabel })}
                          </span>
                        </label>
                      ) : (
                        <p className="muted small">{t("moexAutomation.noPortfolioOverlap")}</p>
                      )}
                    </fieldset>

                    {useRubBudget ? (
                      <label className="modal-field">
                        <span>{t("workflowPanel.sessionCapitalRubLabel")}</span>
                        <input
                          type="number"
                          className="input"
                          min={1000}
                          step={1000}
                          value={sessionCapital}
                          onChange={(e) => setSessionCapital(e.target.value)}
                        />
                        <span className="muted small">{t("workflowPanel.sessionCapitalRubHint")}</span>
                      </label>
                    ) : null}

                    {usePortfolioBudget ? (
                      <>
                        <fieldset className="modal-field session-volume-mode">
                          <legend>{t("workflowPanel.holdingsUnitLabel")}</legend>
                          <label className="checkbox-field">
                            <input
                              type="radio"
                              name="moex-holdings-unit"
                              checked={holdingsUnit === "percent"}
                              onChange={() => setHoldingsUnit("percent")}
                            />
                            <span>{t("workflowPanel.holdingsUnitPercent")}</span>
                          </label>
                          <label className="checkbox-field">
                            <input
                              type="radio"
                              name="moex-holdings-unit"
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
                              {t("moexAutomation.portfolioPctHint", { tickers: portfolioOverlap.join(", ") })}
                            </span>
                          </label>
                        ) : (
                          <label className="modal-field">
                            <span>{t("moexAutomation.existingHoldingsQtyLabel")}</span>
                            <input
                              type="number"
                              className="input"
                              min={1}
                              step={1}
                              value={existingHoldingsQty}
                              onChange={(e) => setExistingHoldingsQty(e.target.value)}
                            />
                            <span className="muted small">
                              {t("moexAutomation.existingHoldingsQtyHint", {
                                tickers: portfolioOverlap.join(", "),
                              })}
                            </span>
                          </label>
                        )}
                      </>
                    ) : null}

                    {useRubBudget && usePortfolioBudget ? (
                      <p className="muted small">{t("moexAutomation.budgetCombinedHint")}</p>
                    ) : null}
                  </section>

                  <div className="create-auto-summary-card">
                    <h4>{t("createAutomation.summaryTitle")}</h4>
                    <dl className="create-auto-summary-dl">
                      <dt>{t("moexAutomation.strategyLabel")}</dt>
                      <dd>{strategyLabel}</dd>
                      <dt>{t("workflowPanel.modeSection")}</dt>
                      <dd>{modeLabel}</dd>
                      <dt>{t("moexAutomation.tickersLabel")}</dt>
                      <dd className="create-auto-summary-symbols">{symbolsLabel}</dd>
                      <dt>{t("createAutomation.sectionBudget")}</dt>
                      <dd>{budgetSummary}</dd>
                    </dl>
                  </div>
                </aside>
              </div>

              {isDuplicate ? <p className="warn small">{t("moexAutomation.duplicateError")}</p> : null}
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
                    !selectedSymbols.length ||
                    isDuplicate ||
                    !issScanReady ||
                    (!useRubBudget && !usePortfolioBudget)
                  }
                  onClick={() => {
                    setError(null);
                    setConfirmOpen(true);
                  }}
                >
                  {t("moexAutomation.createSubmit")}
                </button>
              </div>
            </div>
          </div>
        </div>
      </ModalPortal>

      <OperatorConfirmModal
        open={confirmOpen}
        title={t("moexAutomation.createTitle")}
        lead={t("moexAutomation.createConfirmDetail", { symbols: symbolsLabel })}
        risk={t("workflowsPage.operatorRisk")}
        busy={busy}
        error={error}
        onConfirm={submit}
        onCancel={() => setConfirmOpen(false)}
      />
    </>
  );
}
