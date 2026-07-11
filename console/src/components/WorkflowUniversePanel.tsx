import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiPost, formatOperatorFacingError } from "../api";
import ScalpPairPickerPanel from "./ScalpPairPickerPanel";
import { POLL } from "../config/polling";
import { usePolling } from "../hooks/usePolling";
import { useI18n } from "../i18n/LanguageContext";

type UniverseItem = {
  symbol: string;
  enabled: boolean;
  source?: string;
  added_at?: string | null;
};

type UniverseState = {
  items: UniverseItem[];
  enabled_symbols?: string[];
  runtime_override?: boolean;
  market?: string;
  can_change?: boolean;
  change_blocked_reason?: string | null;
  active_workflow?: string | null;
};

type SearchHit = { symbol: string; label?: string };

type Props = {
  workflow: string;
  market: "crypto" | "securities";
  onChange?: () => void;
  compact?: boolean;
};

export default function WorkflowUniversePanel({ workflow, market, onChange, compact = false }: Props) {
  const { t } = useI18n();
  const [state, setState] = useState<UniverseState | null>(null);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [busy, setBusy] = useState(false);
  const [llmHint, setLlmHint] = useState("");
  const [llmMode, setLlmMode] = useState<"replace" | "merge">("merge");
  const [disableOthers, setDisableOthers] = useState(false);
  const [llmPreview, setLlmPreview] = useState<{
    symbols?: string[];
    rationale?: string;
    fallback?: boolean;
  } | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const fetcher = useCallback(async () => {
    const data = await apiGet<{ status: string } & UniverseState>(
      `/api/workflows/${encodeURIComponent(workflow)}/universe`,
    );
    if (data.status === "ok") {
      setState({
        items: data.items ?? [],
        enabled_symbols: data.enabled_symbols,
        runtime_override: data.runtime_override,
        can_change: data.can_change,
        change_blocked_reason: data.change_blocked_reason,
        active_workflow: data.active_workflow,
      });
    }
    return data;
  }, [workflow]);

  const { refresh: reloadUniverse } = usePolling(fetcher, POLL.OPS, Boolean(workflow), {
    staggerKey: `universe-${workflow}`,
  });

  const load = useCallback(async () => {
    await reloadUniverse();
  }, [reloadUniverse]);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 1) {
      setHits([]);
      return;
    }
    const timer = window.setTimeout(() => {
      apiGet<{ items?: SearchHit[] }>(
        `/api/assets/search?market=${market}&q=${encodeURIComponent(q)}&limit=12`,
      )
        .then((r) => setHits(r.items ?? []))
        .catch(() => setHits([]));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [market, query]);

  const enabledCount = useMemo(
    () => (state?.items ?? []).filter((i) => i.enabled).length,
    [state?.items],
  );

  const locked = state?.can_change === false;
  const isScalp = workflow.toLowerCase().includes("scalp");

  const blockHint =
    locked && state?.change_blocked_reason === "workflow_active"
      ? t("universe.blockedWorkflow", { workflow: state?.active_workflow ?? "n8n" })
      : null;

  const formatError = (err: unknown) => {
    const raw = err instanceof Error ? err.message : String(err);
    if (raw.includes("universe_change_blocked")) {
      return t("universe.blockedWorkflow", { workflow: state?.active_workflow ?? "n8n" });
    }
    return formatOperatorFacingError(err, t);
  };

  const addSymbol = async (symbol: string) => {
    setBusy(true);
    setMessage(null);
    try {
      await apiPost(`/api/workflows/${encodeURIComponent(workflow)}/universe/add`, {
        symbols: [symbol],
        enabled: true,
      });
      setQuery("");
      setHits([]);
      await load();
      onChange?.();
    } catch (err) {
      setMessage(formatError(err));
    } finally {
      setBusy(false);
    }
  };

  const toggleSymbol = async (symbol: string, enabled: boolean) => {
    setBusy(true);
    setMessage(null);
    try {
      await apiPost(`/api/workflows/${encodeURIComponent(workflow)}/universe/toggle`, {
        symbol,
        enabled,
      });
      await load();
      onChange?.();
    } catch (err) {
      setMessage(formatError(err));
    } finally {
      setBusy(false);
    }
  };

  const removeSymbol = async (symbol: string) => {
    setBusy(true);
    setMessage(null);
    try {
      await apiPost(`/api/workflows/${encodeURIComponent(workflow)}/universe/remove`, {
        symbol,
        enabled: false,
      });
      await load();
      onChange?.();
    } catch (err) {
      setMessage(formatError(err));
    } finally {
      setBusy(false);
    }
  };

  const resetUniverse = async () => {
    if (!confirm(t("universe.resetConfirm"))) return;
    setBusy(true);
    try {
      await apiPost(`/api/workflows/${encodeURIComponent(workflow)}/universe/reset`, {});
      setLlmPreview(null);
      await load();
      onChange?.();
    } catch (err) {
      setMessage(formatError(err));
    } finally {
      setBusy(false);
    }
  };

  const runLlm = async (apply: boolean) => {
    setBusy(true);
    setMessage(null);
    try {
      const r = await apiPost<{
        status: string;
        suggestion?: {
          symbols?: string[];
          rationale?: string;
          message?: string;
          fallback?: boolean;
        };
        universe?: UniverseState;
        message?: string;
      }>(
        `/api/workflows/${encodeURIComponent(workflow)}/universe/llm-suggest`,
        {
          mode: llmMode,
          disable_others: disableOthers,
          hint: llmHint || undefined,
          apply,
        },
        { timeoutMs: 210_000, retries: 0 },
      );
      if (r.status !== "ok") {
        setMessage(r.message ?? r.suggestion?.message ?? "LLM error");
        return;
      }
      if (apply && r.universe) {
        setState(r.universe);
        setLlmPreview(null);
        onChange?.();
      } else {
        setLlmPreview({
          symbols: r.suggestion?.symbols ?? [],
          rationale: r.suggestion?.rationale,
          fallback: r.suggestion?.fallback,
        });
      }
    } catch (err) {
      setMessage(formatError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`workflow-universe${compact ? " compact" : ""}${locked ? " locked" : ""}`}>
      {blockHint ? <p className="warn-text small">{blockHint}</p> : null}
      <div className="workflow-universe-head">
        <span className="muted small">
          {t("universe.enabledCount", { count: enabledCount, total: state?.items?.length ?? 0 })}
          {state?.runtime_override ? ` · ${t("universe.runtime")}` : ` · ${t("universe.fromYaml")}`}
        </span>
      </div>

      <div className="workflow-universe-search">
        <input
          type="search"
          className="input"
          placeholder={t("universe.searchPlaceholder")}
          value={query}
          disabled={busy || locked}
          onChange={(e) => setQuery(e.target.value)}
        />
        {hits.length ? (
          <ul className="universe-search-hits">
            {hits.map((h) => (
              <li key={h.symbol}>
                <button type="button" className="tiny" disabled={busy || locked} onClick={() => addSymbol(h.symbol)}>
                  + {h.label ?? h.symbol}
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <ul className="universe-list">
        {(state?.items ?? []).map((item) => (
          <li key={item.symbol} className={item.enabled ? "enabled" : "disabled"}>
            <label className="universe-row">
              <input
                type="checkbox"
                checked={item.enabled}
                disabled={busy || locked}
                onChange={(e) => toggleSymbol(item.symbol, e.target.checked)}
              />
              <span className="mono-small">{item.symbol}</span>
              {item.source ? <span className="pill tiny neutral">{item.source}</span> : null}
            </label>
            <button type="button" className="tiny danger" disabled={busy || locked} onClick={() => removeSymbol(item.symbol)}>
              ×
            </button>
          </li>
        ))}
      </ul>

      {isScalp ? (
        <details className="universe-scalp-picker-details" open>
          <summary className="muted small">{t("universe.scalpPickerTitle")}</summary>
          <ScalpPairPickerPanel workflow={workflow} locked={locked} onApplied={() => void load()} />
        </details>
      ) : null}

      <div className="workflow-universe-llm">
        <details className="universe-llm-details" open={!compact}>
          <summary className="muted small">{t("universe.llmTitle")}</summary>
        <textarea
          className="input"
          rows={2}
          placeholder={t("universe.llmHintPlaceholder")}
          value={llmHint}
          disabled={busy || locked}
          onChange={(e) => setLlmHint(e.target.value)}
        />
        <div className="btn-row">
          <label className="checkbox-inline">
            <input
              type="radio"
              name={`llm-mode-${workflow}`}
              checked={llmMode === "replace"}
              onChange={() => setLlmMode("replace")}
              disabled={locked}
            />
            {t("universe.llmReplace")}
          </label>
          <label className="checkbox-inline">
            <input
              type="radio"
              name={`llm-mode-${workflow}`}
              checked={llmMode === "merge"}
              onChange={() => setLlmMode("merge")}
              disabled={locked}
            />
            {t("universe.llmMerge")}
          </label>
          <label className="checkbox-inline">
            <input
              type="checkbox"
              checked={disableOthers}
              disabled={llmMode === "replace" || locked}
              onChange={(e) => setDisableOthers(e.target.checked)}
            />
            {t("universe.disableOthers")}
          </label>
        </div>
        <div className="btn-row">
          <button type="button" className="tiny" disabled={busy || locked} onClick={() => runLlm(false)}>
            {t("universe.llmPreview")}
          </button>
          <button type="button" className="tiny primary" disabled={busy || locked} onClick={() => runLlm(true)}>
            {t("universe.llmApply")}
          </button>
          <button type="button" className="tiny" disabled={busy || locked} onClick={resetUniverse}>
            {t("universe.resetYaml")}
          </button>
        </div>
        {llmPreview ? (
          <div className="universe-llm-preview small">
            <div>
              <strong>{t("universe.llmSuggested")}:</strong> {(llmPreview.symbols ?? []).join(", ") || "—"}
            </div>
            {llmPreview.fallback ? (
              <p className="warn small">LLM недоступен или не успел ответить — показан базовый список из каталога.</p>
            ) : null}
            {llmPreview.rationale ? <p className="muted">{llmPreview.rationale}</p> : null}
          </div>
        ) : null}
        </details>
      </div>

      {message ? <p className="modal-error small">{message}</p> : null}
      {!compact ? <p className="muted small">{t("universe.llmRunsHint")}</p> : null}
      <p className="muted small">{t("universe.newsHint")}</p>
    </div>
  );
}
