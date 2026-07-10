import { useCallback, useEffect, useRef, useState } from "react";
import { staggerMs } from "../config/polling";
import { useErrorNotifications } from "../context/ErrorNotifications";

type PollingOptions = {
  /** Показывать локальную ошибку только после N неудачных опросов подряд. */
  errorAfterFailures?: number;
  /** Ключ для глобальной полосы ошибок (обычно путь API). */
  errorSource?: string;
  /** Не опрашивать, пока вкладка скрыта (по умолчанию true). */
  pauseWhenHidden?: boolean;
  /** Сдвиг первого запроса, чтобы не бить все эндпоинты разом. */
  staggerKey?: string;
};

export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  enabled = true,
  options?: PollingOptions,
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const failuresRef = useRef(0);
  const fetcherRef = useRef(fetcher);
  const { report } = useErrorNotifications();

  fetcherRef.current = fetcher;

  const errorAfterFailures = options?.errorAfterFailures ?? 2;
  const pauseWhenHidden = options?.pauseWhenHidden ?? true;
  const errorSource = options?.errorSource;
  const staggerKey = options?.staggerKey ?? errorSource ?? "";
  const prevStaggerKey = useRef(staggerKey);

  useEffect(() => {
    if (prevStaggerKey.current === staggerKey) return;
    prevStaggerKey.current = staggerKey;
    failuresRef.current = 0;
    setData(null);
    setLoading(true);
    setError("");
  }, [staggerKey]);

  const refresh = useCallback(async () => {
    if (!enabled) return;
    if (pauseWhenHidden && document.visibilityState === "hidden") return;

    try {
      const result = await fetcherRef.current();
      failuresRef.current = 0;
      setError("");
      if (errorSource) report(errorSource, null);
      setData(result);
    } catch (err) {
      failuresRef.current += 1;
      const msg = err instanceof Error ? err.message : String(err);
      if (failuresRef.current >= errorAfterFailures) {
        if (errorSource) {
          report(errorSource, msg);
          setError("");
        } else {
          setError(msg);
        }
      }
    } finally {
      setLoading(false);
    }
  }, [enabled, errorAfterFailures, errorSource, pauseWhenHidden, report]);

  // Снимаем ошибку только при размонтировании, не при каждом перезапуске таймера.
  useEffect(() => {
    if (!errorSource) return;
    return () => {
      report(errorSource, null);
    };
  }, [errorSource, report]);

  useEffect(() => {
    if (!enabled) return;

    const delay = staggerKey ? staggerMs(staggerKey) : 0;
    const boot = window.setTimeout(() => {
      void refresh();
    }, delay);

    if (intervalMs <= 0) {
      return () => clearTimeout(boot);
    }

    const tick = () => {
      if (pauseWhenHidden && document.visibilityState === "hidden") return;
      void refresh();
    };

    const id = window.setInterval(tick, intervalMs);

    const onVisible = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      clearTimeout(boot);
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [refresh, intervalMs, enabled, pauseWhenHidden, staggerKey]);

  return { data, error, loading, refresh };
};
