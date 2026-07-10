"""Technical indicators — pure Python, no pandas dependency."""

from __future__ import annotations

from typing import Any


def parse_binance_klines(raw: list[Any]) -> list[dict[str, float]]:
    return [
        {
            "t": int(k[0]),
            "o": float(k[1]),
            "h": float(k[2]),
            "l": float(k[3]),
            "c": float(k[4]),
            "v": float(k[5]),
        }
        for k in raw
    ]


def _ema_series(values: list[float], period: int) -> list[float | None]:
    if len(values) < period:
        return [None] * len(values)
    k = 2 / (period + 1)
    out: list[float | None] = [None] * (period - 1)
    ema = sum(values[:period]) / period
    out.append(ema)
    for v in values[period:]:
        ema = v * k + ema * (1 - k)
        out.append(ema)
    return out


def rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) <= period:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 4)


def macd(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> dict[str, float | None]:
    ema_fast = _ema_series(closes, fast)
    ema_slow = _ema_series(closes, slow)
    macd_line: list[float | None] = []
    for ef, es in zip(ema_fast, ema_slow):
        if ef is None or es is None:
            macd_line.append(None)
        else:
            macd_line.append(ef - es)
    valid = [m for m in macd_line if m is not None]
    if len(valid) < signal_period:
        return {"macd": None, "macd_signal": None, "macd_histogram": None}
    signal_series = _ema_series(valid, signal_period)
    m = valid[-1]
    s = signal_series[-1]
    if m is None or s is None:
        return {"macd": None, "macd_signal": None, "macd_histogram": None}
    return {
        "macd": round(m, 6),
        "macd_signal": round(s, 6),
        "macd_histogram": round(m - s, 6),
    }


def _rsi_series(closes: list[float], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    out[period] = 100.0 if avg_loss == 0 else round(100 - (100 / (1 + avg_gain / avg_loss)), 4)
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            out[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i + 1] = round(100 - (100 / (1 + rs)), 4)
    return out


def _macd_series(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    ema_fast = _ema_series(closes, fast)
    ema_slow = _ema_series(closes, slow)
    macd_line: list[float | None] = []
    for ef, es in zip(ema_fast, ema_slow):
        if ef is None or es is None:
            macd_line.append(None)
        else:
            macd_line.append(ef - es)

    signal_line: list[float | None] = [None] * len(closes)
    hist: list[float | None] = [None] * len(closes)
    valid_indices = [i for i, m in enumerate(macd_line) if m is not None]
    if len(valid_indices) < signal_period:
        return macd_line, signal_line, hist

    valid_vals = [macd_line[i] for i in valid_indices]
    sig_series = _ema_series(valid_vals, signal_period)
    for idx, sig in zip(valid_indices, sig_series):
        if sig is None:
            continue
        signal_line[idx] = round(sig, 6)
        m = macd_line[idx]
        if m is not None:
            hist[idx] = round(m - sig, 6)
    return macd_line, signal_line, hist


def _series_points(
    candles: list[dict[str, float]],
    values: list[float | None],
) -> list[dict[str, float]]:
    out: list[dict[str, float]] = []
    for candle, value in zip(candles, values):
        if value is None:
            continue
        t = candle["t"]
        if isinstance(t, str):
            from datetime import datetime

            ts = int(datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp())
        elif isinstance(t, (int, float)) and float(t) > 1e12:
            ts = int(float(t) / 1000)
        else:
            ts = int(t)
        out.append({"time": ts, "value": float(value)})
    return out


def compute_indicator_series(candles: list[dict[str, float]]) -> dict[str, list[dict[str, float]]]:
    """Time-aligned indicator series for chart overlays."""
    if not candles:
        return {}
    closes = [c["c"] for c in candles]
    ema50 = _ema_series(closes, 50)
    ema200 = _ema_series(closes, 200)
    rsi_vals = _rsi_series(closes, 14)
    macd_line, macd_signal, macd_hist = _macd_series(closes)
    return {
        "ema50": _series_points(candles, ema50),
        "ema200": _series_points(candles, ema200),
        "rsi_14": _series_points(candles, rsi_vals),
        "macd": _series_points(candles, macd_line),
        "macd_signal": _series_points(candles, macd_signal),
        "macd_histogram": _series_points(candles, macd_hist),
    }


def compute_indicators(candles: list[dict[str, float]]) -> dict[str, Any]:
    closes = [c["c"] for c in candles]
    ema50_series = _ema_series(closes, 50)
    ema200_series = _ema_series(closes, 200)
    ema50 = ema50_series[-1]
    ema200 = ema200_series[-1]
    macd_vals = macd(closes)
    close = closes[-1]
    trend = "neutral"
    if ema50 is not None and ema200 is not None:
        trend = "up" if ema50 > ema200 else "down"
    return {
        "close": close,
        "rsi_14": rsi(closes),
        "ema50": round(ema50, 4) if ema50 else None,
        "ema200": round(ema200, 4) if ema200 else None,
        "trend": trend,
        **macd_vals,
    }


def _filter_thresholds(config: dict[str, Any]) -> dict[str, Any]:
    rf = config.get("rule_filter", {})
    return {
        "rsi_oversold": rf.get("rsi_oversold", 35),
        "rsi_overbought": rf.get("rsi_overbought", 65),
        "require_macd_cross": bool(rf.get("require_macd_cross", False)),
    }


def _build_filter_checks(indicators: dict[str, Any], thresholds: dict[str, Any]) -> list[dict[str, Any]]:
    oversold = thresholds["rsi_oversold"]
    overbought = thresholds["rsi_overbought"]
    checks: list[dict[str, Any]] = []

    rsi_val = indicators.get("rsi_14")
    if rsi_val is None:
        checks.append(
            {
                "rule": "rsi_oversold",
                "passed": False,
                "detail": "RSI недоступен",
                "actual": {"rsi_14": None},
                "threshold": f"< {oversold}",
            }
        )
    else:
        passed = rsi_val < oversold
        checks.append(
            {
                "rule": "rsi_oversold",
                "passed": passed,
                "detail": f"RSI {rsi_val:.2f} < {oversold}" if passed else f"RSI {rsi_val:.2f} ≥ {oversold}",
                "actual": {"rsi_14": round(rsi_val, 4)},
                "threshold": f"< {oversold}",
            }
        )

    if rsi_val is None:
        checks.append(
            {
                "rule": "rsi_overbought",
                "passed": False,
                "detail": "RSI недоступен",
                "actual": {"rsi_14": None},
                "threshold": f"> {overbought}",
            }
        )
    else:
        passed = rsi_val > overbought
        checks.append(
            {
                "rule": "rsi_overbought",
                "passed": passed,
                "detail": f"RSI {rsi_val:.2f} > {overbought}" if passed else f"RSI {rsi_val:.2f} ≤ {overbought}",
                "actual": {"rsi_14": round(rsi_val, 4)},
                "threshold": f"> {overbought}",
            }
        )

    hist = indicators.get("macd_histogram")
    macd_v = indicators.get("macd")
    sig = indicators.get("macd_signal")
    if hist is None or macd_v is None or sig is None:
        checks.append(
            {
                "rule": "macd_bullish_cross",
                "passed": False,
                "detail": "MACD недоступен",
                "actual": {
                    "macd": macd_v,
                    "macd_signal": sig,
                    "macd_histogram": hist,
                },
                "threshold": "hist > 0 и MACD > signal",
            }
        )
    else:
        passed = hist > 0 and macd_v > sig
        checks.append(
            {
                "rule": "macd_bullish_cross",
                "passed": passed,
                "detail": (
                    f"hist {hist:.6f} > 0, MACD {macd_v:.6f} > signal {sig:.6f}"
                    if passed
                    else f"hist {hist:.6f}, MACD {macd_v:.6f}, signal {sig:.6f}"
                ),
                "actual": {
                    "macd": round(macd_v, 6),
                    "macd_signal": round(sig, 6),
                    "macd_histogram": round(hist, 6),
                },
                "threshold": "hist > 0 и MACD > signal",
            }
        )

    close = indicators.get("close")
    ema50 = indicators.get("ema50")
    ema200 = indicators.get("ema200")
    if not ema200 or not ema50 or close is None:
        checks.append(
            {
                "rule": "golden_cross_context",
                "passed": False,
                "detail": "EMA200 недоступна (нужно ≥200 свечей)" if ema200 is None else "недостаточно данных EMA",
                "actual": {
                    "close": round(close, 4) if close is not None else None,
                    "ema50": round(ema50, 4) if ema50 is not None else None,
                    "ema200": round(ema200, 4) if ema200 is not None else None,
                },
                "threshold": "close > EMA200 и EMA50 > EMA200",
            }
        )
    else:
        passed = close > ema200 and ema50 > ema200
        checks.append(
            {
                "rule": "golden_cross_context",
                "passed": passed,
                "detail": (
                    f"close {close:.4f} > EMA200 {ema200:.4f}, EMA50 {ema50:.4f} > EMA200"
                    if passed
                    else f"close {close:.4f}, EMA50 {ema50:.4f}, EMA200 {ema200:.4f}"
                ),
                "actual": {
                    "close": round(close, 4),
                    "ema50": round(ema50, 4),
                    "ema200": round(ema200, 4),
                },
                "threshold": "close > EMA200 и EMA50 > EMA200",
            }
        )

    return checks


def rule_filter(indicators: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    thresholds = _filter_thresholds(config)
    checks = _build_filter_checks(indicators, thresholds)
    rules = [c["rule"] for c in checks if c.get("passed")]
    proceed = len(rules) > 0
    return {
        **indicators,
        "proceed": proceed,
        "rule_name": "+".join(rules) if rules else None,
        "reject_reason": None if proceed else "no_rule_match",
        "filter_thresholds": thresholds,
        "filter_checks": checks,
    }
