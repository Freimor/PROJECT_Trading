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


def migrate_paper_v1(conn: sqlite3.Connection) -> list[str]:
    applied: list[str] = []
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS paper_sessions (
            id              TEXT PRIMARY KEY,
            label           TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'closed')),
            started_at      TEXT NOT NULL,
            ended_at        TEXT,
            started_by      TEXT,
            baseline_json   TEXT,
            notes           TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS paper_portfolio_snapshots (
            id              TEXT PRIMARY KEY,
            session_id      TEXT,
            captured_at     TEXT NOT NULL,
            snapshot_json   TEXT NOT NULL,
            trigger         TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_paper_sessions_status
        ON paper_sessions(status, started_at DESC)
        """
    )
    applied.append("paper_sessions")
    applied.append("paper_portfolio_snapshots")
    return applied


def migrate_benchmark_v1(conn: sqlite3.Connection) -> list[str]:
    applied: list[str] = []
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS benchmark_cases (
            inputs_hash     TEXT PRIMARY KEY,
            market          TEXT NOT NULL,
            symbol          TEXT NOT NULL,
            decision_at     TEXT NOT NULL,
            indicators_json TEXT NOT NULL,
            original_action TEXT,
            original_model  TEXT,
            prompt_version  TEXT,
            confidence      REAL,
            source          TEXT NOT NULL DEFAULT 'live'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS benchmark_labels (
            id                  TEXT PRIMARY KEY,
            inputs_hash         TEXT NOT NULL UNIQUE,
            horizon_bars        INTEGER NOT NULL,
            forward_return_pct  REAL,
            label               TEXT NOT NULL,
            labeled_at          TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS benchmark_runs (
            id              TEXT PRIMARY KEY,
            started_at      TEXT NOT NULL,
            ended_at        TEXT,
            label           TEXT NOT NULL,
            model           TEXT,
            prompt_version  TEXT,
            cases_count     INTEGER NOT NULL DEFAULT 0,
            status          TEXT NOT NULL DEFAULT 'running'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS benchmark_results (
            id                      TEXT PRIMARY KEY,
            run_id                  TEXT NOT NULL,
            inputs_hash             TEXT NOT NULL,
            action                  TEXT,
            confidence              REAL,
            latency_ms              INTEGER,
            changed_from_original   INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_benchmark_cases_decision
        ON benchmark_cases(decision_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_benchmark_labels_hash
        ON benchmark_labels(inputs_hash)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_benchmark_results_run
        ON benchmark_results(run_id)
        """
    )
    applied.extend(
        [
            "benchmark_cases",
            "benchmark_labels",
            "benchmark_runs",
            "benchmark_results",
        ]
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
        paper = migrate_paper_v1(conn)
        benchmark = migrate_benchmark_v1(conn)
        conn.commit()
        return {
            "news_v2": news,
            "news_alerts_v1": alerts,
            "paper_v1": paper,
            "benchmark_v1": benchmark,
        }
    finally:
        if close:
            conn.close()
