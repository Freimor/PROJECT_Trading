import { useErrorNotifications } from "../context/ErrorNotifications";

export default function ErrorBanner() {
  const { notices, dismiss, dismissAll } = useErrorNotifications();
  const visible = notices.slice(-3);

  return (
    <div className="error-banner-slot" aria-live="polite">
      {visible.length > 0 ? (
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
                  aria-label="Скрыть"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
          {notices.length > 1 && (
            <button type="button" className="error-banner-clear" onClick={dismissAll}>
              Скрыть все
            </button>
          )}
        </div>
      ) : (
        <span className="error-banner-placeholder" aria-hidden="true" />
      )}
    </div>
  );
}

function shortSource(id: string): string {
  const path = id.replace(/^GET\s+|^POST\s+/i, "");
  if (path.length <= 36) return path;
  return `…${path.slice(-34)}`;
}
