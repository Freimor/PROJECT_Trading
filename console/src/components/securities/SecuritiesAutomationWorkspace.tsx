import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiPatch, apiPost, formatOperatorFacingError } from "../../api";
import { POLL } from "../../config/polling";
import { useI18n } from "../../i18n/LanguageContext";
import { usePolling } from "../../hooks/usePolling";
import OperatorConfirmModal from "../OperatorConfirmModal";
import CreateSecuritiesAutomationModal from "./CreateSecuritiesAutomationModal";
import SecuritiesAutomationDetail from "./SecuritiesAutomationDetail";
import SecuritiesAutomationToolbar from "./SecuritiesAutomationToolbar";
import {
  automationTabLabel,
  strategyTabLabel,
  symbolsShortLabel,
} from "../../utils/securitiesWorkflowMap";
import type {
  SecuritiesAutomationInstance,
  SecuritiesAutomationStats,
  SecuritiesAutomationsListResponse,
} from "../../types/securitiesAutomation";

const ACTIVE_TAB_KEY = "securities-automation-active-tab";

type Props = { killSwitch?: boolean };

export default function SecuritiesAutomationWorkspace({ killSwitch }: Props) {
  const { t } = useI18n();
  const [activeId, setActiveId] = useState<string | null>(() => {
    try {
      return sessionStorage.getItem(ACTIVE_TAB_KEY);
    } catch {
      return null;
    }
  });
  const [createOpen, setCreateOpen] = useState(false);
  const [statsMap, setStatsMap] = useState<Record<string, SecuritiesAutomationStats>>({});
  const [stopTarget, setStopTarget] = useState<SecuritiesAutomationInstance | null>(null);
  const [stopBusy, setStopBusy] = useState(false);
  const [stopError, setStopError] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const tickersFetcher = useCallback(
    () => apiGet<string[]>("/api/securities/swing-universe"),
    [],
  );
  const { data: tickerList } = usePolling(tickersFetcher, POLL.OPS, true, {
    staggerKey: "moex-auto-tickers",
  });

  const listFetcher = useCallback(
    () => apiGet<SecuritiesAutomationsListResponse>("/api/securities/automations"),
    [],
  );
  const { data: listData, refresh: refreshList } = usePolling(listFetcher, POLL.OPS, true, {
    staggerKey: "securities-automations",
  });

  const items = listData?.items ?? [];

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

  useEffect(() => {
    let cancelled = false;
    const loadStats = async () => {
      const next: Record<string, SecuritiesAutomationStats> = {};
      await Promise.all(
        items.map(async (inst) => {
          try {
            const s = await apiGet<SecuritiesAutomationStats>(
              `/api/securities/automations/${inst.id}/stats?days=7`,
            );
            next[inst.id] = s;
          } catch {
            /* skip */
          }
        }),
      );
      if (!cancelled) setStatsMap(next);
    };
    if (items.length) void loadStats();
    return () => {
      cancelled = true;
    };
  }, [items]);

  const active = useMemo(() => items.find((i) => i.id === activeId) ?? null, [items, activeId]);

  useEffect(() => {
    setSettingsOpen(false);
  }, [activeId]);

  const tickerOptions = useMemo(() => {
    const base = tickerList?.length ? tickerList : ["SBER", "GAZP", "LKOH"];
    return [...new Set(base)];
  }, [tickerList]);

  const toggleCollapse = async (inst: SecuritiesAutomationInstance, collapsed: boolean) => {
    try {
      await apiPatch(`/api/securities/automations/${inst.id}`, { collapsed, operator: "web:operator" });
      refreshList();
    } catch {
      refreshList();
    }
  };

  const runStop = async (password: string) => {
    if (!stopTarget) return;
    setStopBusy(true);
    setStopError(null);
    try {
      await apiPost(
        `/api/securities/automations/${stopTarget.id}/stop`,
        { operator: "web:operator" },
        { operatorPassword: password },
      );
      setStopTarget(null);
      refreshList();
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

  return (
    <div className="crypto-automation-workspace crypto-automation-workspace--compact">
      <div className="crypto-automation-toolbar crypto-automation-toolbar--compact">
        <h2>{t("workspace.moexTitle")}</h2>
        <button type="button" className="primary" onClick={() => setCreateOpen(true)}>
          {t("moexAutomation.createNew")}
        </button>
      </div>

      {items.length === 0 ? (
        <div className="crypto-automation-empty">
          <p className="muted">{t("moexAutomation.emptyLead")}</p>
          <button type="button" className="primary" onClick={() => setCreateOpen(true)}>
            {t("moexAutomation.createNew")}
          </button>
        </div>
      ) : (
        <>
          <div className="crypto-automation-strip">
            <div className="crypto-automation-tabs" role="tablist">
            {items.map((inst) => {
              const collapsed = Boolean(inst.collapsed);
              const selected = inst.id === activeId;
              const running = inst.status === "running";
              if (collapsed) {
                return (
                  <div
                    key={inst.id}
                    className={`crypto-automation-tab crypto-automation-tab--collapsed${selected ? " is-active" : ""}`}
                    role="tab"
                    aria-selected={selected}
                  >
                    <button
                      type="button"
                      className="crypto-automation-tab-expand"
                      onClick={() => {
                        setActiveId(inst.id);
                        void toggleCollapse(inst, false);
                      }}
                    >
                      <span className="crypto-automation-tab-title">{automationTabLabel(inst, t)}</span>
                      <span className={`pill tiny ${running ? "ok" : "muted"}`}>
                        {running ? t("moexAutomation.statusRunning") : t("moexAutomation.statusStopped")}
                      </span>
                      <span className="crypto-automation-tab-pnl">{formatPnl(inst.id)}</span>
                    </button>
                    <button type="button" className="tiny danger" disabled={!running || killSwitch} onClick={() => setStopTarget(inst)}>
                      {t("workflowPanel.stop")}
                    </button>
                  </div>
                );
              }
              return (
                <button
                  key={inst.id}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  className={`crypto-automation-tab crypto-automation-tab--stacked${selected ? " is-active" : ""}`}
                  onClick={() => setActiveId(inst.id)}
                >
                  <span className="crypto-automation-tab-text">
                    <span className="crypto-automation-tab-strategy">{strategyTabLabel(inst.strategy_id, t)}</span>
                    <span className="crypto-automation-tab-symbols">{symbolsShortLabel(inst)}</span>
                  </span>
                  <span className={`pill tiny ${running ? "ok" : "muted"}`}>{running ? "●" : "○"}</span>
                </button>
              );
            })}
            <button type="button" className="crypto-automation-tab crypto-automation-tab--add" onClick={() => setCreateOpen(true)}>
              + {t("moexAutomation.createNewShort")}
            </button>
            </div>

            {active && !active.collapsed ? (
              <SecuritiesAutomationToolbar
                instance={active}
                killSwitch={killSwitch}
                settingsOpen={settingsOpen}
                onSettingsOpenChange={setSettingsOpen}
                onToggleCollapse={(collapsed) => void toggleCollapse(active, collapsed)}
                onRefresh={refreshList}
                onDeleted={() => {
                  if (activeId === active.id) setActiveId(null);
                  refreshList();
                }}
              />
            ) : null}
          </div>

          {active && !active.collapsed ? (
            <SecuritiesAutomationDetail
              instance={active}
              stats={statsMap[active.id] ?? null}
              settingsOpen={settingsOpen}
              onRefresh={refreshList}
            />
          ) : active && active.collapsed ? (
            <p className="muted small crypto-automation-collapsed-hint">{t("moexAutomation.expandHint")}</p>
          ) : null}
        </>
      )}

      <CreateSecuritiesAutomationModal
        open={createOpen}
        tickerOptions={tickerOptions}
        existingInstances={items}
        onClose={() => setCreateOpen(false)}
        onCreated={(id) => {
          if (id) setActiveId(id);
          refreshList();
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
    </div>
  );
}
