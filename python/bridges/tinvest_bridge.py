"""T-Invest API bridge — HTTP wrapper for n8n (REST via httpx)."""

from __future__ import annotations

import os
from typing import Any

from bridges.tinvest_rest import TinvestRestClient


def _token(sandbox: bool) -> str:
    if sandbox:
        return os.environ.get("TINKOFF_SANDBOX_TOKEN", os.environ.get("TINKOFF_TOKEN", ""))
    return os.environ.get("TINKOFF_TOKEN", "")


def _client(sandbox: bool) -> TinvestRestClient | None:
    token = _token(sandbox)
    if not token:
        return None
    return TinvestRestClient(token, sandbox=sandbox)


def post_dca_order(
    *,
    ticker: str,
    amount_rub: float,
    sandbox: bool = True,
    dry_run: bool = True,
) -> dict[str, Any]:
    if dry_run:
        return {
            "status": "dry_run",
            "ticker": ticker,
            "amount_rub": amount_rub,
            "sandbox": sandbox,
            "message": "Order not sent — dry_run=True",
        }

    client = _client(sandbox)
    if client is None:
        return {
            "status": "error",
            "reject_reason": "missing_tinkoff_token",
            "message": "Set TINKOFF_SANDBOX_TOKEN or TINKOFF_TOKEN in environment",
        }

    try:
        instrument = client.find_instrument(ticker)
        if not instrument:
            return {"status": "error", "reject_reason": "instrument_not_found", "ticker": ticker}

        figi = str(instrument.get("figi", ""))
        if not figi:
            return {"status": "error", "reject_reason": "instrument_not_found", "ticker": ticker}

        account_id = client.get_account_id()
        price = client.get_last_price(figi)
        if price <= 0:
            return {"status": "error", "reject_reason": "no_price", "ticker": ticker, "figi": figi}

        lot_size = max(1, int(instrument.get("lot") or 1))
        lots = max(1, int(amount_rub / (price * lot_size)))
        order = client.post_market_buy(
            account_id=account_id,
            instrument_id=figi,
            lots=lots,
        )
        return {
            "status": "submitted",
            "order_id": order.get("orderId") or order.get("order_id"),
            "ticker": ticker,
            "figi": figi,
            "lots": lots,
            "lot_size": lot_size,
            "price": price,
            "sandbox": sandbox,
        }
    except Exception as exc:
        return {"status": "error", "reject_reason": "tinkoff_api_error", "message": str(exc)}


def get_portfolio_snapshot(sandbox: bool = True) -> dict[str, Any]:
    client = _client(sandbox)
    if client is None:
        return {"status": "error", "reject_reason": "missing_tinkoff_token"}

    try:
        account_id = client.get_account_id()
        positions = client.get_portfolio(account_id)
        return {
            "status": "ok",
            "account_id": account_id,
            "positions": positions,
            "sandbox": sandbox,
        }
    except Exception as exc:
        return {"status": "error", "reject_reason": "tinkoff_api_error", "message": str(exc)}


def check_tinvest_connection(sandbox: bool = True) -> dict[str, Any]:
    """Lightweight connectivity probe for smoke tests and admin status."""
    client = _client(sandbox)
    if client is None:
        return {
            "status": "skipped",
            "reject_reason": "missing_tinkoff_token",
            "sandbox": sandbox,
        }
    try:
        result = client.ping()
        return {**result, "status": "ok"}
    except Exception as exc:
        return {
            "status": "error",
            "reject_reason": "tinkoff_api_error",
            "message": str(exc),
            "sandbox": sandbox,
        }
