import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiGet, apiPost, formatOperatorFacingError } from "../api";
import OperatorConfirmModal from "./OperatorConfirmModal";
import { useI18n } from "../i18n/LanguageContext";
import { usePolling } from "../hooks/usePolling";
import type { ScalpPairScanProgress } from "../types";

type ScanRankRow = {
  symbol: string;
  eligible?: boolean;
  score?: number;
  reject_reason?: string | null;
  metrics?: {
    atr_pct?: number;
    volume_ratio?: number;
    momentum_pct?: number;
    data_symbol?: string;
    data_env?: string;
  };
};

type ParamMeta = {
  min?: number;
  max?: number;
  recommended?: number | null;
  type?: string;
};

type ScanSettings = {
  effective?: Record<string, number | boolean>;
  bounds?: Record<string, { min: number; max: number }>;
  param_meta?: Record<string, ParamMeta>;
  recommended?: Record<string, number>;
  round_trip_fee_pct?: number;
  atr_pct_min_floor?: number;
  runtime_override?: boolean;
};

type LastScanPayload = {
  scanned_at?: string;
  ranked?: ScanRankRow[];
  selected_symbols?: string[];
};

function applyLastScanState(
  last: LastScanPayload | null | undefined,
  setters: {
    setScannedAt: (v: string | null) => void;
    setRanked: (v: ScanRankRow[]) => void;
    setSelected: (v: Set<string>) => void;
  },
  paramTopN: number,
) {
  if (!last) return;
  if (last.scanned_at) setters.setScannedAt(last.scanned_at);
  if (last.ranked?.length) setters.setRanked(last.ranked);
  if (last.selected_symbols?.length) {
    setters.setSelected(new Set(last.selected_symbols));
  } else if (last.ranked?.length) {
    setters.setSelected(
      new Set(last.ranked.filter((r) => r.eligible).slice(0, paramTopN).map((r) => r.symbol)),
    );
  }
}

type ScanPoolInfo = {
  bases_count?: number;
  quote_asset?: string;
  scan_pool_mode?: string;
  catalog_bases_count?: number;
  exchange_bases_count?: number;
  max_scan_bases?: number;
};

type Props = {
  workflow: string;
  locked?: boolean;
  onApplied?: () => void;
};

type ParamKey =
  | "top_n"
  | "min_score"
  | "atr_pct_min"
  | "atr_pct_max"
  | "atr_pct_sweet_min"
  | "atr_pct_sweet_max"
  | "volume_ratio_min"
  | "momentum_min_pct"
  | "max_pair_correlation";

const PARAM_KEYS: ParamKey[] = [
  "top_n",
  "min_score",
  "atr_pct_min",
  "atr_pct_max",
  "atr_pct_sweet_min",
  "atr_pct_sweet_max",
  "volume_ratio_min",
  "momentum_min_pct",
  "max_pair_correlation",
];

function formatParamValue(value: number | null | undefined, key: ParamKey): string {
  if (value == null || !Number.isFinite(value)) return "—";
  if (key === "top_n") return String(Math.round(value));
  if (key === "max_pair_correlation" || key === "min_score") return value.toFixed(2);
  return value.toFixed(2);
}

function ParamScale({
  min,
  max,
  recommended,
  value,
  recLabel,
  paramKey,
}: {
  min: number;
  max: number;
  recommended: number | null | undefined;
  value: number | null | undefined;
  recLabel: string;
  paramKey: ParamKey;
}) {
  const span = max - min;
  if (!Number.isFinite(span) || span <= 0) return null;
  const clampPct = (n: number) => Math.max(0, Math.min(100, ((n - min) / span) * 100));
  const valNum = value != null && Number.isFinite(Number(value)) ? Number(value) : null;
  const recNum = recommended != null && Number.isFinite(Number(recommended)) ? Number(recommended) : null;

  return (
    <div className="scalp-param-scale" aria-hidden>
      <div className="scalp-param-scale-track">
        {recNum != null ? (
          <span
            className="scalp-param-scale-rec"
            style={{ left: `${clampPct(recNum)}%` }}
            title={`${recLabel}: ${formatParamValue(recNum, paramKey)}`}
          />
        ) : null}
        {valNum != null ? (
          <span className="scalp-param-scale-val" style={{ left: `${clampPct(valNum)}%` }} />
        ) : null}
      </div>
      <div className="scalp-param-scale-labels">
        <span>{formatParamValue(min, paramKey)}</span>
        {recNum != null ? (
          <span className="scalp-param-scale-rec-label">
            {recLabel}: {formatParamValue(recNum, paramKey)}
          </span>
        ) : (
          <span />
        )}
        <span>{formatParamValue(max, paramKey)}</span>
      </div>
    </div>
  );
}

export default function ScalpPairPickerPanel({ workflow, locked = false, onApplied }: Props) {
  const { t } = useI18n();
  const [settings, setSettings] = useState<ScanSettings | null>(null);
  const [paramInputs, setParamInputs] = useState<Record<string, string>>({});
  const [ranked, setRanked] = useState<ScanRankRow[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [scannedAt, setScannedAt] = useState<string | null>(null);
  const [pendingApply, setPendingApply] = useState(false);
  const [opError, setOpError] = useState<string | null>(null);
  const [rescanDuringSession, setRescanDuringSession] = useState(true);
  const [scanPool, setScanPool] = useState<ScanPoolInfo | null>(null);
  const prevBusyRef = useRef(false);
  const paramTopNRef = useRef(3);

  const scanStateSetters = useMemo(
    () => ({ setScannedAt, setRanked, setSelected }),
    [setScannedAt, setRanked, setSelected],
  );

  const paramTopN = useMemo(() => {
    const raw = paramInputs.top_n;
    const n = raw !== undefined && raw !== "" ? Number(String(raw).replace(",", ".")) : 3;
    return Number.isFinite(n) ? Math.max(1, Math.round(n)) : 3;
  }, [paramInputs.top_n]);

  useEffect(() => {
    paramTopNRef.current = paramTopN;
  }, [paramTopN]);

  const fetchScanProgress = useCallback(
    () => apiGet<{ status: string } & ScalpPairScanProgress>("/api/crypto/scalp/universe-scan/progress"),
    [],
  );
  const { data: scanProgress } = usePolling(fetchScanProgress, 2_000, busy, {
    staggerKey: "scalp-picker-scan-progress",
  });

  const loadScanPool = useCallback(async () => {
    const data = await apiGet<{ status: string } & ScanPoolInfo>("/api/crypto/scalp/universe-scan/candidates");
    if (data.status === "ok") setScanPool(data);
  }, []);

  const loadSettings = useCallback(async () => {
    const data = await apiGet<{ status: string } & ScanSettings>("/api/crypto/scalp/universe-scan/settings");
    if (data.status === "ok") {
      setSettings(data);
      const eff = data.effective ?? {};
      const inputs: Record<string, string> = {};
      for (const key of PARAM_KEYS) {
        if (eff[key] != null) inputs[key] = String(eff[key]);
      }
      setParamInputs(inputs);
      if (typeof eff.rescan_during_session === "boolean") {
        setRescanDuringSession(eff.rescan_during_session);
      }
    }
  }, []);

  const loadLastScan = useCallback(async () => {
    const data = await apiGet<{
      status: string;
      last_scan?: LastScanPayload;
    }>(`/api/crypto/scalp/universe-scan/last?workflow_name=${encodeURIComponent(workflow)}`);
    applyLastScanState(data.last_scan, scanStateSetters, paramTopNRef.current);
  }, [workflow, scanStateSetters]);

  useEffect(() => {
    loadSettings().catch(() => {});
    loadLastScan().catch(() => {});
    loadScanPool().catch(() => {});
  }, [loadSettings, loadLastScan, loadScanPool]);

  useEffect(() => {
    if (prevBusyRef.current && !busy) {
      void loadLastScan().catch(() => {});
    }
    prevBusyRef.current = busy;
  }, [busy, loadLastScan]);

  const buildSettingsPayload = () => {
    const out: Record<string, number | boolean> = { rescan_during_session: rescanDuringSession };
    for (const key of PARAM_KEYS) {
      const raw = paramInputs[key];
      if (raw === undefined || raw === "") continue;
      const n = Number(String(raw).replace(",", "."));
      if (Number.isFinite(n)) out[key] = n;
    }
    return out;
  };

  const runScan = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const scan = await apiPost<{
        status: string;
        scanned_at?: string;
        ranked?: ScanRankRow[];
        selected_symbols?: string[];
        message?: string;
      }>("/api/crypto/scalp/universe-scan/run", {
        workflow_name: workflow,
        settings: buildSettingsPayload(),
      });
      if (scan.status !== "ok") {
        setMessage(scan.message ?? scan.status);
        return;
      }
      applyLastScanState(scan, scanStateSetters, paramTopN);
      setMessage(t("universe.scalpScanDone", { count: String(scan.ranked?.length ?? 0) }));
    } catch (err) {
      setMessage(formatOperatorFacingError(err, t));
      await loadLastScan().catch(() => {});
    } finally {
      setBusy(false);
    }
  };

  const applySelection = async (password: string) => {
    setOpError(null);
    setBusy(true);
    try {
      const applied = await apiPost<{
        status: string;
        scanned_at?: string;
        selected_symbols?: string[];
        last_scan?: LastScanPayload;
      }>(
        "/api/crypto/scalp/universe-scan/apply",
        {
          workflow_name: workflow,
          symbols: Array.from(selected),
          operator: "web:operator",
        },
        { operatorPassword: password },
      );
      applyLastScanState(
        applied.last_scan ?? {
          scanned_at: applied.scanned_at,
          selected_symbols: applied.selected_symbols,
          ranked,
        },
        scanStateSetters,
        paramTopN,
      );
      await loadLastScan();
      setPendingApply(false);
      setMessage(t("universe.scalpApplyDone", { count: String(selected.size) }));
      onApplied?.();
    } catch (err) {
      setOpError(formatOperatorFacingError(err, t));
    } finally {
      setBusy(false);
    }
  };

  const eligibleCount = useMemo(() => ranked.filter((r) => r.eligible).length, [ranked]);

  const scanDone = scanProgress?.done ?? 0;
  const scanTotal = scanProgress?.total ?? scanPool?.bases_count ?? 0;
  const scanBase = scanProgress?.current_base;

  const scanPoolLabel = useMemo(() => {
    if (scanPool?.bases_count == null) return null;
    const quote = scanPool.quote_asset ?? "USDT";
    const mode = scanPool.scan_pool_mode ?? "catalog";
    if (mode === "combined" || mode === "exchange") {
      return t("universe.scalpScanPoolCombined", {
        count: String(scanPool.bases_count),
        catalog: String(scanPool.catalog_bases_count ?? 0),
        exchange: String(scanPool.exchange_bases_count ?? 0),
        max: String(scanPool.max_scan_bases ?? 60),
        quote,
      });
    }
    return t("universe.scalpScanPool", { count: String(scanPool.bases_count), quote });
  }, [scanPool, t]);

  const rejectLabel = (reason?: string | null) => {
    if (!reason) return "—";
    const key = `universe.scalpReject.${reason}` as "universe.scalpReject.atr_too_low";
    const translated = t(key);
    return translated === key ? reason : translated;
  };

  const paramMeta = (key: ParamKey): ParamMeta => {
    const fromApi = settings?.param_meta?.[key];
    const bounds = settings?.bounds?.[key];
    return {
      min: fromApi?.min ?? bounds?.min,
      max: fromApi?.max ?? bounds?.max,
      recommended: fromApi?.recommended ?? settings?.recommended?.[key] ?? null,
      type: fromApi?.type,
    };
  };

  return (
    <div className="scalp-pair-picker">
      <p className="muted small">{t("universe.scalpPickerHint")}</p>
      {settings?.round_trip_fee_pct != null ? (
        <p className="muted small">
          {t("universe.scalpFeeHint", { fee: String(settings.round_trip_fee_pct) })}
        </p>
      ) : null}
      <p className="muted small">{t("universe.scalpParamLegend")}</p>

      <div className="scalp-scan-params">
        {PARAM_KEYS.map((key) => {
          const meta = paramMeta(key);
          const min = meta.min ?? 0;
          const max = meta.max ?? 1;
          const rawVal = paramInputs[key];
          const numVal = rawVal !== undefined && rawVal !== "" ? Number(String(rawVal).replace(",", ".")) : null;
          const step = key === "top_n" ? 1 : key === "max_pair_correlation" || key === "min_score" ? 0.01 : 0.01;

          return (
            <div key={key} className="scalp-param-field">
              <label className="scalp-param-label">
                <span className="scalp-param-title">
                  {t(`universe.scalpParam.${key}` as "universe.scalpParam.top_n")}
                </span>
                <span className="muted small scalp-param-desc">
                  {t(`universe.scalpParamDesc.${key}` as "universe.scalpParamDesc.top_n")}
                </span>
                <div className="scalp-param-input-row">
                  <input
                    type="number"
                    className="input"
                    step={step}
                    min={min}
                    max={max}
                    value={paramInputs[key] ?? ""}
                    disabled={busy || locked}
                    onChange={(e) => setParamInputs((prev) => ({ ...prev, [key]: e.target.value }))}
                  />
                  <span className="muted small scalp-param-range-text">
                    {t("universe.scalpParamRange", {
                      min: formatParamValue(min, key),
                      max: formatParamValue(max, key),
                      rec: formatParamValue(meta.recommended ?? null, key),
                    })}
                  </span>
                </div>
              </label>
              <ParamScale
                min={min}
                max={max}
                recommended={meta.recommended}
                value={numVal}
                recLabel={t("universe.scalpRecommendedShort")}
                paramKey={key}
              />
            </div>
          );
        })}
      </div>

      <label className="checkbox-field">
        <input
          type="checkbox"
          checked={rescanDuringSession}
          disabled={busy || locked}
          onChange={(e) => setRescanDuringSession(e.target.checked)}
        />
        <span className="small">{t("universe.scalpRescanDuringSession")}</span>
      </label>

      <div className="scalp-scan-actions">
        {scanPoolLabel ? (
          <p className="muted small scalp-scan-pool">{scanPoolLabel}</p>
        ) : null}
        <p className="muted small scalp-scan-pool-detail">{t("universe.scalpScanPoolDetail")}</p>
        <div className="btn-row">
          <button type="button" className="tiny primary" disabled={busy || locked} onClick={() => void runScan()}>
            {busy ? t("universe.scalpRunScanBusy") : t("universe.scalpRunScan")}
          </button>
          {busy ? (
            <span className="scalp-scan-inline-status" role="status" aria-live="polite">
              <span className="scalp-scan-inline-dot" aria-hidden />
              {scanTotal > 0
                ? t("universe.scalpScanProgress", {
                    done: String(scanDone),
                    total: String(scanTotal),
                  })
                : t("universe.scalpScanInProgress")}
              {scanBase ? <span className="muted small"> · {scanBase}</span> : null}
            </span>
          ) : null}
          <button
          type="button"
          className="tiny"
          disabled={busy || locked || selected.size === 0}
          onClick={() => {
            setOpError(null);
            setPendingApply(true);
          }}
        >
          {t("universe.scalpApplySelection", { count: String(selected.size) })}
        </button>
        </div>
      </div>

      {scannedAt ? (
        <p className="muted small">
          {t("universe.scalpScannedAt")}: {String(scannedAt).slice(0, 19).replace("T", " ")} ·{" "}
          {t("universe.scalpEligibleCount", { count: String(eligibleCount), total: String(ranked.length) })}
        </p>
      ) : null}

      {ranked.length > 0 ? (
        <div className="scalp-scan-results">
          <p className="muted small">{t("universe.scalpScoreHint")}</p>
          <table className="scalp-scan-table small">
            <thead>
              <tr>
                <th />
                <th>{t("universe.symbol")}</th>
                <th>{t("universe.scalpScoreCol")}</th>
                <th>{t("universe.scalpMetricAtr")}</th>
                <th>{t("universe.scalpMetricVol")}</th>
                <th>{t("universe.scalpMetricData")}</th>
                <th>{t("universe.scalpStatus")}</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((row) => (
                <tr key={row.symbol} className={row.eligible ? "eligible" : "rejected"}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selected.has(row.symbol)}
                      disabled={busy || locked || !row.eligible}
                      onChange={(e) => {
                        setSelected((prev) => {
                          const next = new Set(prev);
                          if (e.target.checked) next.add(row.symbol);
                          else next.delete(row.symbol);
                          return next;
                        });
                      }}
                    />
                  </td>
                  <td className="mono-small">{row.symbol}</td>
                  <td>{row.score != null ? row.score.toFixed(3) : "—"}</td>
                  <td>{row.metrics?.atr_pct ?? "—"}</td>
                  <td>{row.metrics?.volume_ratio ?? "—"}</td>
                  <td className="mono-small muted">
                    {row.metrics?.data_symbol && row.metrics.data_symbol !== row.symbol
                      ? `${row.metrics.data_symbol}${row.metrics.data_env === "mainnet" ? " · main" : ""}`
                      : row.metrics?.data_env === "mainnet"
                        ? "mainnet"
                        : "—"}
                  </td>
                  <td>{row.eligible ? t("universe.scalpEligible") : rejectLabel(row.reject_reason)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {message ? <p className="muted small">{message}</p> : null}

      <OperatorConfirmModal
        open={pendingApply}
        title={t("universe.scalpApplySelection", { count: String(selected.size) })}
        lead={t("workflowsPage.operatorLead")}
        risk={t("universe.scalpApplyRisk")}
        confirmLabel={t("universe.scalpApplySelection", { count: String(selected.size) })}
        busy={busy}
        error={opError}
        onCancel={() => {
          if (!busy) {
            setPendingApply(false);
            setOpError(null);
          }
        }}
        onConfirm={applySelection}
      />
    </div>
  );
}
