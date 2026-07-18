"""Binance USDT-M Futures API helpers (testnet + live)."""

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


def _credentials(testnet: bool) -> tuple[str, str, str]:
    if testnet:
        key = os.environ.get("BINANCE_FUTURES_TESTNET_API_KEY") or os.environ.get(
            "BINANCE_TESTNET_API_KEY", ""
        )
        secret = os.environ.get("BINANCE_FUTURES_TESTNET_API_SECRET") or os.environ.get(
            "BINANCE_TESTNET_API_SECRET", ""
        )
        base = "https://testnet.binancefuture.com"
    else:
        key = os.environ.get("BINANCE_FUTURES_API_KEY") or os.environ.get("BINANCE_API_KEY", "")
        secret = os.environ.get("BINANCE_FUTURES_API_SECRET") or os.environ.get(
            "BINANCE_API_SECRET", ""
        )
        base = "https://fapi.binance.com"
    return key, secret, base


def _sign(params: dict[str, Any], secret: str) -> str:
    query = urlencode(params)
    return hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()


def _signed_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    testnet: bool = True,
    timeout: float = 30,
) -> dict[str, Any]:
    key, secret, base = _credentials(testnet)
    if not key or not secret:
        return {
            "status": "error",
            "reject_reason": "missing_api_credentials",
            "message": "Set BINANCE_FUTURES_TESTNET_API_KEY/SECRET (or BINANCE_TESTNET_* fallback)",
        }
    payload: dict[str, Any] = dict(params or {})
    payload["timestamp"] = int(time.time() * 1000)
    payload["signature"] = _sign(payload, secret)
    url = f"{base}{path}"
    with httpx.Client(timeout=timeout) as client:
        if method.upper() == "GET":
            resp = client.get(url, params=payload, headers={"X-MBX-APIKEY": key})
        else:
            resp = client.post(url, params=payload, headers={"X-MBX-APIKEY": key})
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    if isinstance(data, dict):
        data["http_status"] = resp.status_code
    return data if isinstance(data, dict) else {"data": data, "http_status": resp.status_code}


def _unwrap_list_response(data: Any) -> list[Any]:
    """Binance list endpoints are wrapped as {data: [...], http_status} by _signed_request."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        inner = data.get("data")
        if isinstance(inner, list):
            return inner
    return []


def fetch_futures_klines(
    symbol: str,
    interval: str = "5m",
    limit: int = 100,
    *,
    testnet: bool = True,
    end_time_ms: int | None = None,
) -> list[Any]:
    _, _, base = _credentials(testnet)
    params: dict[str, Any] = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
    if end_time_ms is not None:
        params["endTime"] = end_time_ms
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{base}/fapi/v1/klines", params=params)
        resp.raise_for_status()
        return resp.json()


@lru_cache(maxsize=128)
def _exchange_info(symbol: str, testnet: bool) -> dict[str, Any]:
    _, _, base = _credentials(testnet)
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{base}/fapi/v1/exchangeInfo", params={"symbol": symbol.upper()})
        resp.raise_for_status()
        data = resp.json()
    symbols = data.get("symbols") or []
    if not symbols:
        raise ValueError(f"unknown_futures_symbol: {symbol}")
    return dict(symbols[0])


def _filter_map(symbol_info: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(f.get("filterType")): dict(f) for f in symbol_info.get("filters") or []}


def normalize_futures_quantity(
    symbol: str,
    quantity: float,
    *,
    testnet: bool = True,
    market_order: bool = True,
) -> dict[str, Any]:
    info = _exchange_info(symbol.upper(), testnet)
    filters = _filter_map(info)
    lot = filters.get("MARKET_LOT_SIZE") if market_order else filters.get("LOT_SIZE")
    lot = lot or filters.get("LOT_SIZE") or {}
    step = Decimal(str(lot.get("stepSize") or "0"))
    min_qty = Decimal(str(lot.get("minQty") or "0"))
    if step <= 0:
        step = Decimal("0.001")
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
    if not result["valid"]:
        result["reject_reason"] = "quantity_below_min_lot"
    return result


def _quantity_param(quantity: Decimal, step: Decimal) -> str:
    precision = max(0, -step.as_tuple().exponent)
    return f"{quantity:.{precision}f}"


def ensure_futures_leverage(
    symbol: str,
    leverage: int,
    *,
    testnet: bool = True,
) -> dict[str, Any]:
    lev = max(1, min(int(leverage), 125))
    return _signed_request(
        "POST",
        "/fapi/v1/leverage",
        params={"symbol": symbol.upper(), "leverage": lev},
        testnet=testnet,
    )


def ensure_futures_margin_type(
    symbol: str,
    margin_type: str,
    *,
    testnet: bool = True,
) -> dict[str, Any]:
    mt = "ISOLATED" if str(margin_type).lower() == "isolated" else "CROSSED"
    return _signed_request(
        "POST",
        "/fapi/v1/marginType",
        params={"symbol": symbol.upper(), "marginType": mt},
        testnet=testnet,
    )


def place_futures_market_order(
    *,
    symbol: str,
    side: str,
    quantity: float,
    testnet: bool = True,
    request_id: str | None = None,
    reduce_only: bool = False,
    leverage: int | None = None,
    margin_mode: str | None = None,
) -> dict[str, Any]:
    if leverage and leverage > 1:
        ensure_futures_leverage(symbol, leverage, testnet=testnet)
    if margin_mode:
        ensure_futures_margin_type(symbol, margin_mode, testnet=testnet)

    qty_norm = normalize_futures_quantity(symbol, quantity, testnet=testnet, market_order=True)
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
        "symbol": symbol.upper(),
        "side": side.upper(),
        "type": "MARKET",
        "quantity": _quantity_param(Decimal(str(normalized_qty)), qty_step),
    }
    if reduce_only:
        params["reduceOnly"] = "true"
    if request_id:
        params["newClientOrderId"] = request_id[:36]

    data = _signed_request("POST", "/fapi/v1/order", params=params, testnet=testnet)
    if qty_norm.get("requested_quantity") != normalized_qty and isinstance(data, dict):
        data["quantity_normalization"] = qty_norm
    data["product"] = "usdt_futures"
    return data


def get_futures_position_risk(
    *,
    testnet: bool = True,
    symbol: str | None = None,
) -> list[dict[str, Any]]:
    """Raw position risk rows from Binance (includes zero-size symbols)."""
    params: dict[str, Any] = {}
    if symbol:
        params["symbol"] = symbol.upper()
    data = _signed_request("GET", "/fapi/v2/positionRisk", params=params, testnet=testnet)
    rows = _unwrap_list_response(data)
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        amt = float(row.get("positionAmt") or 0)
        maint_margin = float(row.get("maintMargin") or 0)
        margin_balance = float(row.get("isolatedMargin") or row.get("initialMargin") or 0)
        margin_ratio = float(row.get("marginRatio") or 0)
        if margin_ratio <= 0 and margin_balance > 0 and maint_margin > 0:
            margin_ratio = maint_margin / margin_balance
        out.append(
            {
                "symbol": str(row.get("symbol", "")).upper(),
                "position_amt": amt,
                "entry_price": float(row.get("entryPrice") or 0),
                "mark_price": float(row.get("markPrice") or 0),
                "unrealized_pnl": float(row.get("unRealizedProfit") or 0),
                "leverage": int(float(row.get("leverage") or 1)),
                "margin_type": row.get("marginType"),
                "position_side": "long" if amt > 0 else "short" if amt < 0 else "flat",
                "liquidation_price": float(row.get("liquidationPrice") or 0),
                "maint_margin": maint_margin,
                "margin_balance": margin_balance,
                "margin_ratio": round(margin_ratio, 6),
            }
        )
    return out


def get_futures_positions(*, testnet: bool = True, symbol: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in get_futures_position_risk(testnet=testnet, symbol=symbol):
        if abs(float(row.get("position_amt") or 0)) < 1e-12:
            continue
        out.append(
            {
                "symbol": row["symbol"],
                "position_amt": row["position_amt"],
                "entry_price": row["entry_price"],
                "mark_price": row["mark_price"],
                "unrealized_pnl": row["unrealized_pnl"],
                "leverage": row["leverage"],
                "margin_type": row["margin_type"],
                "position_side": row["position_side"],
            }
        )
    return out


def get_futures_account(*, testnet: bool = True) -> dict[str, Any]:
    data = _signed_request("GET", "/fapi/v2/account", testnet=testnet)
    if not isinstance(data, dict):
        return {"status": "error", "reject_reason": "invalid_account_response"}
    wallet = float(data.get("totalWalletBalance") or 0)
    margin_balance = float(data.get("totalMarginBalance") or wallet)
    maint = float(data.get("totalMaintMargin") or 0)
    ratio = round(maint / margin_balance, 6) if margin_balance > 0 else 0.0
    return {
        "status": "ok",
        "total_wallet_balance": wallet,
        "total_margin_balance": margin_balance,
        "total_maint_margin": maint,
        "total_unrealized_profit": float(data.get("totalUnrealizedProfit") or 0),
        "margin_ratio": ratio,
        "can_trade": bool(data.get("canTrade", True)),
        "http_status": data.get("http_status"),
    }


def get_futures_force_orders(
    *,
    testnet: bool = True,
    symbol: str | None = None,
    auto_close_type: str = "LIQUIDATION",
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "autoCloseType": auto_close_type.upper(),
        "limit": max(1, min(int(limit), 100)),
    }
    if symbol:
        params["symbol"] = symbol.upper()
    if start_time_ms is not None:
        params["startTime"] = int(start_time_ms)
    if end_time_ms is not None:
        params["endTime"] = int(end_time_ms)
    data = _signed_request("GET", "/fapi/v1/forceOrders", params=params, testnet=testnet)
    rows = _unwrap_list_response(data)
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "order_id": int(row.get("orderId") or 0),
                "symbol": str(row.get("symbol") or "").upper(),
                "side": str(row.get("side") or "").upper(),
                "status": str(row.get("status") or ""),
                "auto_close_type": str(row.get("autoCloseType") or auto_close_type).upper(),
                "price": float(row.get("price") or 0),
                "avg_price": float(row.get("avgPrice") or 0),
                "orig_qty": float(row.get("origQty") or 0),
                "executed_qty": float(row.get("executedQty") or 0),
                "time_ms": int(row.get("time") or 0),
                "update_time_ms": int(row.get("updateTime") or row.get("time") or 0),
            }
        )
    return out


def get_futures_usdt_balance(*, testnet: bool = True) -> float:
    data = _signed_request("GET", "/fapi/v2/balance", testnet=testnet)
    for row in _unwrap_list_response(data):
        if str(row.get("asset") or "").upper() == "USDT":
            return float(
                row.get("availableBalance") or row.get("balance") or row.get("crossWalletBalance") or 0
            )
    return 0.0


def get_futures_margin_equity(*, testnet: bool = True) -> float:
    """Total margin balance in USDT terms (includes USDC/BTC collateral when enabled)."""
    data = _signed_request("GET", "/fapi/v2/account", testnet=testnet)
    if not isinstance(data, dict):
        return 0.0
    margin = float(data.get("totalMarginBalance") or data.get("totalWalletBalance") or 0)
    return margin


def get_futures_ticker_price(symbol: str, *, testnet: bool = True) -> float | None:
    _, _, base = _credentials(testnet)
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{base}/fapi/v1/ticker/price",
                params={"symbol": symbol.upper()},
            )
            if resp.status_code == 200:
                return float(resp.json().get("price", 0) or 0)
    except Exception:
        pass
    return None
