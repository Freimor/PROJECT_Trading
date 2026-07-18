import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiPatch, apiPost, formatOperatorFacingError } from "../../api";
import { POLL } from "../../config/polling";
import { useI18n } from "../../i18n/LanguageContext";
import { usePolling } from "../../hooks/usePolling";
import OperatorConfirmModal from "../OperatorConfirmModal";
import CreateCryptoAutomationModal from "./CreateCryptoAutomationModal";
import CryptoAutomationDetail from "./CryptoAutomationDetail";
import CryptoMarginHaltBanner from "./CryptoMarginHaltBanner";
import AutomationSessionStatsModal from "./AutomationSessionStatsModal";
import { useKlinesFeedHealthMap } from "../../hooks/useKlinesFeedHealthMap";
import { resolveKlinesFeedHealthVariant } from "./KlinesFeedHealthBadge";
import { supportsScalpPreScan } from "../../utils/cryptoWorkflowMap";
import { automationTabLabel } from "../../utils/tradingProduct";
import type {
  CryptoAutomationInstance,
  CryptoAutomationStats,
  CryptoAutomationsListResponse,
  CryptoAutomationStopResponse,
  CryptoInstanceSessionReport,
} from "../../types/cryptoAutomation";

const ACTIVE_TAB_KEY = "crypto-automation-active-tab";

type Props = {
  killSwitch?: boolean;
};

export default function CryptoAutomationWorkspace({ killSwitch }: Props) {
  const { t } = useI18n();
  const [activeId, setActiveId] = useState<string | null>(() => {
    try {
      return sessionStorage.getItem(ACTIVE_TAB_KEY);
    } catch {
      return null;
    }
  });
  const [createOpen, setCreateOpen] = useState(false);
  const [statsMap, setStatsMap] = useState<Record<string, CryptoAutomationStats>>({});
  const [stopTarget, setStopTarget] = useState<CryptoAutomationInstance | null>(null);
  const [stopBusy, setStopBusy] = useState(false);
  const [stopError, setStopError] = useState<string | null>(null);
  const [sessionReport, setSessionReport] = useState<CryptoInstanceSessionReport | null>(null);

  const pairsFetcher = useCallback(() => apiGet<string[]>("/api/crypto/pairs"), []);
  const { data: pairList } = usePolling(pairsFetcher, POLL.OPS, true, {
    staggerKey: "crypto-auto-pairs",
  });

  const listFetcher = useCallback(
    () => apiGet<CryptoAutomationsListResponse>("/api/crypto/automations"),
    [],
  );

  const { data: listData, refresh: refreshList } = usePolling(listFetcher, POLL.OPS, true, {
    staggerKey: "crypto-automations",
  });

  const items = listData?.items ?? [];
  const runningNow = items.some((i) => i.status === "running");
  const tickPollMs = runningNow ? POLL.TICK : POLL.OPS;

  const { refresh: refreshListTick } = usePolling(listFetcher, tickPollMs, runningNow, {
    staggerKey: "crypto-automations-tick",
  });

  const refreshAll = useCallback(() => {
    refreshList();
    if (runningNow) refreshListTick();
  }, [refreshList, refreshListTick, runningNow]);

  const statsFetcher = useCallback(async () => {
    if (!items.length) return {} as Record<string, CryptoAutomationStats>;
    const next: Record<string, CryptoAutomationStats> = {};
    await Promise.all(
      items.map(async (inst) => {
        try {
          const useSession = inst.status === "running" || Boolean(inst.started_at);
          const s = await apiGet<CryptoAutomationStats>(
            `/api/crypto/automations/${inst.id}/stats?${useSession ? "session=1" : "days=7"}`,
          );
          next[inst.id] = s;
        } catch {
          /* skip */
        }
      }),
    );
    return next;
  }, [items]);

  const { data: polledStats } = usePolling(statsFetcher, tickPollMs, items.length > 0, {
    staggerKey: "crypto-auto-stats",
  });

  useEffect(() => {
    if (polledStats) setStatsMap(polledStats);
  }, [polledStats]);

  const scalpSymbols = useMemo(
    () =>
      items
        .filter((i) => supportsScalpPreScan(i.strategy_id))
        .map((i) => i.symbol.toUpperCase()),
    [items],
  );
  const { items: feedHealthMap, alertTicks: feedHealthAlertTicks } = useKlinesFeedHealthMap(
    scalpSymbols,
    tickPollMs,
  );

  useEffect(() => {
    if (!items.length) {
      setActiveId(null);
      return;
    }
    if (activeId && items.some((i) => i.id === activeId)) return;
    setActiveId(items[0].id);
  }, [items, activeId]);

  useEffect(() => {
    try {
      if (activeId) sessionStorage.setItem(ACTIVE_TAB_KEY, activeId);
      else sessionStorage.removeItem(ACTIVE_TAB_KEY);
    } catch {
      /* ignore */
    }
  }, [activeId]);

  const active = useMemo(
    () => items.find((i) => i.id === activeId) ?? null,
    [items, activeId],
  );

  const pairOptions = useMemo(() => {
    const base = pairList?.length ? pairList : ["BTCUSDT", "ETHUSDT", "SOLUSDT"];
    return [...new Set(base)];
  }, [pairList]);

  const toggleCollapse = async (inst: CryptoAutomationInstance, collapsed: boolean) => {
    try {
      await apiPatch(`/api/crypto/automations/${inst.id}`, {
        collapsed,
        operator: "web:operator",
      });
      refreshAll();
    } catch {
      refreshAll();
    }
  };

  const runStop = async (password: string) => {
    if (!stopTarget) return;
    setStopBusy(true);
    setStopError(null);
    try {
      const resp = await apiPost<CryptoAutomationStopResponse>(
        `/api/crypto/automations/${stopTarget.id}/stop`,
        { operator: "web:operator" },
        { operatorPassword: password },
      );
      setStopTarget(null);
      if (resp.session_report) setSessionReport(resp.session_report);
      refreshAll();
    } catch (err) {
      setStopError(formatOperatorFacingError(err, t));
    } finally {
      setStopBusy(false);
    }
  };

  const formatPnl = (id: string) => {
    const p = statsMap[id]?.pnl_pct;
    if (p == null) return "—";
    return `${p >= 0 ? "+" : ""}${p.toFixed(2)}%`;
  };

  const selectInstance = (inst: CryptoAutomationInstance) => {
    setActiveId(inst.id);
    if (inst.collapsed) void toggleCollapse(inst, false);
  };

  return (
    <div className="crypto-automation-workspace crypto-automation-workspace--rail">
      <CryptoMarginHaltBanner onCleared={refreshAll} />

      {items.length === 0 ? (
        <div className="crypto-automation-empty">
          <p className="muted">{t("cryptoAutomation.emptyLead")}</p>
          <button type="button" className="primary" onClick={() => setCreateOpen(true)}>
            {t("cryptoAutomation.createNew")}
          </button>
        </div>
      ) : (
        <div className="crypto-automation-layout">
          <nav className="crypto-automation-rail" aria-label={t("cryptoAutomation.railLabel")}>
            <div className="crypto-automation-rail-head">
              <button type="button" className="primary crypto-automation-rail-create" onClick={() => setCreateOpen(true)}>
                + {t("cryptoAutomation.createNewShort")}
              </button>
              {runningNow ? (
                <p className="muted small crypto-automation-rail-hint">{t("cryptoAutomation.autoRefreshHint")}</p>
              ) : null}
            </div>

            <div className="crypto-automation-rail-list" role="tablist">
              {items.map((inst) => {
                const collapsed = Boolean(inst.collapsed);
                const selected = inst.id === activeId;
                const running = inst.status === "running";
                const isScalp = supportsScalpPreScan(inst.strategy_id);
                const feedHealth = feedHealthMap[inst.symbol.toUpperCase()];
                const feedVariant = isScalp ? resolveKlinesFeedHealthVariant(feedHealth) : null;

                return (
                  <div
                    key={inst.id}
                    className={`crypto-automation-rail-item${selected ? " is-active" : ""}${collapsed ? " is-collapsed" : ""}`}
                    role="tab"
                    aria-selected={selected}
                  >
                    <button
                      type="button"
                      className="crypto-automation-rail-item-main"
                      onClick={() => selectInstance(inst)}
                    >
                      <span className="crypto-automation-rail-item-top">
                        <span className="crypto-automation-rail-symbol">{inst.symbol}</span>
                        <span className={`pill tiny ${running ? "ok" : "muted"}`}>
                          {running ? "●" : "○"}
                        </span>
                      </span>
                      <span className="crypto-automation-rail-strategy">{automationTabLabel(inst, t)}</span>
                      <span className="crypto-automation-rail-meta">
                        {feedVariant ? (
                          <span
                            className={`crypto-automation-tab-feed-dot feed-health-${feedVariant}`}
                            title={feedHealth?.last_source ?? undefined}
                          />
                        ) : null}
                        <span className={`crypto-automation-rail-pnl ${formatPnl(inst.id).startsWith("+") ? "pnl-up" : formatPnl(inst.id).startsWith("-") ? "pnl-down" : ""}`}>
                          {formatPnl(inst.id)}
                        </span>
                      </span>
                    </button>
                    {collapsed ? (
                      <button
                        type="button"
                        className="tiny crypto-automation-rail-expand"
                        onClick={() => selectInstance(inst)}
                      >
                        →
                      </button>
                    ) : selected && running ? (
                      <button
                        type="button"
                        className="tiny danger crypto-automation-rail-stop"
                        disabled={killSwitch}
                        onClick={() => setStopTarget(inst)}
                      >
                        ■
                      </button>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </nav>

          <div className="crypto-automation-main">
            {active && !active.collapsed ? (
              <CryptoAutomationDetail
                instance={active}
                stats={statsMap[active.id] ?? null}
                feedHealth={feedHealthMap[active.symbol.toUpperCase()]}
                feedHealthAlertTicks={feedHealthAlertTicks}
                killSwitch={killSwitch}
                tickPollMs={tickPollMs}
                onRefresh={refreshAll}
                onToggleCollapse={(collapsed) => void toggleCollapse(active, collapsed)}
                onStopped={(report) => {
                  if (report) setSessionReport(report);
                  refreshAll();
                }}
                onDeleted={() => {
                  if (activeId === active.id) setActiveId(null);
                  refreshAll();
                }}
              />
            ) : active && active.collapsed ? (
              <div className="crypto-automation-main-empty">
                <p className="muted">{t("cryptoAutomation.expandHint")}</p>
                <button type="button" className="primary" onClick={() => selectInstance(active)}>
                  {t("cryptoAutomation.expandTab")}
                </button>
              </div>
            ) : (
              <div className="crypto-automation-main-empty">
                <p className="muted">{t("cryptoAutomation.selectAutomation")}</p>
              </div>
            )}
          </div>
        </div>
      )}

      <CreateCryptoAutomationModal
        open={createOpen}
        pairOptions={pairOptions}
        existingInstances={items}
        onClose={() => setCreateOpen(false)}
        onCreated={(id) => {
          if (id) setActiveId(id);
          refreshAll();
        }}
      />

      <OperatorConfirmModal
        open={stopTarget !== null}
        title={t("workflowPanel.stop")}
        risk={t("workflowsPage.operatorRisk")}
        busy={stopBusy}
        error={stopError}
        onConfirm={runStop}
        onCancel={() => setStopTarget(null)}
      />

      <AutomationSessionStatsModal
        report={sessionReport}
        onClose={() => setSessionReport(null)}
        t={t}
      />
    </div>
  );
}
