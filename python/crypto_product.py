"""Crypto trading product — spot vs USDT-M futures (config + env + runtime)."""

from __future__ import annotations

import json
from typing import Any, Literal

from config_loader import load_config
from effective_config import get_config_effective
from runtime_settings import delete_runtime_value, get_runtime_meta

MarketType = Literal["spot", "usdt_futures"]
PositionSide = Literal["long", "short"]

RUNTIME_TRADING_PRODUCT_KEY = "crypto_trading_product"


def yaml_trading_product() -> dict[str, Any]:
    return dict(get_config_effective("crypto_config").get("trading_product") or {})


def get_trading_product_runtime_override() -> dict[str, Any] | None:
    meta = get_runtime_meta(RUNTIME_TRADING_PRODUCT_KEY) or {}
    raw = meta.get("value")
    if raw is None:
        return None
    try:
        data = json.loads(str(raw))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def clear_trading_product_runtime_override() -> None:
    delete_runtime_value(RUNTIME_TRADING_PRODUCT_KEY)


def get_crypto_trading_product(
    *,
    cfg: dict[str, Any] | None = None,
    session_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Effective product settings (YAML + runtime override + per-instance session)."""
    crypto = cfg or get_config_effective("crypto_config")
    tp = dict(crypto.get("trading_product") or {})
    override = get_trading_product_runtime_override()
    if override:
        tp.update({k: v for k, v in override.items() if v is not None})

    if session_config:
        for key in ("market_type", "allow_short", "leverage", "margin_mode"):
            if session_config.get(key) is not None:
                tp[key] = session_config[key]

    market_type = str(tp.get("market_type") or "spot").strip().lower()
    if market_type not in ("spot", "usdt_futures"):
        market_type = "spot"
    max_leverage = int(tp.get("max_leverage") or 5)
    if market_type == "spot":
        leverage = 1
        allow_short = False
    else:
        leverage = int(tp.get("leverage") or 1)
        leverage = max(1, min(leverage, max_leverage))
        allow_short = bool(tp.get("allow_short", False))
    margin_mode = str(tp.get("margin_mode") or "isolated").lower()
    if margin_mode not in ("isolated", "cross"):
        margin_mode = "isolated"
    return {
        "market_type": market_type,
        "is_futures": market_type == "usdt_futures",
        "margin_mode": margin_mode,
        "leverage": leverage,
        "max_leverage": max_leverage,
        "allow_short": allow_short,
        "position_mode": str(tp.get("position_mode") or "one_way").lower(),
        "use_reduce_only_on_exit": bool(tp.get("use_reduce_only_on_exit", True)),
        "runtime_override": override is not None,
        "yaml_default": dict(load_config("crypto_config").get("trading_product") or {}),
    }


def is_futures_trading(
    *,
    cfg: dict[str, Any] | None = None,
    session_config: dict[str, Any] | None = None,
) -> bool:
    return bool(get_crypto_trading_product(cfg=cfg, session_config=session_config).get("is_futures"))


def cfg_for_symbol_trade(
    cfg: dict[str, Any] | None,
    *,
    symbol: str,
    workflow_name: str | None = None,
) -> dict[str, Any]:
    """Merge per-automation trading_product into config for orders/klines."""
    base = dict(cfg or get_config_effective("crypto_config"))
    product = get_crypto_trading_product_for_trade(
        cfg=base,
        symbol=symbol,
        workflow_name=workflow_name,
    )
    tp = dict(base.get("trading_product") or {})
    for key in (
        "market_type",
        "allow_short",
        "leverage",
        "margin_mode",
        "position_mode",
        "use_reduce_only_on_exit",
    ):
        if product.get(key) is not None:
            tp[key] = product[key]
    base["trading_product"] = tp
    return base


def get_crypto_trading_product_for_trade(
    *,
    cfg: dict[str, Any] | None = None,
    symbol: str | None = None,
    workflow_name: str | None = None,
    session_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve trading product for a symbol/workflow (automation instance session)."""
    sc = session_config
    if sc is None and symbol and workflow_name:
        from workflow_session_config_service import get_workflow_session_config

        sc = get_workflow_session_config("crypto", symbol=symbol, workflow_name=workflow_name)
    return get_crypto_trading_product(cfg=cfg, session_config=sc if sc else None)


def order_side_for_entry(position_side: PositionSide) -> str:
    return "BUY" if position_side == "long" else "SELL"


def order_side_for_exit(position_side: PositionSide) -> str:
    return "SELL" if position_side == "long" else "BUY"
