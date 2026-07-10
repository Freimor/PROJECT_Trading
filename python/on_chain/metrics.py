"""On-chain metrics — hash rate ribbons, activity (macro context filter)."""

from __future__ import annotations

from typing import Any

import httpx

from config_loader import load_config

_BLOCKCHAIN_CHART = "https://api.blockchain.info/charts/{chart}?timespan={span}&format=json"


def _cfg() -> dict[str, Any]:
    return load_config("on_chain_config")


def _fetch_chart(chart: str, timespan: str = "1year") -> list[dict[str, Any]]:
    url = _BLOCKCHAIN_CHART.format(chart=chart, span=timespan)
    with httpx.Client(timeout=30) as client:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()
    return data.get("values", [])


def _sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def compute_on_chain_context() -> dict[str, Any]:
    """
    Hash ribbon signal (simplified Ketenci et al. 2024):
    bullish when short MA hash rate crosses above long MA.
    Reference: https://doi.org/10.1016/j.chaos.2023.114305
    """
    cfg = _cfg()
    short_p = int(cfg.get("hash_rate_ma_short", 30))
    long_p = int(cfg.get("hash_rate_ma_long", 60))

    hash_vals = _fetch_chart("hash-rate", cfg.get("timespan", "1year"))
    rates = [float(v["y"]) for v in hash_vals if v.get("y") is not None]
    tx_vals = _fetch_chart("n-transactions", cfg.get("timespan", "1year"))
    txs = [float(v["y"]) for v in tx_vals if v.get("y") is not None]

    ma_short = _sma(rates, short_p)
    ma_long = _sma(rates, long_p)
    hash_ribbon_bullish = ma_short is not None and ma_long is not None and ma_short > ma_long

    tx_ma = _sma(txs, 14)
    tx_recent = txs[-1] if txs else None
    activity_elevated = (
        tx_ma is not None and tx_recent is not None and tx_recent > tx_ma * 1.1
    )

    macro_bias = "neutral"
    if hash_ribbon_bullish and not activity_elevated:
        macro_bias = "bullish_onchain"
    elif not hash_ribbon_bullish:
        macro_bias = "bearish_onchain"

    allow_long = macro_bias != "bearish_onchain" or cfg.get("allow_long_in_bearish", False)

    return {
        "status": "ok",
        "hash_rate_latest": rates[-1] if rates else None,
        "hash_rate_ma_short": round(ma_short, 2) if ma_short else None,
        "hash_rate_ma_long": round(ma_long, 2) if ma_long else None,
        "hash_ribbon_bullish": hash_ribbon_bullish,
        "n_transactions_latest": tx_recent,
        "activity_elevated": activity_elevated,
        "macro_bias": macro_bias,
        "allow_long": allow_long,
        "reference": "https://doi.org/10.1016/j.chaos.2023.114305",
    }


def on_chain_filter_for_signal(*, side: str = "BUY") -> dict[str, Any]:
    ctx = compute_on_chain_context()
    if side.upper() == "BUY" and not ctx.get("allow_long"):
        return {
            "pass": False,
            "reject_reason": "on_chain_bearish",
            "context": ctx,
        }
    return {"pass": True, "context": ctx}
