import { useState } from "react";
import { apiDelete, apiPost, formatOperatorFacingError } from "../../api";
import { useI18n } from "../../i18n/LanguageContext";
import OperatorConfirmModal from "../OperatorConfirmModal";
import type { SecuritiesAutomationInstance } from "../../types/securitiesAutomation";

type Props = {
  instance: SecuritiesAutomationInstance;
  killSwitch?: boolean;
  settingsOpen: boolean;
  onSettingsOpenChange: (open: boolean) => void;
  onToggleCollapse: (collapsed: boolean) => void;
  onRefresh: () => void;
  onDeleted?: () => void;
};

export default function SecuritiesAutomationToolbar({
  instance,
  killSwitch,
  settingsOpen,
  onSettingsOpenChange,
  onToggleCollapse,
  onRefresh,
  onDeleted,
}: Props) {
  const { t } = useI18n();
  const [pendingAction, setPendingAction] = useState<"start" | "stop" | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const isRunning = instance.status === "running";

  const runAction = async (password: string) => {
    if (!pendingAction) return;
    setActionBusy(true);
    setActionError(null);
    try {
      await apiPost(
        `/api/securities/automations/${instance.id}/${pendingAction}`,
        { operator: "web:operator" },
        { operatorPassword: password },
      );
      setPendingAction(null);
      onRefresh();
    } catch (err) {
      setActionError(formatOperatorFacingError(err, t));
    } finally {
      setActionBusy(false);
    }
  };

  const runDelete = async (password: string) => {
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await apiDelete(`/api/securities/automations/${instance.id}`, { operatorPassword: password });
      setDeleteConfirmOpen(false);
      onSettingsOpenChange(false);
      onDeleted?.();
    } catch (err) {
      setDeleteError(formatOperatorFacingError(err, t));
    } finally {
      setDeleteBusy(false);
    }
  };

  return (
    <>
      <div className="crypto-automation-detail-actions">
        <button type="button" className="tiny" onClick={() => onToggleCollapse(true)}>
          {t("moexAutomation.collapseTab")}
        </button>
        <button
          type="button"
          className={`tiny${settingsOpen ? " primary" : ""}`}
          aria-pressed={settingsOpen}
          onClick={() => onSettingsOpenChange(!settingsOpen)}
        >
          {t("moexAutomation.settings")}
        </button>
        {isRunning ? (
          <button
            type="button"
            className="tiny danger"
            disabled={killSwitch}
            onClick={() => setPendingAction("stop")}
          >
            {t("workflowPanel.stop")}
          </button>
        ) : (
          <button
            type="button"
            className="tiny primary"
            disabled={killSwitch}
            onClick={() => setPendingAction("start")}
          >
            {t("workflowPanel.start")}
          </button>
        )}
        <button
          type="button"
          className="tiny danger"
          onClick={() => {
            setDeleteError(null);
            setDeleteConfirmOpen(true);
          }}
        >
          {t("moexAutomation.delete")}
        </button>
      </div>

      <OperatorConfirmModal
        open={pendingAction !== null}
        title={pendingAction === "start" ? t("workflowPanel.start") : t("workflowPanel.stop")}
        risk={t("workflowsPage.operatorRisk")}
        busy={actionBusy}
        error={actionError}
        onConfirm={runAction}
        onCancel={() => setPendingAction(null)}
      />
      <OperatorConfirmModal
        open={deleteConfirmOpen}
        title={t("moexAutomation.deleteTitle")}
        lead={t("moexAutomation.deleteConfirm", { name: instance.name })}
        risk={
          isRunning
            ? `${t("moexAutomation.deleteConfirmRunning")}\n\n${t("workflowsPage.operatorRisk")}`
            : t("workflowsPage.operatorRisk")
        }
        riskTone="danger"
        busy={deleteBusy}
        error={deleteError}
        onConfirm={runDelete}
        onCancel={() => setDeleteConfirmOpen(false)}
      />
    </>
  );
}
