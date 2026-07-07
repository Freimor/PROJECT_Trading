import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet } from "../api";
import { POLL } from "../config/polling";
import { useI18n } from "../i18n/LanguageContext";
import { usePolling } from "../hooks/usePolling";
import type { ActivityFeedItem } from "../types";

type FeedResponse = {
  items: ActivityFeedItem[];
  count?: number;
};

const SCROLL_PREF_KEY = "activityFeedAutoScroll";

function formatFeedTime(iso: string): string {
  try {
    const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`);
    return d.toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso.slice(0, 16);
  }
}

const LEVEL_CLASS: Record<string, string> = {
  success: "activity-success",
  warn: "activity-warn",
  error: "activity-error",
  info: "activity-info",
};

export default function SystemActivityFeed() {
  const { t } = useI18n();
  const listRef = useRef<HTMLUListElement>(null);
  const [autoScroll, setAutoScroll] = useState(
    () => localStorage.getItem(SCROLL_PREF_KEY) !== "false",
  );

  const fetcher = useCallback(
    () => apiGet<FeedResponse>("/api/system/activity-feed?limit=50&days=3"),
    [],
  );

  const { data, loading } = usePolling(fetcher, POLL.ACTIVITY, true, {
    staggerKey: "activity-feed",
  });

  const items = data?.items ?? [];

  useEffect(() => {
    if (!autoScroll || !listRef.current) return;
    listRef.current.scrollTop = 0;
  }, [items, autoScroll]);

  const toggleScroll = () => {
    setAutoScroll((prev) => {
      const next = !prev;
      localStorage.setItem(SCROLL_PREF_KEY, String(next));
      return next;
    });
  };

  return (
    <aside className="activity-feed-panel" aria-label={t("activity.title")}>
      <div className="activity-feed-head">
        <h3>{t("activity.title")}</h3>
        <div className="activity-feed-actions">
          <button
            type="button"
            className={`tiny activity-scroll-toggle ${autoScroll ? "active" : ""}`}
            onClick={toggleScroll}
          >
            {autoScroll ? t("activity.autoScrollOn") : t("activity.autoScrollOff")}
          </button>
          <span className="muted small">{loading && !items.length ? "…" : items.length}</span>
        </div>
      </div>
      <ul
        ref={listRef}
        className={`activity-feed-list ${autoScroll ? "" : "activity-feed-list--frozen"}`}
      >
        {items.map((item) => (
          <li
            key={item.id}
            className={`activity-feed-item ${LEVEL_CLASS[item.level ?? "info"] ?? "activity-info"}`}
          >
            <time className="activity-feed-time">{formatFeedTime(item.occurred_at)}</time>
            <span className="activity-feed-msg">{item.message}</span>
          </li>
        ))}
        {!items.length && !loading && (
          <li className="activity-feed-empty muted">{t("activity.empty")}</li>
        )}
      </ul>
    </aside>
  );
}
