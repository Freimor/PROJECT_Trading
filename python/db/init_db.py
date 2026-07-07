"""Initialize SQLite schema from data/schema.sql."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from db.connection import get_connection, get_db_path
from db.migrate import run_migrations


def _schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "schema.sql"


def init_database(*, force: bool = False) -> Path:
    db_path = get_db_path()
    if db_path.exists() and not force:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='trade_events'"
            ).fetchone()
            if row:
                run_migrations(conn)
                return db_path
        finally:
            conn.close()

    schema_sql = _schema_path().read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
        run_migrations(conn)
    finally:
        conn.close()
    return db_path


if __name__ == "__main__":
    path = init_database()
    print(f"Database ready: {path}")
