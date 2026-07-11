"""Portfolio value and % change vs baseline / recent snapshots."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from workflow_pnl_service import crypto_portfolio_total_usdt, moex_portfolio_total_rub
from db.connection import get_connection
from db.migrate import run_migrations

PERIOD_HOURS = {
    "2h": 2,
    "1d": 24,
    "1w": 24 * 7,
    "1m": 24 * 30,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _pct_change(current: float | None, base: float | None) -> float | None:
    if current is None or base is None or base == 0:
        return None
    return round((current - base) / base * 100, 2)


def _crypto_total(testnet: bool) -> tuple[float | None, str]:
    """All assets marked to USDT (≈ USD)."""
    return crypto_portfolio_total_usdt(testnet=testnet)


def _moex_total(sandbox: bool) -> tuple[float | None, str]:
    return moex_portfolio_total_rub(sandbox=sandbox)


def _value_from_snapshot(snap: dict[str, Any], key: str) -> float | None:
    val = snap.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _baseline_from_db(conn) -> dict[str, Any]:
    session = conn.execute(
        """
        SELECT baseline_json, started_at FROM paper_sessions
        WHERE status = 'active'
        ORDER BY started_at DESC LIMIT 1
        """
    ).fetchone()
    if session and session["baseline_json"]:
        try:
            snap = json.loads(session["baseline_json"])
            return {
                "crypto_usdt": _value_from_snapshot(snap, "crypto_usdt"),
                "moex_rub": _value_from_snapshot(snap, "moex_rub"),
                "source": "paper_session",
                "started_at": session["started_at"],
            }
        except json.JSONDecodeError:
            pass

    row = conn.execute(
        """
        SELECT snapshot_json, captured_at FROM paper_portfolio_snapshots
        ORDER BY captured_at ASC LIMIT 1
        """
    ).fetchone()
    if row and row["snapshot_json"]:
        try:
            snap = json.loads(row["snapshot_json"])
            return {
                "crypto_usdt": _value_from_snapshot(snap, "crypto_usdt"),
                "moex_rub": _value_from_snapshot(snap, "moex_rub"),
                "source": "first_snapshot",
                "started_at": row["captured_at"],
            }
        except json.JSONDecodeError:
            pass

    return {"crypto_usdt": None, "moex_rub": None, "source": "none", "started_at": None}


def _snapshot_before(conn, *, hours_ago: float | None) -> dict[str, Any]:
    if hours_ago is None:
        return {"crypto_usdt": None, "moex_rub": None, "captured_at": None}

    target = (_utc_now() - timedelta(hours=hours_ago)).replace(microsecond=0).isoformat()
    row = conn.execute(
        """
        SELECT snapshot_json, captured_at FROM paper_portfolio_snapshots
        WHERE captured_at <= ?
        ORDER BY captured_at DESC LIMIT 1
        """,
        (target,),
    ).fetchone()
    if not row:
        row = conn.execute(
            """
            SELECT snapshot_json, captured_at FROM paper_portfolio_snapshots
            ORDER BY captured_at ASC LIMIT 1
            """
        ).fetchone()
    if not row or not row["snapshot_json"]:
        return {"crypto_usdt": None, "moex_rub": None, "captured_at": None}
    try:
        snap = json.loads(row["snapshot_json"])
    except json.JSONDecodeError:
        return {"crypto_usdt": None, "moex_rub": None, "captured_at": row["captured_at"]}
    return {
        "crypto_usdt": _value_from_snapshot(snap, "crypto_usdt"),
        "moex_rub": _value_from_snapshot(snap, "moex_rub"),
        "captured_at": row["captured_at"],
    }


def _metric_block(
    *,
    currency: str,
    current: float | None,
    status: str,
    baseline: float | None,
    period_value: float | None,
    period: str,
) -> dict[str, Any]:
    compare_base = baseline if period == "all" else period_value
    if period == "all":
        compare_base = baseline
    else:
        compare_base = period_value if period_value is not None else baseline

    change_pct = _pct_change(current, compare_base)
    direction = "flat"
    if change_pct is not None:
        if change_pct > 0:
            direction = "up"
        elif change_pct < 0:
            direction = "down"

    return {
        "currency": currency,
        "fiat_currency": "USD" if currency == "USDT" else currency,
        "portfolio_total": True,
        "current": current,
        "status": status,
        "baseline": baseline,
        "period": period,
        "period_value": period_value,
        "change_pct": change_pct,
        "direction": direction,
    }


def get_portfolio_performance(*, period: str = "all") -> dict[str, Any]:
    run_migrations()
    period = period if period in ("all", *PERIOD_HOURS.keys()) else "all"

    demo_usdt, demo_usdt_status = _crypto_total(testnet=True)
    demo_rub, demo_rub_status = _moex_total(sandbox=True)
    live_usdt, live_usdt_status = _crypto_total(testnet=False)
    live_rub, live_rub_status = _moex_total(sandbox=False)

    conn = get_connection()
    try:
        baseline = _baseline_from_db(conn)
        hours = PERIOD_HOURS.get(period)
        at_period = _snapshot_before(conn, hours_ago=hours)
    finally:
        conn.close()

    return {
        "status": "ok",
        "period": period,
        "baseline_source": baseline.get("source", "none"),
        "baseline_started_at": baseline.get("started_at"),
        "demo": {
            "crypto_usdt": _metric_block(
                currency="USDT",
                current=demo_usdt,
                status=demo_usdt_status,
                baseline=baseline.get("crypto_usdt"),
                period_value=at_period.get("crypto_usdt"),
                period=period,
            ),
            "moex_rub": _metric_block(
                currency="RUB",
                current=demo_rub,
                status=demo_rub_status,
                baseline=baseline.get("moex_rub"),
                period_value=at_period.get("moex_rub"),
                period=period,
            ),
        },
        "live": {
            "crypto_usdt": _metric_block(
                currency="USDT",
                current=live_usdt,
                status=live_usdt_status,
                baseline=None,
                period_value=None,
                period=period,
            ),
            "moex_rub": _metric_block(
                currency="RUB",
                current=live_rub,
                status=live_rub_status,
                baseline=None,
                period_value=None,
                period=period,
            ),
        },
        "snapshots": {
            "period_at": at_period.get("captured_at"),
            "hint": (
                "Запустите paper-сессию или POST /api/paper/snapshot для базовой линии и истории"
                if baseline.get("source") == "none"
                else None
            ),
        },
    }
