import { useI18n } from "../../i18n/LanguageContext";

export type KlinesFeedHealth = {
  symbol: string;
  consecutive_testnet_poor?: number;
  consecutive_mainnet_fallback?: number;
  consecutive_unusable?: number;
  feed_dead?: boolean;
  last_source?: string | null;
  last_alert_at?: string | null;
  updated_at?: string | null;
};

export type KlinesFeedHealthVariant = "dead" | "unusable" | "fallback" | "ok" | "unknown";

export function resolveKlinesFeedHealthVariant(
  health: KlinesFeedHealth | null | undefined,
): KlinesFeedHealthVariant {
  if (!health?.updated_at) return "unknown";
  if (health.feed_dead) return "dead";
  if ((health.consecutive_unusable ?? 0) > 0) return "unusable";
  if ((health.consecutive_mainnet_fallback ?? 0) > 0) return "fallback";
  if (health.last_source === "testnet" || health.last_source === "mainnet") return "ok";
  return "unknown";
}

type Props = {
  health: KlinesFeedHealth | null | undefined;
  alertTicks?: number;
  /** Shorter label for tab strip */
  compact?: boolean;
};

export default function KlinesFeedHealthBadge({
  health,
  alertTicks = 6,
  compact = false,
}: Props) {
  const { t } = useI18n();
  const variant = resolveKlinesFeedHealthVariant(health);
  const fallbackN = health?.consecutive_mainnet_fallback ?? 0;

  let label: string;
  let title: string;

  switch (variant) {
    case "dead":
      label = compact
        ? t("cryptoAutomation.feedHealthDeadShort")
        : t("cryptoAutomation.feedHealthDead", { n: String(fallbackN), max: String(alertTicks) });
      title = t("cryptoAutomation.feedHealthDeadHint");
      break;
    case "unusable":
      label = compact
        ? t("cryptoAutomation.feedHealthUnusableShort")
        : t("cryptoAutomation.feedHealthUnusable");
      title = t("cryptoAutomation.feedHealthUnusableHint");
      break;
    case "fallback":
      label = compact
        ? t("cryptoAutomation.feedHealthFallbackShort")
        : t("cryptoAutomation.feedHealthFallback", { n: String(fallbackN) });
      title = t("cryptoAutomation.feedHealthFallbackHint");
      break;
    case "ok":
      label = compact
        ? t("cryptoAutomation.feedHealthOkShort")
        : t("cryptoAutomation.feedHealthOk");
      title = t("cryptoAutomation.feedHealthOkHint");
      break;
    default:
      label = compact
        ? t("cryptoAutomation.feedHealthUnknownShort")
        : t("cryptoAutomation.feedHealthUnknown");
      title = t("cryptoAutomation.feedHealthUnknownHint");
  }

  return (
    <span
      className={`automation-product-pill feed-health feed-health-${variant}${compact ? " feed-health-compact" : ""}`}
      title={title}
    >
      {label}
    </span>
  );
}
