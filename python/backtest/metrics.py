"""Simple backtest metrics on logged signals."""

from __future__ import annotations

import json
from typing import Any

from db.connection import get_connection


def signal_summary(*, market: str = "crypto", days: int = 30) -> dict[str, Any]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT stage, decision, reject_reason, COUNT(*) as cnt
            FROM trade_events
            WHERE market = ? AND event_at >= datetime('now', ?)
            GROUP BY stage, decision, reject_reason
            """,
            (market, f"-{days} days"),
        ).fetchall()
        return {"market": market, "days": days, "breakdown": [dict(r) for r in rows]}
    finally:
        conn.close()


def dry_run_funnel(*, market: str = "crypto", days: int = 7) -> dict[str, Any]:
    conn = get_connection()
    try:
        stages = ["signal", "filter", "llm", "guardrails", "risk", "order"]
        funnel = {}
        for stage in stages:
            row = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN decision IN ('approve','execute') THEN 1 ELSE 0 END) as passed,
                    COUNT(*) as total
                FROM trade_events
                WHERE market = ? AND stage = ? AND event_at >= datetime('now', ?)
                """,
                (market, stage, f"-{days} days"),
            ).fetchone()
            funnel[stage] = {"passed": row["passed"] or 0, "total": row["total"] or 0}
        return {"market": market, "funnel": funnel}
    finally:
        conn.close()
