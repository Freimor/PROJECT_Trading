import { NavLink, Outlet } from "react-router-dom";
import { useCallback, useState } from "react";
import ErrorBanner from "../components/ErrorBanner";
import StatusBar from "../components/StatusBar";
import SystemActivityFeed from "../components/SystemActivityFeed";
import { POLL } from "../config/polling";
import { usePolling } from "../hooks/usePolling";
import { apiGet, setOperatorPassword, getOperatorPassword } from "../api";
import { useI18n, type Lang } from "../i18n/LanguageContext";
import type { AutomationOverview } from "../types";

export type AdminLayoutContext = {
  overview: AutomationOverview | null;
  refresh: () => void;
};

export default function AdminLayout() {
  const { t, lang, setLang } = useI18n();
  const [operatorPassword, setOperatorPasswordState] = useState(getOperatorPassword());
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

  const saveOperatorPassword = () => {
    setOperatorPassword(operatorPassword);
    setOperatorPasswordState(operatorPassword);
    refresh();
  };

  const navClass = ({ isActive }: { isActive: boolean }) =>
    isActive ? "nav-link active" : "nav-link";

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>{t("header.title")}</h1>
          <p className="muted">{t("header.subtitle")}</p>
        </div>
        <div className="header-actions">
          <label className="lang-select">
            <span className="muted small">{t("header.language")}</span>
            <select value={lang} onChange={(e) => setLang(e.target.value as Lang)}>
              <option value="ru">{t("lang.ru")}</option>
              <option value="en">{t("lang.en")}</option>
            </select>
          </label>
          <input
            type="password"
            placeholder={t("header.operatorPassword")}
            value={operatorPassword}
            onChange={(e) => setOperatorPasswordState(e.target.value)}
            className="input"
            autoComplete="current-password"
          />
          <button type="button" onClick={saveOperatorPassword}>
            {t("header.savePassword")}
          </button>
          <button type="button" onClick={refresh}>
            {t("header.refresh")}
          </button>
        </div>
      </header>

      <ErrorBanner />

      <StatusBar overview={overview} />

      <nav className="main-nav">
        <NavLink to="/" end className={navClass}>
          {t("nav.overview")}
        </NavLink>
        <NavLink to="/crypto" className={navClass}>
          {t("nav.crypto")}
        </NavLink>
        <NavLink to="/moex" className={navClass}>
          {t("nav.moex")}
        </NavLink>
        <NavLink to="/events" className={navClass}>
          {t("nav.events")}
        </NavLink>
        <NavLink to="/llm" className={navClass}>
          {t("nav.llm")}
        </NavLink>
        <NavLink to="/paper" className={navClass}>
          {t("nav.paper")}
        </NavLink>
        <NavLink to="/benchmark" className={navClass}>
          {t("nav.benchmark")}
        </NavLink>
        <NavLink to="/workflows" className={navClass}>
          {t("nav.workflows")}
        </NavLink>
        <NavLink to="/control" className={navClass}>
          {t("nav.control")}
        </NavLink>
      </nav>

      <main className="app-body">
        <div className="app-main">
          <Outlet context={{ overview, refresh } satisfies AdminLayoutContext} />
        </div>
        <SystemActivityFeed />
      </main>

      <footer className="app-footer muted">{t("footer.disclaimer")}</footer>
    </div>
  );
}
