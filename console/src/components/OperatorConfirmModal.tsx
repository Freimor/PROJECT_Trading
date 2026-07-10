import { useEffect, useRef, useState } from "react";
import { useI18n } from "../i18n/LanguageContext";

type Props = {
  open: boolean;
  title: string;
  lead?: string;
  risk?: string;
  riskTone?: "warn" | "danger" | "";
  confirmLabel?: string;
  busy?: boolean;
  error?: string | null;
  onConfirm: (password: string) => void;
  onCancel: () => void;
};

export default function OperatorConfirmModal({
  open,
  title,
  lead,
  risk,
  riskTone = "warn",
  confirmLabel,
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

  const riskClass =
    riskTone === "danger" ? "danger-text" : riskTone === "warn" ? "warn-text" : "";

  return (
    <div className="modal-overlay" role="presentation" onClick={onCancel}>
      <div
        className="modal-dialog"
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <h3>{title}</h3>
        {lead ? <p className="modal-lead">{lead}</p> : null}
        {risk ? <p className={`modal-risk ${riskClass}`}>{risk}</p> : null}
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
            className="primary"
            disabled={busy || !password.trim()}
            onClick={() => onConfirm(password)}
          >
            {busy ? t("common.loading") : confirmLabel ?? t("workspace.modeModalConfirm")}
          </button>
        </div>
      </div>
    </div>
  );
}
