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


def migrate_benchmark_v2(conn: sqlite3.Connection) -> list[str]:
    """News archive for historical benchmark + published_at index."""
    applied: list[str] = []

    if not _column_exists(conn, "news_items", "benchmark_retained"):
        conn.execute(
            "ALTER TABLE news_items ADD COLUMN benchmark_retained INTEGER NOT NULL DEFAULT 0"
        )
        applied.append("news_items.benchmark_retained")

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_news_published_at
        ON news_items(published_at DESC)
        """
    )
    applied.append("idx_news_published_at")
    return applied


def migrate_system_activity_v1(conn: sqlite3.Connection) -> list[str]:
    applied: list[str] = []
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
    applied.append("system_activity_v1")
    return applied


def migrate_news_filter_v1(conn: sqlite3.Connection) -> list[str]:
    applied: list[str] = []
    if not _column_exists(conn, "news_items", "trade_relevant"):
        conn.execute(
            "ALTER TABLE news_items ADD COLUMN trade_relevant INTEGER NOT NULL DEFAULT 1"
        )
        applied.append("news_items.trade_relevant")
    if not _column_exists(conn, "news_items", "filter_meta"):
        conn.execute("ALTER TABLE news_items ADD COLUMN filter_meta TEXT")
        applied.append("news_items.filter_meta")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_news_trade_relevant
        ON news_items(trade_relevant, published_at DESC)
        """
    )
    return applied


def migrate_signals_engine_v1(conn: sqlite3.Connection) -> list[str]:
    """Signals Engine: LLM analysis persistence, news signals, user context."""
    applied: list[str] = []

    for col, ddl in [
        ("body_raw", "ALTER TABLE news_items ADD COLUMN body_raw TEXT"),
        ("llm_analysis_json", "ALTER TABLE news_items ADD COLUMN llm_analysis_json TEXT"),
        ("llm_model", "ALTER TABLE news_items ADD COLUMN llm_model TEXT"),
        ("llm_analyzed_at", "ALTER TABLE news_items ADD COLUMN llm_analyzed_at TEXT"),
    ]:
        if not _column_exists(conn, "news_items", col):
            conn.execute(ddl)
            applied.append(f"news_items.{col}")

    for col, ddl in [
        ("tags", "ALTER TABLE news_sources ADD COLUMN tags TEXT"),
        ("user_trust_override", "ALTER TABLE news_sources ADD COLUMN user_trust_override REAL"),
    ]:
        if not _column_exists(conn, "news_sources", col):
            conn.execute(ddl)
            applied.append(f"news_sources.{col}")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS news_signals (
            id                  TEXT PRIMARY KEY,
            news_item_id        TEXT NOT NULL,
            market              TEXT NOT NULL DEFAULT 'macro',
            symbols             TEXT NOT NULL,
            impact              TEXT,
            confidence          REAL,
            significance_score  REAL,
            headline_ru         TEXT,
            analysis_ru         TEXT,
            reasoning_trace     TEXT,
            model               TEXT,
            status              TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'consumed', 'expired', 'rejected')),
            consumed_by_event_id TEXT,
            consumed_at         TEXT,
            created_at          TEXT NOT NULL,
            expires_at          TEXT,
            FOREIGN KEY (news_item_id) REFERENCES news_items(id)
        )
        """
    )
    applied.append("news_signals")

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_news_signals_status
        ON news_signals(status, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_news_signals_item
        ON news_signals(news_item_id)
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS news_user_context (
            id              TEXT PRIMARY KEY,
            news_item_id    TEXT NOT NULL UNIQUE,
            operator        TEXT,
            context_text    TEXT NOT NULL DEFAULT '',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL,
            locked_at       TEXT
        )
        """
    )
    applied.append("news_user_context")
    return applied


def migrate_papers_p0_p2(conn: sqlite3.Connection) -> list[str]:
    applied: list[str] = []
    tables = [
        """
        CREATE TABLE IF NOT EXISTS backtest_runs (
            id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            label TEXT NOT NULL,
            symbol TEXT,
            timeframe TEXT,
            report_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'completed'
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS deepfund_sessions (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            started_at TEXT NOT NULL,
            ended_at TEXT,
            training_cutoff_date TEXT,
            started_by TEXT,
            metrics_json TEXT DEFAULT '{}'
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS deepfund_events (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            event_at TEXT NOT NULL,
            symbol TEXT,
            status TEXT,
            payload_json TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS neuratrade_results (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            model TEXT NOT NULL,
            symbol TEXT,
            score REAL,
            status TEXT,
            payload_json TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS papers_candidates (
            id TEXT PRIMARY KEY,
            discovered_at TEXT NOT NULL,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            published TEXT,
            url TEXT NOT NULL UNIQUE,
            relevance_score REAL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'approved', 'rejected', 'ingested'))
        )
        """,
    ]
    for ddl in tables:
        conn.execute(ddl)
    applied.extend(
        ["backtest_runs", "deepfund_sessions", "deepfund_events", "neuratrade_results", "papers_candidates"]
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_backtest_runs_at ON backtest_runs(started_at DESC)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_papers_candidates_status ON papers_candidates(status, discovered_at DESC)"
    )
    return applied


def migrate_host_capability_v1(conn: sqlite3.Connection) -> list[str]:
    applied: list[str] = []
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS host_capability_audits (
            id TEXT PRIMARY KEY,
            audited_at TEXT NOT NULL,
            report_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_host_capability_audits_at ON host_capability_audits(audited_at DESC)"
    )
    applied.append("host_capability_audits")
    return applied


def migrate_papers_v2(conn: sqlite3.Connection) -> list[str]:
    applied: list[str] = []
    for col, ddl in [
        ("citation_count", "ALTER TABLE papers_candidates ADD COLUMN citation_count INTEGER"),
        ("metadata_json", "ALTER TABLE papers_candidates ADD COLUMN metadata_json TEXT"),
        ("draft_path", "ALTER TABLE papers_candidates ADD COLUMN draft_path TEXT"),
        ("reviewed_at", "ALTER TABLE papers_candidates ADD COLUMN reviewed_at TEXT"),
    ]:
        if not _column_exists(conn, "papers_candidates", col):
            conn.execute(ddl)
            applied.append(f"papers_candidates.{col}")
    return applied


def migrate_neuratrade_v2(conn: sqlite3.Connection) -> list[str]:
    applied: list[str] = []
    for col, ddl in [
        ("case_id", "ALTER TABLE neuratrade_results ADD COLUMN case_id TEXT"),
        ("mode", "ALTER TABLE neuratrade_results ADD COLUMN mode TEXT"),
        ("latency_ms", "ALTER TABLE neuratrade_results ADD COLUMN latency_ms INTEGER"),
        ("expected_action", "ALTER TABLE neuratrade_results ADD COLUMN expected_action TEXT"),
        ("actual_action", "ALTER TABLE neuratrade_results ADD COLUMN actual_action TEXT"),
        ("pass_expected", "ALTER TABLE neuratrade_results ADD COLUMN pass_expected INTEGER"),
        ("ablation_id", "ALTER TABLE neuratrade_results ADD COLUMN ablation_id TEXT"),
    ]:
        if not _column_exists(conn, "neuratrade_results", col):
            conn.execute(ddl)
            applied.append(f"neuratrade_results.{col}")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_neuratrade_model_at ON neuratrade_results(model, recorded_at DESC)"
    )
    applied.append("idx_neuratrade_model_at")
    return applied


def migrate_workflow_reports_v1(conn: sqlite3.Connection) -> list[str]:
    applied: list[str] = []
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_session_reports (
            id TEXT PRIMARY KEY,
            market TEXT NOT NULL,
            workflow_name TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT NOT NULL,
            reason TEXT,
            report_json TEXT NOT NULL,
            llm_narrative_json TEXT,
            llm_model TEXT,
            llm_latency_ms INTEGER,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_workflow_session_reports_ended ON workflow_session_reports(ended_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_workflow_session_reports_market ON workflow_session_reports(market, ended_at DESC)"
    )
    applied.append("workflow_session_reports")
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
        benchmark_v2 = migrate_benchmark_v2(conn)
        system_activity = migrate_system_activity_v1(conn)
        signals_engine = migrate_signals_engine_v1(conn)
        news_filter = migrate_news_filter_v1(conn)
        papers_p0_p2 = migrate_papers_p0_p2(conn)
        papers_v2 = migrate_papers_v2(conn)
        host_cap = migrate_host_capability_v1(conn)
        neuratrade_v2 = migrate_neuratrade_v2(conn)
        workflow_reports = migrate_workflow_reports_v1(conn)
        conn.commit()
        return {
            "news_v2": news,
            "news_alerts_v1": alerts,
            "paper_v1": paper,
            "benchmark_v1": benchmark,
            "benchmark_v2": benchmark_v2,
            "system_activity_v1": system_activity,
            "signals_engine_v1": signals_engine,
            "news_filter_v1": news_filter,
            "papers_p0_p2": papers_p0_p2,
            "papers_v2": papers_v2,
            "host_capability_v1": host_cap,
            "neuratrade_v2": neuratrade_v2,
            "workflow_reports_v1": workflow_reports,
        }
    finally:
        if close:
            conn.close()
