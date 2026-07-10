"""MOEX factor sleeve — momentum/value proxy portfolios (HSE Abramov 2025 inspired)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx

from config_loader import load_config
from market_data import fetch_moex_candles_as_of


def _cfg() -> dict[str, Any]:
    return load_config("factor_sleeve")


def _momentum_score(ticker: str, lookback_days: int = 120) -> float | None:
    as_of = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    candles = fetch_moex_candles_as_of(ticker, interval=24, as_of=as_of, limit=lookback_days + 5)
    if len(candles) < 20:
        return None
    start = candles[0]["c"]
    end = candles[-1]["c"]
    if start <= 0:
        return None
    return (end - start) / start


def _low_vol_score(ticker: str, window: int = 60) -> float | None:
    as_of = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    candles = fetch_moex_candles_as_of(ticker, interval=24, as_of=as_of, limit=window + 5)
    if len(candles) < 10:
        return None
    closes = [c["c"] for c in candles]
    rets = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1]]
    if not rets:
        return None
    var = sum(r**2 for r in rets) / len(rets)
    return var


def rank_factor_universe() -> dict[str, Any]:
    """Rank universe by momentum; low-vol as tie-breaker (value proxy)."""
    cfg = _cfg()
    universe = cfg.get("universe", ["SBER", "GAZP", "LKOH", "GMKN", "YNDX", "TMOS"])
    lookback = int(cfg.get("momentum_lookback_days", 120))
    top_n = int(cfg.get("top_n", 3))

    scores: list[dict[str, Any]] = []
    for ticker in universe:
        mom = _momentum_score(ticker, lookback)
        vol = _low_vol_score(ticker)
        if mom is None:
            continue
        scores.append({
            "ticker": ticker,
            "momentum_return": round(mom, 4),
            "volatility_var": round(vol, 6) if vol else None,
        })

    scores.sort(key=lambda x: (-x["momentum_return"], x.get("volatility_var") or 999))
    selected = scores[:top_n]
    weight = round(1.0 / len(selected), 4) if selected else 0

    return {
        "status": "ok",
        "strategy": "factor_momentum_sleeve",
        "lookback_days": lookback,
        "selected": [{**s, "weight": weight} for s in selected],
        "reference": "https://doi.org/10.17323/j.jcfr.2073-0438.19.2.2025.67-81",
        "note": "Separate from intraday swing — rebalance weekly",
    }


def factor_sleeve_rebalance_plan() -> dict[str, Any]:
    ranking = rank_factor_universe()
    cfg = _cfg()
    min_mom = float(cfg.get("min_momentum_return", 0.0))
    filtered = [s for s in ranking.get("selected", []) if s["momentum_return"] >= min_mom]
    return {
        **ranking,
        "selected": filtered,
        "action": "rebalance" if filtered else "hold_cash",
        "workflow": "securities-factor-sleeve",
    }
