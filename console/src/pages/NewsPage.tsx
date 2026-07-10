import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet, apiPatch, apiPost, apiPut } from "../api";
import { POLL } from "../config/polling";
import { useI18n } from "../i18n/LanguageContext";
import { usePolling } from "../hooks/usePolling";

type LlmAnalysis = {
  significant?: boolean;
  significance_score?: number;
  confidence?: number;
  impact?: string;
  analysis_ru?: string;
  lead_ru?: string;
  headline_ru?: string;
};

type NewsSignal = {
  id?: string;
  status?: string;
  impact?: string;
  confidence?: number;
  significance_score?: number;
  model?: string;
  analysis_ru?: string;
  consumed_at?: string;
};

type SignalNewsItem = {
  id?: string;
  title?: string;
  summary?: string;
  body_raw?: string;
  source_name?: string;
  source_tier?: string;
  source_url?: string;
  published_at?: string;
  verification_status?: string;
  trust_score?: number;
  relevance_score?: number;
  matched_symbols_list?: string[];
  used_in_signal?: boolean;
  llm_model?: string;
  llm_analyzed_at?: string;
  llm_analysis?: LlmAnalysis | null;
  signal?: NewsSignal | null;
  user_context?: { context_text?: string; locked_at?: string | null } | null;
  context_editable?: boolean;
  related_signals?: Array<{
    event_at?: string;
    market?: string;
    symbol?: string;
    stage?: string;
    decision?: string;
    workflow_name?: string;
  }>;
  filter_meta_parsed?: {
    relevance_score?: number;
    mode?: string;
    matched_keywords?: string[];
    matched_tags?: string[];
    universe_symbols?: string[];
    reasons?: string[];
  };
};

type FeedResp = {
  status?: string;
  count?: number;
  items?: SignalNewsItem[];
};

type NewsSource = {
  id: string;
  name: string;
  source_tier?: string;
  enabled?: number | boolean;
  effective_trust?: number;
  tags_list?: string[];
  last_fetched_at?: string;
  last_error?: string;
};

type EngineSettings = {
  analysis?: {
    enabled?: boolean;
    analyze_on_ingest?: boolean;
    batch_size?: number;
    min_confidence?: number;
    min_significance_score?: number;
    ollama_model?: string;
  };
  context?: {
    max_signals_per_symbol?: number;
    include_user_context?: boolean;
  };
  filter?: {
    enabled?: boolean;
    mode?: string;
    active_tags?: string[];
    keywords_include?: string[];
    keywords_exclude?: string[];
    require_symbol_or_keyword?: boolean;
    min_keywords?: number;
    min_relevance_score?: number;
    require_keyword_in_title?: boolean;
  };
};

const TAG_OPTIONS = ["crypto", "moex", "macro"] as const;

function linesToList(text: string): string[] {
  return text
    .split(/[\n,;]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function listToLines(items?: string[]): string {
  return (items ?? []).join("\n");
}

function formatWhen(iso?: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso).slice(0, 16).replace("T", " ");
  return d.toLocaleString(undefined, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function NewsContextEditor({
  itemId,
  initial,
  editable,
  onSaved,
}: {
  itemId: string;
  initial: string;
  editable: boolean;
  onSaved: () => void;
}) {
  const { t } = useI18n();
  const [text, setText] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    setText(initial);
  }, [initial, itemId]);

  if (!editable) {
    if (!initial) return null;
    return (
      <div className="news-block news-block-context locked">
        <div className="news-block-label">{t("news.userContextLocked")}</div>
        <p className="news-block-body">{initial}</p>
      </div>
    );
  }

  const save = async () => {
    setBusy(true);
    setMsg(null);
    try {
      await apiPut(`/api/news/items/${itemId}/context`, { context_text: text, operator: "console" });
      setMsg(t("news.contextSaved"));
      onSaved();
    } catch (err) {
      setMsg(String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="news-block news-block-context">
      <div className="news-block-label">{t("news.userContext")}</div>
      <textarea
        className="news-context-input"
        rows={3}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={t("news.userContextPlaceholder")}
      />
      <div className="news-context-actions">
        <button type="button" className="tiny primary" disabled={busy} onClick={save}>
          {busy ? t("common.saving") : t("news.saveContext")}
        </button>
        {msg ? <span className="muted small">{msg}</span> : null}
      </div>
    </div>
  );
}

export default function NewsPage() {
  const { t } = useI18n();
  const [ingestBusy, setIngestBusy] = useState(false);
  const [analyzeBusy, setAnalyzeBusy] = useState(false);
  const [ingestMsg, setIngestMsg] = useState<string | null>(null);
  const [sources, setSources] = useState<NewsSource[]>([]);
  const [settings, setSettings] = useState<EngineSettings | null>(null);
  const [settingsBusy, setSettingsBusy] = useState(false);
  const [reapplyBusy, setReapplyBusy] = useState(false);
  const [includeKwText, setIncludeKwText] = useState("");
  const [excludeKwText, setExcludeKwText] = useState("");

  const fetcher = useCallback(() => apiGet<FeedResp>("/api/news/signal-feed?limit=50"), []);
  const { data, loading, error, refresh } = usePolling(fetcher, POLL.EVENTS, true, {
    staggerKey: "news-signal-feed",
  });

  const loadSidebar = useCallback(async () => {
    try {
      const [src, cfg] = await Promise.all([
        apiGet<NewsSource[]>("/api/news/sources"),
        apiGet<EngineSettings>("/api/signals-engine/settings"),
      ]);
      setSources(src);
      setSettings(cfg);
      setIncludeKwText(listToLines(cfg.filter?.keywords_include));
      setExcludeKwText(listToLines(cfg.filter?.keywords_exclude));
    } catch {
      /* sidebar is non-critical */
    }
  }, []);

  useEffect(() => {
    loadSidebar();
  }, [loadSidebar]);

  const items = data?.items ?? [];

  const runIngest = async () => {
    setIngestBusy(true);
    setIngestMsg(null);
    try {
      const r = await apiPost<{
        inserted?: number;
        filtered_out?: number;
        analysis?: { analyzed?: number };
      }>("/api/news/ingest");
      const analyzed = r.analysis?.analyzed ?? 0;
      const filtered = r.filtered_out ?? 0;
      setIngestMsg(
        t("news.ingestDone", { count: String(r.inserted ?? 0) }) +
          (filtered ? ` · ${t("news.filteredOut", { count: String(filtered) })}` : "") +
          (analyzed ? ` · ${t("news.analyzedCount", { count: String(analyzed) })}` : ""),
      );
      refresh();
      loadSidebar();
    } catch (err) {
      setIngestMsg(String(err));
    } finally {
      setIngestBusy(false);
    }
  };

  const runAnalyze = async () => {
    setAnalyzeBusy(true);
    setIngestMsg(null);
    try {
      const r = await apiPost<{ analyzed?: number }>("/api/signals-engine/analyze-pending?limit=12");
      setIngestMsg(t("news.analyzedCount", { count: String(r.analyzed ?? 0) }));
      refresh();
    } catch (err) {
      setIngestMsg(String(err));
    } finally {
      setAnalyzeBusy(false);
    }
  };

  const toggleSource = async (src: NewsSource) => {
    const enabled = !(src.enabled === 1 || src.enabled === true);
    await apiPatch(`/api/news/sources/${src.id}`, { enabled });
    loadSidebar();
  };

  const saveSettings = async () => {
    if (!settings) return;
    setSettingsBusy(true);
    try {
      const updated = await apiPost<EngineSettings>("/api/signals-engine/settings", {
        analysis_enabled: settings.analysis?.enabled,
        analyze_on_ingest: settings.analysis?.analyze_on_ingest,
        batch_size: settings.analysis?.batch_size,
        min_confidence: settings.analysis?.min_confidence,
        min_significance_score: settings.analysis?.min_significance_score,
        max_signals_per_symbol: settings.context?.max_signals_per_symbol,
        include_user_context: settings.context?.include_user_context,
        filter_enabled: settings.filter?.enabled,
        filter_mode: settings.filter?.mode,
        active_tags: settings.filter?.active_tags,
        keywords_include: linesToList(includeKwText),
        keywords_exclude: linesToList(excludeKwText),
        require_symbol_or_keyword: settings.filter?.require_symbol_or_keyword,
        min_keywords: settings.filter?.min_keywords,
        min_relevance_score: settings.filter?.min_relevance_score,
        require_keyword_in_title: settings.filter?.require_keyword_in_title,
        operator: "console",
      });
      setSettings(updated);
      setIncludeKwText(listToLines(updated.filter?.keywords_include));
      setExcludeKwText(listToLines(updated.filter?.keywords_exclude));
    } finally {
      setSettingsBusy(false);
    }
  };

  const reapplyFilters = async () => {
    if (!settings) return;
    setReapplyBusy(true);
    setIngestMsg(null);
    try {
      const updated = await apiPost<EngineSettings>("/api/signals-engine/settings", {
        analysis_enabled: settings.analysis?.enabled,
        analyze_on_ingest: settings.analysis?.analyze_on_ingest,
        batch_size: settings.analysis?.batch_size,
        min_confidence: settings.analysis?.min_confidence,
        min_significance_score: settings.analysis?.min_significance_score,
        max_signals_per_symbol: settings.context?.max_signals_per_symbol,
        include_user_context: settings.context?.include_user_context,
        filter_enabled: settings.filter?.enabled,
        filter_mode: settings.filter?.mode,
        active_tags: settings.filter?.active_tags,
        keywords_include: linesToList(includeKwText),
        keywords_exclude: linesToList(excludeKwText),
        require_symbol_or_keyword: settings.filter?.require_symbol_or_keyword,
        min_keywords: settings.filter?.min_keywords,
        min_relevance_score: settings.filter?.min_relevance_score,
        require_keyword_in_title: settings.filter?.require_keyword_in_title,
        operator: "console",
      });
      setSettings(updated);
      const r = await apiPost<{ relevant?: number; filtered_out?: number }>(
        "/api/signals-engine/reapply-filters?limit=400",
      );
      setIngestMsg(
        t("news.reapplyDone", {
          relevant: String(r.relevant ?? 0),
          filtered: String(r.filtered_out ?? 0),
        }),
      );
      refresh();
    } catch (err) {
      setIngestMsg(String(err));
    } finally {
      setReapplyBusy(false);
    }
  };

  const toggleFilterTag = (tag: string) => {
    if (!settings) return;
    const current = new Set(settings.filter?.active_tags ?? []);
    if (current.has(tag)) current.delete(tag);
    else current.add(tag);
    setSettings({
      ...settings,
      filter: { ...settings.filter, active_tags: Array.from(current) },
    });
  };

  return (
    <div className="page news-page">
      <div className="page-title">
        <h2>{t("news.title")}</h2>
        <p className="muted">{t("news.subtitle")}</p>
        <div className="news-page-actions">
          <button type="button" className="tiny primary" disabled={ingestBusy} onClick={runIngest}>
            {ingestBusy ? t("news.ingesting") : t("news.ingestNow")}
          </button>
          <button type="button" className="tiny" disabled={analyzeBusy} onClick={runAnalyze}>
            {analyzeBusy ? t("news.analyzing") : t("news.analyzePending")}
          </button>
          {ingestMsg ? <span className="muted small">{ingestMsg}</span> : null}
        </div>
      </div>

      <div className="news-engine-layout">
        <section className="news-engine-feed">
          {loading && items.length === 0 ? <p className="muted">{t("common.loading")}</p> : null}
          {error ? <p className="warn">{error}</p> : null}

          {!loading && !error && items.length === 0 ? (
            <p className="muted">{t("news.empty")}</p>
          ) : (
            <div className="news-feed">
              {items.map((item, idx) => {
                const analysisText =
                  item.llm_analysis?.analysis_ru ||
                  item.llm_analysis?.lead_ru ||
                  item.signal?.analysis_ru ||
                  null;
                const modelLabel = item.llm_model || item.signal?.model || "LLM";
                const body = item.body_raw || item.summary || "";
                const signalStatus = item.signal?.status;

                return (
                  <article key={item.id ?? `${item.title}-${idx}`} className="news-card">
                    <header className="news-card-headline-row">
                      <h3 className="news-card-headline">
                        {item.source_url ? (
                          <a href={item.source_url} target="_blank" rel="noreferrer">
                            {item.title}
                          </a>
                        ) : (
                          item.title
                        )}
                        <span className="news-head-sep"> | </span>
                        <span className="news-head-source">{item.source_name ?? t("news.unknownSource")}</span>
                        <span className="news-head-sep"> | </span>
                        <span className="muted small news-head-time">{formatWhen(item.published_at)}</span>
                      </h3>
                      <div className="news-card-badges">
                        {signalStatus === "consumed" ? (
                          <span className="pill ok">{t("news.signalConsumed")}</span>
                        ) : signalStatus === "pending" ? (
                          <span className="pill warn">{t("news.signalPending")}</span>
                        ) : item.used_in_signal ? (
                          <span className="pill ok">{t("news.usedInSignal")}</span>
                        ) : (
                          <span className="pill">{t("news.ingested")}</span>
                        )}
                        {item.verification_status === "verified" ? (
                          <span className="pill ok">{t("news.verified")}</span>
                        ) : null}
                      </div>
                    </header>

                    {body ? (
                      <div className="news-block news-block-raw">
                        <div className="news-block-divider" />
                        <p className="news-block-body">{body}</p>
                        <div className="news-block-divider" />
                      </div>
                    ) : null}

                    {analysisText ? (
                      <div className="news-block news-block-llm">
                        <div className="news-block-label">
                          {modelLabel}: {item.llm_analysis?.impact || item.signal?.impact || "—"}
                          {item.llm_analysis?.confidence != null
                            ? ` · conf ${item.llm_analysis.confidence.toFixed(2)}`
                            : ""}
                        </div>
                        <p className="news-block-body">{analysisText}</p>
                        <div className="news-block-divider" />
                      </div>
                    ) : (
                      <p className="muted small news-no-analysis">{t("news.noAnalysisYet")}</p>
                    )}

                    {item.id ? (
                      <NewsContextEditor
                        itemId={item.id}
                        initial={item.user_context?.context_text || ""}
                        editable={Boolean(item.context_editable)}
                        onSaved={refresh}
                      />
                    ) : null}

                    <footer className="news-card-foot">
                      <div className="muted small">
                        {t("news.symbols")}: {(item.matched_symbols_list ?? []).join(", ") || "—"}
                      </div>
                      <div className="muted small">
                        trust {item.trust_score ?? "—"} · rel {item.relevance_score ?? "—"} · tier{" "}
                        {item.source_tier ?? "—"}
                        {item.filter_meta_parsed?.relevance_score != null
                          ? ` · score ${item.filter_meta_parsed.relevance_score.toFixed(1)}`
                          : ""}
                        {(item.filter_meta_parsed?.universe_symbols ?? []).length > 0
                          ? ` · univ ${(item.filter_meta_parsed?.universe_symbols ?? []).join(", ")}`
                          : ""}
                        {(item.filter_meta_parsed?.matched_keywords ?? []).length > 0
                          ? ` · kw: ${(item.filter_meta_parsed?.matched_keywords ?? []).join(", ")}`
                          : ""}
                      </div>
                    </footer>

                    {(item.related_signals ?? []).length > 0 ? (
                      <div className="news-signals">
                        <div className="muted small">{t("news.relatedSignals")}</div>
                        {(item.related_signals ?? []).map((sig, si) => (
                          <div key={`${sig.event_at}-${si}`} className="news-signal-row">
                            <span className="mono-small">
                              {formatWhen(sig.event_at)} · {sig.market} · {sig.symbol}
                            </span>
                            <span className="pill tiny">
                              {sig.stage}/{sig.decision}
                            </span>
                            <Link to="/events" className="card-link small">
                              {t("news.openEvents")}
                            </Link>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <aside className="news-engine-sidebar">
          <div className="news-panel">
            <h3>{t("news.sourcesTitle")}</h3>
            <p className="muted small">{t("news.sourcesHint")}</p>
            <ul className="news-sources-list">
              {sources.map((src) => (
                <li key={src.id} className="news-source-row">
                  <div className="news-source-main">
                    <strong>{src.name}</strong>
                    <span className="muted small">
                      trust {(src.effective_trust ?? 0).toFixed(2)} · {src.source_tier}
                    </span>
                    <div className="news-source-tags">
                      {(src.tags_list ?? []).map((tag) => (
                        <span key={tag} className="pill tiny">
                          {tag}
                        </span>
                      ))}
                    </div>
                    {src.last_error ? <span className="warn small">{src.last_error}</span> : null}
                  </div>
                  <button
                    type="button"
                    className={`tiny ${src.enabled === 1 || src.enabled === true ? "" : "danger"}`}
                    onClick={() => toggleSource(src)}
                  >
                    {src.enabled === 1 || src.enabled === true ? t("news.sourceOn") : t("news.sourceOff")}
                  </button>
                </li>
              ))}
            </ul>
          </div>

          <div className="news-panel">
            <h3>{t("news.settingsTitle")}</h3>
            {settings ? (
              <div className="news-settings-form">
                <label className="news-setting-row">
                  <input
                    type="checkbox"
                    checked={Boolean(settings.analysis?.enabled)}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        analysis: { ...settings.analysis, enabled: e.target.checked },
                      })
                    }
                  />
                  {t("news.settingAnalysis")}
                </label>
                <label className="news-setting-row">
                  <input
                    type="checkbox"
                    checked={Boolean(settings.analysis?.analyze_on_ingest)}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        analysis: { ...settings.analysis, analyze_on_ingest: e.target.checked },
                      })
                    }
                  />
                  {t("news.settingOnIngest")}
                </label>
                <label className="news-setting-row">
                  <input
                    type="checkbox"
                    checked={Boolean(settings.context?.include_user_context)}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        context: { ...settings.context, include_user_context: e.target.checked },
                      })
                    }
                  />
                  {t("news.settingUserContext")}
                </label>

                <div className="news-settings-section">
                  <div className="muted small">{t("news.filterTitle")}</div>
                  <label className="news-setting-row">
                    <input
                      type="checkbox"
                      checked={Boolean(settings.filter?.enabled ?? true)}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          filter: { ...settings.filter, enabled: e.target.checked },
                        })
                      }
                    />
                    {t("news.settingFilter")}
                  </label>
                  <label className="news-setting-col">
                    <span className="muted small">{t("news.filterMode")}</span>
                    <select
                      className="input"
                      value={settings.filter?.mode ?? "balanced"}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          filter: { ...settings.filter, mode: e.target.value },
                        })
                      }
                    >
                      <option value="strict">{t("news.modeStrict")}</option>
                      <option value="balanced">{t("news.modeBalanced")}</option>
                      <option value="loose">{t("news.modeLoose")}</option>
                    </select>
                  </label>
                  {(settings.filter?.mode ?? "balanced") === "balanced" ? (
                    <>
                      <label className="news-setting-row">
                        <span className="muted small">{t("news.minKeywords")}</span>
                        <input
                          type="number"
                          className="input news-setting-num"
                          min={1}
                          max={10}
                          value={settings.filter?.min_keywords ?? 2}
                          onChange={(e) =>
                            setSettings({
                              ...settings,
                              filter: {
                                ...settings.filter,
                                min_keywords: parseInt(e.target.value, 10) || 2,
                              },
                            })
                          }
                        />
                      </label>
                      <label className="news-setting-row">
                        <span className="muted small">{t("news.minScore")}</span>
                        <input
                          type="number"
                          className="input news-setting-num"
                          min={0}
                          max={10}
                          step={0.5}
                          value={settings.filter?.min_relevance_score ?? 2.5}
                          onChange={(e) =>
                            setSettings({
                              ...settings,
                              filter: {
                                ...settings.filter,
                                min_relevance_score: parseFloat(e.target.value) || 2.5,
                              },
                            })
                          }
                        />
                      </label>
                      <label className="news-setting-row">
                        <input
                          type="checkbox"
                          checked={Boolean(settings.filter?.require_keyword_in_title ?? true)}
                          onChange={(e) =>
                            setSettings({
                              ...settings,
                              filter: {
                                ...settings.filter,
                                require_keyword_in_title: e.target.checked,
                              },
                            })
                          }
                        />
                        {t("news.requireKeywordInTitle")}
                      </label>
                    </>
                  ) : null}
                  {(settings.filter?.mode ?? "balanced") === "loose" ? (
                    <label className="news-setting-row">
                      <input
                        type="checkbox"
                        checked={Boolean(settings.filter?.require_symbol_or_keyword ?? true)}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            filter: {
                              ...settings.filter,
                              require_symbol_or_keyword: e.target.checked,
                            },
                          })
                        }
                      />
                      {t("news.settingRequireSymbolOrKw")}
                    </label>
                  ) : null}
                  <p className="muted small">{t(`news.modeHint.${settings.filter?.mode ?? "balanced"}`)}</p>
                  <div className="news-filter-tags">
                    {TAG_OPTIONS.map((tag) => (
                      <button
                        key={tag}
                        type="button"
                        className={`tiny pill ${(settings.filter?.active_tags ?? []).includes(tag) ? "primary" : ""}`}
                        onClick={() => toggleFilterTag(tag)}
                      >
                        {tag}
                      </button>
                    ))}
                  </div>
                  <label className="news-setting-col">
                    <span className="muted small">{t("news.keywordsInclude")}</span>
                    <textarea
                      className="news-keywords-area"
                      rows={4}
                      value={includeKwText}
                      onChange={(e) => setIncludeKwText(e.target.value)}
                      placeholder={t("news.keywordsHint")}
                    />
                  </label>
                  <label className="news-setting-col">
                    <span className="muted small">{t("news.keywordsExclude")}</span>
                    <textarea
                      className="news-keywords-area"
                      rows={3}
                      value={excludeKwText}
                      onChange={(e) => setExcludeKwText(e.target.value)}
                    />
                  </label>
                  <button
                    type="button"
                    className="tiny"
                    disabled={reapplyBusy}
                    onClick={reapplyFilters}
                  >
                    {reapplyBusy ? t("news.reapplying") : t("news.reapplyFilters")}
                  </button>
                </div>

                <label className="news-setting-row">
                  <span className="muted small">{t("news.settingMinConf")}</span>
                  <input
                    type="number"
                    className="input news-setting-num"
                    min={0}
                    max={1}
                    step={0.05}
                    value={settings.analysis?.min_confidence ?? 0.45}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        analysis: {
                          ...settings.analysis,
                          min_confidence: parseFloat(e.target.value) || 0,
                        },
                      })
                    }
                  />
                </label>
                <label className="news-setting-row">
                  <span className="muted small">{t("news.settingBatch")}</span>
                  <input
                    type="number"
                    className="input news-setting-num"
                    min={1}
                    max={50}
                    value={settings.analysis?.batch_size ?? 12}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        analysis: {
                          ...settings.analysis,
                          batch_size: parseInt(e.target.value, 10) || 12,
                        },
                      })
                    }
                  />
                </label>
                <button type="button" className="tiny primary" disabled={settingsBusy} onClick={saveSettings}>
                  {settingsBusy ? t("common.saving") : t("news.saveSettings")}
                </button>
              </div>
            ) : (
              <p className="muted small">{t("common.loading")}</p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
