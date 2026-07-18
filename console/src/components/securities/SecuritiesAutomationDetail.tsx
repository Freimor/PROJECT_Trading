import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiGet } from "../../api";
import { POLL } from "../../config/polling";
import { useI18n } from "../../i18n/LanguageContext";
import { useAutoChartLayout } from "../../hooks/useAutoChartLayout";
import { usePolling } from "../../hooks/usePolling";
import AutomationEquityChart, { type AutomationEquityCurve } from "../AutomationEquityChart";
import ChartMarkerMenu, { DEFAULT_MARKER_FILTERS, filterChartMarkers } from "../ChartMarkerMenu";
import PortfolioCard from "../PortfolioCard";
import PriceChartWithMarkers from "../PriceChartWithMarkers";
import SymbolNewsPanel from "../SymbolNewsPanel";
import StrategySubsettingsPanel from "../StrategySubsettingsPanel";
import type { Candle, ChartIndicators, ChartMarker } from "../../types";
import type { SecuritiesAutomationInstance, SecuritiesAutomationStats } from "../../types/securitiesAutomation";
import {
  chartIntervalForStrategy,
  chartOverlaysForStrategy,
  instanceSymbols,
} from "../../utils/securitiesWorkflowMap";
import { filterPriceChartMarkers } from "../../utils/chartSignals";

type CandlesResp = { candles: Candle[] };
type MarkersResp = { markers: ChartMarker[] };
type IndicatorsResp = ChartIndicators & { status?: string };

type Props = {
  instance: SecuritiesAutomationInstance;
  stats?: SecuritiesAutomationStats | null;
  settingsOpen: boolean;
  onRefresh: () => void;
};

export default function SecuritiesAutomationDetail({
  instance,
  stats,
  settingsOpen,
  onRefresh,
}: Props) {
  const { t } = useI18n();
  const chartAreaRef = useRef<HTMLDivElement>(null);
  const [markerFilters, setMarkerFilters] = useState(DEFAULT_MARKER_FILTERS);

  const symbols = instanceSymbols(instance);
  const [chartSymbol, setChartSymbol] = useState(() => symbols[0] ?? instance.symbol);
  const symbol = chartSymbol || instance.symbol;
  const interval = chartIntervalForStrategy(instance.strategy_id);
  const overlays = chartOverlaysForStrategy(instance.strategy_id);
  const panelCount = overlays?.panels?.length ?? 0;
  const isRunning = instance.status === "running";
  const sessionCfg = instance.session_config ?? {};

  useEffect(() => {
    setChartSymbol((prev) => {
      const next = symbols[0] ?? instance.symbol;
      if (symbols.includes(prev.toUpperCase())) return prev;
      return next;
    });
  }, [instance.id, instance.symbol, symbols]);

  const candleFetcher = useCallback(
    () =>
      apiGet<CandlesResp>(
        `/api/charts/candles?market=securities&symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=500&testnet=false&use_cache=false`,
      ),
    [symbol, interval],
  );
  const markerFetcher = useCallback(
    () =>
      apiGet<MarkersResp>(
        `/api/charts/markers?market=securities&symbol=${encodeURIComponent(symbol)}&limit=100&include_news=true`,
      ),
    [symbol],
  );
  const equityFetcher = useCallback(
    () =>
      apiGet<AutomationEquityCurve>(
        `/api/securities/automations/${instance.id}/equity-curve`,
      ),
    [instance.id],
  );
  const indicatorFetcher = useCallback(
    () =>
      apiGet<IndicatorsResp>(
        `/api/charts/indicators?market=securities&symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=500&testnet=false&use_cache=false`,
      ),
    [symbol, interval],
  );

  const { data: candleData, loading: candlesLoading } = usePolling(candleFetcher, POLL.CHART, true, {
    staggerKey: `moex-candles-${instance.id}-${symbol}`,
  });
  const { data: markerData } = usePolling(markerFetcher, POLL.MARKERS, true, {
    staggerKey: `moex-markers-${instance.id}-${symbol}`,
  });
  const { data: equityData, loading: equityLoading } = usePolling(
    equityFetcher,
    POLL.OPS,
    Boolean(instance.started_at),
    { staggerKey: `moex-equity-${instance.id}` },
  );
  const { data: indicatorData } = usePolling(indicatorFetcher, POLL.CHART, true, {
    staggerKey: `moex-ind-${instance.id}-${symbol}`,
  });

  const filteredMarkers = useMemo(
    () =>
      filterChartMarkers(
        filterPriceChartMarkers(markerData?.markers ?? []),
        markerFilters,
      ),
    [markerData?.markers, markerFilters],
  );

  const { chartHeight, panelHeight, needsScroll } = useAutoChartLayout(chartAreaRef, panelCount);

  const strategyLabel = t(`strategies.${instance.strategy_id}.label` as "strategies.swing_signals.label");
  const pnlPct = stats?.pnl_pct;
  const pnlText = pnlPct != null ? `${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(2)}%` : "—";
  const pnlClass = pnlPct == null ? "" : pnlPct > 0 ? "pnl-up" : pnlPct < 0 ? "pnl-down" : "pnl-flat";

  const volumeLabel = useMemo(() => {
    const mode = sessionCfg.session_volume_mode ?? "stablecoin";
    const holdingsPart = () => {
      const unit = String(sessionCfg.existing_holdings_unit || "percent");
      if (unit === "absolute" && sessionCfg.existing_holdings_use_qty != null) {
        return t("moexAutomation.volumeShares", {
          qty: String(sessionCfg.existing_holdings_use_qty),
        });
      }
      const pct = sessionCfg.existing_holdings_use_pct ?? 100;
      return t("moexAutomation.volumePortfolioPct", { pct: String(pct) });
    };
    const rubPart = () =>
      t("moexAutomation.volumeRub", {
        amount: String(sessionCfg.session_capital ?? "—"),
      });

    if (mode === "combined") {
      const parts = [];
      if (sessionCfg.session_capital != null) parts.push(rubPart());
      if (sessionCfg.use_existing_holdings) parts.push(holdingsPart());
      return parts.length ? parts.join(" + ") : "—";
    }
    if (sessionCfg.use_existing_holdings || mode === "existing_holdings") {
      return holdingsPart();
    }
    return rubPart();
  }, [sessionCfg, t]);

  const chartHeadTags = (
    <div className="crypto-chart-pills">
      {symbols.length > 1 ? (
        symbols.map((sym) => (
          <button
            key={sym}
            type="button"
            className={`automation-product-pill symbol automation-symbol-pick${sym === symbol.toUpperCase() ? " is-selected" : ""}`}
            aria-pressed={sym === symbol.toUpperCase()}
            onClick={() => setChartSymbol(sym)}
          >
            {sym}
          </button>
        ))
      ) : (
        <span className="automation-product-pill symbol">{symbol}</span>
      )}
      <span className="automation-product-pill interval">{interval}</span>
    </div>
  );

  return (
    <div className={`crypto-automation-detail crypto-automation-detail--compact${settingsOpen ? " crypto-automation-detail--settings" : ""}`}>
      {settingsOpen ? (
        <div className="crypto-automation-settings-panel">
          <PortfolioCard title={t("moexAutomation.settings")} collapsible={false}>
            <StrategySubsettingsPanel workflow={instance.workflow_name} market="securities" onChange={onRefresh} />
          </PortfolioCard>
        </div>
      ) : (
        <div className="workspace-grid crypto-automation-grid">
          <div className="workspace-main">
            <PortfolioCard title={chartHeadTags} tileId={`moex-chart-${instance.id}`} collapsible={false}>
              <div className="chart-controls">
                <ChartMarkerMenu filters={markerFilters} onChange={setMarkerFilters} />
                <span className="muted small">{t("workspace.markersLegendHint")}</span>
              </div>
              {candlesLoading ? (
                <p className="muted">{t("common.loading")}</p>
              ) : candleData?.candles?.length ? (
                <div ref={chartAreaRef} className={`workspace-chart-slot${needsScroll ? " workspace-chart-slot--scroll" : ""}`}>
                  <div className="workspace-chart-area">
                    <PriceChartWithMarkers
                      key={`${instance.id}-${symbol}-${chartHeight}`}
                      candles={candleData.candles}
                      markers={filteredMarkers}
                      symbol={symbol}
                      interval={interval}
                      height={chartHeight}
                      panelHeight={panelHeight}
                      overlays={overlays}
                      indicators={
                        indicatorData?.series
                          ? { series: indicatorData.series, levels: indicatorData.levels ?? {} }
                          : undefined
                      }
                    />
                    <AutomationEquityChart data={equityData} loading={equityLoading} t={t} />
                  </div>
                </div>
              ) : (
                <p className="muted">{t("workspace.noQuotes")}</p>
              )}
              <SymbolNewsPanel symbol={symbol} market="securities" />
            </PortfolioCard>
          </div>
          <aside className="workspace-side">
            <PortfolioCard title={t("moexAutomation.summary")} collapsible={false}>
              <dl className="risk-effective-grid">
                <dt>{t("moexAutomation.strategyLabel")}</dt>
                <dd>{strategyLabel}</dd>
                <dt>{t("moexAutomation.tickersLabel")}</dt>
                <dd>{symbols.join(", ")}</dd>
                <dt>{t("moexAutomation.budgetLabel")}</dt>
                <dd>{volumeLabel}</dd>
                <dt>{t("moexAutomation.statusLabel")}</dt>
                <dd>{isRunning ? t("moexAutomation.statusRunning") : t("moexAutomation.statusStopped")}</dd>
                <dt>{t("moexAutomation.efficiency")}</dt>
                <dd className={pnlClass || undefined}>{pnlText}</dd>
                <dt>{t("moexAutomation.orders")}</dt>
                <dd>{stats?.orders ?? 0}</dd>
              </dl>
            </PortfolioCard>
          </aside>
        </div>
      )}
    </div>
  );
}
