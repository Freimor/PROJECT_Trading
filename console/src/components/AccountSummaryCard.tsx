import { useState } from "react";
import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import PortfolioCard from "./PortfolioCard";
import { useI18n } from "../i18n/LanguageContext";
import { formatMoexPosition } from "../utils/moex";

export type AccountMetric = {
  currency?: string;
  fiat_currency?: string;
  portfolio_total?: boolean;
  current?: number | null;
  status?: string;
  change_pct?: number | null;
  direction?: "up" | "down" | "flat";
};

export type PerformancePeriod = "all" | "1m" | "1w" | "1d" | "2h";

type Position = { ticker?: string; quantity?: number; avg_price?: number };

type Props = {
  title: string;
  tileId?: string;
  status?: { label: string; tone?: "ok" | "warn" | "danger" | "neutral"; dotOnly?: boolean };
  metric?: AccountMetric | null;
  loading?: boolean;
  emptyMessage?: string;
  positions?: Position[];
  linkTo?: string;
  linkLabel?: string;
  period: PerformancePeriod;
  onPeriodChange: (p: PerformancePeriod) => void;
  children?: ReactNode;
};

const PERIODS: PerformancePeriod[] = ["all", "1m", "1w", "1d", "2h"];

function fmtValue(value: number | null | undefined, currency: string, fiatCurrency?: string): string {
  if (value == null || Number.isNaN(value)) return "—";
  const display = fiatCurrency || currency;
  const suffix =
    display === "RUB" ? " ₽" : display === "USD" ? " USD" : display === "USDT" ? " USDT" : ` ${display}`;
  const digits = display === "RUB" ? 0 : 2;
  return `${value.toLocaleString("ru-RU", { maximumFractionDigits: digits })}${suffix}`;
}

function balanceClass(direction?: string): string {
  if (direction === "up") return "account-balance balance-up";
  if (direction === "down") return "account-balance balance-down";
  return "account-balance";
}

export default function AccountSummaryCard({
  title,
  tileId,
  status,
  metric,
  loading,
  emptyMessage,
  positions,
  linkTo,
  linkLabel,
  period,
  onPeriodChange,
  children,
}: Props) {
  const { t } = useI18n();
  const unavailable =
    metric?.status === "empty" ||
    metric?.status === "error" ||
    (metric?.current == null && !loading);

  const periodLabels: Record<PerformancePeriod, string> = {
    all: t("overview.periodAll"),
    "1m": t("overview.period1m"),
    "1w": t("overview.period1w"),
    "1d": t("overview.period1d"),
    "2h": t("overview.period2h"),
  };

  const footer = linkTo ? (
    <Link to={linkTo} className="card-link">
      {linkLabel ?? `${t("common.open")} →`}
    </Link>
  ) : undefined;

  return (
    <PortfolioCard
      title={title}
      tileId={tileId}
      status={status ? { ...status, dotOnly: status.dotOnly ?? status.tone === "ok" } : undefined}
      footer={footer}
    >
      {loading && !metric && <p className="muted small">{t("common.loading")}</p>}
      {unavailable && !loading && (
        <p className="muted small">{emptyMessage ?? t("common.statusEmpty")}</p>
      )}
      {!unavailable && metric && (
        <>
          <div className="period-buttons">
            {PERIODS.map((p) => (
              <button
                key={p}
                type="button"
                className={`period-btn ${period === p ? "active" : ""}`}
                onClick={() => onPeriodChange(p)}
              >
                {periodLabels[p]}
              </button>
            ))}
          </div>
          <div className="account-primary">
            <strong className={balanceClass(metric.direction)}>
              {fmtValue(metric.current, metric.currency ?? "", metric.fiat_currency)}
            </strong>
            {metric.portfolio_total ? (
              <span className="muted small account-portfolio-hint">{t("overview.portfolioTotal")}</span>
            ) : null}
            {metric.change_pct != null && (
              <span className={`perf-inline perf-${metric.direction ?? "flat"}`}>
                {metric.change_pct > 0 ? "+" : ""}
                {metric.change_pct.toFixed(1)}%
              </span>
            )}
          </div>
          {positions && positions.length > 0 && (
            <ul className="balance-list compact">
              {positions
                .filter((p) => p.ticker !== "RUB000UTSTOM" || (p.quantity ?? 0) > 0)
                .slice(0, 4)
                .map((p) => {
                  const row = formatMoexPosition(p.ticker, p.quantity, p.avg_price, {
                    cashRub: t("workspace.cashRub"),
                    pieces: t("workspace.pieces"),
                  });
                  return (
                    <li key={p.ticker}>
                      <span>{row.label}</span>
                      <span>{row.value}</span>
                    </li>
                  );
                })}
            </ul>
          )}
        </>
      )}
      {children}
    </PortfolioCard>
  );
}
