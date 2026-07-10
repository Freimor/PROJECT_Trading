"""Crypto retail guard — BIS WP 1049 / Bulletin 69 adverse conditions."""

from __future__ import annotations

from typing import Any

from config_loader import load_config


def _cfg() -> dict[str, Any]:
    return load_config("crypto_config").get("retail_guard", {})


def check_retail_guard(
    *,
    indicators: dict[str, Any],
    candles: list[dict[str, float]] | None = None,
) -> dict[str, Any]:
    """
    Block long entries when conditions match retail FOMO / whale distribution patterns.
    Based on BIS: retail enters at peaks; sophisticated players sell into strength.
    """
    cfg = _cfg()
    if not cfg.get("enabled", True):
        return {"pass": True, "flags": [], "reference": "https://www.bis.org/publ/work1049.htm"}

    flags: list[str] = []
    close = indicators.get("close")
    rsi = indicators.get("rsi_14")
    ema200 = indicators.get("ema200")

    rsi_fomo = float(cfg.get("rsi_fomo_threshold", 72))
    if rsi is not None and rsi > rsi_fomo:
        flags.append("rsi_fomo_zone")

    extension_pct = float(cfg.get("max_extension_above_ema200_pct", 0.15))
    if close and ema200 and ema200 > 0:
        ext = (close - ema200) / ema200
        if ext > extension_pct:
            flags.append("extended_above_ema200")

    if candles and len(candles) >= 20:
        lookback = int(cfg.get("price_percentile_lookback", 90))
        window = candles[-lookback:] if len(candles) >= lookback else candles
        highs = [c["h"] for c in window]
        lo, hi = min(highs), max(highs)
        if hi > lo and close is not None:
            pct = (close - lo) / (hi - lo)
            if pct > float(cfg.get("price_percentile_block", 0.85)):
                flags.append("price_near_range_high")

        vols = [c["v"] for c in candles[-20:]]
        avg_vol = sum(vols[:-1]) / max(len(vols) - 1, 1)
        if avg_vol > 0 and vols[-1] > avg_vol * float(cfg.get("volume_spike_multiplier", 2.5)):
            flags.append("volume_spike_retail_entry")

    block_on = set(cfg.get("block_flags", flags))
    active = [f for f in flags if f in block_on or not cfg.get("block_flags")]
    passed = len(active) == 0

    return {
        "pass": passed,
        "flags": flags,
        "active_blocks": active,
        "reject_reason": "retail_guard:" + "+".join(active) if active else None,
        "reference": "https://www.bis.org/publ/bisbull69.pdf",
        "policy": "BIS retail enters at peaks — block long in FOMO conditions",
    }
