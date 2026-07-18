import { useState } from "react";
import { apiGet, apiPost } from "../api";
import PortfolioCard from "../components/PortfolioCard";
import { POLL } from "../config/polling";
import { useErrorNotifications } from "../context/ErrorNotifications";
import { usePolling } from "../hooks/usePolling";
import { useI18n } from "../i18n/LanguageContext";

export default function PaperPage() {
  const { t } = useI18n();
  const [log, setLog] = useState("");
  const [busy, setBusy] = useState(false);
  const { report } = useErrorNotifications();

  const { data: status } = usePolling(() => apiGet("/api/paper/status"), POLL.OPS, true, {
    staggerKey: "paper-status",
  });
  const { data: eff, refresh: refreshEff } = usePolling(
    () => apiGet("/api/paper/effectiveness?days=7"),
    POLL.OPS,
    true,
    { staggerKey: "paper-effectiveness" },
  );

  const run = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(true);
    report("paper/action", null);
    setLog(`${label}…`);
    try {
      const r = await fn();
      setLog(JSON.stringify(r, null, 2));
      refreshEff();
    } catch (err) {
      report("paper/action", String(err));
    } finally {
      setBusy(false);
    }
  };

  const paper = eff as Record<string, unknown> | null;
  const session = paper?.session as Record<string, unknown> | undefined;
  const deltas = paper?.deltas as Record<string, number> | undefined;

  return (
    <div className="page">
      <div className="page-title">
        <h2>{t("paperPage.title")}</h2>
        <p className="muted">{t("paperPage.subtitle")}</p>
      </div>

      <div className="grid cards-2">
        <PortfolioCard
          title={t("paperPage.config")}
          subtitle={String((status as { global_mode?: string })?.global_mode)}
        >
          <pre className="small-pre">{JSON.stringify(status, null, 2)}</pre>
        </PortfolioCard>

        <PortfolioCard title={t("paperPage.effectiveness")}>
          {session ? (
            <>
              <div className="metric-row">
                <span>{t("paperPage.session")}</span>
                <strong>{String(session.label ?? session.id).slice(0, 20)}</strong>
              </div>
              {deltas && (
                <>
                  <div className="metric-row">
                    <span>{t("paperPage.deltaUsdt")}</span>
                    <strong>{deltas.usdt_delta?.toFixed(2) ?? "—"}</strong>
                  </div>
                  <div className="metric-row">
                    <span>{t("paperPage.deltaRub")}</span>
                    <strong>{deltas.rub_delta?.toFixed(0) ?? "—"}</strong>
                  </div>
                </>
              )}
            </>
          ) : (
            <p className="muted">{t("paperPage.noSession")}</p>
          )}
        </PortfolioCard>
      </div>

      <PortfolioCard title={t("paperPage.actions")}>
        <div className="btn-row">
          <button
            type="button"
            disabled={busy}
            onClick={() => run(t("paperPage.snapshot"), () => apiPost("/api/paper/snapshot"))}
          >
            {t("paperPage.snapshot")}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => run(t("paperPage.resetSandbox"), () => apiPost("/api/paper/session/reset"))}
          >
            {t("paperPage.resetSandbox")}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() =>
              run(t("paperPage.runCrypto"), () => apiPost("/api/paper/crypto/run", { symbol: "BTCUSDT" }))
            }
          >
            {t("paperPage.runCrypto")}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() =>
              run(t("paperPage.runMoex"), () => apiPost("/api/paper/securities/swing", { ticker: "SBER" }))
            }
          >
            {t("paperPage.runMoex")}
          </button>
        </div>
      </PortfolioCard>

      {log && (
        <PortfolioCard title={t("paperPage.result")}>
          <pre>{log}</pre>
        </PortfolioCard>
      )}
    </div>
  );
}
