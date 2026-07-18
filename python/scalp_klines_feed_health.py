"""Track consecutive poor testnet klines / mainnet fallback ticks per symbol."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from scalp_klines import ScalpKlinesResult

logger = logging.getLogger(__name__)

FEED_HEALTH_KEY_PREFIX = "crypto_scalp_klines_feed:"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _feed_health_cfg(scalp_cfg: dict[str, Any]) -> dict[str, Any]:
    q = scalp_cfg.get("klines_quality") or {}
    return {
        "feed_dead_alert_ticks": int(q.get("feed_dead_alert_ticks", 6)),
        "block_signals_on_unusable": bool(q.get("block_signals_on_unusable", True)),
        "block_on_feed_dead": bool(q.get("block_on_feed_dead", False)),
        "alert_cooldown_minutes": int(q.get("alert_cooldown_minutes", 30)),
    }


def _load_state(symbol: str) -> dict[str, Any]:
    from runtime_settings import get_runtime_value

    raw = get_runtime_value(f"{FEED_HEALTH_KEY_PREFIX}{symbol.upper()}")
    return dict(raw) if isinstance(raw, dict) else {}


def _save_state(symbol: str, state: dict[str, Any]) -> None:
    from runtime_settings import set_runtime_value

    set_runtime_value(f"{FEED_HEALTH_KEY_PREFIX}{symbol.upper()}", state, updated_by="klines_feed")


def get_klines_feed_health(symbol: str) -> dict[str, Any] | None:
    state = _load_state(symbol)
    if not state:
        return None
    return {
        "symbol": symbol.upper(),
        "consecutive_testnet_poor": int(state.get("consecutive_testnet_poor") or 0),
        "consecutive_mainnet_fallback": int(state.get("consecutive_mainnet_fallback") or 0),
        "consecutive_unusable": int(state.get("consecutive_unusable") or 0),
        "feed_dead": bool(state.get("feed_dead")),
        "last_source": state.get("last_source"),
        "last_alert_at": state.get("last_alert_at"),
        "updated_at": state.get("updated_at"),
    }


def record_klines_feed_health(
    symbol: str,
    result: ScalpKlinesResult,
    scalp_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Update per-symbol counters; emit system alert when testnet feed stays dead."""
    cfg = _feed_health_cfg(scalp_cfg)
    sym = symbol.upper()
    state = _load_state(sym)
    prev_fallback = int(state.get("consecutive_mainnet_fallback") or 0)
    prev_unusable = int(state.get("consecutive_unusable") or 0)

    if result.source == "mainnet_metrics_fallback":
        state["consecutive_testnet_poor"] = int(state.get("consecutive_testnet_poor") or 0) + 1
        state["consecutive_mainnet_fallback"] = prev_fallback + 1
        state["consecutive_unusable"] = 0
    elif result.source == "unusable":
        state["consecutive_unusable"] = prev_unusable + 1
        if result.testnet_poor:
            state["consecutive_testnet_poor"] = int(state.get("consecutive_testnet_poor") or 0) + 1
        state["consecutive_mainnet_fallback"] = 0
    elif result.testnet_poor:
        state["consecutive_testnet_poor"] = int(state.get("consecutive_testnet_poor") or 0) + 1
        state["consecutive_mainnet_fallback"] = 0
        state["consecutive_unusable"] = 0
    else:
        state["consecutive_testnet_poor"] = 0
        state["consecutive_mainnet_fallback"] = 0
        state["consecutive_unusable"] = 0
        state["feed_dead"] = False

    state["last_source"] = result.source
    state["updated_at"] = _utc_now()

    fallback_streak = int(state.get("consecutive_mainnet_fallback") or 0)
    alert_ticks = cfg["feed_dead_alert_ticks"]
    feed_dead = fallback_streak >= alert_ticks
    state["feed_dead"] = feed_dead

    alert_fired = False
    if feed_dead and _should_emit_alert(state, cfg):
        alert_fired = _emit_feed_dead_alert(sym, fallback_streak, result.source)
        if alert_fired:
            state["last_alert_at"] = _utc_now()

    _save_state(sym, state)

    block_reason: str | None = None
    if not result.quality_ok and cfg["block_signals_on_unusable"]:
        block_reason = "klines_unusable"
    elif feed_dead and cfg["block_on_feed_dead"]:
        block_reason = "testnet_feed_dead"

    return {
        "symbol": sym,
        "feed_dead": feed_dead,
        "consecutive_mainnet_fallback": fallback_streak,
        "consecutive_unusable": int(state.get("consecutive_unusable") or 0),
        "alert_fired": alert_fired,
        "block_reason": block_reason,
        "last_source": result.source,
    }


def _should_emit_alert(state: dict[str, Any], cfg: dict[str, Any]) -> bool:
    last = state.get("last_alert_at")
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        cooldown_min = max(1, int(cfg.get("alert_cooldown_minutes", 30)))
        elapsed_min = (datetime.now(timezone.utc) - last_dt).total_seconds() / 60
        return elapsed_min >= cooldown_min
    except ValueError:
        return True


def _emit_feed_dead_alert(symbol: str, streak: int, source: str) -> bool:
    msg = (
        f"Testnet feed dead for {symbol}: {streak} ticks on {source} "
        f"(metrics from mainnet fallback; orders still on testnet)"
    )
    logger.warning(msg)
    try:
        from activity_feed_service import log_system_activity

        log_system_activity(
            msg,
            category="crypto",
            level="warn",
            payload={"symbol": symbol, "streak": streak},
        )
        return True
    except Exception as exc:
        logger.warning("feed_health_activity_failed symbol=%s err=%s", symbol, exc)
        return False
