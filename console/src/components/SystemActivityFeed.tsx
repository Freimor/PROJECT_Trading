import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet } from "../api";
import { POLL } from "../config/polling";
import { useI18n } from "../i18n/LanguageContext";
import { usePolling } from "../hooks/usePolling";
import type { ActivityFeedItem, TradeEvent } from "../types";

type FeedResponse = {
  items?: ActivityFeedItem[];
  count?: number;
};

const SCROLL_PREF_KEY = "activityFeedAutoScroll";
const FEED_MAX_ITEMS = 40;

function feedTimeMs(iso: string): number {
  try {
    const normalized = iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`;
    return new Date(normalized).getTime();
  } catch {
    return 0;
  }
}

function mergeFeedItems(
  incoming: ActivityFeedItem[],
  previous: ActivityFeedItem[],
  maxItems: number,
): ActivityFeedItem[] {
  const byId = new Map<string, ActivityFeedItem>();
  for (const item of [...incoming, ...previous]) {
    byId.set(item.id, item);
  }
  return Array.from(byId.values())
    .sort((a, b) => feedTimeMs(b.occurred_at) - feedTimeMs(a.occurred_at))
    .slice(0, maxItems);
}

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
  const [feedItems, setFeedItems] = useState<ActivityFeedItem[]>([]);
  const [feedError, setFeedError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedDetail, setExpandedDetail] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [autoScroll, setAutoScroll] = useState(
    () => localStorage.getItem(SCROLL_PREF_KEY) !== "false",
  );

  const fetcher = useCallback(
    () => apiGet<FeedResponse>(`/api/system/activity-feed?limit=${FEED_MAX_ITEMS}&days=3`),
    [],
  );

  const { data, loading, error } = usePolling(fetcher, POLL.ACTIVITY, true, {
    staggerKey: "activity-feed",
    errorSource: "GET /api/system/activity-feed",
  });

  useEffect(() => {
    if (error) {
      setFeedError(String(error));
      return;
    }
    setFeedError(null);
    if (!data) return;
    const incoming = data.items ?? [];
    setFeedItems((prev) => mergeFeedItems(incoming, prev, FEED_MAX_ITEMS));
  }, [data, error]);

  useEffect(() => {
    if (!autoScroll || !listRef.current) return;
    listRef.current.scrollTop = 0;
  }, [feedItems, autoScroll]);

  const toggleScroll = () => {
    setAutoScroll((prev) => {
      const next = !prev;
      localStorage.setItem(SCROLL_PREF_KEY, String(next));
      return next;
    });
  };

  const toggleItem = async (item: ActivityFeedItem) => {
    if (expandedId === item.id) {
      setExpandedId(null);
      setExpandedDetail(null);
      return;
    }
    setExpandedId(item.id);
    if (item.ref_type === "trade_event" && item.ref_id) {
      setDetailLoading(true);
      setExpandedDetail(null);
      try {
        const event = await apiGet<TradeEvent>(`/api/events/${encodeURIComponent(item.ref_id)}`);
        setExpandedDetail(event.summary ?? t("activity.noDetail"));
      } catch {
        setExpandedDetail(t("activity.detailError"));
      } finally {
        setDetailLoading(false);
      }
      return;
    }
    setExpandedDetail(null);
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
          <span className="muted small">
            {loading && !feedItems.length
              ? "…"
              : `${feedItems.length}/${FEED_MAX_ITEMS}`}
          </span>
        </div>
      </div>
      {feedError ? <p className="warn small activity-feed-error">{feedError}</p> : null}
      <ul
        ref={listRef}
        className={`activity-feed-list ${autoScroll ? "" : "activity-feed-list--frozen"}`}
      >
        {feedItems.map((item) => {
          const expandable = item.ref_type === "trade_event" && Boolean(item.ref_id);
          const isOpen = expandedId === item.id;
          return (
            <li
              key={item.id}
              className={`activity-feed-item ${LEVEL_CLASS[item.level ?? "info"] ?? "activity-info"}${expandable ? " activity-feed-item--clickable" : ""}${isOpen ? " activity-feed-item--open" : ""}`}
            >
              <button
                type="button"
                className="activity-feed-row"
                disabled={!expandable}
                onClick={() => expandable && void toggleItem(item)}
              >
                <time className="activity-feed-time">{formatFeedTime(item.occurred_at)}</time>
                <span className="activity-feed-msg">{item.message}</span>
                {expandable ? <span className="activity-feed-chevron">{isOpen ? "▾" : "▸"}</span> : null}
              </button>
              {isOpen ? (
                <div className="activity-feed-detail">
                  {detailLoading ? (
                    <span className="muted small">{t("common.loading")}</span>
                  ) : expandedDetail ? (
                    <pre className="activity-feed-detail-text">{expandedDetail}</pre>
                  ) : null}
                </div>
              ) : null}
            </li>
          );
        })}
        {!feedItems.length && !loading && !feedError && (
          <li className="activity-feed-empty muted">{t("activity.empty")}</li>
        )}
      </ul>
    </aside>
  );
}
