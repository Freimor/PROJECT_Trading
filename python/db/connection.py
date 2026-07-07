"""SQLite connection helper."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def get_db_path() -> Path:
    raw = os.environ.get("TRADING_DB_PATH", "data/trading.db")
    path = Path(raw)
    if not path.is_absolute():
        # Resolve relative to project root (parent of python/)
        project_root = Path(__file__).resolve().parents[2]
        path = project_root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn
