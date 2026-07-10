import { useCallback } from "react";
import { Link } from "react-router-dom";
import { apiGet } from "../api";
import { POLL } from "../config/polling";
import { useI18n } from "../i18n/LanguageContext";
import { usePolling } from "../hooks/usePolling";

type NewsItem = {
  id?: string;
  title?: string;
  summary?: string;
  source_name?: string;
  published_at?: string;
  source_url?: string;
};

type Props = {
  symbol: string;
};

export default function SymbolNewsPanel({ symbol }: Props) {
  const { t } = useI18n();
  const fetcher = useCallback(
    () => apiGet<NewsItem[]>(`/api/news/for-symbol/${encodeURIComponent(symbol)}?limit=8`),
    [symbol],
  );
  const { data, loading, error } = usePolling(fetcher, POLL.EVENTS, true, {
    staggerKey: `news-symbol-${symbol}`,
  });

  const items = data ?? [];

  return (
    <div className="symbol-news-panel">
      <div className="symbol-news-head">
        <span className="muted small">{t("workspace.newsFor", { symbol })}</span>
        <Link to="/news" className="card-link small">
          {t("workspace.allNews")}
        </Link>
      </div>
      {loading && !items.length ? <p className="muted small">{t("common.loading")}</p> : null}
      {error ? <p className="warn small">{error}</p> : null}
      {!loading && !error && !items.length ? (
        <p className="muted small">{t("workspace.newsEmpty")}</p>
      ) : null}
      <ul className="event-list symbol-news-list">
        {items.map((item, idx) => (
          <li key={item.id ?? `${item.title}-${idx}`}>
            <span className="muted small">
              {item.published_at ? String(item.published_at).slice(5, 16).replace("T", " ") : "—"}
            </span>
            {item.source_url ? (
              <a href={item.source_url} target="_blank" rel="noreferrer" className="symbol-news-title">
                {item.title}
              </a>
            ) : (
              <span>{item.title}</span>
            )}
            <span className="muted small">{item.source_name}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
