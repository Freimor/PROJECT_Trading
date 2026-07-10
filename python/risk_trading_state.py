"""Open positions, daily equity PnL, daily loss halt — for guardrails enforcement."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from binance_client import get_account_balances
from config_loader import load_config
from runtime_settings import get_runtime_value, set_runtime_value
from workflow_pnl_service import crypto_portfolio_total_usdt, moex_portfolio_total_rub

_STABLE_CRYPTO = frozenset({"USDT", "USDC", "BUSD", "FDUSD", "TUSD", "DAI"})
_DAILY_BASELINE_PREFIX = "daily_equity_baseline"
_DAILY_HALT_PREFIX = "daily_loss_halt"


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _daily_baseline_key(market: str) -> str:
    return f"{_DAILY_BASELINE_PREFIX}:{market}:{_today_utc()}"


def _daily_halt_key(market: str) -> str:
    return f"{_DAILY_HALT_PREFIX}:{market}:{_today_utc()}"


def _demo_flags() -> tuple[bool, bool]:
    crypto_cfg = load_config("crypto_config")
    sec_cfg = load_config("securities_config")
    testnet = crypto_cfg.get("env") == "testnet"
    sandbox = sec_cfg.get("env") == "sandbox"
    return testnet, sandbox


def current_equity(market: str) -> tuple[float | None, str]:
    testnet, sandbox = _demo_flags()
    if market == "crypto":
        return crypto_portfolio_total_usdt(testnet=testnet)
    if market == "securities":
        return moex_portfolio_total_rub(sandbox=sandbox)
    return None, "unknown_market"


def count_open_positions_crypto(*, testnet: bool | None = None) -> int:
    if testnet is None:
        testnet, _ = _demo_flags()
    count = 0
    for bal in get_account_balances(testnet=testnet):
        asset = str(bal.get("asset") or "").upper()
        if asset in _STABLE_CRYPTO:
            continue
        qty = float(bal.get("free", 0) or 0) + float(bal.get("locked", 0) or 0)
        if qty > 1e-8:
            count += 1
    return count


def count_open_positions_securities(*, sandbox: bool | None = None) -> int:
    if sandbox is None:
        _, sandbox = _demo_flags()
    try:
        from bridges.tinvest_bridge import get_portfolio_snapshot

        moex = get_portfolio_snapshot(sandbox=sandbox)
        if moex.get("status") != "ok":
            return 0
        return sum(
            1
            for p in moex.get("positions") or []
            if float(p.get("quantity", 0) or 0) > 0
        )
    except Exception:
        return 0


def count_open_positions(market: str) -> int:
    if market == "crypto":
        return count_open_positions_crypto()
    if market == "securities":
        return count_open_positions_securities()
    return 0


def get_daily_equity_pnl_pct(market: str) -> float | None:
    """Intraday equity change % vs first reading today (UTC)."""
    current, status = current_equity(market)
    if current is None or status not in ("ok", "empty"):
        return None

    key = _daily_baseline_key(market)
    baseline = get_runtime_value(key)
    if baseline is None:
        set_runtime_value(key, {"equity": current, "date": _today_utc()}, updated_by="system")
        return 0.0

    try:
        base_eq = float(baseline.get("equity", 0))
    except (TypeError, ValueError, AttributeError):
        base_eq = 0.0

    if base_eq <= 0:
        return 0.0
    return round((current - base_eq) / base_eq, 6)


def is_daily_halt_active(market: str) -> bool:
    return bool(get_runtime_value(_daily_halt_key(market)))


def activate_daily_halt(market: str, *, reason: str = "daily_loss_limit") -> None:
    set_runtime_value(
        _daily_halt_key(market),
        {"active": True, "reason": reason, "date": _today_utc()},
        updated_by="guardrails",
    )


def check_daily_loss_limit(market: str, limit_pct: float) -> dict[str, Any]:
    """Return guard result fragment; set halt if breached."""
    if is_daily_halt_active(market):
        return {
            "ok": False,
            "reject_reason": "daily_loss_halt",
            "daily_pnl_pct": get_daily_equity_pnl_pct(market),
        }

    pnl_pct = get_daily_equity_pnl_pct(market)
    if pnl_pct is not None and pnl_pct <= -abs(limit_pct):
        activate_daily_halt(market)
        return {
            "ok": False,
            "reject_reason": "daily_loss_limit",
            "daily_pnl_pct": pnl_pct,
        }

    return {"ok": True, "daily_pnl_pct": pnl_pct}


def risk_change_blocked_reason(market: str) -> str | None:
    if is_daily_halt_active(market):
        return "daily_loss_halt_active"
    if count_open_positions(market) > 0:
        return "open_positions"
    return None
