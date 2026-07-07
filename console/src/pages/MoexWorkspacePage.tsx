import { useCallback, useEffect, useMemo, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { apiGet } from "../api";
import AutomationPanel from "../components/AutomationPanel";
import ChartMarkerMenu, {
  DEFAULT_MARKER_FILTERS,
  filterChartMarkers,
} from "../components/ChartMarkerMenu";
import EquityMiniChart from "../components/EquityMiniChart";
import PortfolioCard from "../components/PortfolioCard";
import PriceChartWithMarkers from "../components/PriceChartWithMarkers";
import StrategySelector from "../components/StrategySelector";
import { POLL } from "../config/polling";
import { useI18n } from "../i18n/LanguageContext";
import type { AdminLayoutContext } from "../layouts/AdminLayout";
import { usePolling } from "../hooks/usePolling";
import { formatMoexPosition } from "../utils/moex";
import type { Candle, ChartMarker, StrategyState } from "../types";

type CandlesResp = { candles: Candle[] };
type MarkersResp = { markers: ChartMarker[] };

export default function MoexWorkspacePage() {
  const { t } = useI18n();
  const { overview } = useOutletContext<AdminLayoutContext>();
  const [strategy, setStrategy] = useState<StrategyState | null>(null);
  const [symbol, setSymbol] = useState("SBER");
  const [selected, setSelected] = useState<ChartMarker | null>(null);
  const [markerFilters, setMarkerFilters] = useState(DEFAULT_MARKER_FILTERS);

  const applyStrategy = useCallback((state: StrategyState) => {
    setStrategy(state);
    const def = state.strategy?.chart_default;
    if (def) setSymbol(def);
  }, []);

  useEffect(() => {
    apiGet<StrategyState>("/api/strategies/securities").then(applyStrategy).catch(() => {});
  }, [applyStrategy]);

  const symbols = strategy?.strategy?.symbols?.length
    ? strategy.strategy.symbols
    : ["SBER", "GAZP", "LKOH"];

  const chartInterval = strategy?.strategy?.chart_interval ?? "1d";

  const { data: funnelData } = usePolling<{ funnel?: Record<string, { passed?: number; total?: number }> }>(
    () => apiGet("/api/backtest/funnel?market=securities&days=7"),
    POLL.DASHBOARD,
    true,
    { staggerKey: "moex-funnel" },
  );

  const { data: llmEval } = usePolling<{ count?: number; approve_rate?: number }>(
    () => apiGet("/api/evaluation/metrics?market=securities&days=7"),
    POLL.DASHBOARD,
    true,
    { staggerKey: "moex-llm-eval" },
  );

  const { data: portfolio } = usePolling<{
    total_amount?: number;
    positions?: Array<{ ticker?: string; quantity?: number; avg_price?: number }>;
    status?: string;
  }>(
    () => apiGet("/api/tinvest/portfolio?sandbox=true", { timeoutMs: 45_000 }),
    POLL.PORTFOLIO,
    true,
    { errorSource: "GET /api/tinvest/portfolio", staggerKey: "moex-portfolio" },
  );

  const connectionWarning =
    portfolio?.status === "error"
      ? "T-Invest: no portfolio"
      : overview?.securities?.tinvest_api && overview.securities.tinvest_api !== "ok"
        ? "T-Invest: check connection"
        : undefined;

  const { data: candleData } = usePolling<CandlesResp>(
    useCallback(
      () =>
        apiGet(
          `/api/charts/candles?market=securities&symbol=${encodeURIComponent(symbol)}&interval=${chartInterval}&limit=120&testnet=true&use_cache=false`,
        ),
      [symbol, chartInterval],
    ),
    POLL.CHART,
    true,
    { errorSource: "GET /api/charts/candles?securities", staggerKey: `moex-candles-${symbol}` },
  );

  const { data: markerData } = usePolling<MarkersResp>(
    useCallback(
      () =>
        apiGet(
          `/api/charts/markers?market=securities&symbol=${encodeURIComponent(symbol)}&limit=100&include_news=true`,
        ),
      [symbol],
    ),
    POLL.MARKERS,
    true,
    { staggerKey: `moex-markers-${symbol}` },
  );

  const { data: equity } = usePolling<{ moex_rub?: Array<{ time: number; value: number }> }>(
    () => apiGet("/api/charts/equity?days=30"),
    POLL.EQUITY,
    true,
    { staggerKey: "moex-equity" },
  );

  const filteredMarkers = useMemo(
    () => filterChartMarkers(markerData?.markers ?? [], markerFilters),
    [markerData?.markers, markerFilters],
  );

  const workflow = strategy?.strategy?.workflow ?? "securities-swing-dry-run";
  const strategyLabel = strategy?.strategy?.id
    ? t(`strategies.${strategy.strategy.id}.label` as "strategies.swing_signals.label")
    : "";

  return (
    <div className="page workspace">
      <div className="workspace-toolbar">
        <h2>{t("workspace.moexTitle")}</h2>
        <label>
          {t("workspace.chartTicker")}
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {symbols.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
      </div>

      <StrategySelector market="securities" onChange={applyStrategy} />

      <div className="workspace-grid">
        <div className="workspace-main">
          <PortfolioCard
            title={`${t("workspace.dailyChart")} · ${symbol}`}
            status={{ label: strategyLabel || "—", tone: "neutral" }}
          >
            <div className="chart-controls">
              <span className="muted small">{t("workspace.markerMenu")}</span>
              <ChartMarkerMenu filters={markerFilters} onChange={setMarkerFilters} />
            </div>
            {candleData?.candles?.length ? (
              <PriceChartWithMarkers
                candles={candleData.candles}
                markers={filteredMarkers}
                symbol={symbol}
                interval={chartInterval}
                onMarkerClick={setSelected}
              />
            ) : (
              <p className="muted">{t("workspace.loadingMoex")}</p>
            )}
          </PortfolioCard>
        </div>

        <aside className="workspace-side">
          <AutomationPanel
            title="MOEX"
            env={overview?.securities?.env}
            mode={strategyLabel || overview?.securities?.active_mode}
            workflow={workflow}
            funnel={funnelData}
            llmEval={llmEval}
            ollama={overview?.ollama}
            connectionWarning={connectionWarning}
          />

          <PortfolioCard
            title={t("workspace.sandboxPortfolio")}
            status={{
              label: portfolio?.total_amount != null ? t("common.statusOk") : "—",
              tone: "ok",
            }}
          >
            <div className="metric-row">
              <span>{t("workspace.total")}</span>
              <strong>
                {portfolio?.total_amount != null
                  ? `${Number(portfolio.total_amount).toLocaleString("ru-RU")} ₽`
                  : "—"}
              </strong>
            </div>
            <ul className="balance-list">
              {(portfolio?.positions ?? []).map((p) => {
                const row = formatMoexPosition(p.ticker, p.quantity, p.avg_price, {
                  cashRub: t("workspace.cashRub"),
                  pieces: t("workspace.pieces"),
                });
                return (
                  <li key={p.ticker}>
                    <span>{row.label}</span>
                    <span>{row.value}</span>
                  </li>
                );
              })}
            </ul>
          </PortfolioCard>

          <PortfolioCard title={t("workspace.equityRub")}>
            <EquityMiniChart data={equity?.moex_rub ?? []} color="#f0a030" title="30d" />
          </PortfolioCard>

          {selected && (
            <PortfolioCard title={t("workspace.marker")} status={{ label: selected.kind, tone: "neutral" }}>
              <div className="detail-block">
                <div>{selected.event_at}</div>
                <div>
                  {selected.stage} / {selected.decision}
                </div>
                {selected.confidence != null && <div>confidence: {selected.confidence}</div>}
                {selected.reject_reason && <div className="warn">{selected.reject_reason}</div>}
              </div>
            </PortfolioCard>
          )}
        </aside>
      </div>
    </div>
  );
}
