"""Guardrails enforcement (G1–G12 subset)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from config_loader import load_config
from effective_config import get_guardrails
from market_llm_config import get_market_llm_config
from risk_profile_service import apply_risk_profile_to_guardrails, get_max_open_positions
from risk_trading_state import check_daily_loss_limit, count_open_positions
from workflow_universe_service import enabled_symbols_for_workflow


def _moex_session_ok(guardrails: dict[str, Any]) -> bool:
    session = guardrails.get("session", {})
    tz = ZoneInfo(session.get("timezone", "Europe/Moscow"))
    now = datetime.now(tz)
    if now.weekday() >= 5:
        return False
    start = session.get("moex_start_hour", 10)
    end = session.get("moex_end_hour", 19)
    return start <= now.hour < end


def _effective_allowlist(
    market: str,
    symbols_cfg: dict[str, Any],
    workflow_name: str | None,
) -> list[str]:
    if workflow_name:
        try:
            enabled = enabled_symbols_for_workflow(workflow_name)
            if enabled:
                return [str(s).upper() for s in enabled]
        except ValueError:
            pass

    key = "crypto_whitelist" if market == "crypto" else "moex_whitelist"
    return [str(s).upper() for s in symbols_cfg.get(key, [])]


def _held_position_symbols(market: str) -> set[str]:
    if market == "crypto":
        from binance_client import get_account_balances
        from risk_trading_state import _STABLE_CRYPTO

        testnet = load_config("crypto_config").get("env") == "testnet"
        held: set[str] = set()
        for bal in get_account_balances(testnet=testnet):
            asset = str(bal.get("asset") or "").upper()
            if asset in _STABLE_CRYPTO:
                continue
            qty = float(bal.get("free", 0) or 0) + float(bal.get("locked", 0) or 0)
            if qty > 1e-8:
                held.add(f"{asset}USDT")
        return held

    try:
        from bridges.tinvest_bridge import get_portfolio_snapshot

        sandbox = load_config("securities_config").get("env") == "sandbox"
        moex = get_portfolio_snapshot(sandbox=sandbox)
        if moex.get("status") != "ok":
            return set()
        return {
            str(p.get("ticker") or "").upper()
            for p in moex.get("positions") or []
            if float(p.get("quantity", 0) or 0) > 0
        }
    except Exception:
        return set()


def enforce_guardrails(
    *,
    market: str,
    symbol: str | None,
    llm_decision: dict[str, Any] | None,
    env: str,
    guardrails: dict[str, Any] | None = None,
    workflow_name: str | None = None,
) -> dict[str, Any]:
    base = guardrails or get_guardrails()
    g = apply_risk_profile_to_guardrails(base, market)
    trading = g.get("trading", {})
    symbols = g.get("symbols", {})
    llm_cfg = get_market_llm_config(market)

    if trading.get("kill_switch"):
        return {"pass": False, "reject_reason": "kill_switch_active"}

    if env == "live" and trading.get("live_requires_manual_flag"):
        return {"pass": False, "reject_reason": "live_requires_manual_flag"}

    daily_limit = float(trading.get("daily_loss_limit_pct", 0.03))
    daily_check = check_daily_loss_limit(market, daily_limit)
    if not daily_check.get("ok"):
        return {
            "pass": False,
            "reject_reason": daily_check.get("reject_reason"),
            "daily_pnl_pct": daily_check.get("daily_pnl_pct"),
        }

    max_open = get_max_open_positions(market, trading)
    open_count = count_open_positions(market)
    if symbol and open_count >= max_open:
        sym = symbol.upper()
        if sym not in _held_position_symbols(market):
            return {
                "pass": False,
                "reject_reason": "max_open_positions",
                "open_positions": open_count,
                "max_open_positions": max_open,
            }

    if symbol:
        wl = _effective_allowlist(market, symbols, workflow_name)
        if wl and symbol.upper() not in wl:
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
        if action == "reject":
            reason = (
                llm_decision.get("reject_reason")
                or llm_decision.get("reasoning")
                or "llm_rejected_no_reason"
            )
            return {"pass": False, "reject_reason": reason}
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
    market: str = "crypto",
) -> dict[str, Any]:
    base = guardrails or get_guardrails()
    g = apply_risk_profile_to_guardrails(base, market)
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
        "risk_profile_id": g.get("active_risk_profile_id"),
    }
