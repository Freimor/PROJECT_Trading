"""Bond ladder monitoring — duration shock alerts (Ivashchenko FAJ 2024)."""

from __future__ import annotations

from typing import Any

from config_loader import load_config


def _cfg() -> dict[str, Any]:
    return load_config("bond_ladder")


def evaluate_bond_ladder(*, key_rate_pct: float | None = None) -> dict[str, Any]:
    """
    Evaluate OFZ ladder against duration targets and key-rate shock scenarios.
    Reference: https://doi.org/10.1080/0015198X.2024.2360390
    """
    cfg = _cfg()
    rungs = cfg.get("rungs", [])
    shock_bps = float(cfg.get("key_rate_shock_bps", 100))
    rate = key_rate_pct if key_rate_pct is not None else float(cfg.get("assumed_key_rate_pct", 16.0))

    alerts: list[dict[str, Any]] = []
    total_weight = sum(float(r.get("weight", 0)) for r in rungs) or 1.0
    portfolio_duration = 0.0

    for rung in rungs:
        ticker = rung.get("ticker", "")
        duration = float(rung.get("duration_years", 3))
        weight = float(rung.get("weight", 0)) / total_weight
        portfolio_duration += duration * weight
        target_d = float(rung.get("target_duration_years", duration))
        if abs(duration - target_d) > float(cfg.get("duration_drift_alert_years", 0.5)):
            alerts.append({
                "type": "duration_drift",
                "ticker": ticker,
                "duration": duration,
                "target": target_d,
            })

    shock_loss_pct = portfolio_duration * (shock_bps / 10000) * 100
    if shock_loss_pct > float(cfg.get("shock_loss_alert_pct", 2.0)):
        alerts.append({
            "type": "key_rate_shock",
            "assumed_rate_pct": rate,
            "shock_bps": shock_bps,
            "estimated_loss_pct": round(shock_loss_pct, 2),
        })

    return {
        "status": "ok",
        "portfolio_duration_years": round(portfolio_duration, 2),
        "rungs": rungs,
        "alerts": alerts,
        "action": "review" if alerts else "ok",
        "reference": "https://doi.org/10.1080/0015198X.2024.2360390",
    }
