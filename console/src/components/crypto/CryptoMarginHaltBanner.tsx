import { useCallback, useState } from "react";
import { apiGet, apiPost, formatOperatorFacingError } from "../../api";
import { POLL } from "../../config/polling";
import { useI18n } from "../../i18n/LanguageContext";
import { usePolling } from "../../hooks/usePolling";
import OperatorConfirmModal from "../OperatorConfirmModal";

type MarginHaltResp = {
  status?: string;
  active?: boolean;
  halt?: {
    reason?: string;
    date?: string;
    details?: Record<string, unknown>;
  } | null;
};

type Props = {
  onCleared?: () => void;
};

export default function CryptoMarginHaltBanner({ onCleared }: Props) {
  const { t } = useI18n();
  const [resetOpen, setResetOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetcher = useCallback(
    () => apiGet<MarginHaltResp>("/api/crypto/futures/margin-halt"),
    [],
  );
  const { data, refresh } = usePolling(fetcher, POLL.OPS, true, {
    staggerKey: "crypto-margin-halt",
  });

  if (!data?.active) return null;

  const reason = data.halt?.reason ?? "margin_call";

  const resetHalt = async (password: string) => {
    setBusy(true);
    setError(null);
    try {
      await apiPost(
        "/api/crypto/futures/margin-halt/reset",
        { operator: "web:operator" },
        { operatorPassword: password },
      );
      setResetOpen(false);
      refresh();
      onCleared?.();
    } catch (err) {
      setError(formatOperatorFacingError(err, t));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="crypto-margin-halt-banner" role="alert">
        <div>
          <strong>{t("cryptoFutures.marginHaltTitle")}</strong>
          <p className="small">{t("cryptoFutures.marginHaltLead", { reason })}</p>
        </div>
        <button type="button" className="tiny" onClick={() => setResetOpen(true)}>
          {t("cryptoFutures.marginHaltReset")}
        </button>
      </div>

      <OperatorConfirmModal
        open={resetOpen}
        title={t("cryptoFutures.marginHaltResetTitle")}
        lead={t("cryptoFutures.marginHaltResetLead")}
        risk={t("cryptoFutures.marginHaltResetRisk")}
        riskTone="danger"
        busy={busy}
        error={error}
        onConfirm={resetHalt}
        onCancel={() => !busy && setResetOpen(false)}
      />
    </>
  );
}
