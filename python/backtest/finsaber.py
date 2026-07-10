"""FINSABER-style walk-forward backtest with Deflated Sharpe (Lopez de Prado 2022)."""

from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any

from binance_client import fetch_klines_history
from config_loader import load_config
from db.connection import get_connection
from indicators.technical import compute_indicators, parse_binance_klines, rule_filter


def _deflated_sharpe(sharpe: float, n_trials: int, n_obs: int, skew: float = 0.0, kurt: float = 3.0) -> float:
    """Simplified Deflated Sharpe (Lopez de Prado, JPM 2022)."""
    if n_obs < 2 or n_trials < 1:
        return 0.0
    euler = 0.5772156649
    expected_max = (
        (1 - euler) * _norm_ppf(1 - 1 / n_trials)
        + euler * _norm_ppf(1 - 1 / (n_trials * math.e))
    ) if n_trials > 1 else 0.0
    se = math.sqrt((1 + 0.5 * sharpe**2 - skew * sharpe + (kurt - 3) / 4 * sharpe**2) / (n_obs - 1))
    if se == 0:
        return sharpe
    return (sharpe - expected_max * se) / se


def _norm_ppf(p: float) -> float:
    """Approximate inverse normal CDF (Acklam)."""
    if p <= 0:
        return -10.0
    if p >= 1:
        return 10.0
    a = [-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
         1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00]
    b = [-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
         6.680131188771972e01, -1.328068155288572e01]
    q = p - 0.5
    if abs(q) <= 0.425:
        r = 0.180625 - q * q
        num = sum(a[i] * r ** (i + 1) for i in range(6))
        den = 1 + sum(b[i] * r ** (i + 1) for i in range(5))
        return q * num / den
    r = math.sqrt(-math.log(min(p, 1 - p)))
    c = [1.0, 2.515517, 0.802853, 0.010328]
    d = [1.432788, 0.189269, 0.001308]
    num = c[0] + sum(c[i + 1] / (r + i) for i in range(3))
    den = 1 + sum(d[i] / (r + i) for i in range(3))
    z = num / den
    return z if p > 0.5 else -z


def _forward_return(closes: list[float], idx: int, horizon: int) -> float | None:
    if idx + horizon >= len(closes) or closes[idx] == 0:
        return None
    return (closes[idx + horizon] - closes[idx]) / closes[idx]


def run_walk_forward_backtest(
    *,
    symbol: str = "BTCUSDT",
    timeframe: str = "4h",
    bars: int = 500,
    warmup: int = 200,
    forward_bars: int = 6,
    testnet: bool = False,
) -> dict[str, Any]:
    """Walk-forward rule-filter backtest (FINSABER methodology subset)."""
    crypto_cfg = load_config("crypto_config")
    raw = fetch_klines_history(symbol, timeframe, bars=bars + warmup, testnet=testnet)
    candles = parse_binance_klines(raw)
    if len(candles) < warmup + 50:
        return {"status": "error", "message": "insufficient_history", "bars": len(candles)}

    closes = [c["c"] for c in candles]
    signals: list[dict[str, Any]] = []
    returns: list[float] = []

    for i in range(warmup, len(candles) - forward_bars):
        window = candles[: i + 1]
        indicators = compute_indicators(window)
        filtered = rule_filter(indicators, crypto_cfg)
        if not filtered.get("proceed"):
            continue
        fwd = _forward_return(closes, i, forward_bars)
        if fwd is None:
            continue
        signals.append({
            "bar_index": i,
            "ts": candles[i]["t"],
            "close": closes[i],
            "rule": filtered.get("rule_name"),
            "forward_return_pct": round(fwd * 100, 4),
        })
        returns.append(fwd)

    n = len(returns)
    if n < 5:
        return {
            "status": "ok",
            "symbol": symbol,
            "timeframe": timeframe,
            "signal_count": n,
            "message": "too_few_signals",
        }

    mean_r = sum(returns) / n
    var = sum((r - mean_r) ** 2 for r in returns) / max(n - 1, 1)
    std = math.sqrt(var) if var > 0 else 1e-9
    sharpe = (mean_r / std) * math.sqrt(252 * 6 / forward_bars)  # annualized approx for 4h
    wins = sum(1 for r in returns if r > 0)
    cum = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        cum *= 1 + r
        peak = max(peak, cum)
        max_dd = max(max_dd, (peak - cum) / peak)

    n_trials = max(len(crypto_cfg.get("rule_filter", {})) * 4, 10)
    dsr = _deflated_sharpe(sharpe, n_trials=n_trials, n_obs=n)

    report = {
        "status": "ok",
        "symbol": symbol,
        "timeframe": timeframe,
        "bars_analyzed": len(candles),
        "warmup": warmup,
        "forward_bars": forward_bars,
        "signal_count": n,
        "win_rate": round(wins / n, 4),
        "mean_forward_return_pct": round(mean_r * 100, 4),
        "sharpe_annualized": round(sharpe, 4),
        "deflated_sharpe": round(dsr, 4),
        "max_drawdown_pct": round(max_dd * 100, 4),
        "finsaber_pass": dsr > 0 and mean_r > 0,
        "methodology": "walk_forward_rule_filter_Lopez_de_Prado_DSR",
        "reference": "https://arxiv.org/abs/2505.07078",
        "signals_sample": signals[-5:],
    }
    _persist_backtest_run(report)
    return report


def _persist_backtest_run(report: dict[str, Any]) -> str:
    run_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO backtest_runs (id, started_at, label, symbol, timeframe, report_json, status)
            VALUES (?, datetime('now'), ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                "finsaber_walk_forward",
                report.get("symbol"),
                report.get("timeframe"),
                json.dumps(report, ensure_ascii=False),
                "completed",
            ),
        )
        conn.commit()
    finally:
        conn.close()
    report["run_id"] = run_id
    return run_id


def list_backtest_runs(limit: int = 20) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, started_at, label, symbol, timeframe, status, report_json
            FROM backtest_runs ORDER BY started_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        out = []
        for r in rows:
            item = dict(r)
            try:
                item["report"] = json.loads(item.pop("report_json", "{}") or "{}")
            except json.JSONDecodeError:
                item["report"] = {}
            out.append(item)
        return out
    finally:
        conn.close()
