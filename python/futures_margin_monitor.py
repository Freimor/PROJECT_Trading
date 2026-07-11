"""Futures margin / liquidation monitor — stops crypto automation on margin call."""

from __future__ import annotations

import logging
import time
from typing import Any

from config_loader import load_config
from crypto_product import get_crypto_trading_product, is_futures_trading
from effective_config import get_config_effective
from event_log import log_event
from runtime_settings import get_runtime_value, set_runtime_value

logger = logging.getLogger(__name__)

_HALT_KEY = "futures_margin_halt:crypto"
_STATE_KEY = "futures_margin_monitor_state"


def _monitor_cfg() -> dict[str, Any]:
    return dict(get_config_effective("crypto_config").get("futures_margin_monitor") or {})


def is_futures_margin_halt_active() -> bool:
    payload = get_runtime_value(_HALT_KEY)
    return bool(payload and payload.get("active"))


def get_futures_margin_halt() -> dict[str, Any] | None:
    return get_runtime_value(_HALT_KEY)


def activate_futures_margin_halt(*, reason: str, details: dict[str, Any] | None = None) -> None:
    from datetime import datetime, timezone

    set_runtime_value(
        _HALT_KEY,
        {
            "active": True,
            "reason": reason,
            "details": details or {},
            "date": datetime.now(timezone.utc).date().isoformat(),
        },
        updated_by="futures_margin_monitor",
    )


def clear_futures_margin_halt(*, operator: str = "operator") -> dict[str, Any]:
    from runtime_settings import delete_runtime_value

    prev = get_futures_margin_halt()
    delete_runtime_value(_HALT_KEY)
    log_event(
        market="crypto",
        env=_crypto_env(),
        stage="reconcile",
        decision="approve",
        reject_reason="futures_margin_halt_cleared",
        workflow_name="futures-margin-monitor",
        payload={"operator": operator, "previous_halt": prev},
    )
    return {"status": "ok", "cleared": True, "previous_halt": prev}


def _monitor_state() -> dict[str, Any]:
    raw = get_runtime_value(_STATE_KEY)
    if not isinstance(raw, dict):
        return {"seen_order_ids": []}
    seen = raw.get("seen_order_ids")
    if not isinstance(seen, list):
        raw["seen_order_ids"] = []
    return raw


def _save_monitor_state(state: dict[str, Any]) -> None:
    seen = [int(x) for x in state.get("seen_order_ids") or [] if str(x).isdigit()]
    state["seen_order_ids"] = seen[-200:]
    set_runtime_value(_STATE_KEY, state, updated_by="futures_margin_monitor")


def _crypto_env() -> str:
    cfg = get_config_effective("crypto_config")
    mode = str(cfg.get("mode") or "paper")
    env = str(cfg.get("env") or "testnet")
    if mode == "dry_run":
        return "dry_run"
    if env == "testnet":
        return "paper"
    return "live"


def _trigger_margin_halt(
    *,
    trigger: str,
    details: dict[str, Any],
    auto_stop_workflows: bool,
    apply_kill_switch: bool,
) -> dict[str, Any]:
    if is_futures_margin_halt_active():
        return {
            "status": "already_halted",
            "trigger": trigger,
            "halt": get_futures_margin_halt(),
        }

    activate_futures_margin_halt(reason=trigger, details=details)

    liquidation: dict[str, Any] | None = None
    try:
        from automation_control_service import _maybe_liquidate_session

        liquidation = _maybe_liquidate_session(
            "crypto",
            operator="futures_margin_monitor",
            reason="margin_call",
        )
    except Exception as exc:
        logger.exception("futures_margin_liquidate_failed")
        liquidation = {"status": "error", "message": str(exc)}

    stop_result: dict[str, Any] | None = None
    if auto_stop_workflows:
        try:
            from automation_control_service import stop_market_workflows

            stop_result = stop_market_workflows("crypto")
        except Exception as exc:
            logger.exception("futures_margin_stop_workflows_failed")
            stop_result = {"status": "error", "message": str(exc)}

    kill_result: dict[str, Any] | None = None
    if apply_kill_switch:
        try:
            from admin_service import apply_kill_switch

            kill_result = apply_kill_switch(
                enabled=True,
                operator="futures_margin_monitor",
                source="futures_margin_monitor",
            )
        except Exception as exc:
            logger.exception("futures_margin_kill_switch_failed")
            kill_result = {"status": "error", "message": str(exc)}

    payload = {
        "trigger": trigger,
        "details": details,
        "liquidation": liquidation,
        "workflows_stopped": stop_result,
        "kill_switch": kill_result,
    }
    log_event(
        market="crypto",
        env=_crypto_env(),
        stage="guardrails",
        symbol=details.get("symbol"),
        decision="halt",
        reject_reason="futures_margin_call",
        workflow_name="futures-margin-monitor",
        payload=payload,
    )

    try:
        from activity_feed_service import log_system_activity

        sym = details.get("symbol") or "—"
        log_system_activity(
            f"Futures margin call: автомат crypto остановлен ({sym})",
            category="risk",
            level="error",
            payload=payload,
        )
    except Exception:
        pass

    cfg = load_config("guardrails")
    if cfg.get("alerts", {}).get("telegram_enabled"):
        try:
            from telegram_notify import send_telegram_message

            send_telegram_message(
                "🔴 Futures margin call\n"
                f"Trigger: {trigger}\n"
                f"Symbol: {details.get('symbol', '—')}\n"
                "Crypto automation stopped."
            )
        except Exception:
            pass

    return {
        "status": "halted",
        "trigger": trigger,
        "halt": get_futures_margin_halt(),
        "workflows_stopped": stop_result,
        "kill_switch": kill_result,
    }


def _find_new_liquidations(
    *,
    testnet: bool,
    lookback_minutes: int,
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    from binance_futures_client import get_futures_force_orders

    now_ms = int(time.time() * 1000)
    start_ms = now_ms - max(5, lookback_minutes) * 60 * 1000
    seen = {int(x) for x in state.get("seen_order_ids") or [] if str(x).isdigit()}
    new_rows: list[dict[str, Any]] = []

    for auto_type in ("LIQUIDATION", "ADL"):
        rows = get_futures_force_orders(
            testnet=testnet,
            auto_close_type=auto_type,
            start_time_ms=start_ms,
            end_time_ms=now_ms,
        )
        for row in rows:
            oid = int(row.get("order_id") or 0)
            if oid <= 0:
                continue
            if oid in seen:
                continue
            row["detected_auto_close_type"] = auto_type
            new_rows.append(row)
            seen.add(oid)

    state["seen_order_ids"] = sorted(seen)[-200:]
    return new_rows


def _critical_margin_positions(
    *,
    testnet: bool,
    margin_ratio_halt: float,
) -> list[dict[str, Any]]:
    from binance_futures_client import get_futures_position_risk

    critical: list[dict[str, Any]] = []
    for row in get_futures_position_risk(testnet=testnet):
        if abs(float(row.get("position_amt") or 0)) < 1e-12:
            continue
        ratio = float(row.get("margin_ratio") or 0)
        if ratio >= margin_ratio_halt:
            critical.append(row)
    return critical


def scan_futures_margin_risk(
    *,
    testnet: bool | None = None,
    auto_stop: bool | None = None,
) -> dict[str, Any]:
    """Scan Binance futures for liquidations / critical margin; optionally stop automation."""
    cfg = _monitor_cfg()
    if not cfg.get("enabled", True):
        return {"status": "skipped", "reason": "monitor_disabled"}

    crypto_cfg = get_config_effective("crypto_config")
    product = get_crypto_trading_product(cfg=crypto_cfg)
    if not product.get("is_futures"):
        return {"status": "skipped", "reason": "not_futures_mode", "product": product}

    if testnet is None:
        testnet = str(crypto_cfg.get("env") or "testnet") != "live"

    if is_futures_margin_halt_active():
        return {
            "status": "halt_active",
            "reason": "futures_margin_halt_active",
            "halt": get_futures_margin_halt(),
            "testnet": testnet,
        }

    lookback = int(cfg.get("lookback_minutes", 120))
    margin_ratio_halt = float(cfg.get("margin_ratio_halt", 1.0))
    auto_stop_workflows = bool(cfg.get("auto_stop_workflows", True))
    apply_kill_switch = bool(cfg.get("apply_kill_switch", False))
    if auto_stop is not None:
        auto_stop_workflows = bool(auto_stop)

    state = _monitor_state()
    new_liquidations = _find_new_liquidations(
        testnet=testnet,
        lookback_minutes=lookback,
        state=state,
    )
    _save_monitor_state(state)

    account: dict[str, Any] | None = None
    account_critical = False
    if cfg.get("poll_account_margin_ratio", True):
        from binance_futures_client import get_futures_account

        account = get_futures_account(testnet=testnet)
        if account.get("status") == "ok":
            account_critical = float(account.get("margin_ratio") or 0) >= margin_ratio_halt

    critical_positions = _critical_margin_positions(
        testnet=testnet,
        margin_ratio_halt=margin_ratio_halt,
    )

    trigger: str | None = None
    details: dict[str, Any] = {}

    if new_liquidations:
        primary = sorted(new_liquidations, key=lambda r: r.get("time_ms") or 0)[-1]
        trigger = "liquidation_order"
        details = {
            "symbol": primary.get("symbol"),
            "liquidations": new_liquidations,
            "primary": primary,
        }
    elif account_critical and account:
        trigger = "account_margin_ratio"
        details = {
            "account": account,
            "margin_ratio_halt": margin_ratio_halt,
        }
    elif critical_positions:
        worst = max(critical_positions, key=lambda r: float(r.get("margin_ratio") or 0))
        trigger = "position_margin_ratio"
        details = {
            "symbol": worst.get("symbol"),
            "positions": critical_positions,
            "worst": worst,
            "margin_ratio_halt": margin_ratio_halt,
        }

    if trigger and auto_stop_workflows:
        halt_result = _trigger_margin_halt(
            trigger=trigger,
            details=details,
            auto_stop_workflows=auto_stop_workflows,
            apply_kill_switch=apply_kill_switch,
        )
        return {
            "status": "halted",
            "testnet": testnet,
            "trigger": trigger,
            "details": details,
            **halt_result,
        }

    return {
        "status": "ok",
        "testnet": testnet,
        "new_liquidations": len(new_liquidations),
        "liquidations": new_liquidations[:10],
        "account": account,
        "account_critical": account_critical,
        "critical_positions": critical_positions,
        "margin_ratio_halt": margin_ratio_halt,
        "halt_active": is_futures_margin_halt_active(),
    }


def ensure_futures_margin_ok(*, testnet: bool | None = None) -> dict[str, Any] | None:
    """Lightweight guard used before crypto futures trades."""
    if not is_futures_trading():
        return None
    if is_futures_margin_halt_active():
        return {
            "pass": False,
            "reject_reason": "futures_margin_halt_active",
            "halt": get_futures_margin_halt(),
        }
    cfg = _monitor_cfg()
    if not cfg.get("enabled", True):
        return None
    if not cfg.get("scan_before_trade", True):
        return None
    result = scan_futures_margin_risk(testnet=testnet, auto_stop=True)
    if result.get("status") in ("halted", "halt_active"):
        return {
            "pass": False,
            "reject_reason": "futures_margin_call",
            "scan": result,
        }
    return None
