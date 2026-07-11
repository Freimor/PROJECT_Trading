import { useEffect, useState, type ReactNode } from "react";
import { useI18n } from "../i18n/LanguageContext";
import StatusDot, { isPositiveStatusLabel, labelToDotTone } from "./StatusDot";

export type TileStatus = {
  label: string;
  tone?: "ok" | "warn" | "danger" | "neutral";
  /** Show colored dot instead of text (default: true for OK-like labels). */
  dotOnly?: boolean;
};

type Props = {
  title: string;
  tileId?: string;
  status?: TileStatus;
  /** @deprecated use status */
  subtitle?: string;
  /** Badge/pill next to title (e.g. Spot / Futures). */
  headBadge?: ReactNode;
  collapsible?: boolean;
  defaultCollapsed?: boolean;
  footer?: ReactNode;
  children?: ReactNode;
};

function collapseKey(tileId: string) {
  return `tile-collapsed:${tileId}`;
}

export default function PortfolioCard({
  title,
  tileId,
  status,
  subtitle,
  headBadge,
  collapsible = true,
  defaultCollapsed = false,
  footer,
  children,
}: Props) {
  const { t } = useI18n();
  const id = tileId ?? title;
  const [collapsed, setCollapsed] = useState(() => {
    const saved = localStorage.getItem(collapseKey(id));
    if (saved !== null) return saved === "true";
    return defaultCollapsed;
  });

  const resolvedStatus = status ?? (subtitle ? { label: subtitle, tone: "neutral" as const } : undefined);

  useEffect(() => {
    localStorage.setItem(collapseKey(id), String(collapsed));
  }, [collapsed, id]);

  const toggle = () => {
    if (collapsible) setCollapsed((c) => !c);
  };

  const showDot =
    resolvedStatus &&
    (resolvedStatus.dotOnly !== false &&
      (resolvedStatus.dotOnly === true ||
        resolvedStatus.tone === "ok" ||
        isPositiveStatusLabel(resolvedStatus.label)));

  return (
    <div className={`tile ${collapsed ? "tile-collapsed" : ""}`}>
      <header
        className="tile-head"
        onClick={collapsed ? toggle : undefined}
        role={collapsed ? "button" : undefined}
        tabIndex={collapsed ? 0 : undefined}
        onKeyDown={
          collapsed
            ? (e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  toggle();
                }
              }
            : undefined
        }
      >
        <span className="tile-title">{title}</span>
        {headBadge ? <span className="tile-head-badge">{headBadge}</span> : null}
        {resolvedStatus &&
          (showDot ? (
            <StatusDot
              tone={labelToDotTone(resolvedStatus.label, resolvedStatus.tone)}
              title={resolvedStatus.label}
            />
          ) : (
            <span className={`tile-status status-${resolvedStatus.tone ?? "neutral"}`}>
              {resolvedStatus.label}
            </span>
          ))}
      </header>

      {!collapsed && children && <div className="tile-body">{children}</div>}

      {collapsible && (
        <footer className="tile-foot">
          <button type="button" className="tile-collapse-btn" onClick={toggle}>
            {collapsed ? t("common.expand") : t("common.collapse")}
          </button>
          {!collapsed && footer}
        </footer>
      )}
      {!collapsible && footer && <footer className="tile-foot tile-foot-static">{footer}</footer>}
    </div>
  );
}
