-- PROJECT Trading — схема SQLite (этап 1)
-- Инициализация: python -m db.init_db  или  POST /admin/init

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ============================================================
-- Системные события и health-check
-- ============================================================

CREATE TABLE IF NOT EXISTS system_health_checks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    checked_at      TEXT NOT NULL DEFAULT (datetime('now')),
    service_name    TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('ok', 'warn', 'critical', 'unknown')),
    latency_ms      INTEGER,
    details         TEXT,
  -- JSON: url, http_code, error_message
    workflow_id     TEXT,
    execution_id    TEXT
);

CREATE INDEX IF NOT EXISTS idx_health_checked_at ON system_health_checks(checked_at);
CREATE INDEX IF NOT EXISTS idx_health_service ON system_health_checks(service_name);

-- ============================================================
-- Единый журнал событий торговой системы
-- ============================================================

CREATE TABLE IF NOT EXISTS trade_events (
    id              TEXT PRIMARY KEY,
  -- UUID v4
    event_at        TEXT NOT NULL DEFAULT (datetime('now')),
    market          TEXT NOT NULL CHECK (market IN ('crypto', 'securities', 'shared')),
    env             TEXT NOT NULL CHECK (env IN ('dry_run', 'paper', 'shadow', 'live')),
    stage           TEXT NOT NULL CHECK (stage IN (
                        'signal', 'filter', 'llm', 'guardrails', 'risk',
                        'order', 'fill', 'cancel', 'reconcile', 'error'
                    )),
    symbol          TEXT,
    decision        TEXT CHECK (decision IN ('approve', 'reject', 'execute', 'skip', 'error', 'halt')),
    reject_reason   TEXT,
    workflow_name   TEXT,
    execution_id    TEXT,
    request_id      TEXT,
  -- idempotency key для ордеров
    inputs_hash     TEXT,
  -- SHA-256 контекста для replay (блок 4)
    prompt_version  TEXT,
    model           TEXT,
    confidence      REAL,
    latency_ms      INTEGER,
    payload_json    TEXT NOT NULL DEFAULT '{}',
  -- полный контекст: indicators, llm_response, order_params
    pnl             REAL,
    notional        REAL,
    currency          TEXT DEFAULT 'USD'
);

CREATE INDEX IF NOT EXISTS idx_events_event_at ON trade_events(event_at);
CREATE INDEX IF NOT EXISTS idx_events_market ON trade_events(market);
CREATE INDEX IF NOT EXISTS idx_events_stage ON trade_events(stage);
CREATE INDEX IF NOT EXISTS idx_events_symbol ON trade_events(symbol);
CREATE INDEX IF NOT EXISTS idx_events_inputs_hash ON trade_events(inputs_hash);
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_request_id ON trade_events(request_id)
    WHERE request_id IS NOT NULL;

-- ============================================================
-- LLM-решения (детальный аудит для evaluation pipeline)
-- ============================================================

CREATE TABLE IF NOT EXISTS llm_decisions (
    id              TEXT PRIMARY KEY,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    trade_event_id  TEXT REFERENCES trade_events(id),
    market          TEXT NOT NULL,
    model           TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    system_prompt_hash TEXT,
    user_context_hash  TEXT,
    inputs_hash     TEXT NOT NULL,
    raw_response    TEXT,
    parsed_action   TEXT CHECK (parsed_action IN ('approve', 'reject', 'error')),
    confidence      REAL,
    counter_thesis  TEXT,
    latency_ms      INTEGER,
    tokens_prompt   INTEGER,
    tokens_completion INTEGER,
    reject_reason   TEXT
);

CREATE INDEX IF NOT EXISTS idx_llm_created_at ON llm_decisions(created_at);
CREATE INDEX IF NOT EXISTS idx_llm_model ON llm_decisions(model);
CREATE INDEX IF NOT EXISTS idx_llm_inputs_hash ON llm_decisions(inputs_hash);

-- ============================================================
-- Тактические новости (этап 3 — таблица готова заранее)
-- ============================================================

CREATE TABLE IF NOT EXISTS news_items (
    id              TEXT PRIMARY KEY,
    fetched_at      TEXT NOT NULL DEFAULT (datetime('now')),
    published_at    TEXT,
    source_name     TEXT NOT NULL,
    source_tier     TEXT NOT NULL CHECK (source_tier IN ('official', 'media', 'aggregator', 'social')),
    source_url      TEXT,
    title           TEXT NOT NULL,
    summary         TEXT,
    dedup_hash      TEXT NOT NULL,
    relevance_score REAL DEFAULT 0,
    symbols         TEXT,
  -- JSON array: ["BTC", "SBER"]
    matched_symbols TEXT,
  -- JSON: entity-matched tickers from title/summary
    verification_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (verification_status IN ('verified', 'rejected', 'pending')),
    trust_score     REAL DEFAULT 0,
    reject_reasons  TEXT,
  -- JSON array
    expires_at      TEXT,
    raw_json        TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_news_dedup ON news_items(dedup_hash);
CREATE INDEX IF NOT EXISTS idx_news_published ON news_items(published_at);
CREATE INDEX IF NOT EXISTS idx_news_expires ON news_items(expires_at);

CREATE TABLE IF NOT EXISTS news_alert_deliveries (
    id              TEXT PRIMARY KEY,
    alert_type      TEXT NOT NULL CHECK (alert_type IN ('news', 'trade')),
    ref_id          TEXT NOT NULL,
    sent_at         TEXT NOT NULL,
    payload_json    TEXT,
    UNIQUE(alert_type, ref_id)
);

CREATE INDEX IF NOT EXISTS idx_news_alert_deliveries_sent
    ON news_alert_deliveries(sent_at DESC);

-- ============================================================
-- Источники новостей (конфигурация ingest)
-- ============================================================

CREATE TABLE IF NOT EXISTS news_sources (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    source_tier     TEXT NOT NULL,
    feed_type       TEXT NOT NULL CHECK (feed_type IN ('rss', 'api', 'manual')),
    feed_url        TEXT,
    enabled         INTEGER NOT NULL DEFAULT 1,
    fetch_interval_min INTEGER DEFAULT 15,
    ttl_hours       INTEGER DEFAULT 48,
    symbols_filter  TEXT,
  -- JSON
    allowed_domains TEXT,
  -- JSON: domains allowed in article links
    last_fetched_at TEXT,
    last_error      TEXT
);

-- ============================================================
-- Свечи (кэш для бэктеста и replay)
-- ============================================================

CREATE TABLE IF NOT EXISTS ohlcv_candles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    market          TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    timeframe       TEXT NOT NULL,
    candle_time     TEXT NOT NULL,
    open            REAL NOT NULL,
    high            REAL NOT NULL,
    low             REAL NOT NULL,
    close           REAL NOT NULL,
    volume          REAL,
    fetched_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (market, symbol, timeframe, candle_time)
);

CREATE INDEX IF NOT EXISTS idx_ohlcv_lookup
    ON ohlcv_candles(market, symbol, timeframe, candle_time);

-- ============================================================
-- Снимки позиций (reconciliation)
-- ============================================================

CREATE TABLE IF NOT EXISTS position_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_at     TEXT NOT NULL DEFAULT (datetime('now')),
    market          TEXT NOT NULL,
    env             TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    quantity        REAL NOT NULL,
    avg_price       REAL,
    unrealized_pnl  REAL,
    source          TEXT NOT NULL CHECK (source IN ('exchange', 'local', 'reconciled')),
    raw_json        TEXT
);

CREATE INDEX IF NOT EXISTS idx_positions_snapshot_at ON position_snapshots(snapshot_at);

-- ============================================================
-- Метаданные wiki (для pipeline актуализации)
-- ============================================================

CREATE TABLE IF NOT EXISTS wiki_page_meta (
    file_path       TEXT PRIMARY KEY,
    title           TEXT,
    updated_at      TEXT,
    content_hash    TEXT,
    rag_indexed_at  TEXT,
    broken_links    INTEGER DEFAULT 0,
    last_checked_at TEXT
);

-- ============================================================
-- Версии промптов и конфигов (аудит)
-- ============================================================

CREATE TABLE IF NOT EXISTS config_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at     TEXT NOT NULL DEFAULT (datetime('now')),
    config_name     TEXT NOT NULL,
  -- guardrails.yaml, crypto_config.yaml, ...
    content_hash    TEXT NOT NULL,
    git_commit      TEXT,
    content_snapshot TEXT
);

CREATE INDEX IF NOT EXISTS idx_config_name ON config_versions(config_name, recorded_at);

-- ============================================================
-- Runtime overrides (kill switch и др.)
-- ============================================================

CREATE TABLE IF NOT EXISTS runtime_settings (
    key             TEXT PRIMARY KEY,
    value_json      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    updated_by      TEXT
);

-- ============================================================
-- Подтверждения оператором (web / telegram)
-- ============================================================

CREATE TABLE IF NOT EXISTS operator_confirmations (
    id              TEXT PRIMARY KEY,
    created_at      TEXT NOT NULL,
    expires_at      TEXT NOT NULL,
    action_type     TEXT NOT NULL,
    title           TEXT NOT NULL,
    payload_json    TEXT NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'pending',
    operator        TEXT,
    resolved_at     TEXT,
    source          TEXT
);

CREATE INDEX IF NOT EXISTS idx_confirmations_status ON operator_confirmations(status);
