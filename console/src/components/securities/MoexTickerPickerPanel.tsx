import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiGet, apiPost, formatOperatorFacingError } from "../../api";
import { useI18n } from "../../i18n/LanguageContext";
import { usePolling } from "../../hooks/usePolling";
import ScanParamScale from "../ScanParamScale";
import { formatIsoLocal } from "../../utils/datetime";

type ScanRankRow = {
  symbol: string;
  eligible?: boolean;
  score?: number;
  reject_reason?: string | null;
  metrics?: {
    valtoday?: number;
    numtrades?: number;
    volume_ratio?: number;
    atr_pct?: number;
    momentum_pct?: number;
    rsi_14?: number;
  };
};

type ScanSettings = {
  effective?: Record<string, number | boolean>;
  bounds?: Record<string, { min: number; max: number }>;
  param_meta?: Record<string, { min?: number; max?: number; recommended?: number | null }>;
  recommended?: Record<string, number>;
};

type LastScanPayload = {
  scanned_at?: string;
  ranked?: ScanRankRow[];
  liquidity_pool_count?: number;
  scored_count?: number;
  errors?: Array<{ symbol?: string; error?: string }>;
};

type ScanPoolInfo = {
  tickers_count?: number;
  board?: string;
  min_valtoday_mln?: number;
  max_scan_tickers?: number;
};

type ScanProgress = {
  in_progress?: boolean;
  done?: number;
  total?: number;
  current_ticker?: string;
};

type ParamKey =
  | "top_n"
  | "min_score"
  | "min_valtoday_mln"
  | "min_numtrades"
  | "max_scan_tickers"
  | "volume_ratio_min";

const PARAM_KEYS: ParamKey[] = [
  "top_n",
  "min_score",
  "min_valtoday_mln",
  "min_numtrades",
  "max_scan_tickers",
  "volume_ratio_min",
];

type Props = {
  scanContext?: string;
  multiSelect?: boolean;
  selectedSymbols?: string[];
  onPickSymbols?: (symbols: string[]) => void;
  disabledSymbols?: Set<string>;
};

function formatValtoday(v: number | undefined): string {
  if (v == null || !Number.isFinite(v)) return "—";
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return String(Math.round(v));
}

function formatParamValue(value: number | null | undefined, key: ParamKey): string {
  if (value == null || !Number.isFinite(value)) return "—";
  if (key === "top_n" || key === "min_numtrades" || key === "max_scan_tickers") {
    return String(Math.round(value));
  }
  if (key === "min_score") return value.toFixed(2);
  if (key === "min_valtoday_mln") return value.toFixed(0);
  return value.toFixed(2);
}

export default function MoexTickerPickerPanel({
  scanContext = "moex-create",
  multiSelect = true,
  selectedSymbols = [],
  onPickSymbols,
  disabledSymbols,
}: Props) {
  const { t, lang } = useI18n();
  const [settings, setSettings] = useState<ScanSettings | null>(null);
  const [paramInputs, setParamInputs] = useState<Record<string, string>>({});
  const [ranked, setRanked] = useState<ScanRankRow[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [messageTone, setMessageTone] = useState<"muted" | "warn">("muted");
  const [scannedAt, setScannedAt] = useState<string | null>(null);
  const [scanPool, setScanPool] = useState<ScanPoolInfo | null>(null);
  const [lastMeta, setLastMeta] = useState<LastScanPayload | null>(null);
  const prevBusyRef = useRef(false);

  useEffect(() => {
    setSelected(new Set(selectedSymbols.map((s) => s.toUpperCase())));
  }, [selectedSymbols]);

  const fetchScanProgress = useCallback(
    () => apiGet<{ status: string } & ScanProgress>("/api/securities/universe-scan/progress"),
    [],
  );
  const { data: scanProgress } = usePolling(fetchScanProgress, 1_500, busy, {
    staggerKey: "moex-picker-scan-progress",
  });

  const loadScanPool = useCallback(async () => {
    const data = await apiGet<{ status: string } & ScanPoolInfo>("/api/securities/universe-scan/candidates");
    if (data.status === "ok") setScanPool(data);
  }, []);

  const loadSettings = useCallback(async () => {
    const data = await apiGet<{ status: string } & ScanSettings>("/api/securities/universe-scan/settings");
    if (data.status === "ok") {
      setSettings(data);
      const eff = data.effective ?? {};
      const inputs: Record<string, string> = {};
      for (const key of PARAM_KEYS) {
        if (eff[key] != null) inputs[key] = String(eff[key]);
      }
      setParamInputs(inputs);
    }
  }, []);

  const loadLastScan = useCallback(async () => {
    const data = await apiGet<{ status: string; last_scan?: LastScanPayload }>(
      `/api/securities/universe-scan/last?scan_context=${encodeURIComponent(scanContext)}`,
    );
    const last = data.last_scan;
    if (!last) return;
    setLastMeta(last);
    if (last.scanned_at) setScannedAt(last.scanned_at);
    if (last.ranked) setRanked(last.ranked);
  }, [scanContext]);

  useEffect(() => {
    loadSettings().catch(() => {});
    loadLastScan().catch(() => {});
    loadScanPool().catch(() => {});
  }, [loadSettings, loadLastScan, loadScanPool]);

  useEffect(() => {
    if (prevBusyRef.current && !busy) void loadLastScan().catch(() => {});
    prevBusyRef.current = busy;
  }, [busy, loadLastScan]);

  const buildSettingsPayload = () => {
    const out: Record<string, number> = {};
    for (const key of PARAM_KEYS) {
      const raw = paramInputs[key];
      if (raw === undefined || raw === "") continue;
      const n = Number(String(raw).replace(",", "."));
      if (Number.isFinite(n)) out[key] = n;
    }
    return out;
  };

  const emitPick = (next: Set<string>) => {
    setSelected(next);
    onPickSymbols?.([...next]);
  };

  const pickRow = (row: ScanRankRow, checked = true) => {
    if (busy || !row.eligible || disabledSymbols?.has(row.symbol.toUpperCase())) return;
    const sym = row.symbol.toUpperCase();
    if (!multiSelect) {
      emitPick(new Set([sym]));
      return;
    }
    const next = new Set(selected);
    if (checked) next.add(sym);
    else next.delete(sym);
    emitPick(next);
  };

  const applyScanResponse = (scan: LastScanPayload & { status?: string; message?: string; reason?: string }) => {
    setLastMeta(scan);
    if (scan.scanned_at) setScannedAt(scan.scanned_at);
    setRanked(scan.ranked ?? []);
    const count = scan.ranked?.length ?? 0;
    const eligible = (scan.ranked ?? []).filter((r) => r.eligible).length;
    if (scan.status && scan.status !== "ok") {
      setMessageTone("warn");
      setMessage(scan.message ?? scan.reason ?? scan.status);
      return;
    }
    if (count === 0) {
      setMessageTone("warn");
      setMessage(t("universe.moexScanEmpty"));
      return;
    }
    setMessageTone("muted");
    setMessage(t("universe.moexScanDone", { count: String(count) }));
    if (eligible === 0) {
      setMessageTone("warn");
      setMessage(t("universe.moexScanNoEligible"));
    }
  };

  const runScan = async () => {
    setBusy(true);
    setMessage(null);
    setMessageTone("muted");
    try {
      const scan = await apiPost<
        LastScanPayload & { status: string; message?: string; reason?: string }
      >(
        "/api/securities/universe-scan/run",
        {
          scan_context: scanContext,
          settings: buildSettingsPayload(),
        },
        { timeoutMs: 600_000 },
      );
      applyScanResponse(scan);
    } catch (err) {
      setMessageTone("warn");
      setMessage(formatOperatorFacingError(err, t));
      await loadLastScan().catch(() => {});
    } finally {
      setBusy(false);
    }
  };

  const eligibleCount = useMemo(() => ranked.filter((r) => r.eligible).length, [ranked]);
  const scanDone = scanProgress?.done ?? 0;
  const scanTotal = scanProgress?.total ?? 0;
  const scanTicker = scanProgress?.current_ticker;
  const progressPct = scanTotal > 0 ? Math.min(100, Math.round((scanDone / scanTotal) * 100)) : 0;

  const rejectLabel = (reason?: string | null) => {
    if (!reason) return "—";
    const key = `universe.moexReject.${reason}` as "universe.moexReject.score_low";
    const translated = t(key);
    return translated === key ? reason : translated;
  };

  const paramMeta = (key: ParamKey) => {
    const fromApi = settings?.param_meta?.[key];
    const bounds = settings?.bounds?.[key];
    return {
      min: fromApi?.min ?? bounds?.min ?? 0,
      max: fromApi?.max ?? bounds?.max ?? 100,
      recommended: fromApi?.recommended ?? settings?.recommended?.[key] ?? null,
    };
  };

  return (
    <div className="scalp-pair-picker moex-ticker-picker">
      <p className="muted small">{t("universe.moexPickerHint")}</p>
      <p className="muted small">{t("universe.moexParamLegend")}</p>

      <div className="scalp-scan-params moex-scan-params">
        {PARAM_KEYS.map((key) => {
          const meta = paramMeta(key);
          const step =
            key === "top_n" || key === "min_numtrades" || key === "max_scan_tickers"
              ? 1
              : key === "min_valtoday_mln"
                ? 5
                : 0.05;
          const rawVal = paramInputs[key];
          const numVal = rawVal !== undefined && rawVal !== "" ? Number(String(rawVal).replace(",", ".")) : null;

          return (
            <div key={key} className="scalp-param-field">
              <label className="scalp-param-label">
                <span className="scalp-param-title">
                  {t(`universe.moexParam.${key}` as "universe.moexParam.top_n")}
                </span>
                <span className="muted small scalp-param-desc">
                  {t(`universe.moexParamDesc.${key}` as "universe.moexParamDesc.top_n")}
                </span>
                <div className="scalp-param-input-row">
                  <input
                    type="number"
                    className="input"
                    step={step}
                    min={meta.min}
                    max={meta.max}
                    value={paramInputs[key] ?? ""}
                    disabled={busy}
                    onChange={(e) => setParamInputs((prev) => ({ ...prev, [key]: e.target.value }))}
                  />
                  <span className="muted small scalp-param-range-text">
                    {t("universe.scalpParamRange", {
                      min: formatParamValue(meta.min, key),
                      max: formatParamValue(meta.max, key),
                      rec: formatParamValue(meta.recommended ?? null, key),
                    })}
                  </span>
                </div>
              </label>
              <ScanParamScale
                min={meta.min}
                max={meta.max}
                recommended={meta.recommended}
                value={numVal}
                recLabel={t("universe.scalpRecommendedShort")}
                formatValue={(v) => formatParamValue(v, key)}
              />
            </div>
          );
        })}
      </div>

      <div className="scalp-scan-actions">
        {scanPool?.tickers_count != null ? (
          <p className="muted small scalp-scan-pool">
            {t("universe.moexScanPool", {
              count: String(scanPool.tickers_count),
              board: scanPool.board ?? "TQBR",
              mln: String(scanPool.min_valtoday_mln ?? 15),
            })}
          </p>
        ) : null}
        <p className="muted small">{t("universe.moexScanPoolDetail")}</p>
        <div className="btn-row">
          <button type="button" className="tiny primary" disabled={busy} onClick={() => void runScan()}>
            {busy ? t("universe.moexRunScanBusy") : t("universe.moexRunScan")}
          </button>
          {busy ? (
            <span className="scalp-scan-inline-status" role="status" aria-live="polite">
              <span className="scalp-scan-inline-dot" aria-hidden />
              {scanTotal > 0
                ? t("universe.moexScanProgress", { done: String(scanDone), total: String(scanTotal) })
                : t("universe.moexScanInProgress")}
              {scanTicker ? <span className="muted small"> · {scanTicker}</span> : null}
            </span>
          ) : null}
        </div>
        {busy && scanTotal > 0 ? (
          <div className="moex-scan-progress-bar" role="progressbar" aria-valuenow={progressPct} aria-valuemin={0} aria-valuemax={100}>
            <div className="moex-scan-progress-bar-fill" style={{ width: `${progressPct}%` }} />
          </div>
        ) : null}
      </div>

      {scannedAt ? (
        <p className="muted small">
          {t("universe.moexScannedAt")}: {formatIsoLocal(scannedAt, lang === "en" ? "en-GB" : "ru-RU")} ·{" "}
          {t("universe.moexEligibleCount", { count: String(eligibleCount), total: String(ranked.length) })}
          {lastMeta?.liquidity_pool_count != null
            ? ` · ${t("universe.moexPoolScored", {
                pool: String(lastMeta.liquidity_pool_count),
                scored: String(lastMeta.scored_count ?? ranked.length),
              })}`
            : null}
        </p>
      ) : null}

      {ranked.length > 0 ? (
        <div className="scalp-scan-results moex-scan-results">
          <p className="muted small">{t("universe.moexScoreHint")}</p>
          <table className="scalp-scan-table small moex-scan-table">
            <thead>
              <tr>
                <th />
                <th>{t("universe.moexSymbol")}</th>
                <th>{t("universe.moexScoreCol")}</th>
                <th>{t("universe.moexMetricTurnover")}</th>
                <th>{t("universe.moexMetricVol")}</th>
                <th>{t("universe.moexMetricRsi")}</th>
                <th className="moex-scan-status-col">{t("universe.scalpStatus")}</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((row) => {
                const rowDisabled = busy || !row.eligible || Boolean(disabledSymbols?.has(row.symbol.toUpperCase()));
                const isPicked = selected.has(row.symbol.toUpperCase());
                const statusText = disabledSymbols?.has(row.symbol.toUpperCase())
                  ? t("moexAutomation.duplicateTickerShort")
                  : row.eligible
                    ? t("universe.scalpEligible")
                    : rejectLabel(row.reject_reason);
                return (
                  <tr
                    key={row.symbol}
                    className={`${row.eligible ? "eligible" : "rejected"}${isPicked ? " is-picked" : ""}${!rowDisabled ? " is-clickable" : ""}`}
                    onClick={() => pickRow(row, !isPicked)}
                    title={statusText}
                  >
                    <td onClick={(e) => e.stopPropagation()}>
                      <input
                        type={multiSelect ? "checkbox" : "radio"}
                        name={multiSelect ? undefined : "moex-pick-single"}
                        checked={isPicked}
                        disabled={rowDisabled}
                        onChange={(e) => pickRow(row, e.target.checked)}
                      />
                    </td>
                    <td className="mono-small">{row.symbol}</td>
                    <td>{row.score != null ? row.score.toFixed(3) : "—"}</td>
                    <td>{formatValtoday(row.metrics?.valtoday)}</td>
                    <td>{row.metrics?.volume_ratio ?? "—"}</td>
                    <td>{row.metrics?.rsi_14 != null ? Number(row.metrics.rsi_14).toFixed(1) : "—"}</td>
                    <td className="moex-scan-status-col">{statusText}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : scannedAt ? (
        <p className="warn small">{t("universe.moexScanEmpty")}</p>
      ) : null}

      {message ? <p className={`${messageTone} small`}>{message}</p> : null}
      {(lastMeta?.errors?.length ?? 0) > 0 ? (
        <p className="warn small">
          {t("universe.moexScanErrors", { count: String(lastMeta?.errors?.length ?? 0) })}
        </p>
      ) : null}
    </div>
  );
}
