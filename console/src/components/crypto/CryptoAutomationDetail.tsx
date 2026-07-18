import { useCallback, useMemo, useRef, useState } from "react";
import { apiDelete, apiGet, apiPost, formatOperatorFacingError } from "../../api";
import { POLL } from "../../config/polling";
import { useI18n } from "../../i18n/LanguageContext";
import { useAutoChartLayout } from "../../hooks/useAutoChartLayout";
import { usePolling } from "../../hooks/usePolling";
import AutomationEquityChart, { type AutomationEquityCurve } from "../AutomationEquityChart";
import ChartMarkerMenu, {
  DEFAULT_MARKER_FILTERS,
  filterChartMarkers,
} from "../ChartMarkerMenu";
import OperatorConfirmModal from "../OperatorConfirmModal";
import PortfolioCard from "../PortfolioCard";
import PriceChartWithMarkers from "../PriceChartWithMarkers";
import SymbolNewsPanel from "../SymbolNewsPanel";
import StrategySubsettingsPanel from "../StrategySubsettingsPanel";
import TradingProductPill from "../TradingProductPill";
import KlinesFeedHealthBadge, { type KlinesFeedHealth } from "./KlinesFeedHealthBadge";
import type { Candle, ChartIndicators, ChartMarker } from "../../types";
import type { CryptoAutomationInstance, CryptoAutomationStats, CryptoAutomationStopResponse, CryptoInstanceSessionReport, CryptoInstanceWallet } from "../../types/cryptoAutomation";
import { chartIntervalForStrategy, chartOverlaysForStrategy, supportsScalpPreScan } from "../../utils/cryptoWorkflowMap";
import { filterPriceChartMarkers } from "../../utils/chartSignals";
import { tradingProductFromSessionConfig, tradingProductSummaryText } from "../../utils/tradingProduct";
import AutomationWalletPanel from "./AutomationWalletPanel";

type CandlesResp = {
  candles: Candle[];
  count?: number;
  data_source?: string;
  testnet_poor?: boolean;
};
type MarkersResp = { markers: ChartMarker[] };
type IndicatorsResp = ChartIndicators & { status?: string };

type Props = {
  instance: CryptoAutomationInstance;
  stats?: CryptoAutomationStats | null;
  killSwitch?: boolean;
  feedHealth?: KlinesFeedHealth | null;
  feedHealthAlertTicks?: number;
  tickPollMs?: number;
  onRefresh: () => void;
  onToggleCollapse: (collapsed: boolean) => void;
  onStopped?: (report: CryptoInstanceSessionReport | null) => void;
  onDeleted?: () => void;
};

export default function CryptoAutomationDetail({
  instance,
  stats,
  killSwitch,
  feedHealth,
  feedHealthAlertTicks = 6,
  tickPollMs = POLL.OPS,
  onRefresh,
  onToggleCollapse,
  onStopped,
  onDeleted,
}: Props) {
  const { t } = useI18n();
  const chartAreaRef = useRef<HTMLDivElement>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<"start" | "stop" | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [markerFilters, setMarkerFilters] = useState(DEFAULT_MARKER_FILTERS);

  const symbol = instance.symbol;
  const interval = chartIntervalForStrategy(instance.strategy_id);
  const isRunning = instance.status === "running";

  const candleFetcher = useCallback(
    () =>
      apiGet<CandlesResp>(
        `/api/charts/candles?market=crypto&symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=300&testnet=true&use_cache=false`,
      ),
    [symbol, interval],
  );
  const markerFetcher = useCallback(
    () =>
      apiGet<MarkersResp>(
        `/api/charts/markers?market=crypto&symbol=${encodeURIComponent(symbol)}&limit=120&include_news=true`,
      ),
    [symbol],
  );
  const equityFetcher = useCallback(
    () =>
      apiGet<AutomationEquityCurve>(
        `/api/crypto/automations/${instance.id}/equity-curve`,
      ),
    [instance.id],
  );
  const indicatorFetcher = useCallback(
    () =>
      apiGet<IndicatorsResp>(
        `/api/charts/indicators?market=crypto&symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=300&testnet=true&use_cache=false`,
      ),
    [symbol, interval],
  );

  const pollMs = isRunning ? tickPollMs : POLL.OPS;
  const chartPollMs = isRunning ? tickPollMs : POLL.CHART;
  const markerPollMs = isRunning ? POLL.TICK : POLL.MARKERS;

  const walletFetcher = useCallback(
    () => apiGet<CryptoInstanceWallet>(`/api/crypto/automations/${instance.id}/wallet`),
    [instance.id],
  );
  const { data: wallet, loading: walletLoading } = usePolling(walletFetcher, pollMs, true, {
    staggerKey: `auto-wallet-${instance.id}`,
  });

  const { data: candleData, loading: candlesLoading } = usePolling(candleFetcher, chartPollMs, true, {
    staggerKey: `auto-candles-${instance.id}`,
  });
  const { data: markerData } = usePolling(markerFetcher, markerPollMs, true, {
    staggerKey: `auto-markers-${instance.id}`,
  });
  const { data: equityData, loading: equityLoading } = usePolling(
    equityFetcher,
    pollMs,
    Boolean(instance.started_at),
    { staggerKey: `auto-equity-${instance.id}` },
  );
  const { data: indicatorData } = usePolling(indicatorFetcher, chartPollMs, true, {
    staggerKey: `auto-ind-${instance.id}`,
  });

  const sessionCfg = instance.session_config ?? {};
  const tradingProduct = useMemo(
    () => tradingProductFromSessionConfig(sessionCfg),
    [sessionCfg],
  );
  const liquidateOnStop = Boolean(sessionCfg.liquidate_on_stop);

  const filteredMarkers = useMemo(
    () =>
      filterChartMarkers(
        filterPriceChartMarkers(markerData?.markers ?? []),
        markerFilters,
      ),
    [markerData?.markers, markerFilters],
  );

  const overlays = chartOverlaysForStrategy(instance.strategy_id);
  const panelCount = overlays?.panels?.length ?? 0;
  const { chartHeight, panelHeight, needsScroll } = useAutoChartLayout(chartAreaRef, panelCount);

  const strategyLabel = t(
    `strategies.${instance.strategy_id}.label` as "strategies.llm_swing.label",
  );
  const pnlPct = stats?.pnl_pct;
  const pnlText =
    pnlPct != null ? `${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(2)}%` : "—";
  const pnlClass =
    pnlPct == null ? "" : pnlPct > 0 ? "pnl-up" : pnlPct < 0 ? "pnl-down" : "pnl-flat";

  const modeLabel = t(
    `operationModes.${instance.operation_mode === "dry_run" ? "dryRun" : instance.operation_mode}` as "operationModes.paper",
  );

  const isScalp = supportsScalpPreScan(instance.strategy_id);

  const chartHeadTags = (
    <div className="crypto-chart-pills">
      <span className="automation-product-pill symbol">{symbol}</span>
      <span className="automation-product-pill interval">{interval}</span>
      {tradingProduct ? <TradingProductPill product={tradingProduct} /> : null}
      {candleData?.data_source === "mainnet_metrics_fallback" ? (
        <span className="automation-product-pill chart-data-fallback" title={t("workspace.chartMainnetFallbackHint")}>
          {t("workspace.chartMainnetFallback")}
        </span>
      ) : null}
      {isScalp ? (
        <KlinesFeedHealthBadge health={feedHealth} alertTicks={feedHealthAlertTicks} />
      ) : null}
    </div>
  );

  const runAction = async (password: string) => {
    if (!pendingAction) return;
    setActionBusy(true);
    setActionError(null);
    try {
      const resp = await apiPost<CryptoAutomationStopResponse | { status: string }>(
        `/api/crypto/automations/${instance.id}/${pendingAction}`,
        { operator: "web:operator" },
        { operatorPassword: password },
      );
      setPendingAction(null);
      if (pendingAction === "stop") {
        const report =
          resp && "session_report" in resp ? (resp.session_report ?? null) : null;
        onStopped?.(report);
      } else {
        onRefresh();
      }
    } catch (err) {
      setActionError(formatOperatorFacingError(err, t));
    } finally {
      setActionBusy(false);
    }
  };

  const runDelete = async (password: string) => {
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await apiDelete(`/api/crypto/automations/${instance.id}`, { operatorPassword: password });
      setDeleteConfirmOpen(false);
      setSettingsOpen(false);
      onDeleted?.();
    } catch (err) {
      setDeleteError(formatOperatorFacingError(err, t));
    } finally {
      setDeleteBusy(false);
    }
  };

  return (
    <div className={`crypto-automation-detail${settingsOpen ? " crypto-automation-detail--settings" : ""}`}>
      <div className="crypto-automation-detail-head">
        <div>
          <h3>{instance.name}</h3>
          <p className="muted small">
            {strategyLabel} · {modeLabel}
          </p>
        </div>
        <div className="crypto-automation-detail-actions">
          <button type="button" className="tiny" onClick={() => onToggleCollapse(true)}>
            {t("cryptoAutomation.collapseTab")}
          </button>
          <button
            type="button"
            className={`tiny${settingsOpen ? " primary" : ""}`}
            aria-pressed={settingsOpen}
            onClick={() => setSettingsOpen((v) => !v)}
          >
            {t("cryptoAutomation.settings")}
          </button>
          {isRunning ? (
            <button
              type="button"
              className="tiny danger"
              disabled={killSwitch}
              onClick={() => setPendingAction("stop")}
            >
              {t("workflowPanel.stop")}
            </button>
          ) : (
            <button
              type="button"
              className="tiny primary"
              disabled={killSwitch}
              onClick={() => setPendingAction("start")}
            >
              {t("workflowPanel.start")}
            </button>
          )}
          <button
            type="button"
            className="tiny danger"
            onClick={() => {
              setDeleteError(null);
              setDeleteConfirmOpen(true);
            }}
          >
            {t("cryptoAutomation.delete")}
          </button>
        </div>
      </div>

      {settingsOpen ? (
        <div className="crypto-automation-settings-panel">
          <PortfolioCard title={t("cryptoAutomation.settings")} collapsible={false}>
            <StrategySubsettingsPanel
              workflow={instance.workflow_name}
              market="crypto"
              onChange={onRefresh}
            />
          </PortfolioCard>
        </div>
      ) : (
        <div className="workspace-grid crypto-automation-grid">
        <div className="workspace-main">
          <PortfolioCard title={chartHeadTags} tileId={`chart-${instance.id}`} collapsible={false}>
            <div className="chart-controls">
              <ChartMarkerMenu filters={markerFilters} onChange={setMarkerFilters} />
              <span className="muted small chart-marker-hint">{t("workspace.markersLegendHint")}</span>
            </div>
            {candlesLoading ? (
              <p className="muted">{t("common.loading")}</p>
            ) : candleData?.candles?.length ? (
              <div
                ref={chartAreaRef}
                className={`workspace-chart-slot${needsScroll ? " workspace-chart-slot--scroll" : ""}`}
              >
                <div className="workspace-chart-area">
                  <PriceChartWithMarkers
                    key={`${instance.id}-${chartHeight}`}
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
                  <AutomationEquityChart
                    data={equityData}
                    loading={equityLoading}
                    t={t}
                  />
                </div>
              </div>
            ) : (
              <p className="muted">{t("workspace.noQuotes")}</p>
            )}
            <SymbolNewsPanel symbol={symbol} market="crypto" />
          </PortfolioCard>
        </div>

        <aside className="workspace-side">
          <PortfolioCard title={t("cryptoAutomation.summary")} collapsible={false}>
            <dl className="risk-effective-grid">
              <dt>{t("cryptoAutomation.strategyLabel")}</dt>
              <dd>{strategyLabel}</dd>
              <dt>{t("cryptoAutomation.pairLabel")}</dt>
              <dd>{symbol}</dd>
              <dt>{t("cryptoAutomation.marketLabel")}</dt>
              <dd>{tradingProductSummaryText(tradingProduct, t)}</dd>
              <dt>{t("cryptoAutomation.statusLabel")}</dt>
              <dd>
                {isRunning ? t("cryptoAutomation.statusRunning") : t("cryptoAutomation.statusStopped")}
              </dd>
              {isScalp ? (
                <>
                  <dt>{t("cryptoAutomation.feedHealthLabel")}</dt>
                  <dd>
                    <KlinesFeedHealthBadge
                      health={feedHealth}
                      alertTicks={feedHealthAlertTicks}
                    />
                  </dd>
                </>
              ) : null}
              {stats?.session_capital != null ? (
                <>
                  <dt>{t("cryptoAutomation.sessionCapital")}</dt>
                  <dd>{stats.session_capital} USDT</dd>
                </>
              ) : null}
              {instance.session_config?.llm_assist_enabled != null ? (
                <>
                  <dt>{t("createAutomation.llmAssistStatusLabel")}</dt>
                  <dd>
                    {instance.session_config.llm_assist_enabled
                      ? (() => {
                          const cfg = instance.session_config ?? {};
                          const mode = String(cfg.llm_assist_mode ?? "validate_only");
                          const pct = cfg.llm_assist_sample_pct;
                          if (mode === "advisory") return `${t("createAutomation.llmAssistOn")} · advisory`;
                          if (typeof pct === "number" && pct > 0) {
                            return `${t("createAutomation.llmAssistOn")} · ${pct}%`;
                          }
                          return t("createAutomation.llmAssistOn");
                        })()
                      : t("createAutomation.llmAssistOff")}
                  </dd>
                </>
              ) : null}
              <dt>{t("cryptoAutomation.efficiency")}</dt>
              <dd className={pnlClass || undefined}>
                {pnlText}
                {stats?.scope === "session" ? (
                  <span className="muted small"> ({t("cryptoAutomation.sessionScope")})</span>
                ) : null}
              </dd>
              <dt>{t("cryptoAutomation.signals")}</dt>
              <dd>{stats?.signals ?? "—"}</dd>
              <dt>{t("cryptoAutomation.orders")}</dt>
              <dd>
                {stats?.orders_ok ?? stats?.orders ?? 0}
                {stats?.orders_failed ? ` / ${stats.orders_failed} err` : ""}
              </dd>
              {stats?.invested_notional != null ? (
                <>
                  <dt>{t("cryptoAutomation.investedNotional")}</dt>
                  <dd>{stats.invested_notional} USDT</dd>
                </>
              ) : null}
              {liquidateOnStop ? (
                <>
                  <dt>{t("workflowPanel.liquidateOnStopLabel")}</dt>
                  <dd className="small">
                    {t("workflowPanel.liquidateOnStopActive", { currency: "USDT" })}
                    {tradingProduct?.is_futures ? ` · ${t("workflowPanel.liquidateFuturesNote")}` : null}
                  </dd>
                </>
              ) : null}
            </dl>
            <AutomationWalletPanel wallet={wallet} loading={walletLoading} t={t} />
          </PortfolioCard>
        </aside>
      </div>
      )}

      <OperatorConfirmModal
        open={pendingAction !== null}
        title={pendingAction === "start" ? t("workflowPanel.start") : t("workflowPanel.stop")}
        risk={t("workflowsPage.operatorRisk")}
        busy={actionBusy}
        error={actionError}
        onConfirm={runAction}
        onCancel={() => setPendingAction(null)}
      />

      <OperatorConfirmModal
        open={deleteConfirmOpen}
        title={t("cryptoAutomation.deleteTitle")}
        lead={t("cryptoAutomation.deleteConfirm", { name: instance.name, symbol })}
        risk={
          isRunning
            ? `${t("cryptoAutomation.deleteConfirmRunning")}\n\n${t("workflowsPage.operatorRisk")}`
            : t("workflowsPage.operatorRisk")
        }
        riskTone="danger"
        busy={deleteBusy}
        error={deleteError}
        onConfirm={runDelete}
        onCancel={() => setDeleteConfirmOpen(false)}
      />
    </div>
  );
}
