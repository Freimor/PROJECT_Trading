"""Binance Spot API helpers."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any
from urllib.parse import urlencode

import httpx


def _credentials(testnet: bool) -> tuple[str, str, str]:
    if testnet:
        key = os.environ.get("BINANCE_TESTNET_API_KEY", "")
        secret = os.environ.get("BINANCE_TESTNET_API_SECRET", "")
        base = "https://testnet.binance.vision"
    else:
        key = os.environ.get("BINANCE_API_KEY", "")
        secret = os.environ.get("BINANCE_API_SECRET", "")
        base = "https://api.binance.com"
    return key, secret, base


def fetch_klines(
    symbol: str,
    interval: str = "4h",
    limit: int = 100,
    testnet: bool = False,
    end_time_ms: int | None = None,
) -> list[Any]:
    _, _, base = _credentials(testnet)
    url = f"{base}/api/v3/klines"
    params: dict[str, Any] = {"symbol": symbol, "interval": interval, "limit": limit}
    if end_time_ms is not None:
        params["endTime"] = end_time_ms
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


def fetch_klines_history(
    symbol: str,
    interval: str = "4h",
    *,
    bars: int = 500,
    testnet: bool = False,
) -> list[Any]:
    """Paginate klines backwards for backtesting (max ~1000 per request)."""
    all_rows: list[Any] = []
    end_ms: int | None = None
    remaining = bars
    while remaining > 0:
        batch = min(remaining, 1000)
        rows = fetch_klines(symbol, interval, limit=batch, testnet=testnet, end_time_ms=end_ms)
        if not rows:
            break
        all_rows = rows + all_rows
        end_ms = int(rows[0][0]) - 1
        remaining -= len(rows)
        if len(rows) < batch:
            break
    return all_rows[-bars:] if len(all_rows) > bars else all_rows


def _sign(params: dict[str, Any], secret: str) -> str:
    query = urlencode(params)
    return hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()


def place_market_order(
    *,
    symbol: str,
    side: str,
    quantity: float,
    testnet: bool = True,
    request_id: str | None = None,
) -> dict[str, Any]:
    key, secret, base = _credentials(testnet)
    if not key or not secret:
        return {
            "status": "error",
            "reject_reason": "missing_api_credentials",
            "message": "Set BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_API_SECRET",
        }

    params: dict[str, Any] = {
        "symbol": symbol,
        "side": side.upper(),
        "type": "MARKET",
        "quantity": quantity,
        "timestamp": int(time.time() * 1000),
    }
    if request_id:
        params["newClientOrderId"] = request_id[:36]
    params["signature"] = _sign(params, secret)

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{base}/api/v3/order",
            params=params,
            headers={"X-MBX-APIKEY": key},
        )
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    data["http_status"] = resp.status_code
    return data


def get_open_orders(symbol: str | None = None, testnet: bool = True) -> list[dict]:
    key, secret, base = _credentials(testnet)
    if not key or not secret:
        return []
    params: dict[str, Any] = {"timestamp": int(time.time() * 1000)}
    if symbol:
        params["symbol"] = symbol
    params["signature"] = _sign(params, secret)
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{base}/api/v3/openOrders",
            params=params,
            headers={"X-MBX-APIKEY": key},
        )
    if resp.status_code != 200:
        return []
    return resp.json()


def get_account_balances(testnet: bool = True) -> list[dict]:
    key, secret, base = _credentials(testnet)
    if not key or not secret:
        return []
    params: dict[str, Any] = {"timestamp": int(time.time() * 1000)}
    params["signature"] = _sign(params, secret)
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{base}/api/v3/account",
            params=params,
            headers={"X-MBX-APIKEY": key},
        )
    if resp.status_code != 200:
        return []
    return resp.json().get("balances", [])
