import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "../api";
import AutomationPanel from "../components/AutomationPanel";
import ChartMarkerMenu, {
  DEFAULT_MARKER_FILTERS,
  filterChartMarkers,
} from "../components/ChartMarkerMenu";
import EquityMiniChart from "../components/EquityMiniChart";
import PriceChartWithMarkers from "../components/PriceChartWithMarkers";
import PortfolioCard from "../components/PortfolioCard";
import StrategySelector from "../components/StrategySelector";
import WalletCard from "../components/WalletCard";
import { POLL } from "../config/polling";
import { useI18n } from "../i18n/LanguageContext";
import { usePolling } from "../hooks/usePolling";
import type { BalancesResponse } from "../utils/balances";
import type { Candle, ChartMarker, StrategyState, TradeEvent } from "../types";

type CandlesResp = { candles: Candle[]; count?: number };
type MarkersResp = { markers: ChartMarker[] };
type CryptoDash = {
  config?: { env?: string; mode?: string };
  funnel?: { funnel?: Record<string, { passed?: number; total?: number }> };
  llm_eval?: { count?: number; approve_rate?: number; avg_latency_ms?: number };
  ollama?: { status?: string; latency_ms?: number };
};

const ENVS = ["", "dry_run", "paper", "shadow", "live"] as const;
const INTERVALS = ["5m", "15m", "1h", "4h", "1d"];

export default function CryptoWorkspacePage() {
  const { t } = useI18n();
  const [strategy, setStrategy] = useState<StrategyState | null>(null);
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [interval, setInterval] = useState("4h");
  const [env, setEnv] = useState<string>("");
  const [selected, setSelected] = useState<ChartMarker | null>(null);
  const [replay, setReplay] = useState<Record<string, unknown> | null>(null);
  const [replayBusy, setReplayBusy] = useState(false);
  const [markerFilters, setMarkerFilters] = useState(DEFAULT_MARKER_FILTERS);

  const applyStrategy = useCallback((state: StrategyState) => {
    setStrategy(state);
    const def = state.strategy?.chart_default;
    if (def) setSymbol(def);
    const tf = state.strategy?.chart_interval;
    if (tf) setInterval(tf);
  }, []);

  useEffect(() => {
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

  const candleFetcher = useCallback(
    () =>
      apiGet<CandlesResp>(
        `/api/charts/candles?market=crypto&symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=500&testnet=true&use_cache=false`,
      ),
    [symbol, interval],
  );

  const markerFetcher = useCallback(() => {
    const envQ = env ? `&env=${env}` : "";
    return apiGet<MarkersResp>(
      `/api/charts/markers?market=crypto&symbol=${encodeURIComponent(symbol)}&limit=200&include_news=true${envQ}`,
    );
  }, [symbol, env]);

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

  const { data: candleData, loading: candlesLoading } = usePolling(
    candleFetcher,
    POLL.CHART,
    true,
    { errorSource: "GET /api/charts/candles?crypto", staggerKey: `crypto-candles-${symbol}-${interval}` },
  );
  const { data: markerData } = usePolling(markerFetcher, POLL.MARKERS, true, {
    staggerKey: `crypto-markers-${symbol}`,
  });
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
            <select value={interval} onChange={(e) => setInterval(e.target.value)}>
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

      <StrategySelector market="crypto" onChange={applyStrategy} />

      <div className="workspace-grid">
        <div className="workspace-main">
          <PortfolioCard
            title={t("workspace.chart")}
            status={{
              label: candlesLoading ? t("common.loading") : `${candleCount} candles`,
              tone: "neutral",
            }}
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
                interval={interval}
                onMarkerClick={setSelected}
              />
            ) : (
              !candlesLoading && <p className="muted">{t("workspace.noQuotes")}</p>
            )}
          </PortfolioCard>
        </div>

        <aside className="workspace-side">
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
                {selected.reject_reason && <div className="warn">reject: {selected.reject_reason}</div>}
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
