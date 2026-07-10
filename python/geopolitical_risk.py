"""Geopolitical risk overlay for commodity-linked MOEX positions (Aizenman EJPE 2024)."""

from __future__ import annotations

from typing import Any

from config_loader import load_config
from db.connection import get_connection


def _cfg() -> dict[str, Any]:
    return load_config("geopolitical_risk")


def _recent_geo_news(hours: int = 48) -> list[dict[str, Any]]:
    cfg = _cfg()
    keywords = [k.lower() for k in cfg.get("keywords", [])]
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT title, summary, published_at, matched_symbols
            FROM news_items
            WHERE published_at >= datetime('now', ?)
            AND verification_status = 'verified'
            ORDER BY published_at DESC LIMIT 100
            """,
            (f"-{hours} hours",),
        ).fetchall()
        out = []
        for r in rows:
            text = f"{r['title']} {r['summary'] or ''}".lower()
            matched = [k for k in keywords if k in text]
            if matched:
                out.append({**dict(r), "geo_keywords": matched})
        return out
    finally:
        conn.close()


def compute_geopolitical_score() -> dict[str, Any]:
    """Score 0–1 geopolitical risk; reduce sizing for commodity-linked tickers."""
    cfg = _cfg()
    items = _recent_geo_news(hours=int(cfg.get("lookback_hours", 48)))
    score = min(1.0, len(items) * float(cfg.get("score_per_hit", 0.15)))
    level = "low"
    if score >= float(cfg.get("critical_threshold", 0.7)):
        level = "critical"
    elif score >= float(cfg.get("elevated_threshold", 0.35)):
        level = "elevated"

    commodity_tickers = cfg.get("commodity_linked_tickers", ["LKOH", "GMKN", "ROSN", "NVTK"])
    size_multiplier = 1.0
    if level == "critical":
        size_multiplier = float(cfg.get("critical_size_multiplier", 0.25))
    elif level == "elevated":
        size_multiplier = float(cfg.get("elevated_size_multiplier", 0.5))

    return {
        "status": "ok",
        "geo_score": round(score, 3),
        "risk_level": level,
        "news_hits": len(items),
        "commodity_tickers": commodity_tickers,
        "position_size_multiplier": size_multiplier,
        "sample_headlines": [i["title"] for i in items[:5]],
        "reference": "https://doi.org/10.1016/j.ejpoleco.2024.102574",
    }


def geo_adjust_notional(base_notional: float, ticker: str) -> dict[str, Any]:
    geo = compute_geopolitical_score()
    cfg = _cfg()
    tickers = set(t.upper() for t in geo.get("commodity_tickers", []))
    mult = geo["position_size_multiplier"] if ticker.upper() in tickers else 1.0
    return {
        "original_notional": base_notional,
        "adjusted_notional": round(base_notional * mult, 2),
        "multiplier": mult,
        "geo": geo,
    }
