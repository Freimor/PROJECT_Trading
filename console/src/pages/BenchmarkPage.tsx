import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiGet, apiPost } from "../api";
import PortfolioCard from "../components/PortfolioCard";
import { POLL } from "../config/polling";
import { useErrorNotifications } from "../context/ErrorNotifications";
import { useI18n } from "../i18n/LanguageContext";
import { usePolling } from "../hooks/usePolling";

type Market = "crypto" | "securities";

type CalibJob = {
  state?: "idle" | "running" | "done" | "error" | "cancelled" | "cancelling";
  phase?: string;
  market?: string;
  model?: string;
  message?: string;
  error?: string;
  progress_pct?: number;
  started_at?: string;
  finished_at?: string;
  temperature_index?: number;
  temperature_total?: number;
  current_temperature?: number;
  case_index?: number;
  case_total?: number;
  current_case_id?: string;
  llm_calls_done?: number;
  llm_calls_total?: number;
  result?: { recommended?: Record<string, unknown> };
};

type OllamaModelsResp = {
  status?: string;
  models?: Array<{ name: string }>;
  message?: string;
};

type MarketLlmBlock = {
  llm?: {
    temperature?: number;
    min_confidence?: number;
    max_tokens?: number;
    require_counter_thesis?: boolean;
    counter_thesis_min_chars?: number;
    timeout_ms?: number;
  };
  model?: string;
  prompt_version?: string;
  config_hint?: string;
  calibration?: CalibPlan;
  last_calibration?: Record<string, unknown> | null;
};

type LlmSettings = {
  shared?: {
    require_counter_thesis?: boolean;
    counter_thesis_min_chars?: number;
    timeout_ms?: number;
    max_tokens?: number;
    benchmark_unload_after?: boolean;
  };
  markets?: Record<Market, MarketLlmBlock>;
};

type CalibStage = {
  id?: string;
  group?: string;
  title_ru?: string;
  title_en?: string;
  description_ru?: string;
  description_en?: string;
};

type CalibPlan = {
  temperatures?: number[];
  min_confidence?: number[];
  grid_cells?: number;
  llm_calls?: number;
  fixtures?: { synthetic?: number; historical?: number };
  stages?: CalibStage[];
};

const MODEL_STORAGE_KEY = (m: Market) => `benchmark-calib-model:${m}`;

function formatElapsed(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function formatTimeout(ms?: number): string {
  if (ms == null) return "—";
  if (ms >= 60_000) return `${Math.round(ms / 60_000)} min`;
  return `${ms} ms`;
}

function elapsedFromIso(iso?: string): number {
  if (!iso) return 0;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return 0;
  return Math.max(0, Math.floor((Date.now() - t) / 1000));
}

export default function BenchmarkPage() {
  const { t, lang } = useI18n();
  const [market, setMarket] = useState<Market>("crypto");
  const [log, setLog] = useState("");
  const [busy, setBusy] = useState(false);
  const [jobStatus, setJobStatus] = useState<CalibJob | null>(null);
  const [jobsOverview, setJobsOverview] = useState<Partial<Record<Market, CalibJob>>>({});
  const [selectedModel, setSelectedModel] = useState("");
  const [elapsedSec, setElapsedSec] = useState(0);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const resumedRef = useRef(false);
  const completedRef = useRef<string | null>(null);
  const { report } = useErrorNotifications();

  const { data: reportData, refresh: refreshReport } = usePolling(
    () => apiGet("/api/benchmark/report?days=30"),
    POLL.OPS,
    true,
    { staggerKey: "benchmark-report" },
  );
  const { data: llmSettings, refresh: refreshLlmSettings } = usePolling<LlmSettings>(
    () => apiGet("/api/benchmark/llm-settings"),
    POLL.OPS,
    true,
    { staggerKey: "benchmark-llm-settings" },
  );
  const { data: ollamaModels } = usePolling<OllamaModelsResp>(
    () => apiGet("/api/ollama/models"),
    POLL.OPS,
    true,
    { staggerKey: "benchmark-ollama-models" },
  );
  const { data: plan } = usePolling<CalibPlan>(
    () => apiGet(`/api/benchmark/calibrate/plan?market=${market}`),
    POLL.STATIC,
    true,
    { staggerKey: `benchmark-plan-${market}` },
  );
  const { data: calib, refresh: refreshCalib } = usePolling(
    () => apiGet(`/api/benchmark/calibrate/last-snapshot?market=${market}`),
    POLL.OPS * 2,
    true,
    { staggerKey: `benchmark-calib-${market}` },
  );

  const marketBlock = llmSettings?.markets?.[market];
  const shared = llmSettings?.shared;
  const calGrid = plan ?? marketBlock?.calibration;
  const yamlModel = marketBlock?.model ?? "";
  const modelOptions = ollamaModels?.models?.map((m) => m.name) ?? [];
  const marketJobRunning = jobStatus?.state === "running" || jobStatus?.state === "cancelling";
  const anyJobRunning = Object.values(jobsOverview).some(
    (j) => j?.state === "running" || j?.state === "cancelling",
  );

  const fetchJobStatus = useCallback(async (m: Market) => {
    const status = await apiGet<CalibJob>(`/api/benchmark/calibrate/status?market=${m}`);
    if (m === market) setJobStatus(status);
    return status;
  }, [market]);

  const fetchJobsOverview = useCallback(async () => {
    const overview = await apiGet<{
      markets?: Partial<Record<Market, CalibJob>>;
      active_market?: Market;
    }>("/api/benchmark/calibrate/status");
    if (overview.markets) setJobsOverview(overview.markets);
    return overview;
  }, []);

  // Восстановление прогресса сразу после загрузки / обновления страницы (один раз)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const overview = await fetchJobsOverview();
      if (cancelled) return;
      const active = overview.active_market;
      if (active) {
        setMarket(active);
        const activeJob = overview.markets?.[active];
        if (activeJob) setJobStatus(activeJob);
        if (!resumedRef.current) {
          resumedRef.current = true;
          setLog(t("benchmark.calibResumed"));
        }
      }
    })().catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [fetchJobsOverview, t]);

  // Частый опрос статуса текущего рынка (без задержки stagger)
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const status = await apiGet<CalibJob>(`/api/benchmark/calibrate/status?market=${market}`);
        if (!cancelled) setJobStatus(status);
      } catch {
        /* keep last known status */
      }
    };
    void tick();
    const id = window.setInterval(tick, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [market]);

  // Обзор всех рынков — индикатор на вкладках
  useEffect(() => {
    const tick = () => {
      void fetchJobsOverview();
    };
    tick();
    const id = window.setInterval(tick, 5000);
    return () => window.clearInterval(id);
  }, [fetchJobsOverview]);

  useEffect(() => {
    const stored = sessionStorage.getItem(MODEL_STORAGE_KEY(market));
    setSelectedModel(stored || yamlModel || "");
  }, [market, yamlModel]);

  useEffect(() => {
    if (!marketJobRunning) return;
    const base = elapsedFromIso(jobStatus?.started_at);
    setElapsedSec(base);
    const id = window.setInterval(() => {
      setElapsedSec(elapsedFromIso(jobStatus?.started_at));
    }, 1000);
    return () => window.clearInterval(id);
  }, [jobStatus?.started_at, marketJobRunning]);

  useEffect(() => {
    if (!jobStatus?.state || jobStatus.state === "running" || jobStatus.state === "idle" || jobStatus.state === "cancelling") return;
    const key = `${market}:${jobStatus.finished_at ?? jobStatus.state}`;
    if (completedRef.current === key) return;
    completedRef.current = key;

    if (jobStatus.state === "done") {
      refreshCalib();
      refreshLlmSettings();
      const rec = jobStatus.result?.recommended;
      const marketLabel = market === "crypto" ? t("benchmark.marketCrypto") : t("benchmark.marketMoex");
      if (rec) {
        setLog(
          `${marketLabel} ${t("benchmark.calibDone")}: T=${rec.temperature}, conf=${rec.min_confidence}, score=${rec.composite_score}`,
        );
      } else {
        setLog(`${marketLabel}: ${t("benchmark.calibDone")}`);
      }
      report("benchmark/calibrate", null);
    }
    if (jobStatus.state === "error") {
      const marketLabel = market === "crypto" ? t("benchmark.marketCrypto") : t("benchmark.marketMoex");
      const message = jobStatus.error || jobStatus.message || t("benchmark.calibError");
      setLog(`${marketLabel} — ${t("benchmark.calibError")}: ${message}`);
      report("benchmark/calibrate", message);
    }
    if (jobStatus.state === "cancelled") {
      const marketLabel = market === "crypto" ? t("benchmark.marketCrypto") : t("benchmark.marketMoex");
      setLog(`${marketLabel}: ${t("benchmark.calibCancelled")}`);
      report("benchmark/calibrate", null);
    }
    void fetchJobsOverview();
  }, [jobStatus, market, refreshCalib, refreshLlmSettings, report, t, fetchJobsOverview]);

  const runReport = async () => {
    setBusy(true);
    report("benchmark/outcome", null);
    try {
      await apiPost("/api/benchmark/sample?days=30", {});
      await apiPost("/api/benchmark/label", {});
      refreshReport();
      setLog(t("benchmark.outcomeDone"));
    } catch (err) {
      report("benchmark/outcome", String(err));
    } finally {
      setBusy(false);
    }
  };

  const runCalibration = useCallback(async () => {
    if (marketJobRunning) return;
    report("benchmark/calibrate", null);
    const marketLabel = market === "crypto" ? t("benchmark.marketCrypto") : t("benchmark.marketMoex");
    const model = selectedModel || yamlModel || undefined;
    if (model) sessionStorage.setItem(MODEL_STORAGE_KEY(market), model);
    try {
      const resp = await apiPost<{ status?: string }>("/api/benchmark/calibrate/start", {
        market,
        model,
      });
      completedRef.current = null;
      const status = await fetchJobStatus(market);
      setJobStatus(status);
      void fetchJobsOverview();
      if (resp.status === "already_running") {
        setLog(`${marketLabel}: ${t("benchmark.calibAlreadyRunning")}`);
      } else if (resp.status === "blocked") {
        const other =
          (resp as { blocked_by?: string }).blocked_by === "crypto"
            ? t("benchmark.marketCrypto")
            : t("benchmark.marketMoex");
        setLog(`${marketLabel}: ${t("benchmark.calibBlockedBy", { market: other })}`);
      } else {
        setLog(`${marketLabel}: ${t("benchmark.runCalibration")} (${model ?? yamlModel})…`);
      }
    } catch (err) {
      setLog(`${marketLabel} — ${t("benchmark.calibError")}: ${String(err)}`);
      report("benchmark/calibrate", String(err));
    }
  }, [
    fetchJobStatus,
    fetchJobsOverview,
    market,
    marketJobRunning,
    report,
    selectedModel,
    t,
    yamlModel,
  ]);

  const cancelCalibration = useCallback(async () => {
    setCancelling(true);
    const marketLabel = market === "crypto" ? t("benchmark.marketCrypto") : t("benchmark.marketMoex");
    try {
      await apiPost("/api/benchmark/calibrate/cancel", { market });
      const status = await fetchJobStatus(market);
      setJobStatus(status);
      void fetchJobsOverview();
      setLog(`${marketLabel}: ${t("benchmark.calibCancelling")}`);
    } catch (err) {
      setLog(`${marketLabel} — ${t("benchmark.calibError")}: ${String(err)}`);
      report("benchmark/calibrate", String(err));
    } finally {
      setCancelling(false);
      setCancelOpen(false);
    }
  }, [fetchJobStatus, fetchJobsOverview, market, report, t]);

  const rep = reportData as Record<string, unknown> | null;
  const byMarket = (rep?.by_market ?? {}) as Record<string, { outcome?: Record<string, unknown> }>;
  const cal = (calib as Record<string, unknown> | null) ?? marketBlock?.last_calibration ?? null;
  const rec = cal?.recommended as Record<string, unknown> | undefined;
  const llm = marketBlock?.llm;
  const job = jobStatus;

  const progressPct = useMemo(() => {
    if (job?.progress_pct != null) return Math.max(0, Math.min(100, job.progress_pct));
    return 0;
  }, [job?.progress_pct]);

  const progressLine = useMemo(() => {
    if (!marketJobRunning || !job) return null;
    const elapsed = `${t("benchmark.elapsed")}: ${formatElapsed(elapsedSec)}`;
    const msg = job.message || t("benchmark.calibWaiting");
    return `${elapsed} — ${msg}`;
  }, [marketJobRunning, elapsedSec, job, t]);

  const modelSelectOptions = useMemo(() => {
    const names = new Set(modelOptions);
    if (yamlModel) names.add(yamlModel);
    if (selectedModel) names.add(selectedModel);
    if (job?.model) names.add(job.model);
    return Array.from(names).sort();
  }, [job?.model, modelOptions, selectedModel, yamlModel]);

  const stages = calGrid?.stages ?? [];
  const outcomeStages = stages.filter((s) => s.group === "outcome");
  const calibStages = stages.filter((s) => s.group === "calibration");
  const stageTitle = (s: CalibStage) => (lang === "en" ? s.title_en : s.title_ru) ?? s.id ?? "";
  const stageDesc = (s: CalibStage) => (lang === "en" ? s.description_en : s.description_ru) ?? "";

  const activeStageId = useMemo(() => {
    if (!marketJobRunning || !job) return null;
    if (job.phase === "finalize") return "calib_finalize";
    return "calib_temperature";
  }, [job, marketJobRunning]);

  return (
    <div className="page">
      <div className="page-title">
        <h2>📊 {t("benchmark.title")}</h2>
        <p className="muted">{t("benchmark.subtitle")}</p>
      </div>

      <div className="btn-row benchmark-market-tabs" style={{ marginBottom: "0.75rem" }}>
        {(["crypto", "securities"] as const).map((mkt) => (
          <button
            key={mkt}
            type="button"
            className={market === mkt ? "primary tiny" : "tiny"}
            onClick={() => setMarket(mkt)}
          >
            {mkt === "crypto" ? t("benchmark.marketCrypto") : t("benchmark.marketMoex")}
            {jobsOverview[mkt]?.state === "running" || jobsOverview[mkt]?.state === "cancelling" ? " ●" : ""}
          </button>
        ))}
        <span className="muted small">{t("benchmark.marketHint")}</span>
      </div>

      <div className="btn-row benchmark-actions" style={{ marginBottom: "1rem" }}>
        <button type="button" disabled={busy || marketJobRunning} onClick={runReport}>
          {t("benchmark.updateOutcome")}
        </button>
        <label className="benchmark-model-select">
          <span className="muted small">{t("benchmark.selectModel")}</span>
          <select
            value={selectedModel}
            disabled={marketJobRunning || anyJobRunning}
            onChange={(e) => {
              setSelectedModel(e.target.value);
              sessionStorage.setItem(MODEL_STORAGE_KEY(market), e.target.value);
            }}
          >
            {modelSelectOptions.length === 0 ? (
              <option value="">{t("benchmark.ollamaModelsEmpty")}</option>
            ) : (
              modelSelectOptions.map((name) => (
                <option key={name} value={name}>
                  {name}
                  {name === yamlModel ? ` (${t("benchmark.configModel")})` : ""}
                </option>
              ))
            )}
          </select>
        </label>
        <button
          type="button"
          className="primary"
          disabled={busy || marketJobRunning || !(plan?.temperatures?.length ?? 0) || !selectedModel}
          onClick={runCalibration}
        >
          {marketJobRunning ? t("benchmark.calibrating") : t("benchmark.runCalibration")}
        </button>
        {!marketJobRunning && plan?.llm_calls != null ? (
          <span className="muted">
            ~{plan.llm_calls} LLM · {plan.grid_cells ?? "?"} {t("benchmark.gridCells").toLowerCase()}
          </span>
        ) : null}
        {ollamaModels?.status === "error" ? (
          <span className="muted warn-text">{t("benchmark.ollamaModelsError")}</span>
        ) : null}
      </div>

      {marketJobRunning && job ? (
        <div style={{ marginBottom: "1rem" }}>
          <PortfolioCard title={t("benchmark.calibStatusTitle")}>
            <div className="calib-progress-head">
              <span className="pill">
                {job.state === "cancelling" ? t("benchmark.calibCancelling") : t("benchmark.calibRunning")}
              </span>
              <strong>{progressPct}%</strong>
            </div>
            <div className="calib-progress-track" aria-hidden="true">
              <div className="calib-progress-fill" style={{ width: `${progressPct}%` }} />
            </div>
            {progressLine ? <p className="benchmark-progress">{progressLine}</p> : null}
            <div className="metric-row compact">
              <span>{t("benchmark.selectModel")}</span>
              <strong className="mono-small">{job.model ?? selectedModel ?? "—"}</strong>
            </div>
            <div className="metric-row compact">
              <span>{t("benchmark.calibLlmCalls")}</span>
              <strong>
                {job.llm_calls_done ?? 0} / {job.llm_calls_total ?? plan?.llm_calls ?? "?"}
              </strong>
            </div>
            {job.temperature_total ? (
              <div className="metric-row compact">
                <span>{t("benchmark.temperature")}</span>
                <strong>
                  {job.temperature_index ?? 0}/{job.temperature_total}
                  {job.current_temperature != null ? ` · T=${job.current_temperature}` : ""}
                </strong>
              </div>
            ) : null}
            {job.case_total ? (
              <div className="metric-row compact">
                <span>{t("benchmark.cases")}</span>
                <strong>
                  {job.case_index ?? 0}/{job.case_total}
                  {job.current_case_id ? ` · ${job.current_case_id}` : ""}
                </strong>
              </div>
            ) : null}
            <div className="btn-row" style={{ marginTop: "0.75rem" }}>
              <button
                type="button"
                className="danger"
                disabled={cancelling}
                onClick={() => setCancelOpen(true)}
              >
                {cancelling ? t("benchmark.calibCancelling") : t("benchmark.cancelCalibration")}
              </button>
            </div>
          </PortfolioCard>
        </div>
      ) : null}

      {cancelOpen ? (
        <div className="modal-overlay" role="presentation" onClick={() => !cancelling && setCancelOpen(false)}>
          <div
            className="modal-dialog"
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
          >
            <h3>{t("benchmark.cancelCalibTitle")}</h3>
            <p className="modal-lead">{t("benchmark.cancelCalibLead")}</p>
            <p className="modal-risk danger-text">{t("benchmark.cancelCalibRisk")}</p>
            <div className="modal-actions">
              <button type="button" disabled={cancelling} onClick={() => setCancelOpen(false)}>
                {t("benchmark.cancelCalibBack")}
              </button>
              <button type="button" className="primary danger" disabled={cancelling} onClick={cancelCalibration}>
                {cancelling ? t("common.loading") : t("benchmark.cancelCalibConfirm")}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <div style={{ marginBottom: "1rem" }}>
      <PortfolioCard title={t("benchmark.stagesTitle")}>
        <p className="muted small">{t("benchmark.stagesHint")}</p>
        {outcomeStages.length > 0 ? (
          <>
            <h4 className="benchmark-stage-group">{t("benchmark.stagesOutcome")}</h4>
            <ul className="benchmark-stages-list">
              {outcomeStages.map((stage) => (
                <li key={stage.id}>
                  <strong>{stageTitle(stage)}</strong>
                  <p className="muted small">{stageDesc(stage)}</p>
                </li>
              ))}
            </ul>
          </>
        ) : null}
        {calibStages.length > 0 ? (
          <>
            <h4 className="benchmark-stage-group">{t("benchmark.stagesCalibration")}</h4>
            <ul className="benchmark-stages-list">
              {calibStages.map((stage) => (
                <li
                  key={stage.id}
                  className={activeStageId === stage.id ? "benchmark-stage-active" : undefined}
                >
                  <strong>{stageTitle(stage)}</strong>
                  <p className="muted small">{stageDesc(stage)}</p>
                </li>
              ))}
            </ul>
          </>
        ) : null}
        <p className="muted small" style={{ marginTop: "0.75rem" }}>
          {t("benchmark.concurrentCalibNote")}
        </p>
      </PortfolioCard>
      </div>

      <div className="grid cards-2" style={{ marginBottom: "1rem" }}>
        <PortfolioCard
          title={`${t("benchmark.llmSettingsTitle")} — ${
            market === "crypto" ? t("benchmark.marketCrypto") : t("benchmark.marketMoex")
          }`}
        >
          <div className="metric-row">
            <span>
              {market === "crypto" ? t("benchmark.modelCrypto") : t("benchmark.modelSecurities")}
            </span>
            <strong className="mono-small">{yamlModel || "—"}</strong>
          </div>
          <div className="metric-row">
            <span>
              {market === "crypto" ? t("benchmark.promptCrypto") : t("benchmark.promptSecurities")}
            </span>
            <strong className="mono-small">{marketBlock?.prompt_version ?? "—"}</strong>
          </div>
          <hr className="card-divider" />
          <div className="metric-row">
            <span>{t("benchmark.temperature")}</span>
            <strong>{llm?.temperature ?? "—"}</strong>
          </div>
          <div className="metric-row">
            <span>{t("benchmark.minConfidence")}</span>
            <strong>{llm?.min_confidence ?? "—"}</strong>
          </div>
          <div className="metric-row">
            <span>{t("benchmark.maxTokens")}</span>
            <strong>{llm?.max_tokens ?? shared?.max_tokens ?? "—"}</strong>
          </div>
          <p className="muted small" style={{ marginTop: "0.5rem" }}>
            {marketBlock?.config_hint}
          </p>
        </PortfolioCard>

        <PortfolioCard title={t("benchmark.sharedSettings")}>
          <div className="metric-row">
            <span>{t("benchmark.counterThesis")}</span>
            <strong>
              {shared?.require_counter_thesis
                ? t("benchmark.counterThesisRequired", {
                    chars: String(shared.counter_thesis_min_chars ?? 10),
                  })
                : t("benchmark.counterThesisOff")}
            </strong>
          </div>
          <div className="metric-row">
            <span>{t("benchmark.timeout")}</span>
            <strong>{formatTimeout(shared?.timeout_ms)}</strong>
          </div>
          <div className="metric-row">
            <span>{t("benchmark.unloadAfter")}</span>
            <strong>{shared?.benchmark_unload_after ? t("benchmark.yes") : t("benchmark.no")}</strong>
          </div>
          <hr className="card-divider" />
          <div className="metric-row">
            <span>{t("benchmark.temperature")}</span>
            <strong className="mono-small">
              {(calGrid?.temperatures ?? []).join(", ") || "—"}
            </strong>
          </div>
          <div className="metric-row">
            <span>{t("benchmark.minConfidence")}</span>
            <strong className="mono-small">
              {(calGrid?.min_confidence ?? []).join(", ") || "—"}
            </strong>
          </div>
          <div className="metric-row">
            <span>{t("benchmark.gridCells")}</span>
            <strong>{calGrid?.grid_cells ?? "—"}</strong>
          </div>
          <div className="metric-row">
            <span>{t("benchmark.llmCalls")}</span>
            <strong>{calGrid?.llm_calls ?? "—"}</strong>
          </div>
          <div className="metric-row">
            <span>{t("benchmark.fixtures")}</span>
            <strong>
              {t("benchmark.fixturesSynthetic")} {calGrid?.fixtures?.synthetic ?? 0} ·{" "}
              {t("benchmark.fixturesHistorical")} {calGrid?.fixtures?.historical ?? 0}
            </strong>
          </div>
        </PortfolioCard>
      </div>

      <div className="grid cards-2">
        <PortfolioCard title={t("benchmark.outcomeTitle")}>
          <div className="metric-row">
            <span>{t("benchmark.cases")}</span>
            <strong>{String(rep?.total_cases ?? 0)}</strong>
          </div>
          <div className="metric-row">
            <span>{t("benchmark.labeled")}</span>
            <strong>{String(rep?.labeled_cases ?? 0)}</strong>
          </div>
          {Object.entries(byMarket).map(([mkt, block]) => (
            <div key={mkt} className="market-block">
              <strong>{mkt}</strong>
              <div className="muted">
                {t("benchmark.precision")}: {String(block.outcome?.precision_approve ?? "—")} ·{" "}
                {t("benchmark.recall")}: {String(block.outcome?.recall ?? "—")}
              </div>
            </div>
          ))}
        </PortfolioCard>

        <PortfolioCard
          title={`${t("benchmark.lastCalibrationTitle")} — ${
            market === "crypto" ? t("benchmark.marketCrypto") : t("benchmark.marketMoex")
          }`}
        >
          {cal?.status === "ok" && rec ? (
            <>
              <div className="metric-row">
                <span>{t("benchmark.recommendation")}</span>
                <strong>
                  T={String(rec.temperature)} conf={String(rec.min_confidence)}
                </strong>
              </div>
              <div className="metric-row">
                <span>{t("benchmark.score")}</span>
                <strong>{String(rec.composite_score)}</strong>
              </div>
              <p className="muted small">{String(cal.recommendation_note ?? "")}</p>
            </>
          ) : (
            <p className="muted">{t("benchmark.noCalibration")}</p>
          )}
        </PortfolioCard>
      </div>

      {log ? (
        <PortfolioCard title={t("benchmark.logTitle")}>
          <pre>{log}</pre>
        </PortfolioCard>
      ) : null}
    </div>
  );
}
