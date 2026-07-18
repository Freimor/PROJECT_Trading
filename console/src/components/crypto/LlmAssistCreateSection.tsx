import { useEffect, useState } from "react";
import { apiGet } from "../../api";
import { useI18n } from "../../i18n/LanguageContext";

export type LlmAssistMode = "disabled" | "advisory" | "validate_only";

export type LlmAssistCreateProfile = {
  status?: string;
  strategy_id?: string;
  supports_assist?: boolean;
  kind?: string;
  default_enabled?: boolean;
  default_mode?: LlmAssistMode;
  default_sample_pct?: number;
  title_ru?: string;
  title_en?: string;
  summary_ru?: string;
  summary_en?: string;
  steps_ru?: string[];
  steps_en?: string[];
  when_off_ru?: string;
  when_off_en?: string;
  caution_ru?: string;
  caution_en?: string;
  modes_ru?: Record<string, string>;
  modes_en?: Record<string, string>;
};

type Props = {
  strategyId: string;
  enabled: boolean;
  mode: LlmAssistMode;
  samplePct: number;
  onEnabledChange: (v: boolean) => void;
  onModeChange: (v: LlmAssistMode) => void;
  onSamplePctChange: (v: number) => void;
};

export default function LlmAssistCreateSection({
  strategyId,
  enabled,
  mode,
  samplePct,
  onEnabledChange,
  onModeChange,
  onSamplePctChange,
}: Props) {
  const { t, lang } = useI18n();
  const [profile, setProfile] = useState<LlmAssistCreateProfile | null>(null);

  useEffect(() => {
    if (!strategyId) return;
    apiGet<LlmAssistCreateProfile>(
      `/api/crypto/llm-assist-profile?strategy_id=${encodeURIComponent(strategyId)}`,
    )
      .then((p) => setProfile(p))
      .catch(() => setProfile(null));
  }, [strategyId]);

  if (!profile?.supports_assist) {
    return (
      <div className="create-auto-llm create-auto-llm--unavailable">
        <h4>{t("createAutomation.llmAssistTitle")}</h4>
        <p className="muted small">{t("createAutomation.llmAssistUnavailable")}</p>
      </div>
    );
  }

  const title = lang === "ru" ? profile.title_ru : profile.title_en;
  const summary = lang === "ru" ? profile.summary_ru : profile.summary_en;
  const steps = lang === "ru" ? profile.steps_ru : profile.steps_en;
  const whenOff = lang === "ru" ? profile.when_off_ru : profile.when_off_en;
  const caution = lang === "ru" ? profile.caution_ru : profile.caution_en;
  const modesMap = lang === "ru" ? profile.modes_ru : profile.modes_en;
  const isScalp = profile.kind === "hybrid_sample";

  return (
    <section className="create-auto-llm">
      <div className="create-auto-llm-head">
        <h4>{title ?? t("createAutomation.llmAssistTitle")}</h4>
        <label className="create-auto-llm-toggle checkbox-row">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => onEnabledChange(e.target.checked)}
          />
          <span>{t("createAutomation.llmAssistEnable")}</span>
        </label>
      </div>

      <p className="create-auto-llm-summary">{summary}</p>

      {enabled ? (
        <div className="create-auto-llm-details">
          {steps?.length ? (
            <div className="create-auto-llm-block">
              <p className="create-auto-llm-block-title">{t("createAutomation.llmAssistHowTitle")}</p>
              <ol className="create-auto-llm-steps">
                {steps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </div>
          ) : null}

          {!isScalp && modesMap ? (
            <div className="create-auto-llm-block">
              <label className="modal-field">
                <span>{t("createAutomation.llmAssistModeLabel")}</span>
                <select
                  className="input"
                  value={mode}
                  onChange={(e) => onModeChange(e.target.value as LlmAssistMode)}
                >
                  <option value="validate_only">{modesMap.validate_only}</option>
                  <option value="advisory">{modesMap.advisory}</option>
                </select>
              </label>
            </div>
          ) : null}

          {isScalp && enabled ? (
            <div className="create-auto-llm-block">
              <label className="modal-field">
                <span>{t("createAutomation.llmAssistSampleLabel")}</span>
                <input
                  type="range"
                  min={5}
                  max={40}
                  step={5}
                  value={samplePct}
                  onChange={(e) => onSamplePctChange(Number(e.target.value))}
                  className="create-auto-llm-range"
                />
                <span className="create-auto-llm-sample-value">
                  {t("createAutomation.llmAssistSampleValue", { pct: samplePct })}
                </span>
              </label>
            </div>
          ) : null}

          {caution ? <p className="warn small create-auto-llm-caution">{caution}</p> : null}
        </div>
      ) : whenOff ? (
        <p className="muted small create-auto-llm-off">{whenOff}</p>
      ) : null}
    </section>
  );
}
