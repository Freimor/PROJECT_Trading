"""LLM decisions audit — list and inspect for admin console."""

from __future__ import annotations

from typing import Any

from db.connection import get_connection
from db.migrate import run_migrations


def _decision_rows_from_events(conn, where_extra: str, params: list[Any], limit: int, offset: int) -> list[dict]:
    """trade_events stage=llm without a matching llm_decisions row."""
    rows = conn.execute(
        f"""
        SELECT
            e.id AS id,
            e.event_at AS created_at,
            e.id AS trade_event_id,
            e.market,
            COALESCE(e.model, '') AS model,
            COALESCE(e.prompt_version, '') AS prompt_version,
            COALESCE(e.inputs_hash, '') AS inputs_hash,
            COALESCE(e.decision, 'unknown') AS parsed_action,
            e.confidence,
            NULL AS counter_thesis,
            e.latency_ms,
            e.reject_reason,
            e.symbol,
            e.env,
            e.event_at AS trade_event_at,
            e.workflow_name,
            'trade_event' AS source
        FROM trade_events e
        WHERE e.stage = 'llm'
          AND NOT EXISTS (
              SELECT 1 FROM llm_decisions l WHERE l.trade_event_id = e.id
          )
          {where_extra}
        ORDER BY e.event_at DESC
        LIMIT ? OFFSET ?
        """,
        [*params, limit, offset],
    ).fetchall()
    return [dict(r) for r in rows]


def list_llm_decisions(
    *,
    market: str | None = None,
    action: str | None = None,
    model: str | None = None,
    symbol: str | None = None,
    decision_id: str | None = None,
    trade_event_id: str | None = None,
    days: int = 30,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    run_migrations()
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    conn = get_connection()
    try:
        if decision_id or trade_event_id:
            lookup = decision_id or trade_event_id
            row = conn.execute(
                """
                SELECT
                    l.id, l.created_at, l.trade_event_id, l.market, l.model,
                    l.prompt_version, l.inputs_hash, l.parsed_action, l.confidence,
                    l.counter_thesis, l.latency_ms, l.reject_reason,
                    e.symbol, e.env, e.event_at AS trade_event_at, e.workflow_name,
                    'llm_decisions' AS source
                FROM llm_decisions l
                LEFT JOIN trade_events e ON e.id = l.trade_event_id
                WHERE l.id = ? OR l.trade_event_id = ?
                LIMIT 1
                """,
                (lookup, lookup),
            ).fetchone()
            if row:
                return {
                    "status": "ok",
                    "total": 1,
                    "limit": 1,
                    "offset": 0,
                    "decisions": [dict(row)],
                }
            ev = conn.execute(
                """
                SELECT
                    e.id AS id,
                    e.event_at AS created_at,
                    e.id AS trade_event_id,
                    e.market,
                    COALESCE(e.model, '') AS model,
                    COALESCE(e.prompt_version, '') AS prompt_version,
                    COALESCE(e.inputs_hash, '') AS inputs_hash,
                    COALESCE(e.decision, 'unknown') AS parsed_action,
                    e.confidence,
                    NULL AS counter_thesis,
                    e.latency_ms,
                    e.reject_reason,
                    e.symbol,
                    e.env,
                    e.event_at AS trade_event_at,
                    e.workflow_name,
                    'trade_event' AS source
                FROM trade_events e
                WHERE e.stage = 'llm' AND e.id = ?
                LIMIT 1
                """,
                (lookup,),
            ).fetchone()
            if ev:
                return {
                    "status": "ok",
                    "total": 1,
                    "limit": 1,
                    "offset": 0,
                    "decisions": [dict(ev)],
                }
            return {"status": "ok", "total": 0, "limit": limit, "offset": offset, "decisions": []}

        where = (
            "WHERE datetime(REPLACE(SUBSTR(l.created_at, 1, 19), 'T', ' ')) "
            ">= datetime('now', ?)"
        )
        params: list[Any] = [f"-{days} days"]
        ev_where = (
            "AND datetime(REPLACE(SUBSTR(e.event_at, 1, 19), 'T', ' ')) "
            ">= datetime('now', ?)"
        )
        ev_params: list[Any] = [f"-{days} days"]

        if market:
            where += " AND l.market = ?"
            params.append(market)
            ev_where += " AND e.market = ?"
            ev_params.append(market)
        if action:
            where += " AND l.parsed_action = ?"
            params.append(action)
            ev_where += " AND e.decision = ?"
            ev_params.append(action)
        if model:
            where += " AND l.model = ?"
            params.append(model)
            ev_where += " AND e.model = ?"
            ev_params.append(model)
        if symbol:
            where += " AND UPPER(COALESCE(e.symbol, '')) = ?"
            params.append(symbol.upper())
            ev_where += " AND UPPER(COALESCE(e.symbol, '')) = ?"
            ev_params.append(symbol.upper())

        from_table = f"""
            FROM llm_decisions l
            LEFT JOIN trade_events e ON e.id = l.trade_event_id
            {where}
        """

        total_llm = conn.execute(f"SELECT COUNT(*) AS cnt {from_table}", params).fetchone()["cnt"]

        total_ev = conn.execute(
            f"""
            SELECT COUNT(*) AS cnt FROM trade_events e
            WHERE e.stage = 'llm'
              AND NOT EXISTS (SELECT 1 FROM llm_decisions l2 WHERE l2.trade_event_id = e.id)
              {ev_where}
            """,
            ev_params,
        ).fetchone()["cnt"]

        llm_rows = conn.execute(
            f"""
            SELECT
                l.id, l.created_at, l.trade_event_id, l.market, l.model,
                l.prompt_version, l.inputs_hash, l.parsed_action, l.confidence,
                l.counter_thesis, l.latency_ms, l.reject_reason,
                e.symbol, e.env, e.event_at AS trade_event_at, e.workflow_name,
                'llm_decisions' AS source
            {from_table}
            ORDER BY l.created_at DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()

        decisions = [dict(r) for r in llm_rows]
        remaining = limit - len(decisions)
        if remaining > 0:
            ev_offset = max(0, offset - total_llm)
            decisions.extend(
                _decision_rows_from_events(conn, ev_where, ev_params, remaining, ev_offset)
            )

        return {
            "status": "ok",
            "total": total_llm + total_ev,
            "limit": limit,
            "offset": offset,
            "decisions": decisions[:limit],
        }
    finally:
        conn.close()


def get_llm_decision(decision_id: str) -> dict[str, Any] | None:
    run_migrations()
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT l.*, e.symbol, e.env, e.event_at AS trade_event_at, e.workflow_name
            FROM llm_decisions l
            LEFT JOIN trade_events e ON e.id = l.trade_event_id
            WHERE l.id = ? OR l.trade_event_id = ?
            """,
            (decision_id, decision_id),
        ).fetchone()
        if row:
            return dict(row)
        ev = conn.execute(
            """
            SELECT
                e.id, e.event_at AS created_at, e.id AS trade_event_id, e.market,
                e.model, e.prompt_version, e.inputs_hash, e.decision AS parsed_action,
                e.confidence, NULL AS counter_thesis, e.latency_ms, e.reject_reason,
                e.symbol, e.env, e.event_at AS trade_event_at, e.workflow_name
            FROM trade_events e
            WHERE e.stage = 'llm' AND e.id = ?
            """,
            (decision_id,),
        ).fetchone()
        return dict(ev) if ev else None
    finally:
        conn.close()
