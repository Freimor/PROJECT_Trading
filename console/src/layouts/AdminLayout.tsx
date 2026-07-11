import { useCallback, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import AppSidebar from "../components/AppSidebar";
import AppTopBar from "../components/AppTopBar";
import ErrorBanner from "../components/ErrorBanner";
import StatusBar from "../components/StatusBar";
import SystemActivityFeed from "../components/SystemActivityFeed";
import { POLL } from "../config/polling";
import { usePolling } from "../hooks/usePolling";
import { apiGet } from "../api";
import { useI18n } from "../i18n/LanguageContext";
import AriaProviders from "../ui/AriaProviders";
import type { AutomationOverview } from "../types";

export type AdminLayoutContext = {
  overview: AutomationOverview | null;
  refresh: () => void;
};

const FEED_PREF_KEY = "consoleFeedOpen";

export default function AdminLayout() {
  const { t } = useI18n();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [feedOpen, setFeedOpen] = useState(
    () => localStorage.getItem(FEED_PREF_KEY) !== "false",
  );

  const fetchOverview = useCallback(() => apiGet<AutomationOverview>("/api/automation/overview?days=7"), []);
  const { data: overview, refresh } = usePolling<AutomationOverview>(
    fetchOverview,
    POLL.OVERVIEW,
    true,
    {
      errorSource: "GET /api/automation/overview",
      staggerKey: "layout-overview",
    },
  );

  const toggleFeed = () => {
    setFeedOpen((prev) => {
      const next = !prev;
      localStorage.setItem(FEED_PREF_KEY, String(next));
      return next;
    });
  };

  const location = useLocation();
  const isWorkspace = /^\/(crypto|moex)(\/|$)/.test(location.pathname);

  return (
    <AriaProviders>
      <div className="app-shell-v2">
        <AppSidebar
          mobileOpen={mobileNavOpen}
          onCloseMobile={() => setMobileNavOpen(false)}
          onRefresh={refresh}
          onToggleFeed={toggleFeed}
          feedOpen={feedOpen}
        />

        <div className="app-main-column">
          <AppTopBar onToggleNav={() => setMobileNavOpen((v) => !v)} />

          <ErrorBanner />
          <StatusBar overview={overview} onRefresh={refresh} />

          <div
            className={`app-body-v2${feedOpen ? "" : " feed-collapsed"}${isWorkspace ? " workspace-route" : ""}`}
          >
            <main className={`app-content${isWorkspace ? " content-workspace" : ""}`}>
              <Outlet context={{ overview, refresh } satisfies AdminLayoutContext} />
            </main>
            {feedOpen ? <SystemActivityFeed /> : null}
          </div>

          <footer className="app-footer muted">{t("footer.disclaimer")}</footer>
        </div>
      </div>
    </AriaProviders>
  );
}
