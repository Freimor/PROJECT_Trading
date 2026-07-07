"""Admin operations for web console and Telegram bot."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import httpx

from backtest.metrics import dry_run_funnel
from config_loader import load_config, wiki_root
from db.connection import get_connection
from effective_config import get_guardrails
from event_log import log_event
from llm_client import ollama_host
from runtime_settings import is_kill_switch_active, set_kill_switch
from telegram_notify import send_telegram_message


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_confirmations_table() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operator_confirmations (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                action_type TEXT NOT NULL,
                title TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'pending',
                operator TEXT,
                resolved_at TEXT,
                source TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def ping_ollama() -> dict[str, Any]:
    start = datetime.now(timezone.utc)
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{ollama_host()}/api/tags")
        latency = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        if resp.status_code != 200:
            return {"status": "critical", "latency_ms": latency, "error": resp.text[:200]}
        models = [m.get("name") for m in resp.json().get("models", [])]
        return {"status": "ok", "latency_ms": latency, "models": models[:5]}
    except httpx.HTTPError as exc:
        return {"status": "critical", "latency_ms": None, "error": str(exc)}


def get_system_status() -> dict[str, Any]:
    guardrails = get_guardrails()
    trading = guardrails.get("trading", {})
    conn = get_connection()
    try:
        last_event = conn.execute(
            "SELECT event_at, workflow_name, stage, decision, env FROM trade_events ORDER BY event_at DESC LIMIT 1"
        ).fetchone()
        health_rows = conn.execute(
            """
            SELECT service_name, status, checked_at FROM system_health_checks
            ORDER BY checked_at DESC LIMIT 6
            """
        ).fetchall()
    finally:
        conn.close()

    ollama = ping_ollama()
    return {
        "timestamp": _utc_now(),
        "kill_switch": bool(trading.get("kill_switch")),
        "trading_mode": trading.get("mode", "dry_run"),
        "live_enabled": os.environ.get("LIVE_TRADING_ENABLED", "false").lower() == "true",
        "ollama": ollama,
        "db_path": os.environ.get("TRADING_DB_PATH", ""),
        "wiki": str(wiki_root()),
        "last_event": dict(last_event) if last_event else None,
        "health_latest": [dict(r) for r in health_rows],
    }


def stats_digest(*, days: int = 7) -> dict[str, Any]:
    conn = get_connection()
    try:
        env_rows = conn.execute(
            """
            SELECT env, COUNT(*) as cnt
            FROM trade_events
            WHERE event_at >= datetime('now', ?)
            GROUP BY env
            """,
            (f"-{days} days",),
        ).fetchall()
        llm_rows = conn.execute(
            """
            SELECT decision, COUNT(*) as cnt, AVG(latency_ms) as avg_latency
            FROM trade_events
            WHERE stage = 'llm' AND event_at >= datetime('now', ?)
            GROUP BY decision
            """,
            (f"-{days} days",),
        ).fetchall()
        stage_rejects = conn.execute(
            """
            SELECT stage, COUNT(*) as cnt
            FROM trade_events
            WHERE decision IN ('reject', 'error', 'halt', 'skip')
              AND event_at >= datetime('now', ?)
            GROUP BY stage
            ORDER BY cnt DESC
            LIMIT 5
            """,
            (f"-{days} days",),
        ).fetchall()
        live_orders = conn.execute(
            """
            SELECT COUNT(*) as cnt, COALESCE(SUM(pnl), 0) as total_pnl
            FROM trade_events
            WHERE env = 'live' AND stage IN ('order', 'fill')
              AND event_at >= datetime('now', ?)
            """,
            (f"-{days} days",),
        ).fetchone()
        dry_signals = conn.execute(
            """
            SELECT COUNT(*) as cnt
            FROM trade_events
            WHERE env = 'dry_run' AND stage = 'signal'
              AND event_at >= datetime('now', ?)
            """,
            (f"-{days} days",),
        ).fetchone()
    finally:
        conn.close()

    funnel_crypto = dry_run_funnel(market="crypto", days=days)
    funnel_sec = dry_run_funnel(market="securities", days=days)

    return {
        "days": days,
        "by_env": {r["env"]: r["cnt"] for r in env_rows},
        "dry_run_signals": dry_signals["cnt"] if dry_signals else 0,
        "llm": {
            r["decision"]: {"count": r["cnt"], "avg_latency_ms": round(r["avg_latency"] or 0)}
            for r in llm_rows
        },
        "top_reject_stages": [dict(r) for r in stage_rejects],
        "live": {
            "orders": live_orders["cnt"] if live_orders else 0,
            "pnl": round(live_orders["total_pnl"] or 0, 2) if live_orders else 0,
        },
        "funnel": {"crypto": funnel_crypto.get("funnel"), "securities": funnel_sec.get("funnel")},
    }


def get_live_checklist() -> dict[str, Any]:
    crypto = load_config("crypto_config")
    guardrails = get_guardrails()
    compliance = crypto.get("compliance", {})
    checks = {
        "kill_switch_off": not guardrails.get("trading", {}).get("kill_switch"),
        "compliance_geo_reviewed": compliance.get("geo_restrictions_reviewed", False),
        "compliance_legal_counsel": compliance.get("legal_counsel_consulted", False),
        "compliance_kyc": compliance.get("kyc_completed", False),
        "fiat_offramp_disabled": not compliance.get("fiat_offramp_automation", True),
        "live_env_flag": os.environ.get("LIVE_TRADING_ENABLED", "false").lower() == "true",
        "binance_credentials": bool(os.environ.get("BINANCE_API_KEY")),
        "tinkoff_credentials": bool(
            os.environ.get("TINKOFF_TOKEN") or os.environ.get("TINKOFF_SANDBOX_TOKEN")
        ),
    }
    return {"ready_for_live": all(checks.values()), "checks": checks}


def services_restart_plan(services: list[str] | None = None) -> dict[str, Any]:
    allowed = ("db-api", "telegram-bot", "n8n", "console", "proxy-gateway")
    chosen = [s for s in (services or ["db-api"]) if s in allowed]
    if not chosen:
        chosen = ["db-api"]
    commands = [f"docker compose restart {s}" for s in chosen]
    return {
        "status": "manual",
        "message": "Выполните на хосте (PowerShell / терминал):",
        "commands": commands,
    }


def apply_kill_switch(*, enabled: bool, operator: str, source: str) -> dict[str, Any]:
    yaml_kill = bool(load_config("guardrails").get("trading", {}).get("kill_switch", False))
    set_kill_switch(enabled, operator=operator)
    log_event(
        market="shared",
        env="dry_run",
        stage="error" if enabled else "reconcile",
        decision="halt" if enabled else "approve",
        reject_reason="kill_switch_enabled" if enabled else "kill_switch_disabled",
        workflow_name="admin",
        payload={"operator": operator, "source": source, "yaml_default": yaml_kill},
    )
    if load_config("guardrails").get("alerts", {}).get("telegram_enabled"):
        emoji = "🔴" if enabled else "🟢"
        send_telegram_message(
            f"{emoji} Kill switch {'ON' if enabled else 'OFF'}\n"
            f"Operator: {operator}\nSource: {source}"
        )
    return {"kill_switch": enabled, "operator": operator}


def create_confirmation(
    *,
    action_type: str,
    title: str,
    payload: dict[str, Any] | None = None,
    ttl_minutes: int = 5,
    source: str = "api",
) -> dict[str, Any]:
    _ensure_confirmations_table()
    conf_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=ttl_minutes)
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO operator_confirmations
                (id, created_at, expires_at, action_type, title, payload_json, status, source)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                conf_id,
                now.replace(microsecond=0).isoformat(),
                expires.replace(microsecond=0).isoformat(),
                action_type,
                title,
                json.dumps(payload or {}, ensure_ascii=False),
                source,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    text = f"⚠️ Требуется подтверждение\n{title}\nID: {conf_id[:8]}…"
    send_telegram_message(text)
    return {"id": conf_id, "expires_at": expires.isoformat(), "action_type": action_type}


def list_pending_confirmations() -> list[dict[str, Any]]:
    _ensure_confirmations_table()
    _expire_old_confirmations()
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, created_at, expires_at, action_type, title, payload_json, source
            FROM operator_confirmations
            WHERE status = 'pending'
            ORDER BY created_at ASC
            """
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json") or "{}")
            result.append(item)
        return result
    finally:
        conn.close()


def _expire_old_confirmations() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE operator_confirmations
            SET status = 'expired', resolved_at = ?
            WHERE status = 'pending' AND expires_at < ?
            """,
            (_utc_now(), _utc_now()),
        )
        conn.commit()
    finally:
        conn.close()


def resolve_confirmation(
    conf_id: str,
    *,
    decision: Literal["approved", "rejected"],
    operator: str,
) -> dict[str, Any]:
    _ensure_confirmations_table()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM operator_confirmations WHERE id = ?",
            (conf_id,),
        ).fetchone()
        if not row:
            return {"status": "error", "message": "not_found"}
        if row["status"] != "pending":
            return {"status": "error", "message": f"already_{row['status']}"}
        if row["expires_at"] < _utc_now():
            conn.execute(
                "UPDATE operator_confirmations SET status='expired', resolved_at=? WHERE id=?",
                (_utc_now(), conf_id),
            )
            conn.commit()
            return {"status": "error", "message": "expired"}

        conn.execute(
            """
            UPDATE operator_confirmations
            SET status = ?, operator = ?, resolved_at = ?
            WHERE id = ?
            """,
            (decision, operator, _utc_now(), conf_id),
        )
        conn.commit()
        payload = json.loads(row["payload_json"] or "{}")
    finally:
        conn.close()

    result: dict[str, Any] = {
        "status": "ok",
        "id": conf_id,
        "decision": decision,
        "action_type": row["action_type"],
        "payload": payload,
    }

    if decision == "approved" and row["action_type"] == "kill_switch_on":
        result["kill_switch"] = apply_kill_switch(enabled=True, operator=operator, source="confirmation")
    elif decision == "approved" and row["action_type"] == "kill_switch_off":
        result["kill_switch"] = apply_kill_switch(enabled=False, operator=operator, source="confirmation")

    log_event(
        market="shared",
        env="dry_run",
        stage="reconcile",
        decision="approve" if decision == "approved" else "reject",
        workflow_name="confirmation",
        payload={"confirmation_id": conf_id, "action_type": row["action_type"], "operator": operator},
    )
    return result


def run_smoke_test() -> dict[str, Any]:
    from smoke_test import main as smoke_main
    import io
    import contextlib

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            smoke_main()
        return {"status": "ok", "output": buf.getvalue()}
    except Exception as exc:
        return {"status": "error", "output": buf.getvalue(), "error": str(exc)}


def notify_telegram(*, level: str, message: str) -> dict[str, Any]:
    disclaimer = load_config("guardrails").get("alerts", {}).get(
        "disclaimer", "Automated signal. Not financial advice."
    )
    text = f"[{level}] {message}\n\n{disclaimer}"
    result = send_telegram_message(text)
    if result.get("ok"):
        log_event(
            market="shared",
            env="dry_run",
            stage="reconcile",
            decision="execute",
            workflow_name="telegram-notify",
            payload={"level": level, "message": message[:500]},
        )
    return result
