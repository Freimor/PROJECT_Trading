"""Scalp kline fetch — testnet with mainnet metrics fallback when candles are flat."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from binance_trading import fetch_market_klines
from crypto_product import get_crypto_trading_product_for_trade
from indicators.technical import parse_binance_klines


@dataclass(frozen=True)
class ScalpKlinesResult:
    candles: list[dict[str, float]]
    source: str
    testnet_poor: bool
    quality_ok: bool
    fallback_attempted: bool


def klines_quality_settings(scalp_cfg: dict[str, Any]) -> dict[str, Any]:
    q = scalp_cfg.get("klines_quality") or {}
    return {
        "min_bars": int(q.get("min_bars", 30)),
        "flat_range_pct_max": float(q.get("flat_range_pct_max", 0.03)),
    }


def klines_quality_poor(
    candles: list[dict[str, float]],
    *,
    min_bars: int = 30,
    flat_range_pct_max: float = 0.03,
) -> bool:
    """True when candles are too flat for indicator/filter use (common on futures testnet)."""
    if len(candles) < min_bars:
        return True
    window = candles[-20:]
    closes = [c["c"] for c in window]
    if not closes or closes[-1] <= 0:
        return True
    unique_closes = len({round(x, 8) for x in closes})
    if unique_closes <= 2:
        return True
    highs = [c["h"] for c in candles[-10:]]
    lows = [c["l"] for c in candles[-10:]]
    mid = sum(closes[-10:]) / min(len(closes[-10:]), 10)
    if mid <= 0:
        return True
    range_pct = (max(highs) - min(lows)) / mid * 100
    return range_pct < flat_range_pct_max


def chart_klines_quality_poor(
    candles: list[dict[str, float]],
    *,
    min_bars: int = 30,
    flat_range_pct_max: float = 0.03,
    flat_bar_ratio_max: float = 0.85,
) -> bool:
    """Stricter quality for chart display — testnet often has flat historical bars."""
    if klines_quality_poor(candles, min_bars=min_bars, flat_range_pct_max=flat_range_pct_max):
        return True
    if not candles:
        return True
    flat = sum(
        1
        for c in candles
        if c.get("o") == c.get("h") == c.get("l") == c.get("c")
    )
    return flat / len(candles) >= flat_bar_ratio_max


def fetch_scalp_candles(
    *,
    symbol: str,
    timeframe: str,
    limit: int,
    testnet: bool,
    crypto_cfg: dict[str, Any],
    workflow_name: str = "",
    scalp_cfg: dict[str, Any],
    session_config: dict[str, Any] | None = None,
    mainnet_fallback: bool | None = None,
) -> ScalpKlinesResult:
    """
    Return parsed candles and quality metadata.
    Paper/testnet: optional mainnet fallback for signal metrics when testnet klines are flat.
    Orders still execute on testnet — only indicator input may come from mainnet.
    """
    quality = klines_quality_settings(scalp_cfg)
    min_bars = quality["min_bars"]
    flat_max = quality["flat_range_pct_max"]

    product = get_crypto_trading_product_for_trade(
        cfg=crypto_cfg,
        symbol=symbol,
        workflow_name=workflow_name or None,
        session_config=session_config,
    )
    raw = fetch_market_klines(
        symbol, timeframe, limit=limit, testnet=testnet, cfg={**crypto_cfg, **product}
    )
    candles = parse_binance_klines(raw)
    source = "testnet" if testnet else "mainnet"
    testnet_poor = bool(testnet and klines_quality_poor(candles, min_bars=min_bars, flat_range_pct_max=flat_max))
    fallback_attempted = False

    use_fallback = (
        bool(scalp_cfg.get("signal_klines_mainnet_fallback", True))
        if mainnet_fallback is None
        else bool(mainnet_fallback)
    )
    if testnet and use_fallback and testnet_poor:
        fallback_attempted = True
        try:
            raw_main = fetch_market_klines(
                symbol, timeframe, limit=limit, testnet=False, cfg={**crypto_cfg, **product}
            )
            candles_main = parse_binance_klines(raw_main)
            if not klines_quality_poor(candles_main, min_bars=min_bars, flat_range_pct_max=flat_max):
                return ScalpKlinesResult(
                    candles=candles_main,
                    source="mainnet_metrics_fallback",
                    testnet_poor=True,
                    quality_ok=True,
                    fallback_attempted=True,
                )
        except Exception:
            pass

    quality_ok = len(candles) >= min_bars and not klines_quality_poor(
        candles, min_bars=min_bars, flat_range_pct_max=flat_max
    )
    if not quality_ok:
        source = "unusable"
    return ScalpKlinesResult(
        candles=candles,
        source=source,
        testnet_poor=testnet_poor,
        quality_ok=quality_ok,
        fallback_attempted=fallback_attempted,
    )
