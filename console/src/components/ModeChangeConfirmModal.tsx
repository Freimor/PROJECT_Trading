import { useEffect, useRef, useState } from "react";
import { useI18n } from "../i18n/LanguageContext";

type Mode = "demo" | "live";

type Props = {
  open: boolean;
  marketTitle: string;
  targetMode: Mode;
  busy?: boolean;
  error?: string | null;
  onConfirm: (password: string) => void;
  onCancel: () => void;
};

export default function ModeChangeConfirmModal({
  open,
  marketTitle,
  targetMode,
  busy = false,
  error = null,
  onConfirm,
  onCancel,
}: Props) {
  const { t } = useI18n();
  const [password, setPassword] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) {
      setPassword("");
      return;
    }
    const timer = window.setTimeout(() => inputRef.current?.focus(), 50);
    return () => window.clearTimeout(timer);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;

  const modeLabel = t(`workspace.mode${targetMode === "live" ? "Live" : "Demo"}` as "workspace.modeDemo");
  const riskKey =
    targetMode === "live" ? "workspace.modeRiskLive" : "workspace.modeRiskDemo";

  return (
    <div className="modal-overlay" role="presentation" onClick={onCancel}>
      <div
        className="modal-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="mode-change-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id="mode-change-title">{t("workspace.modeModalTitle")}</h3>
        <p className="modal-lead">
          {t("workspace.modeModalQuestion", { market: marketTitle, mode: modeLabel })}
        </p>
        <p className={`modal-risk ${targetMode === "live" ? "danger-text" : "warn-text"}`}>
          {t(riskKey)}
        </p>
        <label className="modal-field">
          <span>{t("workspace.modeModalPassword")}</span>
          <input
            ref={inputRef}
            type="password"
            className="input"
            value={password}
            autoComplete="current-password"
            disabled={busy}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && password.trim()) onConfirm(password);
            }}
          />
        </label>
        {error ? <p className="modal-error">{error}</p> : null}
        <div className="modal-actions">
          <button type="button" disabled={busy} onClick={onCancel}>
            {t("workspace.modeModalCancel")}
          </button>
          <button
            type="button"
            className={targetMode === "live" ? "primary danger" : "primary"}
            disabled={busy || !password.trim()}
            onClick={() => onConfirm(password)}
          >
            {busy ? t("common.loading") : t("workspace.modeModalConfirm")}
          </button>
        </div>
      </div>
    </div>
  );
}
