import { useI18n } from "../i18n/LanguageContext";
import ModalPortal from "../ui/ModalPortal";
type Props = {
  strategyId: string;
  onClose: () => void;
};

export default function StrategyDetailModal({ strategyId, onClose }: Props) {
  const { t } = useI18n();
  const label = t(`strategies.${strategyId}.label` as "strategies.llm_swing.label");
  const detailKey = `strategies.${strategyId}.detail` as "strategies.llm_swing.detail";
  const detail = t(detailKey);

  return (
    <ModalPortal>
      <div className="modal-overlay" role="presentation" onClick={onClose}>
        <div
          className="modal-dialog strategy-detail-modal"
          role="dialog"
          aria-labelledby="strategy-detail-title"
          onClick={(e) => e.stopPropagation()}
        >
          <h3 id="strategy-detail-title">{label}</h3>
          <pre className="strategy-detail-pre">{detail}</pre>
          <div className="modal-actions">
            <button type="button" className="tiny" onClick={onClose}>
              {t("common.close")}
            </button>
          </div>
        </div>
      </div>
    </ModalPortal>
  );}
