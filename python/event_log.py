"""Persist trade events to SQLite."""

from __future__ import annotations

import json
import uuid
from typing import Any

from db.connection import get_connection


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def log_event(
    *,
    market: str,
    env: str,
    stage: str,
    symbol: str | None = None,
    decision: str | None = None,
    reject_reason: str | None = None,
    workflow_name: str | None = None,
    execution_id: str | None = None,
    request_id: str | None = None,
    inputs_hash: str | None = None,
    prompt_version: str | None = None,
    model: str | None = None,
    confidence: float | None = None,
    latency_ms: int | None = None,
    payload: dict | None = None,
    pnl: float | None = None,
    notional: float | None = None,
    currency: str = "USD",
) -> str:
    event_id = str(uuid.uuid4())
    event_at = _utc_now()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO trade_events (
                id, event_at, market, env, stage, symbol, decision, reject_reason,
                workflow_name, execution_id, request_id, inputs_hash, prompt_version,
                model, confidence, latency_ms, payload_json, pnl, notional, currency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id, event_at, market, env, stage, symbol, decision, reject_reason,
                workflow_name, execution_id, request_id, inputs_hash, prompt_version,
                model, confidence, latency_ms,
                json.dumps(payload or {}, ensure_ascii=False),
                pnl, notional, currency,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    if stage == "order" and decision in ("approve", "submitted"):
        try:
            from news_alert_service import maybe_trade_alert

            maybe_trade_alert(
                event_id=event_id,
                market=market,
                env=env,
                stage=stage,
                symbol=symbol,
                decision=decision,
                workflow_name=workflow_name,
                notional=notional,
                currency=currency,
                event_at=event_at,
            )
        except Exception:
            pass

    return event_id


def log_llm_decision(
    *,
    trade_event_id: str | None,
    market: str,
    model: str,
    prompt_version: str,
    inputs_hash: str,
    raw_response: str,
    parsed: dict[str, Any],
    latency_ms: int,
) -> str:
    decision_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO llm_decisions (
                id, market, model, prompt_version, inputs_hash, raw_response,
                parsed_action, confidence, counter_thesis, latency_ms, trade_event_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id, market, model, prompt_version, inputs_hash, raw_response,
                parsed.get("action"), parsed.get("confidence"),
                parsed.get("counter_thesis"), latency_ms, trade_event_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return decision_id


def daily_pnl_pct(market: str | None = None) -> float:
    conn = get_connection()
    try:
        q = """
            SELECT COALESCE(SUM(pnl), 0) AS total
            FROM trade_events
            WHERE date(event_at) = date('now')
        """
        params: list = []
        if market:
            q += " AND market = ?"
            params.append(market)
        row = conn.execute(q, params).fetchone()
        return float(row["total"] if row else 0)
    finally:
        conn.close()
