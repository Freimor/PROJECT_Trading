"""Unified Binance trading router — spot vs USDT-M futures."""

from __future__ import annotations

from typing import Any

from crypto_product import get_crypto_trading_product


def fetch_market_klines(
    symbol: str,
    interval: str,
    limit: int = 100,
    *,
    testnet: bool = True,
    end_time_ms: int | None = None,
    cfg: dict[str, Any] | None = None,
) -> list[Any]:
    product = get_crypto_trading_product(cfg=cfg)
    if product.get("is_futures"):
        from binance_futures_client import fetch_futures_klines

        return fetch_futures_klines(
            symbol, interval, limit, testnet=testnet, end_time_ms=end_time_ms
        )
    from binance_client import fetch_klines

    return fetch_klines(symbol, interval, limit, testnet=testnet, end_time_ms=end_time_ms)


def normalize_order_quantity(
    symbol: str,
    quantity: float,
    *,
    testnet: bool = True,
    market_order: bool = True,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    product = get_crypto_trading_product(cfg=cfg)
    if product.get("is_futures"):
        from binance_futures_client import normalize_futures_quantity

        return normalize_futures_quantity(symbol, quantity, testnet=testnet, market_order=market_order)
    from binance_client import normalize_order_quantity as spot_norm

    return spot_norm(symbol, quantity, testnet=testnet, market_order=market_order)


def place_market_order(
    *,
    symbol: str,
    side: str,
    quantity: float,
    testnet: bool = True,
    request_id: str | None = None,
    reduce_only: bool = False,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    product = get_crypto_trading_product(cfg=cfg)
    if product.get("is_futures"):
        from binance_futures_client import place_futures_market_order

        return place_futures_market_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            testnet=testnet,
            request_id=request_id,
            reduce_only=reduce_only,
            leverage=int(product.get("leverage") or 1),
            margin_mode=str(product.get("margin_mode") or "isolated"),
        )
    from binance_client import place_market_order as spot_order

    return spot_order(
        symbol=symbol,
        side=side,
        quantity=quantity,
        testnet=testnet,
        request_id=request_id,
    )


def get_market_price(symbol: str, *, testnet: bool = True, cfg: dict[str, Any] | None = None) -> float | None:
    product = get_crypto_trading_product(cfg=cfg)
    if product.get("is_futures"):
        from binance_futures_client import get_futures_ticker_price

        return get_futures_ticker_price(symbol, testnet=testnet)
    import httpx
    from binance_client import _credentials

    _, _, base = _credentials(testnet)
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{base}/api/v3/ticker/price", params={"symbol": symbol.upper()})
            if resp.status_code == 200:
                return float(resp.json().get("price", 0) or 0)
    except Exception:
        pass
    return None


def get_trading_equity(*, testnet: bool = True, cfg: dict[str, Any] | None = None) -> float:
    product = get_crypto_trading_product(cfg=cfg)
    if product.get("is_futures"):
        from binance_futures_client import get_futures_usdt_balance

        return get_futures_usdt_balance(testnet=testnet)
    from binance_client import get_account_balances
    from crypto_quote import wallet_quote_balance

    return wallet_quote_balance(get_account_balances(testnet=testnet))


def get_open_position(
    symbol: str,
    *,
    testnet: bool = True,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    product = get_crypto_trading_product(cfg=cfg)
    if not product.get("is_futures"):
        return None
    from binance_futures_client import get_futures_positions

    sym = symbol.upper()
    for row in get_futures_positions(testnet=testnet, symbol=sym):
        if row.get("symbol") == sym:
            return row
    return None
