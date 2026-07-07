"""Human-readable system activity feed for web console."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from db.connection import get_connection

_MARKET_LABELS = {
    "crypto": "crypto",
    "securities": "MOEX",
    "shared": "система",
}

_WORKFLOW_LABELS = {
    "crypto-signal-dry-run": "Crypto автомат",
    "crypto-signal-paper": "Crypto автомат (paper)",
    "crypto-paper-auto": "Crypto автомат",
    "securities-swing-dry-run": "MOEX swing автомат",
    "securities-swing-paper": "MOEX swing автомат (paper)",
    "securities-dca-sandbox": "MOEX DCA sandbox",
    "shared-health-check": "Health-check",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_table() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS system_activity (
                id              TEXT PRIMARY KEY,
                occurred_at     TEXT NOT NULL,
                category        TEXT NOT NULL,
                level           TEXT NOT NULL DEFAULT 'info',
                message         TEXT NOT NULL,
                ref_type        TEXT,
                ref_id          TEXT,
                payload_json    TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_system_activity_at
            ON system_activity(occurred_at DESC)
            """
        )
        conn.commit()
    finally:
        conn.close()


def log_system_activity(
    message: str,
    *,
    category: str = "system",
    level: str = "info",
    ref_type: str | None = None,
    ref_id: str | None = None,
    payload: dict[str, Any] | None = None,
    occurred_at: str | None = None,
) -> str:
    _ensure_table()
    activity_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO system_activity
                (id, occurred_at, category, level, message, ref_type, ref_id, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                activity_id,
                occurred_at or _utc_now(),
                category,
                level,
                message,
                ref_type,
                ref_id,
                json.dumps(payload or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return activity_id


def _trade_event_message(row: dict[str, Any]) -> str | None:
    stage = row.get("stage")
    symbol = row.get("symbol") or "?"
    market = _MARKET_LABELS.get(str(row.get("market", "")), str(row.get("market", "")))
    decision = row.get("decision")
    workflow = row.get("workflow_name") or ""

    if stage == "signal":
        wf = _WORKFLOW_LABELS.get(workflow, workflow)
        suffix = f" · {wf}" if wf else ""
        return f"Сигнал {symbol} ({market}){suffix}"

    if stage == "llm":
        if decision == "approve":
            conf = row.get("confidence")
            conf_s = f", confidence {conf:.0%}" if isinstance(conf, (int, float)) else ""
            return f"LLM одобрил {symbol}{conf_s}"
        if decision == "reject":
            reason = row.get("reject_reason") or "без причины"
            return f"LLM отклонил {symbol}: {reason}"

    if stage == "order" and decision in ("execute", "approve", "submitted"):
        notional = row.get("notional")
        currency = row.get("currency") or ("USDT" if row.get("market") == "crypto" else "RUB")
        if isinstance(notional, (int, float)) and notional > 0:
            unit = "₽" if currency in ("RUB", "rub") else currency
            return f"Покупка {symbol} на {notional:,.0f} {unit}".replace(",", " ")
        return f"Ордер на покупку {symbol}"

    if stage == "fill":
        return f"Исполнена покупка {symbol}"

    if stage == "guardrails" and decision in ("reject", "halt", "skip"):
        return f"Guardrails: {row.get('reject_reason') or 'отклонено'}"

    if stage == "error" or decision == "error":
        return f"Ошибка {symbol}: {row.get('reject_reason') or workflow or '—'}"

    return None


def _trade_event_level(row: dict[str, Any]) -> str:
    stage = row.get("stage")
    decision = row.get("decision")
    if stage in ("error",) or decision == "error":
        return "error"
    if stage == "guardrails" and decision in ("reject", "halt"):
        return "warn"
    if stage in ("fill", "order") and decision in ("execute", "approve", "submitted"):
        return "success"
    return "info"


def _trade_event_category(row: dict[str, Any]) -> str:
    market = row.get("market")
    if market in ("crypto", "securities"):
        return str(market)
    return "system"


def _workflow_boot_messages(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One 'automat is running' line per workflow per calendar day."""
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda r: str(r.get("event_at", ""))):
        workflow = str(row.get("workflow_name") or "")
        if not workflow or workflow not in _WORKFLOW_LABELS:
            continue
        day = str(row.get("event_at", ""))[:10]
        key = (workflow, day)
        if key in seen:
            continue
        seen.add(key)
        label = _WORKFLOW_LABELS[workflow]
        out.append(
            {
                "id": f"boot:{workflow}:{day}",
                "occurred_at": row.get("event_at"),
                "category": "crypto" if "crypto" in workflow else "securities",
                "level": "success",
                "message": f"{label} запустился и функционирует",
                "ref_type": "workflow_boot",
                "ref_id": workflow,
            }
        )
    return out


def _health_messages(*, since: str, limit: int) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT checked_at, service_name, status, details
            FROM system_health_checks
            WHERE checked_at >= ?
            ORDER BY checked_at DESC
            LIMIT ?
            """,
            (since, limit),
        ).fetchall()
    finally:
        conn.close()

    labels = {
        "ollama": "Ollama",
        "db_api": "DB API",
        "binance": "Binance API",
        "moex_iss": "MOEX ISS",
        "n8n": "n8n",
    }
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        service = str(row["service_name"])
        status = str(row["status"])
        day = str(row["checked_at"])[:10]
        dedupe_key = (service, status, day)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        label = labels.get(service, service)
        if status == "ok":
            msg = f"{label}: сервис доступен"
            level = "success"
        elif status == "warn":
            msg = f"{label}: предупреждение"
            level = "warn"
        else:
            msg = f"{label}: недоступен"
            level = "error"
        out.append(
            {
                "id": f"health:{service}:{row['checked_at']}",
                "occurred_at": row["checked_at"],
                "category": "system",
                "level": level,
                "message": msg,
                "ref_type": "health",
                "ref_id": service,
            }
        )
    return out


def _runtime_messages(*, since: str) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT key, value_json, updated_at, updated_by
            FROM runtime_settings
            WHERE updated_at >= ? AND key = 'kill_switch'
            ORDER BY updated_at DESC
            """,
            (since,),
        ).fetchall()
    finally:
        conn.close()

    out: list[dict[str, Any]] = []
    for row in rows:
        enabled = json.loads(row["value_json"])
        operator = row["updated_by"] or "оператор"
        if enabled:
            msg = f"Kill switch включён ({operator})"
            level = "error"
        else:
            msg = f"Kill switch выключен ({operator})"
            level = "success"
        out.append(
            {
                "id": f"runtime:{row['key']}:{row['updated_at']}",
                "occurred_at": row["updated_at"],
                "category": "risk",
                "level": level,
                "message": msg,
                "ref_type": "runtime",
                "ref_id": row["key"],
            }
        )
    return out


def _paper_session_messages(*, since: str) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, label, started_at, started_by
            FROM paper_sessions
            WHERE started_at >= ?
            ORDER BY started_at DESC
            LIMIT 20
            """,
            (since,),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "id": f"paper:{row['id']}",
            "occurred_at": row["started_at"],
            "category": "system",
            "level": "info",
            "message": f"Paper-сессия «{row['label']}» запущена",
            "ref_type": "paper_session",
            "ref_id": row["id"],
        }
        for row in rows
    ]


def get_activity_feed(*, limit: int = 60, days: int = 3) -> dict[str, Any]:
    _ensure_table()
    since_dt = datetime.now(timezone.utc) - timedelta(days=max(1, days))
    since = since_dt.replace(microsecond=0).isoformat()

    conn = get_connection()
    try:
        system_rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, occurred_at, category, level, message, ref_type, ref_id
                FROM system_activity
                WHERE occurred_at >= ?
                ORDER BY occurred_at DESC
                LIMIT ?
                """,
                (since, limit),
            ).fetchall()
        ]

        trade_rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, event_at, market, env, stage, symbol, decision,
                       reject_reason, workflow_name, confidence, notional, currency
                FROM trade_events
                WHERE event_at >= ?
                  AND stage IN ('signal', 'llm', 'guardrails', 'order', 'fill', 'error')
                ORDER BY event_at DESC
                LIMIT ?
                """,
                (since, limit * 2),
            ).fetchall()
        ]
    finally:
        conn.close()

    items: list[dict[str, Any]] = []

    for row in system_rows:
        items.append(
            {
                "id": row["id"],
                "occurred_at": row["occurred_at"],
                "category": row["category"],
                "level": row["level"],
                "message": row["message"],
                "ref_type": row.get("ref_type"),
                "ref_id": row.get("ref_id"),
            }
        )

    items.extend(_workflow_boot_messages(trade_rows))
    items.extend(_health_messages(since=since, limit=40))
    items.extend(_runtime_messages(since=since))
    items.extend(_paper_session_messages(since=since))

    for row in trade_rows:
        message = _trade_event_message(row)
        if not message:
            continue
        items.append(
            {
                "id": f"trade:{row['id']}",
                "occurred_at": row["event_at"],
                "category": _trade_event_category(row),
                "level": _trade_event_level(row),
                "message": message,
                "ref_type": "trade_event",
                "ref_id": row["id"],
            }
        )

    items.sort(key=lambda x: str(x.get("occurred_at", "")), reverse=True)

    # Dedupe identical messages within 2 minutes
    deduped: list[dict[str, Any]] = []
    seen_msgs: list[tuple[str, datetime]] = []
    for item in items:
        msg = str(item.get("message", ""))
        try:
            ts = datetime.fromisoformat(str(item.get("occurred_at", "")).replace("Z", "+00:00"))
        except ValueError:
            ts = datetime.now(timezone.utc)
        skip = False
        for prev_msg, prev_ts in seen_msgs:
            if prev_msg == msg and abs((ts - prev_ts).total_seconds()) < 120:
                skip = True
                break
        if skip:
            continue
        seen_msgs.append((msg, ts))
        deduped.append(item)
        if len(deduped) >= limit:
            break

    return {"items": deduped, "count": len(deduped), "days": days}
