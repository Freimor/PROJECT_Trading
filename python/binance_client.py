"""Binance Spot API helpers."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from decimal import Decimal, ROUND_DOWN
from functools import lru_cache
from typing import Any
from urllib.parse import urlencode

import httpx

_NETWORK_ERRORS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.NetworkError,
)


class BinanceNetworkError(RuntimeError):
    """Binance HTTP request failed after retries (DNS, TLS, timeout)."""


def _get_with_retry(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30,
    retries: int = 3,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(max(1, retries)):
        try:
            with httpx.Client(timeout=timeout) as client:
                return client.get(url, params=params, headers=headers)
        except _NETWORK_ERRORS as exc:
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(0.4 * (attempt + 1))
    raise BinanceNetworkError(str(last_exc or "binance_unreachable")) from last_exc


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
    resp = _get_with_retry(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


@lru_cache(maxsize=4)
def list_spot_exchange_symbols(testnet: bool) -> tuple[dict[str, Any], ...]:
    """All SPOT symbols from Binance exchangeInfo (cached per env)."""
    _, _, base = _credentials(testnet)
    with httpx.Client(timeout=120) as client:
        resp = client.get(f"{base}/api/v3/exchangeInfo")
        resp.raise_for_status()
        rows = resp.json().get("symbols") or []
    return tuple(dict(r) for r in rows if isinstance(r, dict))


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


@lru_cache(maxsize=128)
def _exchange_info(symbol: str, testnet: bool) -> dict[str, Any]:
    _, _, base = _credentials(testnet)
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{base}/api/v3/exchangeInfo", params={"symbol": symbol})
        resp.raise_for_status()
        data = resp.json()
    symbols = data.get("symbols") or []
    if not symbols:
        raise ValueError(f"unknown_symbol: {symbol}")
    return dict(symbols[0])


def _filter_map(symbol_info: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(f.get("filterType")): dict(f) for f in symbol_info.get("filters") or []}


def _lot_filter(filters: dict[str, dict[str, Any]], *, market_order: bool) -> dict[str, Any]:
    if market_order:
        market = filters.get("MARKET_LOT_SIZE") or {}
        step = Decimal(str(market.get("stepSize", "0")))
        if step > 0:
            return market
    return filters.get("LOT_SIZE") or {}


def normalize_order_quantity(
    symbol: str,
    quantity: float,
    *,
    testnet: bool = True,
    market_order: bool = True,
) -> dict[str, Any]:
    """Round quantity down to Binance LOT_SIZE / MARKET_LOT_SIZE step."""
    info = _exchange_info(symbol.upper(), testnet)
    filters = _filter_map(info)
    lot = _lot_filter(filters, market_order=market_order)
    step = Decimal(str(lot.get("stepSize") or "0"))
    min_qty = Decimal(str(lot.get("minQty") or "0"))
    if step <= 0:
        step = Decimal("0.00000001")

    raw = Decimal(str(quantity))
    steps = (raw / step).to_integral_value(rounding=ROUND_DOWN)
    normalized = steps * step

    result: dict[str, Any] = {
        "symbol": symbol.upper(),
        "requested_quantity": quantity,
        "normalized_quantity": float(normalized),
        "step_size": str(step),
        "min_qty": str(min_qty),
        "valid": normalized >= min_qty and normalized > 0,
    }

    notional_filter = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL") or {}
    min_notional = notional_filter.get("minNotional")
    if min_notional is not None:
        result["min_notional"] = str(min_notional)

    if not result["valid"]:
        result["reject_reason"] = "quantity_below_min_lot"
    return result


def _quantity_param(quantity: Decimal, step: Decimal) -> str:
    precision = max(0, -step.as_tuple().exponent)
    return f"{quantity:.{precision}f}"


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

    qty_norm = normalize_order_quantity(symbol, quantity, testnet=testnet, market_order=True)
    if not qty_norm.get("valid"):
        return {
            "status": "error",
            "reject_reason": qty_norm.get("reject_reason", "invalid_quantity"),
            "msg": "Quantity below exchange min lot after normalization",
            "http_status": 400,
            "quantity_normalization": qty_norm,
        }

    normalized_qty = float(qty_norm["normalized_quantity"])
    qty_step = Decimal(str(qty_norm["step_size"]))
    params: dict[str, Any] = {
        "symbol": symbol,
        "side": side.upper(),
        "type": "MARKET",
        "quantity": _quantity_param(Decimal(str(normalized_qty)), qty_step),
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
    if qty_norm.get("requested_quantity") != normalized_qty:
        data["quantity_normalization"] = qty_norm
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
    try:
        resp = _get_with_retry(
            f"{base}/api/v3/account",
            params=params,
            headers={"X-MBX-APIKEY": key},
            timeout=30,
        )
    except BinanceNetworkError:
        raise
    if resp.status_code != 200:
        return []
    return resp.json().get("balances", [])
