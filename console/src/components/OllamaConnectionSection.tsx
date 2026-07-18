import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost, formatOperatorFacingError } from "../api";
import { useI18n } from "../i18n/LanguageContext";
import OperatorConfirmModal from "./OperatorConfirmModal";
import PortfolioCard from "./PortfolioCard";

type OllamaPreset = {
  id: string;
  host?: string | null;
  label_ru?: string;
  label_en?: string;
  hint_ru?: string;
  hint_en?: string;
};

type OllamaConnectionState = {
  status: string;
  preset?: string;
  custom_host?: string | null;
  env_default_host?: string;
  effective_host?: string;
  runtime_override?: boolean;
  presets?: OllamaPreset[];
  ping?: {
    reachable?: boolean;
    latency_ms?: number;
    models_count?: number;
    message?: string;
  };
};

type Props = {
  bare?: boolean;
};

export default function OllamaConnectionSection({ bare = false }: Props) {
  const { t, lang } = useI18n();
  const [state, setState] = useState<OllamaConnectionState | null>(null);
  const [preset, setPreset] = useState("docker");
  const [customHost, setCustomHost] = useState("http://host.docker.internal:11434");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [pendingApply, setPendingApply] = useState(false);
  const [opError, setOpError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const data = await apiGet<OllamaConnectionState>("/api/ollama/connection");
    setState(data);
    if (data.preset && data.preset !== "env") setPreset(data.preset);
    if (data.custom_host) setCustomHost(data.custom_host);
  }, []);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);

  const presetLabel = (p: OllamaPreset) =>
    lang === "ru" ? p.label_ru ?? p.id : p.label_en ?? p.id;

  const apply = async (password: string) => {
    setBusy(true);
    setOpError(null);
    try {
      const resp = await apiPost<OllamaConnectionState>(
        "/api/ollama/connection",
        {
          preset,
          custom_host: preset === "custom" ? customHost.trim() : null,
          operator: "web:operator",
        },
        { operatorPassword: password },
      );
      setState(resp);
      setPendingApply(false);
      setMsg(t("ollamaConnection.saved"));
    } catch (err) {
      setOpError(formatOperatorFacingError(err, t));
    } finally {
      setBusy(false);
    }
  };

  const ping = state?.ping;
  const pingClass = ping?.reachable ? "ok-text" : "warn-text";

  const body = (
    <>
      <p className="muted small">{t("ollamaConnection.lead")}</p>
      <dl className="risk-effective-grid">
        <dt>{t("ollamaConnection.effectiveHost")}</dt>
        <dd className="mono-small">{state?.effective_host ?? "—"}</dd>
        <dt>{t("ollamaConnection.envDefault")}</dt>
        <dd className="mono-small">{state?.env_default_host ?? "—"}</dd>
        <dt>{t("ollamaConnection.ping")}</dt>
        <dd className={pingClass}>
          {ping?.reachable
            ? t("ollamaConnection.pingOk", {
                ms: String(ping.latency_ms ?? "—"),
                n: String(ping.models_count ?? 0),
              })
            : ping?.message ?? t("ollamaConnection.pingFail")}
        </dd>
      </dl>

      <fieldset className="field-stack">
        <legend>{t("ollamaConnection.presetLegend")}</legend>
        {(state?.presets ?? []).map((p) => (
          <label key={p.id} className="radio-row">
            <input
              type="radio"
              name="ollama-preset"
              value={p.id}
              checked={preset === p.id}
              onChange={() => setPreset(p.id)}
            />
            <span>
              <strong>{presetLabel(p)}</strong>
              {p.host ? <span className="muted small"> — {p.host}</span> : null}
              <br />
              <span className="muted small">
                {lang === "ru" ? p.hint_ru : p.hint_en}
              </span>
            </span>
          </label>
        ))}
      </fieldset>

      {preset === "custom" ? (
        <label className="field-stack">
          <span>{t("ollamaConnection.customUrl")}</span>
          <input
            className="input"
            value={customHost}
            onChange={(e) => setCustomHost(e.target.value)}
            placeholder="http://host.docker.internal:11434"
          />
        </label>
      ) : null}

      <div className="btn-row">
        <button type="button" className="primary" onClick={() => setPendingApply(true)}>
          {t("ollamaConnection.apply")}
        </button>
        <button type="button" disabled={busy} onClick={() => void load()}>
          {t("header.refresh")}
        </button>
      </div>
      {msg ? <p className="muted small">{msg}</p> : null}

      <OperatorConfirmModal
        open={pendingApply}
        title={t("ollamaConnection.apply")}
        lead={t("workflowsPage.operatorLead")}
        risk={t("ollamaConnection.applyRisk")}
        busy={busy}
        error={opError}
        onConfirm={apply}
        onCancel={() => {
          if (!busy) {
            setPendingApply(false);
            setOpError(null);
          }
        }}
      />
    </>
  );

  if (bare) return body;
  return <PortfolioCard title={t("ollamaConnection.title")}>{body}</PortfolioCard>;
}
