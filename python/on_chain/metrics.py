"""On-chain metrics — hash rate ribbons, activity (macro context filter)."""

from __future__ import annotations

from typing import Any, Literal

import httpx

from config_loader import load_config

OnChainMode = Literal["off", "advisory", "moderate", "strict"]

_BLOCKCHAIN_CHART = "https://api.blockchain.info/charts/{chart}?timespan={span}&format=json"

_VALID_MODES = frozenset({"off", "advisory", "moderate", "strict"})


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


def ribbon_ma_gap_pct(ma_short: float | None, ma_long: float | None) -> float | None:
    if ma_short is None or ma_long is None or ma_long == 0:
        return None
    return round((ma_short - ma_long) / ma_long * 100, 3)


def ribbon_severity(gap_pct: float | None, cfg: dict[str, Any] | None = None) -> str:
    """bullish | neutral | mild_bearish | strong_bearish | unknown"""
    if gap_pct is None:
        return "unknown"
    cfg = cfg or _cfg()
    neutral = float(cfg.get("neutral_ma_gap_pct", 1.0))
    strong = float(cfg.get("strong_bearish_ma_gap_pct", 2.5))
    if gap_pct >= neutral:
        return "bullish"
    if gap_pct <= -strong:
        return "strong_bearish"
    if gap_pct > -neutral:
        return "neutral"
    return "mild_bearish"


def should_block_long_for_mode(
    *,
    severity: str,
    mode: OnChainMode,
    allow_long_in_bearish: bool = False,
) -> bool:
    if allow_long_in_bearish or mode in ("off", "advisory"):
        return False
    if mode == "strict":
        return severity in ("mild_bearish", "strong_bearish")
    if mode == "moderate":
        return severity == "strong_bearish"
    return False


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
    gap_pct = ribbon_ma_gap_pct(ma_short, ma_long)
    severity = ribbon_severity(gap_pct, cfg)
    hash_ribbon_bullish = ma_short is not None and ma_long is not None and ma_short > ma_long

    tx_ma = _sma(txs, 14)
    tx_recent = txs[-1] if txs else None
    activity_elevated = (
        tx_ma is not None and tx_recent is not None and tx_recent > tx_ma * 1.1
    )

    macro_bias = "neutral"
    if hash_ribbon_bullish and not activity_elevated:
        macro_bias = "bullish_onchain"
    elif severity in ("mild_bearish", "strong_bearish"):
        macro_bias = "bearish_onchain"

    allow_long_strict = not should_block_long_for_mode(
        severity=severity,
        mode="strict",
        allow_long_in_bearish=bool(cfg.get("allow_long_in_bearish", False)),
    )

    mode_preview: dict[str, bool] = {}
    for mode in ("moderate", "strict", "advisory"):
        mode_preview[mode] = should_block_long_for_mode(
            severity=severity,
            mode=mode,  # type: ignore[arg-type]
            allow_long_in_bearish=bool(cfg.get("allow_long_in_bearish", False)),
        )

    return {
        "status": "ok",
        "hash_rate_latest": rates[-1] if rates else None,
        "hash_rate_ma_short": round(ma_short, 2) if ma_short else None,
        "hash_rate_ma_long": round(ma_long, 2) if ma_long else None,
        "ribbon_ma_gap_pct": gap_pct,
        "ribbon_severity": severity,
        "hash_ribbon_bullish": hash_ribbon_bullish,
        "n_transactions_latest": tx_recent,
        "activity_elevated": activity_elevated,
        "macro_bias": macro_bias,
        "allow_long": allow_long_strict,
        "would_block_by_mode": mode_preview,
        "reference": "https://doi.org/10.1016/j.chaos.2023.114305",
    }


def on_chain_filter_for_signal(
    *,
    side: str = "BUY",
    mode: OnChainMode = "moderate",
) -> dict[str, Any]:
    mode_norm = str(mode).lower()
    if mode_norm not in _VALID_MODES:
        mode_norm = "moderate"

    if mode_norm == "off":
        return {"pass": True, "mode": "off", "skipped": True}

    cfg = _cfg()
    ctx = compute_on_chain_context()
    severity = str(ctx.get("ribbon_severity", "unknown"))
    block = side.upper() == "BUY" and should_block_long_for_mode(
        severity=severity,
        mode=mode_norm,  # type: ignore[arg-type]
        allow_long_in_bearish=bool(cfg.get("allow_long_in_bearish", False)),
    )

    if block:
        reason = (
            "on_chain_strong_bearish"
            if severity == "strong_bearish"
            else "on_chain_bearish"
        )
        return {
            "pass": False,
            "mode": mode_norm,
            "reject_reason": reason,
            "context": ctx,
        }

    return {
        "pass": True,
        "mode": mode_norm,
        "context": ctx,
        "advisory_only": mode_norm == "advisory",
    }


def apply_on_chain_gate(
    on_chain_cfg: dict[str, Any] | None,
    *,
    side: str = "BUY",
    default_mode: OnChainMode = "moderate",
) -> dict[str, Any]:
    """Strategy-level on-chain gate (reads enabled + mode from strategy YAML)."""
    cfg = on_chain_cfg or {}
    if not cfg.get("enabled", True):
        return {"pass": True, "mode": "off", "skipped": True}

    mode = str(cfg.get("mode", default_mode)).lower()
    if mode not in _VALID_MODES:
        mode = default_mode

    return on_chain_filter_for_signal(side=side, mode=mode)  # type: ignore[arg-type]
