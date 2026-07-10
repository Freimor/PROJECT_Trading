import { NavLink } from "react-router-dom";
import { NAV_GROUPS } from "../config/navigation";
import { useI18n } from "../i18n/LanguageContext";
import Hint from "../ui/Hint";

type Props = {
  mobileOpen: boolean;
  onCloseMobile: () => void;
};

export default function AppSidebar({ mobileOpen, onCloseMobile }: Props) {
  const { t } = useI18n();

  return (
    <>
      <div
        className={`sidebar-backdrop ${mobileOpen ? "visible" : ""}`}
        onClick={onCloseMobile}
        aria-hidden={!mobileOpen}
      />
      <aside className={`app-sidebar ${mobileOpen ? "mobile-open" : ""}`} aria-label={t("shell.sidebar")}>
        <div className="sidebar-brand">
          <span className="sidebar-brand-mark" aria-hidden />
          <div>
            <strong>{t("header.title")}</strong>
            <span className="muted small">{t("header.subtitle")}</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {NAV_GROUPS.map((group) => (
            <div key={group.groupKey} className="sidebar-group">
              <div className="sidebar-group-label">{t(group.groupKey)}</div>
              <ul className="sidebar-group-list">
                {group.items.map((item) => {
                  const label = t(item.labelKey);
                  const hint = t(item.hintKey);
                  const Icon = item.icon;

                  return (
                    <li key={item.to}>
                      <Hint label={hint}>
                        <NavLink
                          to={item.to}
                          end={item.end}
                          className={({ isActive }) =>
                            `sidebar-link${isActive ? " active" : ""}`
                          }
                          onClick={onCloseMobile}
                        >
                          <Icon />
                          <span className="sidebar-link-label">{label}</span>
                        </NavLink>
                      </Hint>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
      </aside>
    </>
  );
}
