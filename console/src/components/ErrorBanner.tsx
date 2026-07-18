import { useErrorNotifications } from "../context/ErrorNotifications";
import { useI18n } from "../i18n/LanguageContext";

function shortSource(id: string): string {
  const slash = id.lastIndexOf("/");
  if (slash >= 0) return id.slice(slash + 1) || id;
  return id.length > 48 ? `${id.slice(0, 45)}…` : id;
}

export default function ErrorBanner() {
  const { t } = useI18n();
  const { notices, dismiss, dismissAll } = useErrorNotifications();
  const visible = notices.slice(-3);

  if (visible.length === 0) return null;

  return (
    <div className="error-banner-slot" aria-live="polite">
      <div className="error-banner">
        <div className="error-banner-body">
          {visible.map((n) => (
            <div className="error-banner-item" key={n.id}>
              <span className="error-banner-source">{shortSource(n.id)}</span>
              <span className="error-banner-msg">{n.message}</span>
              <button
                type="button"
                className="error-banner-dismiss"
                onClick={() => dismiss(n.id)}
                aria-label={t("errors.dismiss")}
              >
                ×
              </button>
            </div>
          ))}
        </div>
        {notices.length > 1 ? (
          <button type="button" className="error-banner-clear" onClick={dismissAll}>
            {t("errors.dismissAll")}
          </button>
        ) : null}
      </div>
    </div>
  );
}
