"""DeepFund-style live-paper session — post-training-cutoff isolation."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from config_loader import load_config
from crypto_pipeline import run_crypto_signal
from db.connection import get_connection


def _cfg() -> dict[str, Any]:
    return load_config("deepfund_config")


def get_active_session() -> dict[str, Any] | None:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT * FROM deepfund_sessions
            WHERE status = 'active' ORDER BY started_at DESC LIMIT 1
            """
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def start_session(*, label: str = "deepfund-live-paper", operator: str = "system") -> dict[str, Any]:
    cfg = _cfg()
    existing = get_active_session()
    if existing:
        return {"status": "exists", "session": existing}

    session_id = str(uuid.uuid4())
    cutoff = cfg.get("training_cutoff_date", "2024-09-01")
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO deepfund_sessions
            (id, label, status, started_at, training_cutoff_date, started_by, metrics_json)
            VALUES (?, ?, 'active', datetime('now'), ?, ?, '{}')
            """,
            (session_id, label, cutoff, operator),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "status": "started",
        "session_id": session_id,
        "training_cutoff_date": cutoff,
        "reference": "https://arxiv.org/abs/2505.11065",
    }


def run_deepfund_cycle(*, equity: float = 10000.0) -> dict[str, Any]:
    """Run one DeepFund cycle: signals on post-cutoff data only (live market)."""
    session = get_active_session()
    if not session:
        start_session()
        session = get_active_session()
    if not session:
        return {"status": "error", "message": "no_session"}

    cfg = _cfg()
    symbols = cfg.get("symbols", ["BTCUSDT", "ETHUSDT"])
    results: list[dict[str, Any]] = []
    for symbol in symbols:
        result = run_crypto_signal(
            symbol=symbol,
            env="paper",
            workflow_name="deepfund-live-paper",
            skip_llm=cfg.get("skip_llm", False),
            equity=equity,
        )
        results.append(result)
        _log_cycle_event(session["id"], symbol, result)

    summary = _aggregate_metrics(session["id"])
    return {
        "status": "ok",
        "session_id": session["id"],
        "training_cutoff_date": session.get("training_cutoff_date"),
        "symbols": symbols,
        "results": results,
        "metrics": summary,
        "reference": "https://arxiv.org/abs/2505.11065",
    }


def _log_cycle_event(session_id: str, symbol: str, result: dict[str, Any]) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO deepfund_events (id, session_id, event_at, symbol, status, payload_json)
            VALUES (?, ?, datetime('now'), ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                session_id,
                symbol,
                result.get("status"),
                json.dumps(result, ensure_ascii=False, default=str)[:8000],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _aggregate_metrics(session_id: str) -> dict[str, Any]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT status, COUNT(*) as cnt FROM deepfund_events
            WHERE session_id = ? GROUP BY status
            """,
            (session_id,),
        ).fetchall()
        return {"by_status": {r["status"]: r["cnt"] for r in rows}}
    finally:
        conn.close()


def close_session(session_id: str | None = None) -> dict[str, Any]:
    sid = session_id or (get_active_session() or {}).get("id")
    if not sid:
        return {"status": "error", "message": "no_active_session"}
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE deepfund_sessions SET status = 'closed', ended_at = datetime('now') WHERE id = ?",
            (sid,),
        )
        conn.commit()
    finally:
        conn.close()
    return {"status": "closed", "session_id": sid}
