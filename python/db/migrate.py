"""SQLite schema migrations (additive)."""

from __future__ import annotations

import sqlite3


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def migrate_news_v2(conn: sqlite3.Connection) -> list[str]:
    """Add verification columns for news authenticity pipeline."""
    applied: list[str] = []

    if not _column_exists(conn, "news_items", "verification_status"):
        conn.execute(
            "ALTER TABLE news_items ADD COLUMN verification_status TEXT NOT NULL DEFAULT 'pending'"
        )
        applied.append("news_items.verification_status")

    if not _column_exists(conn, "news_items", "trust_score"):
        conn.execute("ALTER TABLE news_items ADD COLUMN trust_score REAL DEFAULT 0")
        applied.append("news_items.trust_score")

    if not _column_exists(conn, "news_items", "matched_symbols"):
        conn.execute("ALTER TABLE news_items ADD COLUMN matched_symbols TEXT")
        applied.append("news_items.matched_symbols")

    if not _column_exists(conn, "news_items", "reject_reasons"):
        conn.execute("ALTER TABLE news_items ADD COLUMN reject_reasons TEXT")
        applied.append("news_items.reject_reasons")

    if not _column_exists(conn, "news_sources", "allowed_domains"):
        conn.execute("ALTER TABLE news_sources ADD COLUMN allowed_domains TEXT")
        applied.append("news_sources.allowed_domains")

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_news_verification
        ON news_items(verification_status, trust_score)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_news_matched_symbols
        ON news_items(matched_symbols)
        """
    )
    return applied


def migrate_news_alerts_v1(conn: sqlite3.Connection) -> list[str]:
    applied: list[str] = []
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS news_alert_deliveries (
            id              TEXT PRIMARY KEY,
            alert_type      TEXT NOT NULL CHECK (alert_type IN ('news', 'trade')),
            ref_id          TEXT NOT NULL,
            sent_at         TEXT NOT NULL,
            payload_json    TEXT,
            UNIQUE(alert_type, ref_id)
        )
        """
    )
    applied.append("news_alert_deliveries")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_news_alert_deliveries_sent
        ON news_alert_deliveries(sent_at DESC)
        """
    )
    return applied


def run_migrations(conn: sqlite3.Connection | None = None) -> dict[str, list[str]]:
    close = False
    if conn is None:
        from db.connection import get_connection

        conn = get_connection()
        close = True
    try:
        news = migrate_news_v2(conn)
        alerts = migrate_news_alerts_v1(conn)
        conn.commit()
        return {"news_v2": news, "news_alerts_v1": alerts}
    finally:
        if close:
            conn.close()
