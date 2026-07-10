import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { apiGet, apiPost } from "../api";
import AutomationPanel from "../components/AutomationPanel";
import MarketWorkflowPanel from "../components/MarketWorkflowPanel";
import ChartMarkerMenu, {
  DEFAULT_MARKER_FILTERS,
  filterChartMarkers,
} from "../components/ChartMarkerMenu";
import EquityMiniChart from "../components/EquityMiniChart";
import PriceChartWithMarkers from "../components/PriceChartWithMarkers";
import SymbolNewsPanel from "../components/SymbolNewsPanel";
import PortfolioCard from "../components/PortfolioCard";
import WalletCard from "../components/WalletCard";
import { POLL } from "../config/polling";
import { useI18n } from "../i18n/LanguageContext";
import type { AdminLayoutContext } from "../layouts/AdminLayout";
import { usePolling } from "../hooks/usePolling";
import type { BalancesResponse } from "../utils/balances";
import type { Candle, ChartIndicators, ChartMarker, StrategyState, TradeEvent } from "../types";

type CandlesResp = { candles: Candle[]; count?: number };
type MarkersResp = { markers: ChartMarker[] };
type IndicatorsResp = ChartIndicators & { status?: string };
type CryptoDash = {
  config?: { env?: string; mode?: string };
  funnel?: { funnel?: Record<string, { passed?: number; total?: number }> };
  llm_eval?: { count?: number; approve_rate?: number; avg_latency_ms?: number };
  ollama?: { status?: string; latency_ms?: number };
};

const ENVS = ["", "dry_run", "paper", "shadow", "live"] as const;
const INTERVALS = ["5m", "15m", "1h", "4h", "1d"] as const;
const INTERVAL_STORAGE_KEY = "crypto-chart-interval";

function readStoredInterval(): string {
  try {
    const stored = sessionStorage.getItem(INTERVAL_STORAGE_KEY);
    if (stored && (INTERVALS as readonly string[]).includes(stored)) return stored;
  } catch {
    /* ignore */
  }
  return "4h";
}

function chartLimitForInterval(tf: string): number {
  if (tf === "5m" || tf === "15m") return 300;
  if (tf === "1h") return 400;
  return 500;
}

export default function CryptoWorkspacePage() {
  const { t } = useI18n();
  const { overview } = useOutletContext<AdminLayoutContext>();
  const [strategy, setStrategy] = useState<StrategyState | null>(null);
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [interval, setChartInterval] = useState(readStoredInterval);
  const [env, setEnv] = useState<string>("");
  const [selected, setSelected] = useState<ChartMarker | null>(null);
  const [replay, setReplay] = useState<Record<string, unknown> | null>(null);
  const [replayBusy, setReplayBusy] = useState(false);
  const [markerFilters, setMarkerFilters] = useState(DEFAULT_MARKER_FILTERS);
  const userPickedInterval = useRef(false);

  const applyStrategy = useCallback((state: StrategyState) => {
    setStrategy(state);
    const syms = state.strategy?.symbols ?? [];
    const def = state.strategy?.chart_default;
    setSymbol((prev) => (syms.includes(prev) ? prev : def ?? syms[0] ?? prev));
    const tf = state.strategy?.chart_interval;
    if (tf && !userPickedInterval.current && !sessionStorage.getItem(INTERVAL_STORAGE_KEY)) {
      setChartInterval(tf);
    }
  }, []);

  useEffect(() => {
    apiGet<StrategyState>("/api/strategies/crypto").then(applyStrategy).catch(() => {});
  }, [applyStrategy]);

  const refreshStrategy = useCallback(() => {
    apiGet<StrategyState>("/api/strategies/crypto").then(applyStrategy).catch(() => {});
  }, [applyStrategy]);

  const symbols = useMemo(() => {
    if (strategy?.strategy?.symbols?.length) return strategy.strategy.symbols;
    return ["BTCUSDT", "ETHUSDT"];
  }, [strategy]);

  const workflow = strategy?.strategy?.workflow ?? "crypto-signal-dry-run";
  const strategyLabel = strategy?.strategy?.id
    ? t(`strategies.${strategy.strategy.id}.label` as "strategies.llm_swing.label")
    : "";

  const candleLimit = chartLimitForInterval(interval);

  const candleFetcher = useCallback(
    () =>
      apiGet<CandlesResp>(
        `/api/charts/candles?market=crypto&symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=${candleLimit}&testnet=true&use_cache=false`,
      ),
    [symbol, interval, candleLimit],
  );

  const markerFetcher = useCallback(() => {
    const envQ = env ? `&env=${env}` : "";
    return apiGet<MarkersResp>(
      `/api/charts/markers?market=crypto&symbol=${encodeURIComponent(symbol)}&limit=200&include_news=true${envQ}`,
    );
  }, [symbol, env]);

  const indicatorFetcher = useCallback(
    () =>
      apiGet<IndicatorsResp>(
        `/api/charts/indicators?market=crypto&symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=${candleLimit}&testnet=true&use_cache=false`,
      ),
    [symbol, interval, candleLimit],
  );

  const eventsFetcher = useCallback(
    () =>
      apiGet<TradeEvent[]>(
        `/api/events?market=crypto&symbol=${encodeURIComponent(symbol)}&limit=15${env ? `&env=${env}` : ""}`,
      ),
    [symbol, env],
  );

  const balancesFetcher = useCallback(
    () => apiGet<BalancesResponse>("/api/binance/balances?testnet=true&top=20"),
    [],
  );

  const dashFetcher = useCallback(
    () => apiGet<CryptoDash>("/api/crypto/testnet-dashboard?days=7"),
    [],
  );

  const { data: candleData, loading: candlesLoading, error: candlesError } = usePolling(
    candleFetcher,
    POLL.CHART,
    true,
    { errorSource: "GET /api/charts/candles?crypto", staggerKey: `crypto-candles-${symbol}-${interval}` },
  );
  const { data: markerData } = usePolling(markerFetcher, POLL.MARKERS, true, {
    staggerKey: `crypto-markers-${symbol}`,
  });
  const { data: indicatorData } = usePolling(
    indicatorFetcher,
    POLL.CHART,
    Boolean(strategy?.strategy?.chart_overlays),
    { staggerKey: `crypto-indicators-${symbol}-${interval}` },
  );
  const { data: events } = usePolling(eventsFetcher, POLL.EVENTS, true, {
    staggerKey: `crypto-events-${symbol}`,
  });
  const { data: balances, loading: balancesLoading } = usePolling(
    balancesFetcher,
    POLL.WALLET,
    true,
    { errorSource: "GET /api/binance/balances", staggerKey: "crypto-balances" },
  );
  const { data: dash } = usePolling(dashFetcher, POLL.DASHBOARD, true, {
    errorSource: "GET /api/crypto/testnet-dashboard",
    staggerKey: "crypto-dash",
  });
  const { data: equity } = usePolling<{ crypto_usdt?: Array<{ time: number; value: number }> }>(
    () => apiGet("/api/charts/equity?days=30"),
    POLL.EQUITY,
    true,
    { staggerKey: "crypto-equity" },
  );

  const filteredMarkers = useMemo(
    () => filterChartMarkers(markerData?.markers ?? [], markerFilters),
    [markerData?.markers, markerFilters],
  );

  const runReplay = async () => {
    if (!selected?.inputs_hash) return;
    setReplayBusy(true);
    setReplay(null);
    try {
      const r = await apiPost<Record<string, unknown>>(
        "/api/evaluation/replay",
        { inputs_hash: selected.inputs_hash },
        { timeoutMs: 600_000 },
      );
      setReplay(r);
    } catch (err) {
      setReplay({ status: "error", message: String(err) });
    } finally {
      setReplayBusy(false);
    }
  };

  const base = symbol.replace("USDT", "");
  const candleCount = candleData?.count ?? candleData?.candles?.length ?? 0;

  return (
    <div className="page workspace">
      <div className="workspace-toolbar">
        <h2>{t("workspace.cryptoTitle")}</h2>
        <div className="toolbar-controls">
          <label>
            {t("workspace.chartPair")}
            <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
              {symbols.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("workspace.tf")}
            <select
              value={interval}
              onChange={(e) => {
                userPickedInterval.current = true;
                const tf = e.target.value;
                sessionStorage.setItem(INTERVAL_STORAGE_KEY, tf);
                setChartInterval(tf);
              }}
            >
              {INTERVALS.map((tf) => (
                <option key={tf} value={tf}>
                  {tf}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("workspace.env")}
            <select value={env} onChange={(e) => setEnv(e.target.value)}>
              {ENVS.map((e) => (
                <option key={e || "all"} value={e}>
                  {e || t("common.all")}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="workspace-grid">
        <div className="workspace-main">
          <PortfolioCard
            title={`${t("workspace.chart")} · ${interval}`}
            status={{
              label: candlesLoading ? t("common.loading") : `${candleCount} candles`,
              tone: "neutral",
            }}
          >
            <div className="chart-controls">
              <span className="muted small">{t("workspace.markerMenu")}</span>
              <ChartMarkerMenu filters={markerFilters} onChange={setMarkerFilters} />
            </div>
            {candlesLoading ? (
              <p className="muted chart-loading">{t("common.loading")} ({interval})</p>
            ) : candleData?.candles?.length ? (
              <PriceChartWithMarkers
                key={`${symbol}-${interval}`}
                candles={candleData.candles}
                markers={filteredMarkers}
                symbol={symbol}
                interval={interval}
                overlays={strategy?.strategy?.chart_overlays}
                indicators={
                  indicatorData?.series
                    ? { series: indicatorData.series, levels: indicatorData.levels ?? {} }
                    : undefined
                }
                onMarkerClick={setSelected}
              />
            ) : (
              !candlesLoading && (
                <p className="muted">{candlesError ? String(candlesError) : t("workspace.noQuotes")}</p>
              )
            )}
            <SymbolNewsPanel symbol={symbol} />
          </PortfolioCard>
        </div>

        <aside className="workspace-side">
          <MarketWorkflowPanel
            market="crypto"
            killSwitch={Boolean(overview?.kill_switch)}
            onStrategyChange={applyStrategy}
          />

          <AutomationPanel
            title="Crypto"
            env={dash?.config?.env}
            mode={strategyLabel || dash?.config?.mode}
            workflow={workflow}
            funnel={dash?.funnel}
            llmEval={dash?.llm_eval}
            ollama={dash?.ollama}
          />

          <WalletCard data={balances} loading={balancesLoading} highlightAssets={["USDT", base, "BTC", "ETH"]} />

          <PortfolioCard title={t("workspace.equityUsdt")}>
            <EquityMiniChart data={equity?.crypto_usdt ?? []} title="30d" color="#3dd68c" />
          </PortfolioCard>

          {selected && (
            <PortfolioCard title={t("workspace.marker")} status={{ label: selected.kind, tone: "neutral" }}>
              <div className="detail-block">
                <div>{selected.event_at}</div>
                <div>
                  {selected.stage} / {selected.decision}
                </div>
                {selected.confidence != null && <div>confidence: {selected.confidence}</div>}
                {selected.model && <div>model: {selected.model}</div>}
                {selected.latency_ms != null && <div>latency: {selected.latency_ms} ms</div>}
                {selected.reject_reason && selected.stage !== "filter" && (
                  <div className="warn">reject: {selected.reject_reason}</div>
                )}
                {selected.summary && selected.stage === "filter" && (
                  <p className="event-summary small">{selected.summary}</p>
                )}
                {selected.counter_thesis && (
                  <p className="thesis">{selected.counter_thesis.slice(0, 300)}</p>
                )}
                {selected.inputs_hash && (
                  <code className="hash">{selected.inputs_hash.slice(0, 16)}…</code>
                )}
              </div>
              {selected.inputs_hash && (
                <button type="button" className="tiny" disabled={replayBusy} onClick={runReplay}>
                  {replayBusy ? "Replay…" : "Replay LLM"}
                </button>
              )}
              {replay && (
                <pre className="replay-out small-pre">
                  {JSON.stringify(
                    {
                      changed: replay.changed,
                      was: (replay.original as { parsed_action?: string })?.parsed_action,
                      now: (replay.replay as { action?: string })?.action,
                      message: replay.message,
                    },
                    null,
                    2,
                  )}
                </pre>
              )}
              <button
                type="button"
                className="linkish"
                onClick={() => {
                  setSelected(null);
                  setReplay(null);
                }}
              >
                Close
              </button>
            </PortfolioCard>
          )}

          <PortfolioCard title={t("workspace.eventsByPair")}>
            <ul className="event-list">
              {(events ?? []).map((e) => (
                <li key={e.id}>
                  <span className="muted">{String(e.event_at).slice(5, 16)}</span>
                  <span>
                    {e.stage}/{e.decision}
                  </span>
                  <span className="pill tiny">{e.env}</span>
                  {e.summary && e.stage === "filter" ? (
                    <div className="event-summary small muted">{e.summary.split("\n")[0]}</div>
                  ) : null}
                </li>
              ))}
              {!events?.length && <li className="muted">{symbol}</li>}
            </ul>
          </PortfolioCard>
        </aside>
      </div>
    </div>
  );
}
