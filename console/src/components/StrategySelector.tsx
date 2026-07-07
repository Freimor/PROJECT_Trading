import { useCallback, useMemo, useState } from "react";
import { apiGet, apiPost } from "../api";
import { POLL } from "../config/polling";
import { useI18n } from "../i18n/LanguageContext";
import { usePolling } from "../hooks/usePolling";
import type { StrategyState } from "../types";

type Props = {
  market: "crypto" | "securities";
  onChange?: (state: StrategyState) => void;
};

export default function StrategySelector({ market, onChange }: Props) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);
  const [localError, setLocalError] = useState("");

  const fetcher = useCallback(() => apiGet<StrategyState>(`/api/strategies/${market}`), [market]);

  const { data, refresh } = usePolling(fetcher, POLL.DASHBOARD, true, {
    staggerKey: `strategy-${market}`,
  });

  const strategies = useMemo(
    () => (data?.strategies ?? []).filter((s) => s.uses_llm !== false),
    [data?.strategies],
  );

  const select = async (strategyId: string) => {
    if (strategyId === data?.active || busy) return;
    setBusy(true);
    setLocalError("");
    try {
      const next = await apiPost<StrategyState>(`/api/strategies/${market}`, {
        strategy_id: strategyId,
        operator: "web:operator",
      });
      onChange?.(next);
      refresh();
    } catch (err) {
      setLocalError(
        err instanceof Error && err.message.includes("401")
          ? "Admin API key required (header field)"
          : String(err),
      );
    } finally {
      setBusy(false);
    }
  };

  if (!strategies.length) return null;

  const active = data?.active && strategies.some((s) => s.id === data.active)
    ? data.active
    : strategies[0]?.id;

  return (
    <div className="strategy-selector">
      <div className="strategy-selector-head">
        <span className="strategy-selector-title">{t("workspace.strategy")}</span>
        <span className="muted small">
          {active ? t(`strategies.${active}.label` as "strategies.llm_swing.label") : ""}
        </span>
      </div>
      <div className="strategy-options">
        {strategies.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`strategy-option ${active === s.id ? "active" : ""}`}
            disabled={busy}
            onClick={() => select(s.id)}
          >
            <strong>{t(`strategies.${s.id}.label` as "strategies.llm_swing.label")}</strong>
            <span className="muted small strategy-desc">
              {t(`strategies.${s.id}.description` as "strategies.llm_swing.description")}
            </span>
          </button>
        ))}
      </div>
      {localError && <p className="warn small">{localError}</p>}
    </div>
  );
}
