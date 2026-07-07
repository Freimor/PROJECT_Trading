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


def rule_filter(indicators: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    rf = config.get("rule_filter", {})
    rules: list[str] = []
    rsi_val = indicators.get("rsi_14")
    if rsi_val is not None and rsi_val < rf.get("rsi_oversold", 35):
        rules.append("rsi_oversold")
    if rsi_val is not None and rsi_val > rf.get("rsi_overbought", 65):
        rules.append("rsi_overbought")
    hist = indicators.get("macd_histogram")
    macd_v = indicators.get("macd")
    sig = indicators.get("macd_signal")
    if hist is not None and macd_v is not None and sig is not None:
        if hist > 0 and macd_v > sig:
            rules.append("macd_bullish_cross")
    close = indicators.get("close")
    ema50 = indicators.get("ema50")
    ema200 = indicators.get("ema200")
    if close and ema200 and ema50:
        if close > ema200 and ema50 > ema200:
            rules.append("golden_cross_context")
    proceed = len(rules) > 0
    return {
        **indicators,
        "proceed": proceed,
        "rule_name": "+".join(rules) if rules else None,
        "reject_reason": None if proceed else "no_rule_match",
    }
