"""Guardrails enforcement (G1–G12 subset)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from config_loader import load_config
from effective_config import get_guardrails


def _moex_session_ok(guardrails: dict[str, Any]) -> bool:
    session = guardrails.get("session", {})
    tz = ZoneInfo(session.get("timezone", "Europe/Moscow"))
    now = datetime.now(tz)
    if now.weekday() >= 5:
        return False
    start = session.get("moex_start_hour", 10)
    end = session.get("moex_end_hour", 19)
    return start <= now.hour < end


def enforce_guardrails(
    *,
    market: str,
    symbol: str | None,
    llm_decision: dict[str, Any] | None,
    env: str,
    guardrails: dict[str, Any] | None = None,
) -> dict[str, Any]:
    g = guardrails or get_guardrails()
    trading = g.get("trading", {})
    symbols = g.get("symbols", {})
    llm_cfg = g.get("llm", {})

    if trading.get("kill_switch"):
        return {"pass": False, "reject_reason": "kill_switch_active"}

    if env == "live" and trading.get("live_requires_manual_flag"):
        return {"pass": False, "reject_reason": "live_requires_manual_flag"}

    allowed_envs = trading.get("allowed_envs", [])
    if env == "live" and "live" not in allowed_envs:
        pass  # live checked separately
    elif env in ("paper", "dry_run", "shadow") and env not in allowed_envs and "dry_run" not in allowed_envs:
        if env not in ("testnet", "sandbox"):
            pass

    if symbol and market == "crypto":
        wl = symbols.get("crypto_whitelist", [])
        if wl and symbol not in wl:
            return {"pass": False, "reject_reason": "symbol_not_whitelisted"}

    if symbol and market == "securities":
        wl = symbols.get("moex_whitelist", [])
        if wl and symbol not in wl:
            return {"pass": False, "reject_reason": "symbol_not_whitelisted"}

    if market == "securities" and not _moex_session_ok(g):
        return {"pass": False, "reject_reason": "outside_session"}

    if llm_decision:
        action = llm_decision.get("action") or llm_decision.get("parsed_action")
        if action not in llm_cfg.get("allowed_actions", ["approve", "reject"]):
            return {"pass": False, "reject_reason": "invalid_action"}
        forbidden = llm_cfg.get("forbidden_output_fields", [])
        for field in forbidden:
            if field in llm_decision and llm_decision[field] is not None:
                return {"pass": False, "reject_reason": "llm_overreach"}
        conf = llm_decision.get("confidence")
        if action == "approve":
            if conf is None or conf < llm_cfg.get("min_confidence", 0.7):
                return {"pass": False, "reject_reason": "low_confidence"}
            if llm_cfg.get("require_counter_thesis"):
                ct = llm_decision.get("counter_thesis") or ""
                if len(ct) < llm_cfg.get("counter_thesis_min_chars", 10):
                    return {"pass": False, "reject_reason": "missing_counter_thesis"}

    return {"pass": True, "reject_reason": None}


def position_size_dry_run(
    *,
    equity: float,
    entry_price: float,
    guardrails: dict[str, Any] | None = None,
) -> dict[str, Any]:
    g = guardrails or get_guardrails()
    trading = g.get("trading", {})
    risk_pct = trading.get("risk_per_trade_pct", 0.01)
    min_stop = trading.get("min_stop_distance_pct", 0.015)
    max_notional_pct = trading.get("max_notional_pct_equity", 0.05)

    stop_distance = entry_price * min_stop
    risk_amount = equity * risk_pct
    qty_by_risk = risk_amount / stop_distance if stop_distance else 0
    max_notional = equity * max_notional_pct
    qty_by_notional = max_notional / entry_price if entry_price else 0
    quantity = min(qty_by_risk, qty_by_notional)
    stop_price = entry_price * (1 - min_stop)
    take_profit_price = entry_price * (1 + min_stop * 2)

    return {
        "quantity": round(quantity, 8),
        "entry_price": entry_price,
        "stop_price": round(stop_price, 4),
        "take_profit_price": round(take_profit_price, 4),
        "notional": round(quantity * entry_price, 2),
    }
