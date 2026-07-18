import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost, formatOperatorFacingError } from "../api";
import { useI18n } from "../i18n/LanguageContext";
import OperatorConfirmModal from "./OperatorConfirmModal";

type StrategyAssist = {
  id: string;
  kind: string;
  label_ru?: string;
  label_en?: string;
  hint_ru?: string;
  hint_en?: string;
  effective?: { enabled?: boolean; sample_pct?: number; mode?: string };
  yaml_default?: { enabled?: boolean; sample_pct?: number; mode?: string };
  uses_global_llm_mode?: boolean;
  runtime_override?: boolean;
};

type LlmAssistState = {
  status: string;
  ollama?: { effective_host?: string; reachable?: boolean };
  guardrails_llm_mode?: {
    effective?: string;
    yaml_default?: string;
    runtime_override?: boolean;
    options?: { id: string; label_ru?: string; label_en?: string }[];
  };
  strategies?: StrategyAssist[];
};

type Props = {
  workflow?: string;
  onChange?: () => void;
};

export default function LlmAssistSection({ workflow, onChange }: Props) {
  const { t, lang } = useI18n();
  const [data, setData] = useState<LlmAssistState | null>(null);
  const [scalpEnabled, setScalpEnabled] = useState(false);
  const [scalpSample, setScalpSample] = useState(20);
  const [swingMode, setSwingMode] = useState("validate_only");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [pending, setPending] = useState<"scalp" | "swing" | null>(null);
  const [opError, setOpError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const qs = workflow ? `?workflow=${encodeURIComponent(workflow)}` : "";
    const resp = await apiGet<LlmAssistState>(`/api/llm-assist${qs}`);
    setData(resp);
    const scalp = resp.strategies?.find((s) => s.id === "crypto_scalp_hybrid");
    if (scalp?.effective) {
      setScalpEnabled(Boolean(scalp.effective.enabled));
      setScalpSample(scalp.effective.sample_pct ?? 20);
    }
    setSwingMode(resp.guardrails_llm_mode?.effective ?? "validate_only");
  }, [workflow]);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);

  const scalpStrategy = data?.strategies?.find((s) => s.id === "crypto_scalp_hybrid");
  const swingStrategies = (data?.strategies ?? []).filter((s) => s.kind === "swing_validate");
  const showScalp = !workflow || scalpStrategy != null;
  const showSwing = swingStrategies.length > 0;

  const strategyLabel = (s: StrategyAssist) =>
    lang === "ru" ? s.label_ru ?? s.id : s.label_en ?? s.id;

  const applyScalp = async (password: string) => {
    setBusy(true);
    setOpError(null);
    try {
      await apiPost(
        "/api/llm-assist/crypto_scalp_hybrid",
        {
          enabled: scalpEnabled,
          sample_pct: scalpSample,
          operator: "web:operator",
        },
        { operatorPassword: password },
      );
      setPending(null);
      setMsg(t("llmAssist.saved"));
      await load();
      onChange?.();
    } catch (err) {
      setOpError(formatOperatorFacingError(err, t));
    } finally {
      setBusy(false);
    }
  };

  const applySwing = async (password: string) => {
    setBusy(true);
    setOpError(null);
    try {
      await apiPost(
        "/api/llm-assist/llm_swing",
        { llm_mode: swingMode, operator: "web:operator" },
        { operatorPassword: password },
      );
      setPending(null);
      setMsg(t("llmAssist.saved"));
      await load();
      onChange?.();
    } catch (err) {
      setOpError(formatOperatorFacingError(err, t));
    } finally {
      setBusy(false);
    }
  };

  if (!data?.strategies?.length && !data?.guardrails_llm_mode) {
    return null;
  }

  return (
    <div className="llm-assist-section">
      <h4>{t("llmAssist.title")}</h4>
      <p className="muted small">{t("llmAssist.lead")}</p>
      {data.ollama?.effective_host ? (
        <p className="muted small">
          {t("llmAssist.ollamaHost")}: <span className="mono-small">{data.ollama.effective_host}</span>
          {data.ollama.reachable === false ? (
            <span className="warn-text"> — {t("llmAssist.ollamaUnreachable")}</span>
          ) : null}
        </p>
      ) : null}

      {showSwing ? (
        <div className="llm-assist-block">
          <p className="small">
            <strong>{t("llmAssist.swingModeTitle")}</strong>
          </p>
          <p className="muted small">{t("llmAssist.swingModeHint")}</p>
          <ul className="muted small">
            {swingStrategies.map((s) => (
              <li key={s.id}>{strategyLabel(s)}</li>
            ))}
          </ul>
          <select
            className="input"
            value={swingMode}
            onChange={(e) => setSwingMode(e.target.value)}
          >
            {(data.guardrails_llm_mode?.options ?? []).map((o) => (
              <option key={o.id} value={o.id}>
                {lang === "ru" ? o.label_ru : o.label_en}
              </option>
            ))}
          </select>
          <button type="button" className="tiny primary" onClick={() => setPending("swing")}>
            {t("llmAssist.applySwing")}
          </button>
        </div>
      ) : null}

      {showScalp && scalpStrategy ? (
        <div className="llm-assist-block">
          <p className="small">
            <strong>{strategyLabel(scalpStrategy)}</strong>
          </p>
          <p className="muted small">
            {lang === "ru" ? scalpStrategy.hint_ru : scalpStrategy.hint_en}
          </p>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={scalpEnabled}
              onChange={(e) => setScalpEnabled(e.target.checked)}
            />
            <span>{t("llmAssist.scalpEnabled")}</span>
          </label>
          <label className="field-stack">
            <span>{t("llmAssist.scalpSamplePct")}</span>
            <input
              className="input"
              type="number"
              min={0}
              max={100}
              disabled={!scalpEnabled}
              value={scalpSample}
              onChange={(e) => setScalpSample(Number(e.target.value))}
            />
          </label>
          <p className="muted small">
            {t("llmAssist.scalpYamlDefault", {
              enabled: String(scalpStrategy.yaml_default?.enabled ?? false),
              pct: String(scalpStrategy.yaml_default?.sample_pct ?? 0),
            })}
          </p>
          <button type="button" className="tiny primary" onClick={() => setPending("scalp")}>
            {t("llmAssist.applyScalp")}
          </button>
        </div>
      ) : null}

      {msg ? <p className="muted small">{msg}</p> : null}

      <OperatorConfirmModal
        open={pending === "scalp"}
        title={t("llmAssist.applyScalp")}
        lead={t("workflowsPage.operatorLead")}
        risk={t("llmAssist.applyRisk")}
        busy={busy}
        error={opError}
        onConfirm={applyScalp}
        onCancel={() => {
          if (!busy) {
            setPending(null);
            setOpError(null);
          }
        }}
      />
      <OperatorConfirmModal
        open={pending === "swing"}
        title={t("llmAssist.applySwing")}
        lead={t("workflowsPage.operatorLead")}
        risk={t("llmAssist.applyRisk")}
        busy={busy}
        error={opError}
        onConfirm={applySwing}
        onCancel={() => {
          if (!busy) {
            setPending(null);
            setOpError(null);
          }
        }}
      />
    </div>
  );
}
