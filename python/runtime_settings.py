"""Runtime overrides (SQLite) — kill switch without editing YAML on read-only mounts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from db.connection import get_connection


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_table() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_settings (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_runtime_value(key: str) -> Any | None:
    _ensure_table()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT value_json FROM runtime_settings WHERE key = ?",
            (key,),
        ).fetchone()
        if not row:
            return None
        return json.loads(row["value_json"])
    finally:
        conn.close()


def get_runtime_meta(key: str) -> dict[str, Any] | None:
    """Return runtime override value + timestamps for UI/status."""
    _ensure_table()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT value_json, updated_at, updated_by FROM runtime_settings WHERE key = ?",
            (key,),
        ).fetchone()
        if not row:
            return None
        return {
            "key": key,
            "value": json.loads(row["value_json"]),
            "updated_at": row["updated_at"],
            "updated_by": row["updated_by"],
        }
    finally:
        conn.close()


def set_runtime_value(key: str, value: Any, *, updated_by: str | None = None) -> None:
    _ensure_table()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO runtime_settings (key, value_json, updated_at, updated_by)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at = excluded.updated_at,
                updated_by = excluded.updated_by
            """,
            (key, json.dumps(value), _utc_now(), updated_by),
        )
        conn.commit()
    finally:
        conn.close()


def is_kill_switch_active(yaml_default: bool = False) -> bool:
    runtime = get_runtime_value("kill_switch")
    if runtime is not None:
        return bool(runtime)
    return yaml_default


def delete_runtime_value(key: str) -> None:
    _ensure_table()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM runtime_settings WHERE key = ?", (key,))
        conn.commit()
    finally:
        conn.close()


def set_kill_switch(enabled: bool, *, operator: str) -> bool:
    set_runtime_value("kill_switch", enabled, updated_by=operator)
    return enabled
