import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type ErrorNotice = {
  id: string;
  message: string;
  at: number;
};

type ErrorNotificationsContextValue = {
  notices: ErrorNotice[];
  report: (id: string, message: string | null | undefined) => void;
  dismiss: (id: string) => void;
  dismissAll: () => void;
};

const ErrorNotificationsContext = createContext<ErrorNotificationsContextValue | null>(null);

export function ErrorNotificationsProvider({ children }: { children: ReactNode }) {
  const [notices, setNotices] = useState<ErrorNotice[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(() => new Set());

  const report = useCallback((id: string, message: string | null | undefined) => {
    if (!message) {
      setNotices((prev) => prev.filter((n) => n.id !== id));
      return;
    }
    setDismissed((prev) => {
      if (!prev.has(id)) return prev;
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
    setNotices((prev) => {
      const next = prev.filter((n) => n.id !== id);
      return [...next, { id, message, at: Date.now() }];
    });
  }, []);

  const dismiss = useCallback((id: string) => {
    setDismissed((prev) => new Set(prev).add(id));
    setNotices((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const dismissAll = useCallback(() => {
    setNotices((prev) => {
      setDismissed((d) => {
        const next = new Set(d);
        prev.forEach((n) => next.add(n.id));
        return next;
      });
      return [];
    });
  }, []);

  const value = useMemo(
    () => ({ notices, report, dismiss, dismissAll }),
    [notices, report, dismiss, dismissAll],
  );

  return (
    <ErrorNotificationsContext.Provider value={value}>
      {children}
    </ErrorNotificationsContext.Provider>
  );
}

export function useErrorNotifications() {
  const ctx = useContext(ErrorNotificationsContext);
  if (!ctx) {
    throw new Error("useErrorNotifications must be used within ErrorNotificationsProvider");
  }
  return ctx;
}
