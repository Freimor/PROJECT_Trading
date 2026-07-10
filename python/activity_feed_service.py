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
    "crypto-signal-dry-run": "Крипто: сигналы (без сделок)",
    "crypto-signal-paper": "Крипто: автоторговля (демо)",
    "crypto-monitor-testnet": "Крипто: мониторинг демо-счёта",
    "crypto-paper-auto": "Крипто: автоторговля (демо)",
    "crypto-scalp-auto": "Крипто: scalp hybrid (paper)",
    "crypto-scalp-hybrid-paper": "Крипто: scalp hybrid (paper)",
    "securities-swing-dry-run": "MOEX: сигналы swing (без сделок)",
    "securities-swing-paper": "MOEX: swing (paper)",
    "securities-dca-sandbox": "MOEX: DCA (sandbox)",
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


from filter_event_details import summarize_filter_activity


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

    if stage == "filter":
        if decision == "approve":
            return summarize_filter_activity(row)
        if decision in ("skip", "reject"):
            return summarize_filter_activity(row)

    if stage == "llm":
        if decision == "approve":
            conf = row.get("confidence")
            conf_s = f", confidence {conf:.0%}" if isinstance(conf, (int, float)) else ""
            return f"LLM одобрил {symbol}{conf_s}"
        if decision == "reject":
            reason = row.get("reject_reason")
            if not reason:
                payload = row.get("payload_json")
                if payload:
                    try:
                        import json

                        parsed = json.loads(payload) if isinstance(payload, str) else payload
                        if isinstance(parsed, dict):
                            reason = parsed.get("reasoning") or parsed.get("reject_reason")
                    except (json.JSONDecodeError, TypeError):
                        pass
            reason = reason or "без причины"
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


def get_activity_feed(*, limit: int = 40, days: int = 3) -> dict[str, Any]:
    _ensure_table()
    since_dt = datetime.now(timezone.utc) - timedelta(days=max(1, days))
    since = since_dt.replace(microsecond=0).isoformat()
    trade_limit = max(limit * 3, 120)

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
                (since, min(30, limit)),
            ).fetchall()
        ]

        trade_rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, event_at, market, env, stage, symbol, decision,
                       reject_reason, workflow_name, confidence, notional, currency,
                       payload_json
                FROM trade_events
                WHERE event_at >= ?
                  AND stage IN ('signal', 'filter', 'llm', 'guardrails', 'order', 'fill', 'error')
                ORDER BY event_at DESC
                LIMIT ?
                """,
                (since, trade_limit),
            ).fetchall()
        ]
    finally:
        conn.close()

    trade_items: list[dict[str, Any]] = []
    for row in trade_rows:
        message = _trade_event_message(row)
        if not message:
            continue
        trade_items.append(
            {
                "id": f"trade:{row['id']}",
                "occurred_at": row["event_at"],
                "category": _trade_event_category(row),
                "level": _trade_event_level(row),
                "message": message,
                "ref_type": "trade_event",
                "ref_id": row["id"],
                "_priority": 0,
            }
        )

    system_items: list[dict[str, Any]] = []
    for row in system_rows:
        system_items.append(
            {
                "id": row["id"],
                "occurred_at": row["occurred_at"],
                "category": row["category"],
                "level": row["level"],
                "message": row["message"],
                "ref_type": row.get("ref_type"),
                "ref_id": row.get("ref_id"),
                "_priority": 2,
            }
        )

    for boot in _workflow_boot_messages(trade_rows):
        boot["_priority"] = 1
        system_items.append(boot)
    for health in _health_messages(since=since, limit=12):
        health["_priority"] = 2
        system_items.append(health)
    for runtime in _runtime_messages(since=since):
        runtime["_priority"] = 2
        system_items.append(runtime)
    for paper in _paper_session_messages(since=since):
        paper["_priority"] = 2
        system_items.append(paper)

    trade_items.sort(key=lambda x: str(x.get("occurred_at", "")), reverse=True)
    system_items.sort(key=lambda x: str(x.get("occurred_at", "")), reverse=True)

    # Trade events first — health/boot cannot crowd out signals from other symbols.
    trade_cap = min(len(trade_items), int(limit * 0.75))
    merged = trade_items[:trade_cap]
    seen_ids = {str(i["id"]) for i in merged}
    for item in system_items:
        if len(merged) >= limit:
            break
        if str(item["id"]) in seen_ids:
            continue
        merged.append(item)
        seen_ids.add(str(item["id"]))

    merged.sort(key=lambda x: str(x.get("occurred_at", "")), reverse=True)

    for item in merged:
        item.pop("_priority", None)

    return {"items": merged[:limit], "count": min(len(merged), limit), "days": days}
