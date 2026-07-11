"""Runtime crypto workflow settings (quote stablecoin, trading product)."""

from __future__ import annotations

import json
from typing import Any

from crypto_product import (
    RUNTIME_TRADING_PRODUCT_KEY,
    clear_trading_product_runtime_override,
    get_crypto_trading_product,
    yaml_trading_product,
)
from crypto_quote import (
    RUNTIME_QUOTE_KEY,
    allowed_quote_assets,
    get_crypto_quote_asset,
    yaml_quote_asset,
)
from runtime_settings import delete_runtime_value, get_runtime_meta, set_runtime_value


def get_crypto_workflow_settings() -> dict[str, Any]:
    quote_meta = get_runtime_meta(RUNTIME_QUOTE_KEY) or {}
    quote_runtime = quote_meta.get("value") is not None
    quote = get_crypto_quote_asset()
    product = get_crypto_trading_product()
    return {
        "quote_asset": quote,
        "allowed_quote_assets": allowed_quote_assets(),
        "yaml_default": yaml_quote_asset(),
        "runtime_override": quote_runtime,
        "trading_product": product,
    }


def set_crypto_quote_asset(quote_asset: str, *, operator: str = "web:operator") -> dict[str, Any]:
    q = str(quote_asset).strip().upper()
    allowed = allowed_quote_assets()
    if q not in allowed:
        raise ValueError(f"invalid_quote_asset: {q}")
    set_runtime_value(RUNTIME_QUOTE_KEY, q, updated_by=operator)
    return {"status": "ok", **get_crypto_workflow_settings()}


def reset_crypto_quote_asset(*, operator: str = "web:operator") -> dict[str, Any]:
    delete_runtime_value(RUNTIME_QUOTE_KEY)
    return {"status": "ok", **get_crypto_workflow_settings(), "operator": operator}


def set_crypto_trading_product(
    *,
    market_type: str,
    allow_short: bool = False,
    leverage: int | None = None,
    margin_mode: str | None = None,
    operator: str = "web:operator",
) -> dict[str, Any]:
    mt = str(market_type or "spot").strip().lower()
    if mt not in ("spot", "usdt_futures"):
        raise ValueError(f"invalid_market_type: {market_type}")

    yaml_tp = yaml_trading_product()
    max_lev = int(yaml_tp.get("max_leverage") or 5)
    lev = int(leverage if leverage is not None else yaml_tp.get("leverage") or 1)
    lev = max(1, min(lev, max_lev))

    mm = str(margin_mode or yaml_tp.get("margin_mode") or "isolated").lower()
    if mm not in ("isolated", "cross"):
        raise ValueError(f"invalid_margin_mode: {margin_mode}")

    short_ok = bool(allow_short) and mt == "usdt_futures"
    payload = {
        "market_type": mt,
        "allow_short": short_ok,
        "leverage": lev,
        "margin_mode": mm,
    }
    set_runtime_value(RUNTIME_TRADING_PRODUCT_KEY, json.dumps(payload, ensure_ascii=False), updated_by=operator)
    return {"status": "ok", **get_crypto_workflow_settings()}


def reset_crypto_trading_product(*, operator: str = "web:operator") -> dict[str, Any]:
    clear_trading_product_runtime_override()
    return {"status": "ok", **get_crypto_workflow_settings(), "operator": operator}
