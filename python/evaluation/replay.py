"""LLM evaluation — replay and metrics."""

from __future__ import annotations

import json
from typing import Any

from db.connection import get_connection
from llm_client import validate_signal


def replay_by_inputs_hash(
    inputs_hash: str,
    *,
    model: str | None = None,
    prompt_version: str | None = None,
) -> dict[str, Any]:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT * FROM trade_events
            WHERE inputs_hash = ? AND stage = 'signal'
            ORDER BY event_at DESC LIMIT 1
            """,
            (inputs_hash,),
        ).fetchone()
        if not row:
            return {"status": "error", "message": "inputs_hash not found"}
        payload = json.loads(row["payload_json"] or "{}")
        indicators = payload.get("indicators", {})
        symbol = row["symbol"] or "BTCUSDT"
        market = row["market"]
        pv = prompt_version or row["prompt_version"] or "crypto_validate_v1"

        original = conn.execute(
            """
            SELECT * FROM llm_decisions WHERE inputs_hash = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (inputs_hash,),
        ).fetchone()

        new_result = validate_signal(
            market=market, symbol=symbol, indicators=indicators,
            prompt_version=pv, model=model,
        )
        return {
            "status": "ok",
            "inputs_hash": inputs_hash,
            "symbol": symbol,
            "original": dict(original) if original else None,
            "replay": new_result,
            "changed": (
                original is not None
                and original["parsed_action"] != new_result.get("action")
            ),
        }
    finally:
        conn.close()


def evaluation_metrics(*, market: str | None = None, days: int = 7) -> dict[str, Any]:
    conn = get_connection()
    try:
        q = """
            SELECT parsed_action, confidence, latency_ms, model
            FROM llm_decisions
            WHERE created_at >= datetime('now', ?)
        """
        params: list = [f"-{days} days"]
        if market:
            q += " AND market = ?"
            params.append(market)
        rows = conn.execute(q, params).fetchall()
        if not rows:
            return {"count": 0, "message": "no data"}
        approves = sum(1 for r in rows if r["parsed_action"] == "approve")
        confidences = [r["confidence"] for r in rows if r["confidence"] is not None]
        latencies = [r["latency_ms"] for r in rows if r["latency_ms"] is not None]
        return {
            "count": len(rows),
            "approve_rate": round(approves / len(rows), 4),
            "avg_confidence": round(sum(confidences) / len(confidences), 4) if confidences else None,
            "avg_latency_ms": int(sum(latencies) / len(latencies)) if latencies else None,
            "models": list({r["model"] for r in rows}),
        }
    finally:
        conn.close()


def champion_challenger_report(
    *,
    inputs_hashes: list[str],
    champion_model: str,
    challenger_model: str,
    prompt_version: str = "crypto_validate_v1",
) -> dict[str, Any]:
    results = []
    agree = 0
    for ih in inputs_hashes:
        champ = replay_by_inputs_hash(ih, model=champion_model, prompt_version=prompt_version)
        chall = replay_by_inputs_hash(ih, model=challenger_model, prompt_version=prompt_version)
        c_action = champ.get("replay", {}).get("action")
        ch_action = chall.get("replay", {}).get("action")
        if c_action == ch_action:
            agree += 1
        results.append({
            "inputs_hash": ih,
            "champion": c_action,
            "challenger": ch_action,
        })
    n = len(inputs_hashes) or 1
    return {
        "compared": len(inputs_hashes),
        "agreement_rate": round(agree / n, 4),
        "champion_model": champion_model,
        "challenger_model": challenger_model,
        "details": results,
    }
