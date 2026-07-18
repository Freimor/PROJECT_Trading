import { useState, type ReactNode } from "react";
import { Link, useOutletContext } from "react-router-dom";
import { apiGet } from "../api";
import AccountSummaryCard, {
  type AccountMetric,
  type PerformancePeriod,
} from "../components/AccountSummaryCard";
import MetricStatusRow from "../components/MetricStatusRow";
import PortfolioCard from "../components/PortfolioCard";
import { POLL } from "../config/polling";
import en from "../i18n/en";
import { useI18n } from "../i18n/LanguageContext";
import ru from "../i18n/ru";
import type { AdminLayoutContext } from "../layouts/AdminLayout";
import { usePolling } from "../hooks/usePolling";
import { formatMoexNextOpen } from "../utils/moex";
import { normalizeBalances, type BalancesResponse } from "../utils/balances";

type PerformanceResp = {
  baseline_started_at?: string;
  demo?: { crypto_usdt?: AccountMetric; moex_rub?: AccountMetric };
  live?: { crypto_usdt?: AccountMetric; moex_rub?: AccountMetric };
  snapshots?: { hint?: string };
};

type MoexDash = {
  positions?: Array<{ ticker?: string; quantity?: number; avg_price?: number }>;
};

type CryptoDash = {
  llm_eval?: { approve_rate?: number };
};

type LiveChecklist = { ready_for_live?: boolean; checks?: Record<string, boolean> };

type HostStatus = {
  in_moex_session?: boolean;
  moex_session?: string;
  moex_next_open?: { kind?: string; time_msk?: string; weekday?: number };
  host?: { cpu_pct?: number; ram_pct?: number; ram_used_gb?: number; ram_total_gb?: number; available?: boolean };
  ollama?: { status?: string; latency_ms?: number };
};

function checklistStats(checks?: Record<string, boolean>) {
  const entries = Object.values(checks ?? {});
  return { ok: entries.filter(Boolean).length, total: entries.length };
}

function funnelLine(block?: { passed?: number; total?: number }) {
  if (!block) return "—";
  return `${block.passed ?? 0}/${block.total ?? 0}`;
}

function fmtStartDate(iso: string | undefined, locale: string) {
  if (!iso) return "";
  try {
    return new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`).toLocaleDateString(locale);
  } catch {
    return iso.slice(0, 10);
  }
}

function OverviewSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="overview-section">
      <h3 className="overview-section-title">{title}</h3>
      <div className="grid cards-2">{children}</div>
    </section>
  );
}

export default function OverviewPage() {
  const { t, lang } = useI18n();
  const { overview } = useOutletContext<AdminLayoutContext>();
  const [period, setPeriod] = useState<PerformancePeriod>("all");
  const weekdays = lang === "en" ? en.overview.weekdays : ru.overview.weekdays;
  const dateLocale = lang === "en" ? "en-GB" : "ru-RU";

  const { data: performance } = usePolling<PerformanceResp>(
    () => apiGet(`/api/portfolio/performance?period=${period}`),
    POLL.TICK,
    true,
    { errorSource: "GET /api/portfolio/performance", staggerKey: `overview-perf-${period}` },
  );

  const { data: binanceBalances } = usePolling<BalancesResponse>(
    () => apiGet("/api/binance/balances?testnet=true&top=0"),
    POLL.TICK,
    true,
    { staggerKey: "overview-binance-bal" },
  );

  const demoCryptoBalances = normalizeBalances(binanceBalances).rows;

  const { data: moexPortfolio } = usePolling<MoexDash>(
    () => apiGet("/api/tinvest/portfolio?sandbox=true", { timeoutMs: 45_000 }),
    POLL.PORTFOLIO,
    true,
    { staggerKey: "overview-moex-pos" },
  );

  const { data: cryptoDash } = usePolling<CryptoDash>(
    () => apiGet("/api/crypto/testnet-dashboard?days=7"),
    POLL.DASHBOARD,
    true,
    { staggerKey: "overview-crypto-dash" },
  );

  const { data: liveChecklist } = usePolling<LiveChecklist>(
    () => apiGet("/api/live/checklist"),
    POLL.DASHBOARD,
    true,
    { staggerKey: "overview-live-checklist" },
  );

  const { data: host } = usePolling<HostStatus>(
    () => apiGet("/api/system/host-status"),
    POLL.DASHBOARD,
    true,
    { staggerKey: "overview-host" },
  );

  const started = fmtStartDate(performance?.baseline_started_at, dateLocale);
  const sinceSuffix = started ? ` · ${t("overview.since")} ${started}` : "";
  const moexOpenHint = !host?.in_moex_session
    ? formatMoexNextOpen(t, host?.moex_next_open, weekdays)
    : null;

  const { ok: liveChecksOk, total: liveChecksTotal } = checklistStats(liveChecklist?.checks);

  const demoCrypto = performance?.demo?.crypto_usdt;
  const demoMoex = performance?.demo?.moex_rub;

  return (
    <div className="page">
      <div className="page-title">
        <h2>{t("overview.title")}</h2>
        <p className="muted">{t("overview.subtitle")}</p>
        {performance?.snapshots?.hint && (
          <p className="muted small warn">{performance.snapshots.hint}</p>
        )}
      </div>

      <OverviewSection title={t("overview.demoAccounts")}>
        <AccountSummaryCard
          tileId="demo-binance"
          title={`${t("overview.binanceTestnet")}${sinceSuffix}`}
          status={{
            label: t("common.statusOk"),
            tone: demoCrypto?.status === "ok" ? "ok" : "warn",
            dotOnly: demoCrypto?.status === "ok",
          }}
          metric={demoCrypto}
          period={period}
          onPeriodChange={setPeriod}
          balances={demoCryptoBalances}
          emptyMessage={t("overview.emptyTestnet")}
          linkTo="/crypto"
          linkLabel={t("overview.openCrypto")}
        />
        <AccountSummaryCard
          tileId="demo-tinvest"
          title={`${t("overview.tinvestSandbox")}${sinceSuffix}`}
          status={{
            label: t("common.statusOk"),
            tone: overview?.securities?.tinvest_api === "ok" ? "ok" : "warn",
            dotOnly: overview?.securities?.tinvest_api === "ok",
          }}
          metric={demoMoex}
          period={period}
          onPeriodChange={setPeriod}
          positions={moexPortfolio?.positions}
          emptyMessage={t("overview.emptySandbox")}
          linkTo="/moex"
          linkLabel={t("overview.openMoex")}
        />
      </OverviewSection>

      <OverviewSection title={t("overview.liveAccounts")}>
        <AccountSummaryCard
          tileId="live-binance"
          title={t("overview.binanceLive")}
          status={{
            label: t("common.connected"),
            tone: performance?.live?.crypto_usdt?.status === "ok" ? "ok" : "neutral",
            dotOnly: performance?.live?.crypto_usdt?.status === "ok",
          }}
          metric={performance?.live?.crypto_usdt}
          period={period}
          onPeriodChange={setPeriod}
          emptyMessage={t("overview.emptyLiveCrypto")}
        />
        <AccountSummaryCard
          tileId="live-tinvest"
          title={t("overview.tinvestLive")}
          status={{
            label: t("common.connected"),
            tone: performance?.live?.moex_rub?.status === "ok" ? "ok" : "neutral",
            dotOnly: performance?.live?.moex_rub?.status === "ok",
          }}
          metric={performance?.live?.moex_rub}
          period={period}
          onPeriodChange={setPeriod}
          emptyMessage={t("overview.emptyLiveMoex")}
        />
      </OverviewSection>

      <OverviewSection title={t("overview.demoAutomations")}>
        <PortfolioCard
          tileId="auto-crypto-demo"
          title={t("overview.cryptoTestnet")}
          status={{ label: "testnet", tone: "neutral", dotOnly: false }}
          footer={
            <Link to="/crypto" className="card-link">
              {t("common.workspace")} →
            </Link>
          }
        >
          <div className="metric-row">
            <span>{t("overview.strategy")}</span>
            <strong>{overview?.crypto?.strategy_label ?? "—"}</strong>
          </div>
          <div className="metric-row">
            <span>{t("overview.operationMode")}</span>
            <strong>
              {overview?.crypto?.operation_mode === "live"
                ? t("overview.modeLiveLabel")
                : t("overview.modeDemoLabel")}
            </strong>
          </div>
          <div className="metric-row">
            <span>{t("overview.funnel")}</span>
            <strong>{funnelLine(overview?.crypto?.funnel_signal)}</strong>
          </div>
          <div className="metric-row">
            <span>{t("overview.llmApprove")}</span>
            <strong>
              {cryptoDash?.llm_eval?.approve_rate != null
                ? `${(Number(cryptoDash.llm_eval.approve_rate) * 100).toFixed(0)}%`
                : "—"}
            </strong>
          </div>
          <div className="metric-row">
            <span>{t("overview.signals7d")}</span>
            <strong>{overview?.dry_run_signals_7d ?? 0}</strong>
          </div>
        </PortfolioCard>

        <PortfolioCard
          tileId="auto-moex-demo"
          title={t("overview.moexSandbox")}
          status={{
            label: t("common.statusOk"),
            tone: overview?.securities?.tinvest_api === "ok" ? "ok" : "warn",
            dotOnly: overview?.securities?.tinvest_api === "ok",
          }}
          footer={
            <Link to="/moex" className="card-link">
              {t("common.workspace")} →
            </Link>
          }
        >
          <div className="metric-row">
            <span>{t("overview.strategy")}</span>
            <strong>{overview?.securities?.strategy_label ?? "—"}</strong>
          </div>
          <div className="metric-row">
            <span>{t("overview.operationMode")}</span>
            <strong>
              {overview?.securities?.operation_mode === "live"
                ? t("overview.modeLiveLabel")
                : t("overview.modeDemoLabel")}
            </strong>
          </div>
          <div className="metric-row">
            <span>{t("overview.funnel")}</span>
            <strong>{funnelLine(overview?.securities?.funnel_signal)}</strong>
          </div>
          <div className="metric-row">
            <span>{t("overview.env")}</span>
            <strong>{overview?.securities?.env ?? "sandbox"}</strong>
          </div>
        </PortfolioCard>
      </OverviewSection>

      <OverviewSection title={t("overview.liveAutomations")}>
        <PortfolioCard
          tileId="auto-crypto-live"
          title={t("overview.cryptoLive")}
          status={{
            label: overview?.live_flag ? t("common.statusOn") : t("overview.liveDisabled"),
            tone: overview?.live_flag ? "warn" : "neutral",
          }}
          footer={
            <Link to="/control" className="card-link">
              {t("common.control")} →
            </Link>
          }
        >
          <div className="metric-row">
            <span>{t("overview.liveFlag")}</span>
            <strong>{overview?.live_flag ? "enabled" : "off"}</strong>
          </div>
          <div className="metric-row">
            <span>{t("overview.checklist")}</span>
            <strong>
              {liveChecksTotal ? `${liveChecksOk}/${liveChecksTotal}` : "—"}
              {liveChecklist?.ready_for_live ? ` · ${t("overview.ready")}` : ""}
            </strong>
          </div>
          <div className="metric-row">
            <span>{t("overview.systemMode")}</span>
            <strong>
              {overview?.operation_mode === "mixed"
                ? "Mixed"
                : overview?.operation_mode === "live"
                  ? t("overview.modeLiveLabel")
                  : t("overview.modeDemoLabel")}
            </strong>
          </div>
        </PortfolioCard>

        <PortfolioCard
          tileId="auto-moex-live"
          title={t("overview.moexLive")}
          status={{
            label: overview?.live_flag ? "live" : t("overview.sandboxOnly"),
            tone: "neutral",
          }}
          footer={
            <Link to="/control" className="card-link">
              {t("common.control")} →
            </Link>
          }
        >
          <div className="metric-row">
            <span>{t("overview.liveFlag")}</span>
            <strong>{overview?.live_flag ? "enabled" : "off"}</strong>
          </div>
          <div className="metric-row">
            <span>{t("overview.checklist")}</span>
            <strong>{liveChecksTotal ? `${liveChecksOk}/${liveChecksTotal}` : "—"}</strong>
          </div>
          <div className="metric-row">
            <span>{t("overview.killSwitch")}</span>
            <strong>{overview?.kill_switch ? "ON" : "OFF"}</strong>
          </div>
        </PortfolioCard>
      </OverviewSection>

      <OverviewSection title={t("overview.system")}>
        <PortfolioCard
          tileId="system-host"
          title={t("overview.host")}
          status={{
            label: "online",
            tone: host?.host?.cpu_pct != null ? "ok" : "neutral",
            dotOnly: host?.host?.cpu_pct != null,
          }}
        >
          <div className="metric-row">
            <span>{t("overview.cpu")}</span>
            <strong>{host?.host?.cpu_pct != null ? `${host.host.cpu_pct}%` : "—"}</strong>
          </div>
          <div className="metric-row">
            <span>{t("overview.ram")}</span>
            <strong>
              {host?.host?.ram_pct != null
                ? `${host.host.ram_pct}% (${host.host.ram_used_gb}/${host.host.ram_total_gb} GB)`
                : "—"}
            </strong>
          </div>
        </PortfolioCard>

        <PortfolioCard
          tileId="system-other"
          title={t("overview.exchangeLlm")}
          status={{
            label: host?.in_moex_session ? t("overview.sessionOpen") : t("overview.sessionClosed"),
            tone: host?.in_moex_session ? "ok" : "warn",
            dotOnly: host?.in_moex_session,
          }}
        >
          {moexOpenHint && <p className="muted small">{moexOpenHint}</p>}
          <MetricStatusRow
            label={t("overview.moexSession")}
            tone={host?.in_moex_session ? "ok" : "warn"}
          />
          <div className="metric-row">
            <span>{t("overview.schedule")}</span>
            <strong className="small">{host?.moex_session ?? "—"}</strong>
          </div>
          <MetricStatusRow
            label={t("overview.ollama")}
            tone={
              (host?.ollama?.status ?? overview?.ollama?.status) === "ok" ? "ok" : "warn"
            }
          />
          <div className="metric-row">
            <span>{t("overview.lastEvent")}</span>
            <strong className="small">
              {overview?.last_event
                ? `${String(overview.last_event.event_at).slice(0, 16)} · ${overview.last_event.workflow_name}`
                : "—"}
            </strong>
          </div>
        </PortfolioCard>
      </OverviewSection>
    </div>
  );
}
