"""Scalp trade direction — long vs short from micro-structure rules."""

from __future__ import annotations

from typing import Any, Literal

Direction = Literal["long", "short"]


def scalp_bearish_rule_filter(
    indicators: dict[str, Any],
    extras: dict[str, Any],
    rules: dict[str, Any],
) -> dict[str, Any]:
    """Mirror of bullish scalp rules for short entries."""
    mom = float(extras.get("momentum_pct", 0))
    checks: list[dict[str, Any]] = []
    strengths: list[float] = []

    rsi = indicators.get("rsi_14")
    rsi_lo = float(rules.get("rsi_oversold", 35))
    rsi_hi = float(rules.get("rsi_overbought", 65))
    rsi_pass = rsi is not None and rsi_lo <= rsi <= rsi_hi
    rsi_strength = 0.0
    if rsi is not None:
        if rsi >= rsi_hi - 5:
            rsi_strength = min(1.0, (rsi - (rsi_hi - 5)) / 10)
        elif rsi <= rsi_lo + 5:
            rsi_strength = 0.3
    checks.append({"rule": "rsi_active", "passed": rsi_pass, "strength": round(rsi_strength, 3)})
    if rsi_pass:
        strengths.append(rsi_strength)

    vol_min = float(rules.get("volume_spike_min", 1.35))
    vol_ratio = float(extras.get("volume_ratio", 1))
    vol_pass = vol_ratio >= vol_min
    vol_strength = min(1.0, (vol_ratio - 1) / max(vol_min, 0.01))
    checks.append({"rule": "volume_spike", "passed": vol_pass, "strength": round(vol_strength, 3)})
    if vol_pass:
        strengths.append(vol_strength)

    hist = indicators.get("macd_histogram")
    macd_v = indicators.get("macd")
    sig = indicators.get("macd_signal")
    macd_pass = (
        hist is not None
        and macd_v is not None
        and sig is not None
        and hist < 0
        and macd_v < sig
        and mom < 0
    )
    macd_strength = 0.4 if macd_pass else 0.0
    checks.append({"rule": "macd_momentum_bear", "passed": macd_pass, "strength": macd_strength})
    if macd_pass:
        strengths.append(macd_strength)

    if rules.get("require_trend_align", True):
        trend = indicators.get("trend")
        trend_pass = trend == "down" and mom < 0
        trend_strength = 0.35 if trend_pass else 0.0
        checks.append({"rule": "trend_bear_align", "passed": trend_pass, "strength": trend_strength})
        if trend_pass:
            strengths.append(trend_strength)

    passed_rules = [c["rule"] for c in checks if c.get("passed")]
    proceed = len(passed_rules) >= 2
    if not strengths:
        ambiguity = 1.0
    else:
        ambiguity = round(max(0.0, min(1.0, 1.0 - max(strengths))), 4)

    return {
        "proceed": proceed,
        "reject_reason": None if proceed else "scalp_no_bear_rule_match",
        "rule_name": "+".join(passed_rules) if passed_rules else None,
        "ambiguity_score": ambiguity,
        "filter_checks": checks,
        "passed_rules": passed_rules,
    }


def resolve_scalp_direction(
    indicators: dict[str, Any],
    extras: dict[str, Any],
    rules: dict[str, Any],
    *,
    allow_short: bool,
    bullish_filter: dict[str, Any],
) -> Direction | None:
    """Pick long vs short after rule filters; None = no trade."""
    bear = scalp_bearish_rule_filter(indicators, extras, rules) if allow_short else {"proceed": False}
    bull_ok = bool(bullish_filter.get("proceed"))
    bear_ok = bool(bear.get("proceed"))

    if bull_ok and not bear_ok:
        return "long"
    if bear_ok and not bull_ok:
        return "short"
    if bull_ok and bear_ok:
        mom = float(extras.get("momentum_pct", 0))
        return "long" if mom >= 0 else "short"
    return None
