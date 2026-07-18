"""PNL % since workflow start — baseline captured on enable, cleared on stop."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from binance_client import get_account_balances
from runtime_settings import delete_runtime_value, get_runtime_meta, set_runtime_value

WORKFLOW_BASELINE_KEY = {
    "crypto": "crypto_workflow_baseline",
    "securities": "securities_workflow_baseline",
}

_STABLE = frozenset({"USDT", "USDC", "BUSD", "FDUSD"})
_PNL_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_PNL_CACHE_TTL_SEC = 45.0


def _credentials(testnet: bool) -> tuple[str, str, str]:
    from binance_client import _credentials as creds

    return creds(testnet)


def _pct_change(current: float | None, base: float | None) -> float | None:
    if current is None or base is None or base == 0:
        return None
    return round((current - base) / base * 100, 2)


def _direction(pct: float | None) -> str:
    if pct is None:
        return "flat"
    if pct > 0:
        return "up"
    if pct < 0:
        return "down"
    return "flat"


def crypto_portfolio_total_usdt(*, testnet: bool = True) -> tuple[float | None, str]:
    balances = get_account_balances(testnet=testnet)
    if not balances:
        return None, "empty"

    _, _, base_url = _credentials(testnet)
    prices: dict[str, float] = {}
    try:
        with httpx.Client(timeout=12) as client:
            resp = client.get(f"{base_url}/api/v3/ticker/price")
            if resp.status_code == 200:
                for row in resp.json():
                    sym = str(row.get("symbol", ""))
                    if sym.endswith("USDT"):
                        prices[sym] = float(row.get("price", 0) or 0)
    except Exception:
        prices = {}

    total = 0.0
    for row in balances:
        free = float(row.get("free", 0) or 0)
        locked = float(row.get("locked", 0) or 0)
        qty = free + locked
        if qty <= 1e-12:
            continue
        asset = str(row.get("asset") or "").upper()
        if asset in _STABLE:
            total += qty
            continue
        price = prices.get(f"{asset}USDT", 0.0)
        if price > 0:
            total += qty * price

    return round(total, 2), "ok"


def usdt_prices_map(*, testnet: bool = True) -> dict[str, float]:
    _, _, base_url = _credentials(testnet)
    prices: dict[str, float] = {}
    try:
        with httpx.Client(timeout=12) as client:
            resp = client.get(f"{base_url}/api/v3/ticker/price")
            if resp.status_code == 200:
                for row in resp.json():
                    sym = str(row.get("symbol", ""))
                    if sym.endswith("USDT"):
                        prices[sym] = float(row.get("price", 0) or 0)
    except Exception:
        pass
    return prices


def balance_usdt_value(asset: str, qty: float, *, prices: dict[str, float]) -> float:
    sym = str(asset or "").upper()
    if sym in _STABLE:
        return qty
    price = prices.get(f"{sym}USDT", 0.0)
    return qty * price if price > 0 else 0.0


def enrich_balances_usdt(
    rows: list[dict[str, Any]],
    *,
    testnet: bool = True,
) -> list[dict[str, Any]]:
    prices = usdt_prices_map(testnet=testnet)
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        total = float(item.get("total") or item.get("free") or 0)
        item["usdt_value"] = round(balance_usdt_value(str(item.get("asset", "")), total, prices=prices), 4)
        out.append(item)
    return out


def moex_portfolio_total_rub(*, sandbox: bool = True) -> tuple[float | None, str]:
    from bridges.tinvest_rest import TinvestRestClient
    import os

    token = (
        os.environ.get("TINKOFF_SANDBOX_TOKEN", "").strip()
        if sandbox
        else os.environ.get("TINKOFF_TOKEN", "").strip()
    )
    if not token:
        return None, "missing_token"
    try:
        client = TinvestRestClient(token, sandbox=sandbox, timeout=12.0)
        accounts = client.get_accounts()
        if not accounts:
            return None, "no_account"
        account_id = str(accounts[0]["id"])
        portfolio = client.get_portfolio(account_id)
        total = portfolio.get("total_amount")
        if total is None:
            return None, "empty"
        return round(float(total), 2), "ok"
    except Exception as exc:
        return None, str(exc)[:80]


def _demo_flags(operation_mode: str) -> tuple[bool, bool]:
    """Return (binance_testnet, tinvest_sandbox) for portfolio read."""
    if operation_mode == "live":
        return False, False
    return True, True


def _read_baseline(market: str) -> dict[str, Any] | None:
    meta = get_runtime_meta(WORKFLOW_BASELINE_KEY[market])
    if not meta or not meta.get("value"):
        return None
    try:
        data = json.loads(str(meta["value"]))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def capture_workflow_baseline(
    market: str,
    *,
    operator: str = "system",
    operation_mode: str = "demo",
) -> dict[str, Any]:
    if market not in WORKFLOW_BASELINE_KEY:
        raise ValueError(f"unknown_market: {market}")

    testnet, sandbox = _demo_flags(operation_mode)

    if market == "crypto":
        total, status = crypto_portfolio_total_usdt(testnet=testnet)
        currency = "USDT"
    else:
        total, status = moex_portfolio_total_rub(sandbox=sandbox)
        currency = "RUB"

    payload = {
        "total": total,
        "currency": currency,
        "status": status,
        "operation_mode": operation_mode,
        "testnet": testnet,
        "sandbox": sandbox,
        "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    set_runtime_value(
        WORKFLOW_BASELINE_KEY[market],
        json.dumps(payload, ensure_ascii=False),
        updated_by=operator,
    )
    return payload


def clear_workflow_baseline(market: str) -> None:
    if market in WORKFLOW_BASELINE_KEY:
        delete_runtime_value(WORKFLOW_BASELINE_KEY[market])


def get_workflow_pnl(
    market: str,
    *,
    active: bool,
    operation_mode: str,
) -> dict[str, Any]:
    if market not in WORKFLOW_BASELINE_KEY:
        raise ValueError(f"unknown_market: {market}")

    if not active:
        return {
            "status": "inactive",
            "pnl_pct": None,
            "direction": "flat",
            "currency": "USDT" if market == "crypto" else "RUB",
        }

    cache_key = f"{market}:{operation_mode}"
    cached = _PNL_CACHE.get(cache_key)
    if cached and (time.time() - cached[0]) < _PNL_CACHE_TTL_SEC:
        return cached[1]

    baseline = _read_baseline(market)
    if not baseline:
        try:
            baseline = capture_workflow_baseline(
                market,
                operator="pnl_backfill",
                operation_mode=operation_mode,
            )
        except Exception as exc:
            return {
                "status": "error",
                "message": str(exc),
                "pnl_pct": None,
                "direction": "flat",
                "currency": "USDT" if market == "crypto" else "RUB",
            }

    testnet = bool(baseline.get("testnet", operation_mode != "live"))
    sandbox = bool(baseline.get("sandbox", operation_mode != "live"))

    if market == "crypto":
        current, status = crypto_portfolio_total_usdt(testnet=testnet)
        currency = "USDT"
    else:
        current, status = moex_portfolio_total_rub(sandbox=sandbox)
        currency = "RUB"

    base_total = baseline.get("total")
    try:
        base_total_f = float(base_total) if base_total is not None else None
    except (TypeError, ValueError):
        base_total_f = None

    pnl_pct = _pct_change(current, base_total_f)
    result = {
        "status": status if current is not None else "unavailable",
        "pnl_pct": pnl_pct,
        "direction": _direction(pnl_pct),
        "current_total": current,
        "baseline_total": base_total_f,
        "currency": currency,
        "baseline_captured_at": baseline.get("captured_at"),
    }
    _PNL_CACHE[cache_key] = (time.time(), result)
    return result
