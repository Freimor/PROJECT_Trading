import { useCallback } from "react";
import { apiGet } from "../api";
import { POLL } from "../config/polling";
import { usePolling } from "./usePolling";
import type { KlinesFeedHealth } from "../components/crypto/KlinesFeedHealthBadge";

type FeedHealthResponse = {
  status: string;
  items: Record<string, KlinesFeedHealth>;
  alert_ticks?: number;
};

export function useKlinesFeedHealthMap(symbols: string[], intervalMs: number = POLL.OPS) {
  const key = symbols
    .map((s) => s.toUpperCase())
    .sort()
    .join(",");

  const fetcher = useCallback(async (): Promise<FeedHealthResponse> => {
    if (!symbols.length) {
      return { status: "ok", items: {}, alert_ticks: 6 };
    }
    return apiGet<FeedHealthResponse>(
      `/api/crypto/scalp/klines-feed-health?symbols=${encodeURIComponent(key)}`,
    );
  }, [key, symbols.length]);

  const { data, refresh } = usePolling(fetcher, intervalMs, symbols.length > 0, {
    staggerKey: `klines-feed-${key}`,
  });

  return {
    items: data?.items ?? {},
    alertTicks: data?.alert_ticks ?? 6,
    refresh,
  };
}
