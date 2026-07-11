"""HTTP API for n8n workflows — full trading automation backend."""

from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import Body, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from operator_auth import (
    admin_key_configured,
    operator_auth_required,
    operator_password_configured,
    verify_operator_auth,
)
from binance_client import get_account_balances, get_open_orders
from binance_trading import get_open_position, get_trading_equity, place_market_order
from crypto_product import get_crypto_trading_product
from bridges.tinvest_bridge import check_tinvest_connection, get_portfolio_snapshot, post_dca_order
from testing_service import get_testing_overview, get_tinvest_sandbox_dashboard
from automation_control_service import (
    apply_market_operation_mode,
    apply_operation_mode,
    apply_trading_mode,
    add_market_workflow,
    clear_market_mode,
    clear_trading_mode,
    get_active_market_workflow,
    get_automation_control_state,
    get_market_control_state,
    get_market_diagnostics,
    is_multi_automation_enabled,
    normalize_trading_mode,
    operation_mode_detail,
    run_workflow_once,
    set_multi_automation_enabled,
    stop_single_market_workflow,
    sync_market_workflows,
    toggle_workflow_by_name,
    select_market_workflow,
    start_market_workflow,
    stop_market_workflows,
    trading_mode_to_operation,
)
from strategy_service import get_strategy_state, set_active_strategy, symbols_for_workflow
from risk_profile_service import get_risk_profile_state, reset_risk_profile, set_risk_profile
from asset_catalog_service import search_assets
from workflow_universe_service import (
    WORKFLOW_REGISTRY,
    add_symbols_to_workflow,
    apply_llm_universe_suggestion,
    get_workflow_universe,
    remove_symbol_from_workflow,
    reset_workflow_universe,
    save_workflow_universe,
    set_symbol_enabled,
    suggest_universe_with_llm,
    _fallback_universe_suggestion,
)
from admin_service import (
    apply_kill_switch,
    create_confirmation,
    get_live_checklist,
    get_system_status,
    list_pending_confirmations,
    notify_telegram,
    resolve_confirmation,
    run_smoke_test,
    services_restart_plan,
    stats_digest,
)
from bot_data_service import (
    automat_documentation,
    get_automation_overview,
    get_crypto_testnet_dashboard,
    get_host_status,
    get_system_summary,
    list_recent_news,
    list_signal_news_feed,
    wiki_table_of_contents,
)
from config_loader import load_config, wiki_root
from crypto_pipeline import run_crypto_signal
from crypto_scalp_pipeline import run_crypto_scalp_signal
from effective_config import get_config_effective, get_guardrails
from db.connection import get_connection, get_db_path
from db.init_db import init_database
from evaluation.replay import champion_challenger_report, evaluation_metrics, replay_by_inputs_hash
from event_log import log_event
from guardrails import enforce_guardrails, position_size_dry_run
from indicators.technical import compute_indicators, parse_binance_klines, rule_filter
from llm_client import list_ollama_models, reset_ollama_cache, validate_signal
from news_service import (
    ingest_all,
    list_news_for_symbol,
    news_context_for_symbols,
    news_verification_stats,
    purge_expired,
    seed_sources,
)
from news_alert_service import (
    get_alert_settings,
    process_news_alerts,
    resolve_watch_symbols,
    update_alert_settings,
)
from signals_engine_service import (
    analyze_news_item,
    analyze_pending_news,
    get_engine_settings,
    list_sources_enriched,
    save_user_context,
    update_engine_settings,
    update_news_source,
    reapply_trade_filters,
)
from paper_trading_service import (
    capture_snapshot,
    get_paper_config,
    paper_effectiveness,
    reset_paper_session,
    run_crypto_paper_trade,
    run_crypto_scalp_paper_trade,
    run_securities_swing_paper,
    start_paper_session,
)
from n8n_service import (
    activate_workflow,
    deactivate_workflow,
    import_all_workflows,
    import_market_workflows,
    list_workflows,
    set_workflow_cron,
)
from benchmark_service import (
    aggregate_golden_results,
    benchmark_report,
    benchmark_report_by_model,
    get_benchmark_snapshot,
    label_outcomes,
    list_golden_cases,
    run_full_benchmark,
    run_golden_benchmark,
    run_benchmark_replay,
    run_one_golden_case,
    sample_benchmark_cases,
    save_benchmark_snapshot,
)
from calibration_service import (
    cancel_calibration_job,
    finalize_calibration,
    get_calibration_job_status,
    get_calibration_plan,
    get_calibration_snapshot,
    get_llm_settings_snapshot,
    list_calibration_jobs_status,
    run_calibration,
    run_calibration_temperature,
    start_calibration_job,
)
from backtest.metrics import dry_run_funnel, signal_summary
from backtest.finsaber import list_backtest_runs, run_walk_forward_backtest
from deepfund_service import close_session, get_active_session, run_deepfund_cycle, start_session
from factor_sleeve_service import factor_sleeve_rebalance_plan, rank_factor_universe
from regulatory_monitor import scan_regulatory_risk
from papers_monitor import (
    create_obsidian_draft,
    ingest_paper_candidates,
    list_candidates,
    list_pending_candidates,
    research_dashboard,
    update_candidate_status,
)
from neuratrade_harness import get_leaderboard, recommend_model, run_harness_cycle
from on_chain.metrics import compute_on_chain_context
from bond_ladder_service import evaluate_bond_ladder
from geopolitical_risk import compute_geopolitical_score, geo_adjust_notional
from host_capability_service import get_last_host_audit, run_host_capability_audit
from workflow_report_service import (
    finalize_workflow_session,
    get_workflow_report,
    list_workflow_reports,
)
from trading_agents.orchestrator import run_trading_agents
from charts_service import get_chart_candles, get_chart_indicators, get_chart_markers, list_symbols_for_market
from llm_audit_service import get_llm_decision, list_llm_decisions
from portfolio_snapshot_service import capture_exchange_position_snapshots, get_equity_curve
from portfolio_performance_service import get_portfolio_performance
from historical_benchmark_service import (
    get_historical_snapshot,
    list_historical_cases,
    promote_live_case_to_historical,
    run_historical_benchmark,
    run_one_historical_case,
    save_historical_snapshot,
)
from securities_pipeline import run_securities_dca_dry_run, run_securities_swing_dry_run
from event_summary import summarize_trade_event
from event_context_service import build_event_context
from activity_feed_service import get_activity_feed, log_system_activity
from market_llm_config import normalize_market
from telegram_proxy import proxy_status, select_working_proxy
from runtime_settings import set_runtime_value


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    seed_sources()
    try:
        from news_service import ingest_all, news_verification_stats, purge_expired

        stats = news_verification_stats()
        if sum(stats.get("by_status", {}).values()) == 0:
            purge_expired()
            ingest_all()
            log_system_activity("Первичная загрузка новостей", category="news", level="info")
    except Exception as exc:
        log_system_activity(f"News bootstrap: {exc}", category="news", level="warn")
    try:
        from automation_control_service import reset_workflows_on_boot

        for market in ("crypto", "securities"):
            result = reset_workflows_on_boot(market)
            deactivated = [
                w["name"] for w in result.get("workflows", []) if w.get("action") == "deactivated"
            ]
            if deactivated:
                log_system_activity(
                    f"Старт: выключены workflow ({market}): {', '.join(deactivated)}",
                    category="control",
                    level="info",
                )
            if result.get("status") == "error":
                log_system_activity(
                    f"Сброс workflow при старте ({market}): {result.get('message')}",
                    category="control",
                    level="warn",
                )
    except Exception as exc:
        log_system_activity(f"Сброс workflow при старте: {exc}", category="control", level="warn")
    try:
        from ollama_manager_service import bootstrap_ollama_models_background

        bootstrap_ollama_models_background()
    except Exception as exc:
        log_system_activity(f"Ollama bootstrap: {exc}", category="system", level="warn")
    log_system_activity("Старт системы", category="system", level="success")
    yield


app = FastAPI(
    title="PROJECT Trading DB API",
    version="1.0.0",
    description="Backend для n8n: индикаторы, pipeline, новости, ордера, evaluation.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---

class HealthCheckItem(BaseModel):
    service_name: str
    status: Literal["ok", "warn", "critical", "unknown"]
    latency_ms: int | None = None
    details: dict[str, Any] | None = None
    workflow_id: str | None = None
    execution_id: str | None = None


class HealthBatchRequest(BaseModel):
    checks: list[HealthCheckItem]


class N8nCronRequest(BaseModel):
    cron_expression: str = Field(..., min_length=1, max_length=120)
    node_id: str | None = None
    node_name: str | None = None


class TradeEventRequest(BaseModel):
    market: Literal["crypto", "securities", "shared"]
    env: Literal["dry_run", "paper", "shadow", "live"] = "dry_run"
    stage: Literal[
        "signal", "filter", "llm", "guardrails", "risk",
        "order", "fill", "cancel", "reconcile", "error"
    ]
    symbol: str | None = None
    decision: Literal["approve", "reject", "execute", "skip", "error", "halt"] | None = None
    reject_reason: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    request_id: str | None = None
    inputs_hash: str | None = None
    prompt_version: str | None = None
    model: str | None = None
    confidence: float | None = None
    latency_ms: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    pnl: float | None = None
    notional: float | None = None
    currency: str = "USD"
    event_id: str | None = None
    event_at: str | None = None


class CryptoSignalRequest(BaseModel):
    symbol: str
    env: Literal["dry_run", "paper", "shadow", "live"] = "dry_run"
    skip_llm: bool = False
    equity: float = 10000.0


class BinanceOrderRequest(BaseModel):
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    testnet: bool = True
    request_id: str | None = None
    env: Literal["paper", "live"] = "paper"
    reduce_only: bool = False
    product: Literal["auto", "spot", "usdt_futures"] = "auto"


class SecuritiesSwingRequest(BaseModel):
    ticker: str
    env: Literal["dry_run", "paper", "shadow", "live"] = "dry_run"
    skip_llm: bool = False


class TinvestDcaRequest(BaseModel):
    ticker: str | None = None
    amount_rub: float | None = None
    sandbox: bool = True
    dry_run: bool = True


class ReplayRequest(BaseModel):
    inputs_hash: str
    model: str | None = None
    prompt_version: str | None = None


class ChampionRequest(BaseModel):
    inputs_hashes: list[str]
    champion_model: str
    challenger_model: str
    prompt_version: str = "crypto_validate_v1"


class BenchmarkRunRequest(BaseModel):
    days: int = 30
    market: Literal["crypto", "securities"] | None = None
    model: str | None = None
    challenger_model: str | None = None
    skip_golden: bool = False


class BenchmarkReplayRequest(BaseModel):
    model: str | None = None
    prompt_version: str | None = None
    market: Literal["crypto", "securities"] | None = None
    limit: int = 30


class GoldenOneRequest(BaseModel):
    case_id: str
    market: Literal["crypto", "securities"]
    model: str | None = None


class BenchmarkSnapshotRequest(BaseModel):
    golden: dict[str, Any]
    report: dict[str, Any] | None = None
    kind: str = "golden"


class CalibrationRequest(BaseModel):
    model: str | None = None
    market: Literal["crypto", "securities"] | None = None
    temperatures: list[float] | None = None
    min_confidence: list[float] | None = None
    operator: str = "web"


class CalibrationTemperatureRequest(BaseModel):
    temperature: float
    model: str | None = None
    market: Literal["crypto", "securities"] | None = None


class StrategySelectRequest(BaseModel):
    strategy_id: str
    operator: str = "web:operator"


class RiskProfileSetRequest(BaseModel):
    profile_id: str
    operator: str = "web:operator"


class KillSwitchRequest(BaseModel):
    enabled: bool
    operator: str = "api"
    source: str = "web"


class TradingModeRequest(BaseModel):
    mode: Literal["demo", "live", "dry_run", "paper", "shadow"]
    operator: str = "web:operator"
    apply_workflows: bool = True


class MarketModeRequest(BaseModel):
    mode: Literal["demo", "live"]
    operator: str = "web:operator"
    apply_workflows: bool = True
    password: str | None = None


class WorkflowToggleRequest(BaseModel):
    active: bool
    operator: str = "web:operator"


class ConfirmationRequest(BaseModel):
    action_type: str
    title: str
    payload: dict[str, Any] = Field(default_factory=dict)
    ttl_minutes: int = 5
    source: str = "api"


class ConfirmationResolveRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    operator: str = "api"


class TelegramNotifyRequest(BaseModel):
    level: str = "INFO"
    message: str


class NewsAlertsSettingsRequest(BaseModel):
    news_enabled: bool | None = None
    trade_enabled: bool | None = None
    trade_push: bool | None = None
    operator: str = "api"


class SignalsEngineSettingsRequest(BaseModel):
    analysis_enabled: bool | None = None
    analyze_on_ingest: bool | None = None
    batch_size: int | None = Field(None, ge=1, le=50)
    min_confidence: float | None = Field(None, ge=0, le=1)
    min_significance_score: float | None = Field(None, ge=0, le=1)
    max_signals_per_symbol: int | None = Field(None, ge=1, le=20)
    include_user_context: bool | None = None
    filter_enabled: bool | None = None
    active_tags: list[str] | None = None
    keywords_include: list[str] | None = None
    keywords_exclude: list[str] | None = None
    require_symbol_or_keyword: bool | None = None
    filter_mode: str | None = Field(None, pattern="^(loose|balanced|strict)$")
    min_keywords: int | None = Field(None, ge=1, le=10)
    min_relevance_score: float | None = Field(None, ge=0, le=10)
    require_keyword_in_title: bool | None = None
    operator: str = "api"


class NewsUserContextRequest(BaseModel):
    context_text: str = Field("", max_length=2000)
    operator: str = "console"


class NewsSourceUpdateRequest(BaseModel):
    enabled: bool | None = None
    tags: list[str] | None = None
    user_trust_override: float | None = Field(None, ge=0, le=1)
    clear_trust_override: bool = False


class WorkflowUniverseSaveRequest(BaseModel):
    items: list[dict[str, Any]]
    operator: str = "web:operator"


class WorkflowUniverseAddRequest(BaseModel):
    symbols: list[str]
    enabled: bool = True
    operator: str = "web:operator"


class WorkflowUniverseToggleRequest(BaseModel):
    symbol: str
    enabled: bool
    operator: str = "web:operator"


class WorkflowUniverseLlmRequest(BaseModel):
    mode: Literal["replace", "merge"] = "merge"
    disable_others: bool = False
    hint: str | None = None
    apply: bool = False
    operator: str = "web:operator"


class WorkflowSelectRequest(BaseModel):
    workflow_name: str
    trading_mode: Literal["dry_run", "paper", "live"] | None = None
    session_volume_mode: Literal["stablecoin", "existing_holdings"] | None = None
    session_capital: float | None = Field(None, gt=0, le=100_000_000)
    use_existing_holdings: bool = False
    existing_holdings_unit: Literal["percent", "absolute"] = "percent"
    existing_holdings_use_pct: float = Field(0, ge=0, le=100)
    existing_holdings_use_qty: float | None = Field(None, gt=0)
    liquidate_on_stop: bool = False
    liquidate_on_margin_call: bool | None = None
    additive: bool = False
    operator: str = "web:operator"


class MultiAutomationRequest(BaseModel):
    enabled: bool
    operator: str = "web:operator"


class WorkflowStopOneRequest(BaseModel):
    workflow_name: str
    operator: str = "web:operator"


class CryptoQuoteAssetRequest(BaseModel):
    quote_asset: str
    operator: str = "web:operator"


class CryptoTradingProductRequest(BaseModel):
    market_type: Literal["spot", "usdt_futures"]
    allow_short: bool = False
    leverage: int = Field(3, ge=1, le=20)
    margin_mode: Literal["isolated", "cross"] = "isolated"
    operator: str = "web:operator"


class ScalpScanSettingsPatch(BaseModel):
    top_n: int | None = Field(None, ge=1, le=10)
    min_score: float | None = Field(None, ge=0.1, le=0.95)
    atr_pct_min: float | None = Field(None, ge=0.2, le=1.5)
    atr_pct_max: float | None = Field(None, ge=0.5, le=5.0)
    atr_pct_sweet_min: float | None = Field(None, ge=0.2, le=2.0)
    atr_pct_sweet_max: float | None = Field(None, ge=0.3, le=3.0)
    volume_ratio_min: float | None = Field(None, ge=0.5, le=3.0)
    momentum_min_pct: float | None = Field(None, ge=0.02, le=1.0)
    max_pair_correlation: float | None = Field(None, ge=0.5, le=0.99)
    rescan_interval_hours: int | None = Field(None, ge=1, le=24)
    rescan_during_session: bool | None = None
    operator: str = "web:operator"


class ScalpScanRunRequest(BaseModel):
    workflow_name: str = "crypto-scalp-hybrid-paper"
    settings: ScalpScanSettingsPatch | None = None


class ScalpScanApplyRequest(BaseModel):
    workflow_name: str = "crypto-scalp-hybrid-paper"
    symbols: list[str]
    scan_id: str | None = None
    operator: str = "web:operator"


class WorkflowScheduleRequest(BaseModel):
    option_id: str
    operator: str = "web:operator"


class WorkflowRunOnceRequest(BaseModel):
    workflow_name: str
    operator: str = "web:operator"


def _check_admin_key(
    admin_key: str | None = None,
    *,
    operator_password: str | None = None,
) -> None:
    _check_operator_auth(password=operator_password, admin_key=admin_key)


def _check_operator_auth(
    *,
    password: str | None = None,
    admin_key: str | None = None,
) -> None:
    if not verify_operator_auth(password=password, admin_key=admin_key):
        raise HTTPException(status_code=401, detail="OPERATOR_PASSWORD_INVALID")


@app.get("/api/auth/operator")
def operator_auth_status(
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    return {
        "password_required": operator_auth_required(),
        "operator_password_configured": operator_password_configured(),
        "admin_key_configured": admin_key_configured(),
        "authenticated": verify_operator_auth(
            password=x_operator_password,
            admin_key=x_admin_key,
        ),
    }


# --- Health & admin ---

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "db_path": str(get_db_path()), "wiki": str(wiki_root())}


@app.post("/admin/init")
def admin_init(force: bool = False) -> dict[str, str]:
    path = init_database(force=force)
    seed_sources()
    return {"status": "initialized", "db_path": str(path)}


@app.post("/api/health/batch")
def log_health_batch(body: HealthBatchRequest) -> dict[str, Any]:
    conn = get_connection()
    try:
        for check in body.checks:
            conn.execute(
                """
                INSERT INTO system_health_checks
                    (checked_at, service_name, status, latency_ms, details,
                     workflow_id, execution_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _utc_now(), check.service_name, check.status, check.latency_ms,
                    json.dumps(check.details or {}, ensure_ascii=False),
                    check.workflow_id, check.execution_id,
                ),
            )
        conn.commit()
        return {"inserted": len(body.checks)}
    finally:
        conn.close()


@app.get("/api/health/latest")
def health_latest(limit: int = 20) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM system_health_checks ORDER BY checked_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# --- Events ---

@app.post("/api/events")
def log_trade_event(body: TradeEventRequest) -> dict[str, str]:
    event_id = body.event_id or str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO trade_events (
                id, event_at, market, env, stage, symbol, decision, reject_reason,
                workflow_name, execution_id, request_id, inputs_hash, prompt_version,
                model, confidence, latency_ms, payload_json, pnl, notional, currency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id, body.event_at or _utc_now(), body.market, body.env, body.stage,
                body.symbol, body.decision, body.reject_reason, body.workflow_name,
                body.execution_id, body.request_id, body.inputs_hash, body.prompt_version,
                body.model, body.confidence, body.latency_ms,
                json.dumps(body.payload, ensure_ascii=False),
                body.pnl, body.notional, body.currency,
            ),
        )
        conn.commit()
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc) and body.request_id:
            raise HTTPException(status_code=409, detail="duplicate request_id") from exc
        raise
    finally:
        conn.close()
    return {"event_id": event_id}


@app.get("/api/events")
def list_trade_events(
    market: str | None = None,
    stage: str | None = None,
    stages: str | None = None,
    env: str | None = None,
    decision: str | None = None,
    symbol: str | None = None,
    days: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        query = "SELECT * FROM trade_events WHERE 1=1"
        params: list[Any] = []
        if market:
            query += " AND market = ?"
            params.append(market)
        if stages:
            stage_list = [s.strip() for s in stages.split(",") if s.strip()]
            if stage_list:
                placeholders = ",".join("?" * len(stage_list))
                query += f" AND stage IN ({placeholders})"
                params.extend(stage_list)
        elif stage:
            query += " AND stage = ?"
            params.append(stage)
        if env:
            query += " AND env = ?"
            params.append(env)
        if decision:
            query += " AND decision = ?"
            params.append(decision)
        if symbol:
            query += " AND UPPER(COALESCE(symbol, '')) = ?"
            params.append(symbol.upper())
        if days is not None and days > 0:
            query += (
                " AND datetime(REPLACE(SUBSTR(event_at, 1, 19), 'T', ' ')) "
                ">= datetime('now', ?)"
            )
            params.append(f"-{int(days)} days")
        query += " ORDER BY event_at DESC LIMIT ?"
        params.append(limit)
        rows = [dict(row) for row in conn.execute(query, params).fetchall()]
        for row in rows:
            row["summary"] = summarize_trade_event(row)
        return rows
    finally:
        conn.close()


@app.get("/api/events/{event_id}")
def get_trade_event(event_id: str) -> dict[str, Any]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM trade_events WHERE id = ?", (event_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="event_not_found")
        data = dict(row)
        data["summary"] = summarize_trade_event(data)
        data["context"] = build_event_context(data)
        return data
    finally:
        conn.close()


@app.get("/api/charts/candles")
def charts_candles(
    market: Literal["crypto", "securities"] = "crypto",
    symbol: str = "BTCUSDT",
    interval: str = "4h",
    limit: int = 200,
    testnet: bool = True,
    use_cache: bool = False,
) -> dict[str, Any]:
    return get_chart_candles(
        market=market,
        symbol=symbol,
        interval=interval,
        limit=limit,
        testnet=testnet,
        use_cache=use_cache,
    )


@app.get("/api/charts/indicators")
def charts_indicators(
    market: Literal["crypto", "securities"] = "crypto",
    symbol: str = "BTCUSDT",
    interval: str = "4h",
    limit: int = 200,
    testnet: bool = True,
    use_cache: bool = False,
) -> dict[str, Any]:
    return get_chart_indicators(
        market=market,
        symbol=symbol,
        interval=interval,
        limit=limit,
        testnet=testnet,
        use_cache=use_cache,
    )


@app.get("/api/charts/markers")
def charts_markers(
    market: Literal["crypto", "securities"] = "crypto",
    symbol: str = "BTCUSDT",
    env: str | None = None,
    from_time: str | None = None,
    to_time: str | None = None,
    limit: int = 200,
    include_news: bool = True,
) -> dict[str, Any]:
    return get_chart_markers(
        market=market,
        symbol=symbol,
        env=env,
        from_time=from_time,
        to_time=to_time,
        limit=limit,
        include_news=include_news,
    )


@app.get("/api/charts/symbols")
def charts_symbols(market: Literal["crypto", "securities"] = "crypto") -> dict[str, Any]:
    return {"market": market, "symbols": list_symbols_for_market(market)}


@app.get("/api/charts/equity")
def charts_equity(days: int = 30) -> dict[str, Any]:
    return get_equity_curve(days=days)


@app.get("/api/portfolio/performance")
def portfolio_performance(period: str = "all") -> dict[str, Any]:
    return get_portfolio_performance(period=period)


@app.get("/api/llm/decisions")
def llm_decisions_list(
    market: str | None = None,
    action: str | None = None,
    model: str | None = None,
    symbol: str | None = None,
    decision_id: str | None = None,
    trade_event_id: str | None = None,
    days: int = 30,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    return list_llm_decisions(
        market=market,
        action=action,
        model=model,
        symbol=symbol,
        decision_id=decision_id,
        trade_event_id=trade_event_id,
        days=days,
        limit=limit,
        offset=offset,
    )


@app.get("/api/llm/decisions/{decision_id}")
def llm_decision_detail(decision_id: str) -> dict[str, Any]:
    row = get_llm_decision(decision_id)
    if not row:
        raise HTTPException(status_code=404, detail="decision not found")
    return row


@app.post("/api/portfolio/snapshot")
def portfolio_snapshot_capture() -> dict[str, Any]:
    return capture_exchange_position_snapshots()


# --- Config ---

@app.get("/api/config/{name}")
def get_config(name: str) -> dict[str, Any]:
    allowed = {"guardrails", "crypto_config", "securities_config"}
    if name not in allowed:
        raise HTTPException(status_code=404, detail="unknown config")
    return get_config_effective(name)


@app.get("/api/strategies/{market}")
def strategies_state(market: str) -> dict[str, Any]:
    if market not in ("crypto", "securities"):
        raise HTTPException(status_code=404, detail="unknown market")
    return get_strategy_state(market)


@app.post("/api/strategies/{market}")
def strategies_set_active(
    market: str,
    body: StrategySelectRequest,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    if market not in ("crypto", "securities"):
        raise HTTPException(status_code=404, detail="unknown market")
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    try:
        return set_active_strategy(market, body.strategy_id, operator=body.operator)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/strategy/risk-profile/{market}")
def strategy_risk_profile_get(market: str) -> dict[str, Any]:
    if market not in ("crypto", "securities"):
        raise HTTPException(status_code=404, detail="unknown market")
    try:
        return {"status": "ok", **get_risk_profile_state(market)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/strategy/risk-profile/{market}")
def strategy_risk_profile_set(
    market: str,
    body: RiskProfileSetRequest,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    if market not in ("crypto", "securities"):
        raise HTTPException(status_code=404, detail="unknown market")
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    try:
        return {"status": "ok", **set_risk_profile(market, body.profile_id, operator=body.operator)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/strategy/risk-profile/{market}/reset")
def strategy_risk_profile_reset(
    market: str,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    if market not in ("crypto", "securities"):
        raise HTTPException(status_code=404, detail="unknown market")
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    try:
        return {"status": "ok", **reset_risk_profile(market, operator="web:operator")}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/crypto/workflow-settings")
def crypto_workflow_settings_get() -> dict[str, Any]:
    from crypto_workflow_settings_service import get_crypto_workflow_settings

    return {"status": "ok", **get_crypto_workflow_settings()}


@app.post("/api/crypto/workflow-settings/quote-asset")
def crypto_workflow_settings_set_quote(
    body: CryptoQuoteAssetRequest,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    from crypto_workflow_settings_service import set_crypto_quote_asset

    try:
        return set_crypto_quote_asset(body.quote_asset, operator=body.operator)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/crypto/workflow-settings/quote-asset/reset")
def crypto_workflow_settings_reset_quote(
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    from crypto_workflow_settings_service import reset_crypto_quote_asset

    return reset_crypto_quote_asset(operator="web:operator")


@app.post("/api/crypto/workflow-settings/trading-product")
def crypto_workflow_settings_set_trading_product(
    body: CryptoTradingProductRequest,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    from crypto_workflow_settings_service import set_crypto_trading_product

    try:
        return set_crypto_trading_product(
            market_type=body.market_type,
            allow_short=body.allow_short,
            leverage=body.leverage,
            margin_mode=body.margin_mode,
            operator=body.operator,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/crypto/workflow-settings/trading-product/reset")
def crypto_workflow_settings_reset_trading_product(
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    from crypto_workflow_settings_service import reset_crypto_trading_product

    return reset_crypto_trading_product(operator="web:operator")


# --- Crypto pipeline (этап 2) ---

@app.post("/api/crypto/signal")
def crypto_signal(body: CryptoSignalRequest) -> dict[str, Any]:
    from workflow_session_config_service import resolve_workflow_equity

    effective_equity = resolve_workflow_equity("crypto", default=body.equity)
    return run_crypto_signal(
        symbol=body.symbol, env=body.env,
        skip_llm=body.skip_llm, equity=effective_equity,
    )


@app.post("/api/crypto/scalp/signal")
def crypto_scalp_signal(
    symbol: str = "BTCUSDT",
    env: str = "dry_run",
    skip_llm: bool = False,
    equity: float = 10000.0,
) -> dict[str, Any]:
    scalp_cfg = load_config("crypto_scalp_hybrid")
    wf = (
        str(scalp_cfg.get("dry_run", {}).get("workflow_name", "crypto-scalp-hybrid-dry-run"))
        if env == "dry_run"
        else str(scalp_cfg.get("paper", {}).get("workflow_name", "crypto-scalp-hybrid-paper"))
    )
    from crypto_scalp_pipeline import _scalp_llm_enabled
    from workflow_session_config_service import resolve_workflow_equity

    effective_equity = resolve_workflow_equity("crypto", default=equity)
    return run_crypto_scalp_signal(
        symbol=symbol,
        env=env,
        workflow_name=wf,
        skip_llm=skip_llm or not _scalp_llm_enabled(scalp_cfg),
        equity=effective_equity,
    )


@app.get("/api/crypto/scalp/universe-scan/candidates")
def crypto_scalp_universe_scan_candidates(testnet: bool = True) -> dict[str, Any]:
    from crypto_scalp_universe_scan import get_scan_candidate_info

    return {"status": "ok", **get_scan_candidate_info(testnet=testnet)}


@app.get("/api/crypto/scalp/universe-scan/progress")
def crypto_scalp_universe_scan_progress() -> dict[str, Any]:
    from crypto_scalp_universe_scan import get_scalp_scan_progress

    return {"status": "ok", **get_scalp_scan_progress()}


@app.get("/api/crypto/scalp/universe-scan/settings")
def crypto_scalp_scan_settings_get() -> dict[str, Any]:
    from crypto_scalp_scan_settings_service import get_effective_scan_settings

    return {"status": "ok", **get_effective_scan_settings()}


@app.post("/api/crypto/scalp/universe-scan/settings")
def crypto_scalp_scan_settings_set(
    body: ScalpScanSettingsPatch,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    from crypto_scalp_scan_settings_service import set_scan_settings

    patch = body.model_dump(exclude={"operator"}, exclude_none=True)
    try:
        return {"status": "ok", **set_scan_settings(patch, operator=body.operator)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/crypto/scalp/universe-scan/settings/reset")
def crypto_scalp_scan_settings_reset(
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    from crypto_scalp_scan_settings_service import reset_scan_settings

    return {"status": "ok", **reset_scan_settings(operator="web:operator")}


@app.get("/api/crypto/scalp/universe-scan")
def crypto_scalp_universe_scan_preview(
    workflow_name: str = "crypto-scalp-hybrid-paper",
    apply: bool = False,
    top_n: int | None = None,
) -> dict[str, Any]:
    from crypto_scalp_universe_scan import (
        apply_scalp_universe_scan,
        get_last_scan,
        scan_scalp_universe,
    )

    scan = scan_scalp_universe(workflow_name, top_n=top_n, testnet=True)
    if apply and scan.get("status") == "ok" and scan.get("selected_symbols"):
        applied = apply_scalp_universe_scan(workflow_name, scan, operator="api")
        return {**scan, "apply": applied}
    last = get_last_scan(workflow_name)
    if last:
        scan["last_saved"] = last
    return scan


@app.post("/api/crypto/scalp/universe-scan/run")
def crypto_scalp_universe_scan_run(body: ScalpScanRunRequest) -> dict[str, Any]:
    from crypto_scalp_universe_scan import scan_scalp_universe

    overrides = None
    if body.settings:
        overrides = body.settings.model_dump(exclude={"operator"}, exclude_none=True)
    return scan_scalp_universe(
        body.workflow_name.strip(),
        testnet=True,
        config_overrides=overrides,
    )


@app.post("/api/crypto/scalp/universe-scan/apply")
def crypto_scalp_universe_scan_apply(
    body: ScalpScanApplyRequest,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    from crypto_scalp_universe_scan import apply_user_selected_symbols, get_last_scan

    wf = body.workflow_name.strip()
    last = get_last_scan(wf)
    try:
        return apply_user_selected_symbols(
            wf,
            body.symbols,
            scan_result=last,
            operator=body.operator,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/crypto/scalp/universe-scan/last")
def crypto_scalp_universe_scan_last(workflow_name: str = "crypto-scalp-hybrid-paper") -> dict[str, Any]:
    from crypto_scalp_universe_scan import get_last_scan
    from runtime_settings import get_runtime_meta

    key = f"crypto_scalp_last_scan:{workflow_name.strip()}"
    last = get_last_scan(workflow_name)
    meta = get_runtime_meta(key)
    return {
        "status": "ok",
        "last_scan": last,
        "updated_at": meta.get("updated_at") if meta else None,
    }


@app.get("/api/crypto/pairs")
def crypto_pairs() -> list[str]:
    try:
        wf = get_active_market_workflow("crypto")
        if not wf:
            state = get_strategy_state("crypto")
            wf = str(state.get("strategy", {}).get("workflow", ""))
        if wf:
            symbols = symbols_for_workflow(wf)
            if symbols:
                return symbols
        for fallback in (
            "crypto-scalp-hybrid-paper",
            "crypto-signal-paper",
            "crypto-signal-dry-run",
            "crypto-scalp-hybrid-dry-run",
        ):
            symbols = symbols_for_workflow(fallback)
            if symbols:
                return symbols
    except Exception:
        pass
    return load_config("crypto_config").get("pairs", [])


# --- News (этап 3) ---

@app.post("/api/news/ingest")
def news_ingest() -> dict[str, Any]:
    purge_expired()
    stats = ingest_all()
    try:
        alert_stats = process_news_alerts(limit=5)
        stats["alerts"] = alert_stats
    except Exception as exc:
        stats["alerts"] = {"status": "error", "error": str(exc)}
    return stats


@app.get("/api/news/context")
def news_context(symbols: str, limit: int = 5) -> dict[str, str]:
    sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
    return {"summary": news_context_for_symbols(sym_list, limit=limit)}


# --- Binance (этап 4) ---

@app.post("/api/binance/order")
def binance_order(body: BinanceOrderRequest) -> dict[str, Any]:
    guardrails = get_guardrails()
    if guardrails.get("trading", {}).get("kill_switch"):
        return {"status": "halted", "reject_reason": "kill_switch_active"}
    try:
        from futures_margin_monitor import ensure_futures_margin_ok

        margin_block = ensure_futures_margin_ok(testnet=body.testnet)
        if margin_block:
            return {"status": "halted", **margin_block}
    except Exception:
        pass
    if body.env == "live" and guardrails.get("trading", {}).get("live_requires_manual_flag"):
        live_flag = os.environ.get("LIVE_TRADING_ENABLED", "false").lower() == "true"
        if not live_flag:
            return {"status": "blocked", "reject_reason": "live_requires_manual_flag"}

    rid = body.request_id or str(uuid.uuid4())
    crypto_cfg = get_config_effective("crypto_config")
    if body.product != "auto":
        crypto_cfg = {
            **crypto_cfg,
            "trading_product": {
                **(crypto_cfg.get("trading_product") or {}),
                "market_type": body.product if body.product != "auto" else "spot",
            },
        }
    result = place_market_order(
        symbol=body.symbol,
        side=body.side,
        quantity=body.quantity,
        testnet=body.testnet,
        request_id=rid,
        reduce_only=body.reduce_only,
        cfg=crypto_cfg,
    )
    log_event(
        market="crypto", env="paper" if body.testnet else "live",
        stage="order", symbol=body.symbol,
        decision="execute" if result.get("orderId") and result.get("http_status") == 200 else "error",
        request_id=rid, payload=result,
        workflow_name="crypto-execute-testnet",
    )
    return {"request_id": rid, **result}


@app.get("/api/binance/open-orders")
def binance_open_orders(symbol: str | None = None, testnet: bool = True) -> list[dict]:
    return get_open_orders(symbol, testnet=testnet)


@app.get("/api/binance/balances")
def binance_balances(testnet: bool = True, top: int = 12) -> dict[str, Any]:
    """Wallet summary — spot balances or futures USDT margin when configured."""
    crypto_cfg = get_config_effective("crypto_config")
    product = get_crypto_trading_product(cfg=crypto_cfg)
    if product.get("is_futures"):
        usdt = get_trading_equity(testnet=testnet, cfg=crypto_cfg)
        return {
            "status": "ok",
            "testnet": testnet,
            "product": product.get("market_type"),
            "usdt_balance": usdt,
            "balances": [{"asset": "USDT", "free": usdt, "locked": 0.0}],
        }

    raw = get_account_balances(testnet=testnet)
    if not raw:
        return {
            "status": "empty",
            "testnet": testnet,
            "message": "Нет данных. Проверьте BINANCE_TESTNET_API_KEY/SECRET в .env и перезапустите db-api.",
            "balances": [],
        }

    priority = {"USDT": 0, "USDC": 1, "BTC": 2, "ETH": 3, "BNB": 4}
    parsed: list[dict[str, Any]] = []
    for row in raw:
        free = float(row.get("free", 0) or 0)
        locked = float(row.get("locked", 0) or 0)
        if free <= 0 and locked <= 0:
            continue
        asset = str(row.get("asset", ""))
        parsed.append({"asset": asset, "free": free, "locked": locked, "total": free + locked})

    parsed.sort(
        key=lambda b: (
            priority.get(b["asset"], 100),
            -b["total"],
            b["asset"],
        )
    )
    limit = max(1, min(top, 50))
    return {
        "status": "ok",
        "testnet": testnet,
        "balances": parsed[:limit],
        "total_assets": len(parsed),
    }


@app.get("/api/crypto/trading-product")
def crypto_trading_product() -> dict[str, Any]:
    """Effective spot vs USDT-M futures settings from crypto_config."""
    crypto_cfg = get_config_effective("crypto_config")
    product = get_crypto_trading_product(cfg=crypto_cfg)
    return {"status": "ok", **product}


@app.get("/api/binance/futures/positions")
def binance_futures_positions(
    symbol: str | None = None,
    testnet: bool = True,
) -> dict[str, Any]:
    """Open USDT-M futures positions (requires futures API keys)."""
    from binance_futures_client import get_futures_positions

    rows = get_futures_positions(testnet=testnet, symbol=symbol)
    return {"status": "ok", "testnet": testnet, "positions": rows, "count": len(rows)}


@app.post("/api/crypto/futures/margin-scan")
def crypto_futures_margin_scan(
    auto_stop: bool = True,
    testnet: bool | None = None,
) -> dict[str, Any]:
    """Detect futures liquidations / critical margin; stop crypto automation on margin call."""
    from futures_margin_monitor import scan_futures_margin_risk

    return scan_futures_margin_risk(testnet=testnet, auto_stop=auto_stop)


@app.get("/api/crypto/futures/margin-halt")
def crypto_futures_margin_halt_status() -> dict[str, Any]:
    from futures_margin_monitor import get_futures_margin_halt, is_futures_margin_halt_active

    return {
        "status": "ok",
        "active": is_futures_margin_halt_active(),
        "halt": get_futures_margin_halt(),
    }


@app.post("/api/crypto/futures/margin-halt/reset")
def crypto_futures_margin_halt_reset(
    x_operator_password: str | None = Header(default=None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    from futures_margin_monitor import clear_futures_margin_halt

    return clear_futures_margin_halt(operator="web:operator")


# --- Securities (этапы 5, 7) ---

@app.post("/api/securities/dca")
def securities_dca(dry_run: bool = True, env: str = "dry_run") -> dict[str, Any]:
    result = run_securities_dca_dry_run(env=env)
    if not dry_run and result.get("status") == "ready_for_order":
        sec = load_config("securities_config")
        dca = sec.get("index_dca", sec.get("dca", {}))
        order = post_dca_order(
            ticker=dca.get("ticker", "TMOS"),
            amount_rub=dca.get("amount_rub", 10000),
            sandbox=sec.get("env") == "sandbox",
            dry_run=False,
        )
        log_event(
            market="securities", env="paper", stage="order",
            symbol=dca.get("ticker"), decision="execute" if order.get("status") == "submitted" else "error",
            payload=order, currency="RUB", workflow_name="securities-dca-sandbox",
        )
        return {**result, "order": order}
    return result


@app.post("/api/securities/swing")
def securities_swing(body: SecuritiesSwingRequest) -> dict[str, Any]:
    return run_securities_swing_dry_run(
        ticker=body.ticker, env=body.env, skip_llm=body.skip_llm,
    )


@app.get("/api/securities/swing-universe")
def swing_universe() -> list[str]:
    wf = get_active_market_workflow("securities")
    if wf and wf.startswith("securities-swing"):
        symbols = symbols_for_workflow(wf)
        if symbols:
            return symbols
    for fallback in ("securities-swing-paper", "securities-swing-dry-run"):
        symbols = symbols_for_workflow(fallback)
        if symbols:
            return symbols
    return load_config("securities_config").get("swing_signals", {}).get("universe", [])


@app.get("/api/assets/search")
def assets_search(
    market: Literal["crypto", "securities"],
    q: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    items = search_assets(market, q, limit=min(max(limit, 1), 50))
    return {"status": "ok", "market": market, "query": q, "items": items}


@app.get("/api/workflows/registry")
def workflows_registry() -> dict[str, Any]:
    return {"status": "ok", "workflows": WORKFLOW_REGISTRY}


@app.get("/api/workflows/{workflow_name}/universe")
def workflow_universe_get(workflow_name: str) -> dict[str, Any]:
    try:
        return {"status": "ok", **get_workflow_universe(workflow_name)}
    except ValueError as exc:
        msg = str(exc)
        code = 400 if msg.startswith("universe_change_blocked:") else 404
        raise HTTPException(status_code=code, detail=msg) from exc


@app.put("/api/workflows/{workflow_name}/universe")
def workflow_universe_put(workflow_name: str, body: WorkflowUniverseSaveRequest) -> dict[str, Any]:
    try:
        saved = save_workflow_universe(workflow_name, body.items, operator=body.operator)
        return {"status": "ok", **saved}
    except ValueError as exc:
        msg = str(exc)
        code = 400 if msg.startswith("universe_change_blocked:") else 404
        raise HTTPException(status_code=code, detail=msg) from exc


@app.post("/api/workflows/{workflow_name}/universe/add")
def workflow_universe_add(workflow_name: str, body: WorkflowUniverseAddRequest) -> dict[str, Any]:
    try:
        saved = add_symbols_to_workflow(
            workflow_name,
            body.symbols,
            enabled=body.enabled,
            operator=body.operator,
        )
        return {"status": "ok", **saved}
    except ValueError as exc:
        msg = str(exc)
        code = 400 if msg.startswith("universe_change_blocked:") else 404
        raise HTTPException(status_code=code, detail=msg) from exc


@app.post("/api/workflows/{workflow_name}/universe/toggle")
def workflow_universe_toggle(
    workflow_name: str,
    body: WorkflowUniverseToggleRequest,
) -> dict[str, Any]:
    try:
        saved = set_symbol_enabled(
            workflow_name,
            body.symbol,
            body.enabled,
            operator=body.operator,
        )
        return {"status": "ok", **saved}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/workflows/{workflow_name}/universe/remove")
def workflow_universe_remove(
    workflow_name: str,
    body: WorkflowUniverseToggleRequest,
) -> dict[str, Any]:
    try:
        saved = remove_symbol_from_workflow(workflow_name, body.symbol, operator=body.operator)
        return {"status": "ok", **saved}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/workflows/{workflow_name}/universe/reset")
def workflow_universe_reset(workflow_name: str) -> dict[str, Any]:
    try:
        saved = reset_workflow_universe(workflow_name)
        return {"status": "ok", **saved}
    except ValueError as exc:
        msg = str(exc)
        code = 400 if msg.startswith("universe_change_blocked:") else 404
        raise HTTPException(status_code=code, detail=msg) from exc


@app.post("/api/workflows/{workflow_name}/universe/llm-suggest")
def workflow_universe_llm(
    workflow_name: str,
    body: WorkflowUniverseLlmRequest,
) -> dict[str, Any]:
    try:
        suggestion = suggest_universe_with_llm(workflow_name, hint=body.hint)
        if suggestion.get("status") != "ok":
            suggestion = _fallback_universe_suggestion(
                workflow_name,
                hint=body.hint,
                llm_error=suggestion.get("message"),
            )
        if body.apply and suggestion.get("symbols"):
            applied = apply_llm_universe_suggestion(
                workflow_name,
                suggestion["symbols"],
                mode=body.mode,
                disable_others=body.disable_others,
                operator=body.operator,
            )
            return {
                "status": "ok",
                "suggestion": suggestion,
                "universe": applied,
            }
        return {"status": "ok", "suggestion": suggestion}
    except ValueError as exc:
        msg = str(exc)
        code = 400 if msg.startswith("universe_change_blocked:") else 404
        raise HTTPException(status_code=code, detail=msg) from exc
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.get("/api/tinvest/portfolio")
def tinvest_portfolio(sandbox: bool = True) -> dict[str, Any]:
    return get_portfolio_snapshot(sandbox=sandbox)


@app.get("/api/tinvest/status")
def tinvest_status(sandbox: bool = True) -> dict[str, Any]:
    return check_tinvest_connection(sandbox=sandbox)


@app.get("/api/testing/overview")
def testing_overview(days: int = 7) -> dict[str, Any]:
    return get_testing_overview(days=days)


@app.get("/api/testing/tinvest-sandbox")
def testing_tinvest_sandbox(days: int = 7) -> dict[str, Any]:
    try:
        return get_tinvest_sandbox_dashboard(days=days)
    except Exception as exc:
        return {
            "days": days,
            "status": "error",
            "message": str(exc),
            "connection": {"status": "error", "message": str(exc)},
            "portfolio": {"status": "error", "message": str(exc)},
        }


# --- Evaluation (этап 6) ---

@app.post("/api/evaluation/replay")
def evaluation_replay(body: ReplayRequest) -> dict[str, Any]:
    return replay_by_inputs_hash(body.inputs_hash, model=body.model, prompt_version=body.prompt_version)


@app.get("/api/evaluation/metrics")
def eval_metrics(market: str | None = None, days: int = 7) -> dict[str, Any]:
    return evaluation_metrics(market=market, days=days)


@app.post("/api/evaluation/champion-challenger")
def eval_champion(body: ChampionRequest) -> dict[str, Any]:
    return champion_challenger_report(
        inputs_hashes=body.inputs_hashes,
        champion_model=body.champion_model,
        challenger_model=body.challenger_model,
        prompt_version=body.prompt_version,
    )


# --- LLM Benchmark ---


@app.get("/api/benchmark/report")
def benchmark_report_endpoint(days: int = 30, market: str | None = None) -> dict[str, Any]:
    return benchmark_report(days=days, market=market)


@app.get("/api/benchmark/report/by-model")
def benchmark_report_by_model_endpoint(days: int = 30, market: str | None = None) -> dict[str, Any]:
    return benchmark_report_by_model(days=days, market=market)


@app.post("/api/benchmark/sample")
def benchmark_sample(days: int = 30, market: str | None = None) -> dict[str, Any]:
    return sample_benchmark_cases(days=days, market=market)


@app.post("/api/benchmark/label")
def benchmark_label(market: str | None = None, limit: int = 100) -> dict[str, Any]:
    return label_outcomes(market=market, limit=limit)


@app.post("/api/benchmark/golden")
def benchmark_golden(model: str | None = None, market: str | None = None) -> dict[str, Any]:
    return run_golden_benchmark(model=model, market=market)


@app.get("/api/benchmark/golden/cases")
def benchmark_golden_cases(market: str | None = None) -> list[dict[str, Any]]:
    return list_golden_cases(market=market)


@app.post("/api/benchmark/golden/one")
def benchmark_golden_one(body: GoldenOneRequest) -> dict[str, Any]:
    return run_one_golden_case(case_id=body.case_id, market=body.market, model=body.model)


@app.get("/api/benchmark/synthetic/cases")
def benchmark_synthetic_cases(market: str | None = None) -> list[dict[str, Any]]:
    """Alias: synthetic tier (known inputs)."""
    return list_golden_cases(market=market)


@app.post("/api/benchmark/synthetic")
def benchmark_synthetic(model: str | None = None, market: str | None = None) -> dict[str, Any]:
    return run_golden_benchmark(model=model, market=market)


@app.get("/api/benchmark/historical/cases")
def benchmark_historical_cases(market: str | None = None) -> list[dict[str, Any]]:
    return list_historical_cases(market=market)


@app.post("/api/benchmark/historical/one")
def benchmark_historical_one(body: GoldenOneRequest) -> dict[str, Any]:
    return run_one_historical_case(case_id=body.case_id, market=body.market, model=body.model)


@app.post("/api/benchmark/historical")
def benchmark_historical(model: str | None = None, market: str | None = None) -> dict[str, Any]:
    return run_historical_benchmark(model=model, market=market)


@app.get("/api/benchmark/historical/last-snapshot")
def benchmark_historical_last_snapshot() -> dict[str, Any]:
    snap = get_historical_snapshot()
    return snap or {"status": "empty"}


@app.post("/api/benchmark/historical/snapshot")
def benchmark_historical_save_snapshot(body: dict[str, Any]) -> dict[str, Any]:
    return save_historical_snapshot(body)


@app.post("/api/benchmark/historical/promote/{inputs_hash}")
def benchmark_promote_historical(
    inputs_hash: str,
    expected_action: Literal["approve", "reject"],
    summary: str,
) -> dict[str, Any]:
    return promote_live_case_to_historical(
        inputs_hash,
        expected_action=expected_action,
        summary=summary,
    )


@app.post("/api/benchmark/ollama/reset")
def benchmark_ollama_reset(model: str | None = None) -> dict[str, Any]:
    """Unload model from Ollama RAM (keep_alive=0) after benchmark."""
    return reset_ollama_cache(model)


@app.get("/api/benchmark/host-capability/last")
def benchmark_host_capability_last() -> dict[str, Any]:
    last = get_last_host_audit()
    return last or {"status": "empty"}


@app.post("/api/benchmark/host-capability/run")
def benchmark_host_capability_run(
    llm_samples: int = 2,
    models: str | None = None,
) -> dict[str, Any]:
    model_list = [m.strip() for m in models.split(",") if m.strip()] if models else None
    return run_host_capability_audit(models=model_list, llm_samples=llm_samples)


@app.get("/api/automation/pipeline-health")
def automation_pipeline_health(days: int = 1) -> dict[str, Any]:
    """Explain missing events: workflows, modes, last trade_events."""
    from db.connection import get_connection

    ctrl = get_automation_control_state()
    conn = get_connection()
    try:
        last = conn.execute(
            """
            SELECT event_at, market, env, stage, workflow_name, reject_reason
            FROM trade_events ORDER BY event_at DESC LIMIT 1
            """
        ).fetchone()
        today_count = conn.execute(
            """
            SELECT COUNT(*) as c FROM trade_events
            WHERE event_at >= datetime('now', '-1 day')
            """
        ).fetchone()["c"]
    finally:
        conn.close()
    hints: list[str] = []
    if not last:
        hints.append("Нет событий в trade_events — проверьте активные workflow в n8n")
    elif today_count == 0:
        hints.append(
            f"Сегодня 0 событий; последнее: {last['event_at']} ({last['workflow_name']}, env={last['env']})"
        )
    for wf in ctrl.get("workflows", []):
        if wf.get("expected_for_mode") and not wf.get("active"):
            hints.append(f"Workflow {wf['name']} должен быть активен в режиме paper, но выключен")
    crypto_wf = next((w for w in ctrl.get("workflows", []) if w.get("name") == "crypto-signal-paper"), None)
    if crypto_wf and crypto_wf.get("active"):
        hints.append(
            "crypto-signal-paper пишет события через /api/paper/crypto/run (workflow_name=crypto-paper-auto), не crypto-signal-dry-run"
        )
    return {
        "control": ctrl,
        "events_last_24h": today_count,
        "last_event": dict(last) if last else None,
        "hints": hints,
        "tinvest_sandbox": check_tinvest_connection(sandbox=True),
    }


@app.get("/api/benchmark/calibrate/plan")
def benchmark_calibrate_plan(market: str | None = None) -> dict[str, Any]:
    return get_calibration_plan(market=market)


@app.get("/api/benchmark/llm-settings")
def benchmark_llm_settings() -> dict[str, Any]:
    return get_llm_settings_snapshot()


@app.post("/api/benchmark/calibrate/start")
def benchmark_calibrate_start(body: CalibrationRequest | None = None) -> dict[str, Any]:
    body = body or CalibrationRequest()
    return start_calibration_job(market=body.market, model=body.model)


@app.post("/api/benchmark/calibrate/cancel")
def benchmark_calibrate_cancel(body: CalibrationRequest | None = None) -> dict[str, Any]:
    body = body or CalibrationRequest()
    return cancel_calibration_job(market=body.market)


@app.get("/api/benchmark/calibrate/status")
def benchmark_calibrate_status(market: str | None = None) -> dict[str, Any]:
    if market:
        return get_calibration_job_status(market=market)
    return list_calibration_jobs_status()


@app.get("/api/ollama/models")
def ollama_models() -> dict[str, Any]:
    return list_ollama_models()


@app.get("/api/ollama/models/status")
def ollama_models_status() -> dict[str, Any]:
    from ollama_manager_service import get_models_status

    return get_models_status()


@app.post("/api/ollama/models/ensure")
def ollama_models_ensure(
    include_optional: bool = False,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    from ollama_manager_service import ensure_required_models

    return ensure_required_models(
        operator="web:operator",
        background=True,
        include_optional=include_optional,
    )


@app.post("/api/ollama/models/pull")
def ollama_models_pull(
    body: dict[str, Any],
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    from ollama_manager_service import pull_ollama_model

    model = str(body.get("model", "")).strip()
    if not model:
        raise HTTPException(status_code=400, detail="model required")
    return pull_ollama_model(model, operator="web:operator", background=True)


@app.post("/api/ollama/models/delete")
def ollama_models_delete(
    body: dict[str, Any],
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    from ollama_manager_service import delete_ollama_model

    model = str(body.get("model", "")).strip()
    if not model:
        raise HTTPException(status_code=400, detail="model required")
    try:
        return delete_ollama_model(
            model,
            operator="web:operator",
            force=bool(body.get("force")),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/ollama/pull/{job_id}")
def ollama_pull_job_status(job_id: str) -> dict[str, Any]:
    from ollama_manager_service import get_pull_job

    job = get_pull_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_not_found")
    return job


@app.post("/api/benchmark/calibrate")
def benchmark_calibrate(body: CalibrationRequest | None = None) -> dict[str, Any]:
    body = body or CalibrationRequest()
    return run_calibration(
        model=body.model,
        market=body.market,
        temperatures=body.temperatures,
        min_confidence_values=body.min_confidence,
    )


@app.post("/api/benchmark/calibrate/temperature")
def benchmark_calibrate_temperature(body: CalibrationTemperatureRequest) -> dict[str, Any]:
    return run_calibration_temperature(
        temperature=body.temperature,
        model=body.model,
        market=body.market,
    )


@app.post("/api/benchmark/calibrate/finalize")
def benchmark_calibrate_finalize(body: CalibrationRequest | None = None) -> dict[str, Any]:
    body = body or CalibrationRequest()
    return finalize_calibration(model=body.model, market=body.market)


@app.get("/api/benchmark/calibrate/last-snapshot")
def benchmark_calibrate_last_snapshot(market: str | None = None) -> dict[str, Any]:
    snap = get_calibration_snapshot(market=market)
    return snap or {"status": "empty", "market": market or "crypto"}


@app.post("/api/benchmark/calibrate/apply")
def benchmark_calibrate_apply(body: CalibrationRequest | None = None) -> dict[str, Any]:
    body = body or CalibrationRequest()
    operator = body.operator or "web"
    mkt = normalize_market(body.market)
    snap = get_calibration_snapshot(market=mkt)
    if not isinstance(snap, dict) or snap.get("status") != "ok":
        return {"status": "error", "message": "no_calibration_snapshot", "market": mkt}
    rec = snap.get("recommended")
    if not isinstance(rec, dict) or rec.get("temperature") is None or rec.get("min_confidence") is None:
        return {"status": "error", "message": "snapshot_missing_recommendation", "market": mkt}

    override = {
        "temperature": float(rec["temperature"]),
        "min_confidence": float(rec["min_confidence"]),
        "source": "calibration_snapshot",
        "snapshot_saved_at": snap.get("saved_at"),
        "snapshot_model": snap.get("model"),
    }
    set_runtime_value(f"llm_override:{mkt}", override, updated_by=str(operator))
    try:
        log_system_activity(
            f"LLM параметры применены ({mkt}): T={override['temperature']}, conf={override['min_confidence']}",
            category=mkt,
            level="info",
            payload=override,
        )
    except Exception:
        pass
    return {"status": "ok", "market": mkt, "override": override}


@app.post("/api/benchmark/snapshot")
def benchmark_save_snapshot(body: BenchmarkSnapshotRequest, operator: str = "api") -> dict[str, Any]:
    return save_benchmark_snapshot(
        {"golden": body.golden, "report": body.report, "kind": body.kind},
        operator=operator,
    )


@app.get("/api/benchmark/last-snapshot")
def benchmark_last_snapshot() -> dict[str, Any]:
    snap = get_benchmark_snapshot()
    return snap or {"status": "empty"}


@app.post("/api/benchmark/replay")
def benchmark_replay(body: BenchmarkReplayRequest) -> dict[str, Any]:
    return run_benchmark_replay(
        model=body.model,
        prompt_version=body.prompt_version,
        market=body.market,
        limit=body.limit,
    )


@app.post("/api/benchmark/run")
def benchmark_run(body: BenchmarkRunRequest) -> dict[str, Any]:
    return run_full_benchmark(
        days=body.days,
        market=body.market,
        model=body.model,
        challenger_model=body.challenger_model,
        skip_golden=body.skip_golden,
    )


@app.get("/api/backtest/funnel")
def backtest_funnel(market: str = "crypto", days: int = 7) -> dict[str, Any]:
    return dry_run_funnel(market=market, days=days)


@app.get("/api/backtest/summary")
def backtest_summary(market: str = "crypto", days: int = 30) -> dict[str, Any]:
    return signal_summary(market=market, days=days)


@app.post("/api/backtest/finsaber")
def backtest_finsaber(
    symbol: str = "BTCUSDT",
    timeframe: str = "4h",
    bars: int = 500,
    forward_bars: int = 6,
) -> dict[str, Any]:
    return run_walk_forward_backtest(
        symbol=symbol, timeframe=timeframe, bars=bars, forward_bars=forward_bars,
    )


@app.get("/api/backtest/finsaber/runs")
def backtest_finsaber_runs(limit: int = 20) -> list[dict[str, Any]]:
    return list_backtest_runs(limit=limit)


@app.post("/api/deepfund/start")
def deepfund_start(label: str = "deepfund-live-paper") -> dict[str, Any]:
    return start_session(label=label)


@app.get("/api/deepfund/session")
def deepfund_session() -> dict[str, Any]:
    session = get_active_session()
    return session or {"status": "none"}


@app.post("/api/deepfund/cycle")
def deepfund_cycle(equity: float = 10000.0) -> dict[str, Any]:
    return run_deepfund_cycle(equity=equity)


@app.post("/api/deepfund/close")
def deepfund_close() -> dict[str, Any]:
    return close_session()


@app.get("/api/onchain/context")
def onchain_context() -> dict[str, Any]:
    return compute_on_chain_context()


@app.get("/api/factor-sleeve/rank")
def factor_sleeve_rank() -> dict[str, Any]:
    return rank_factor_universe()


@app.post("/api/factor-sleeve/rebalance")
def factor_sleeve_rebalance() -> dict[str, Any]:
    return factor_sleeve_rebalance_plan()


@app.post("/api/regulatory/scan")
def regulatory_scan(auto_kill_switch: bool = False) -> dict[str, Any]:
    return scan_regulatory_risk(auto_kill_switch=auto_kill_switch)


@app.post("/api/neuratrade/cycle")
def neuratrade_cycle(body: dict[str, Any] | None = None, equity: float = 10000.0) -> dict[str, Any]:
    payload = body or {}
    return run_harness_cycle(
        equity=float(payload.get("equity", equity)),
        mode=payload.get("mode"),
    )


@app.get("/api/neuratrade/leaderboard")
def neuratrade_leaderboard(limit: int = 15) -> list[dict[str, Any]]:
    return get_leaderboard(limit=limit)


@app.get("/api/neuratrade/recommend")
def neuratrade_recommend() -> dict[str, Any]:
    rec = recommend_model()
    return {"status": "ok", "recommended": rec}


@app.post("/api/papers/monitor/ingest")
def papers_monitor_ingest(create_drafts: bool = False) -> dict[str, Any]:
    return ingest_paper_candidates(create_drafts=create_drafts)


@app.get("/api/papers/monitor/pending")
def papers_monitor_pending(limit: int = 30) -> list[dict[str, Any]]:
    return list_pending_candidates(limit=limit)


@app.get("/api/papers/monitor/candidates")
def papers_monitor_candidates(status: str = "pending", limit: int = 50) -> list[dict[str, Any]]:
    return list_candidates(status=status, limit=limit)


@app.get("/api/research/dashboard")
def research_dashboard_api() -> dict[str, Any]:
    return research_dashboard()


@app.post("/api/papers/monitor/{candidate_id}/draft")
def papers_create_draft(candidate_id: str) -> dict[str, Any]:
    return create_obsidian_draft(candidate_id)


@app.post("/api/papers/monitor/{candidate_id}/status")
def papers_update_status(candidate_id: str, body: dict[str, Any]) -> dict[str, Any]:
    status = str(body.get("status", "rejected"))
    return update_candidate_status(candidate_id, status)


@app.post("/api/trading-agents/run")
def trading_agents_run(body: dict[str, Any]) -> dict[str, Any]:
    return run_trading_agents(
        market=body.get("market", "crypto"),
        symbol=body["symbol"],
        indicators=body.get("indicators", {}),
        news_summary=body.get("news_summary", ""),
    )


@app.get("/api/bond-ladder/evaluate")
def bond_ladder_evaluate(key_rate_pct: float | None = None) -> dict[str, Any]:
    return evaluate_bond_ladder(key_rate_pct=key_rate_pct)


@app.get("/api/geopolitical/score")
def geopolitical_score() -> dict[str, Any]:
    return compute_geopolitical_score()


@app.post("/api/geopolitical/adjust-notional")
def geopolitical_adjust(body: dict[str, Any]) -> dict[str, Any]:
    return geo_adjust_notional(float(body.get("notional", 0)), str(body.get("ticker", "")))


# --- Reports ---

@app.post("/api/reports/daily")
def daily_report() -> dict[str, Any]:
    logs_dir = wiki_root() / "logs" / "executions"
    logs_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")
    funnel = dry_run_funnel()
    metrics = evaluation_metrics(days=1)
    health = health_latest(limit=4)
    lines = [
        f"# Execution report {date}",
        "",
        "## Funnel (7d)",
        f"```json\n{json.dumps(funnel, ensure_ascii=False, indent=2)}\n```",
        "",
        "## LLM metrics (24h)",
        f"```json\n{json.dumps(metrics, ensure_ascii=False, indent=2)}\n```",
        "",
        "## Latest health",
    ]
    for h in health:
        lines.append(f"- {h.get('service_name')}: {h.get('status')}")
    path = logs_dir / f"{date}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return {"path": str(path), "funnel": funnel, "metrics": metrics}


@app.get("/api/workflow/reports")
def workflow_reports_list(market: str | None = None, limit: int = 20) -> dict[str, Any]:
    items = list_workflow_reports(market=market, limit=limit)
    return {"items": items, "count": len(items)}


@app.get("/api/workflow/reports/{report_id}")
def workflow_report_get(report_id: str) -> dict[str, Any]:
    row = get_workflow_report(report_id)
    if not row:
        raise HTTPException(status_code=404, detail="report_not_found")
    return row


@app.post("/api/workflow/reports/finalize")
def workflow_report_finalize(
    market: str,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    """Manual finalize (testing) — normally called automatically on workflow stop."""
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    if market not in ("crypto", "securities"):
        raise HTTPException(status_code=404, detail="unknown market")
    from automation_control_service import get_market_control_state

    ctrl = get_market_control_state(market)
    started_at = ctrl.get("workflow_started_at")
    workflow_name = ctrl.get("active_workflow")
    if not started_at or not workflow_name:
        raise HTTPException(status_code=400, detail="no_active_workflow_session")
    result = finalize_workflow_session(
        market,
        started_at=started_at,
        workflow_name=workflow_name,
        reason="manual",
        operator="web:operator",
    )
    if not result:
        raise HTTPException(status_code=500, detail="finalize_failed")
    return result


# --- Live checklist (этап 8) ---

@app.get("/api/live/checklist")
def live_checklist() -> dict[str, Any]:
    return get_live_checklist()


@app.get("/api/automation/overview")
def automation_overview(days: int = 7) -> dict[str, Any]:
    return get_automation_overview(days=days)


@app.get("/api/automation/docs")
def automation_docs(section: str | None = None) -> dict[str, Any]:
    return automat_documentation(section)


@app.get("/api/crypto/testnet-dashboard")
def crypto_testnet_dashboard(days: int = 7) -> dict[str, Any]:
    return get_crypto_testnet_dashboard(days=days)


@app.get("/api/system/summary")
def system_summary_endpoint() -> dict[str, Any]:
    return get_system_summary()


@app.get("/api/system/host-status")
def system_host_status() -> dict[str, Any]:
    return get_host_status()


@app.get("/api/system/activity-feed")
def system_activity_feed(limit: int = 40, days: int = 3) -> dict[str, Any]:
    """Read-only feed for UI; does not delete trade_events or system_activity rows."""
    capped = max(1, min(int(limit), 40))
    return get_activity_feed(limit=capped, days=days)


@app.get("/api/wiki/toc")
def wiki_toc() -> dict[str, Any]:
    return wiki_table_of_contents()


@app.get("/api/news/latest")
def news_latest(limit: int = 8, include_trades: bool = True) -> list[dict[str, Any]]:
    return list_recent_news(limit=limit, include_trades=include_trades)


@app.get("/api/news/signal-feed")
def news_signal_feed(
    limit: int = 40,
    market: str | None = None,
    universe_only: bool = False,
) -> dict[str, Any]:
    items = list_signal_news_feed(limit=limit, market=market, universe_only=universe_only)
    return {"status": "ok", "count": len(items), "items": items, "market": market}


@app.get("/api/news/alerts/settings")
def news_alerts_settings() -> dict[str, Any]:
    settings = get_alert_settings()
    settings["watch_symbols_resolved"] = resolve_watch_symbols()
    return settings


@app.post("/api/news/alerts/settings")
def news_alerts_settings_update(body: NewsAlertsSettingsRequest) -> dict[str, Any]:
    return update_alert_settings(
        news_enabled=body.news_enabled,
        trade_enabled=body.trade_enabled,
        trade_push=body.trade_push,
        operator=body.operator,
    )


@app.post("/api/news/alerts/process")
def news_alerts_process(limit: int = 5) -> dict[str, Any]:
    return process_news_alerts(limit=limit)


@app.get("/api/signals-engine/settings")
def signals_engine_settings() -> dict[str, Any]:
    return get_engine_settings()


@app.post("/api/signals-engine/settings")
def signals_engine_settings_update(body: SignalsEngineSettingsRequest) -> dict[str, Any]:
    return update_engine_settings(
        analysis_enabled=body.analysis_enabled,
        analyze_on_ingest=body.analyze_on_ingest,
        batch_size=body.batch_size,
        min_confidence=body.min_confidence,
        min_significance_score=body.min_significance_score,
        max_signals_per_symbol=body.max_signals_per_symbol,
        include_user_context=body.include_user_context,
        filter_enabled=body.filter_enabled,
        active_tags=body.active_tags,
        keywords_include=body.keywords_include,
        keywords_exclude=body.keywords_exclude,
        require_symbol_or_keyword=body.require_symbol_or_keyword,
        filter_mode=body.filter_mode,
        min_keywords=body.min_keywords,
        min_relevance_score=body.min_relevance_score,
        require_keyword_in_title=body.require_keyword_in_title,
        operator=body.operator,
    )


@app.post("/api/signals-engine/reapply-filters")
def signals_engine_reapply_filters(limit: int = 400) -> dict[str, Any]:
    return reapply_trade_filters(limit=limit)


@app.post("/api/signals-engine/analyze-pending")
def signals_engine_analyze_pending(limit: int = 12) -> dict[str, Any]:
    return analyze_pending_news(limit=limit)


@app.post("/api/news/items/{item_id}/analyze")
def news_item_analyze(item_id: str) -> dict[str, Any]:
    return analyze_news_item(item_id)


@app.put("/api/news/items/{item_id}/context")
def news_item_context(item_id: str, body: NewsUserContextRequest) -> dict[str, Any]:
    return save_user_context(item_id, body.context_text, operator=body.operator)


@app.patch("/api/news/sources/{source_id}")
def news_source_update(source_id: str, body: NewsSourceUpdateRequest) -> dict[str, Any]:
    return update_news_source(
        source_id,
        enabled=body.enabled,
        tags=body.tags,
        user_trust_override=body.user_trust_override,
        clear_trust_override=body.clear_trust_override,
    )


# --- Paper trading test harness ---

@app.get("/api/paper/status")
def paper_status() -> dict[str, Any]:
    return get_paper_config()


@app.get("/api/paper/effectiveness")
def paper_effectiveness_endpoint(days: int = 7) -> dict[str, Any]:
    return paper_effectiveness(days=days)


@app.post("/api/paper/session/start")
def paper_session_start(label: str = "paper-test", operator: str = "api") -> dict[str, Any]:
    return start_paper_session(label=label, operator=operator)


@app.post("/api/paper/session/reset")
def paper_session_reset(reset_moex: bool = True, operator: str = "api") -> dict[str, Any]:
    return reset_paper_session(reset_moex=reset_moex, operator=operator)


@app.post("/api/paper/crypto/scalp/run")
def paper_crypto_scalp_run(symbol: str = "BTCUSDT", skip_llm: bool = False) -> dict[str, Any]:
    return run_crypto_scalp_paper_trade(symbol=symbol, skip_llm=skip_llm)


@app.post("/api/paper/crypto/run")
def paper_crypto_run(symbol: str = "BTCUSDT", skip_llm: bool = False) -> dict[str, Any]:
    return run_crypto_paper_trade(symbol=symbol, skip_llm=skip_llm)


@app.post("/api/paper/securities/swing")
def paper_securities_swing(ticker: str = "SBER", skip_llm: bool = False) -> dict[str, Any]:
    return run_securities_swing_paper(ticker=ticker, skip_llm=skip_llm)


@app.post("/api/paper/snapshot")
def paper_snapshot() -> dict[str, Any]:
    return capture_snapshot(trigger="api")


# --- n8n workflow management (Public API v1) ---


@app.get("/api/n8n/workflows")
def n8n_workflows(active: bool | None = None) -> dict[str, Any]:
    try:
        items = list_workflows(active=active)
        # Return a stable minimal shape for the bot UI
        out = []
        for w in items:
            out.append(
                {
                    "id": w.get("id"),
                    "name": w.get("name"),
                    "active": w.get("active"),
                    "tags": [t.get("name") for t in (w.get("tags") or []) if isinstance(t, dict)],
                }
            )
        return {"status": "ok", "workflows": out}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.get("/api/automation/control")
def automation_control() -> dict[str, Any]:
    return get_automation_control_state()


@app.get("/api/automation/control/{market}")
def automation_control_market(market: str) -> dict[str, Any]:
    if market not in ("crypto", "securities"):
        raise HTTPException(status_code=404, detail="unknown market")
    try:
        return get_market_control_state(market)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/automation/control/{market}/multi-automation")
def automation_multi_automation(
    market: str,
    body: MultiAutomationRequest,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    if market not in ("crypto", "securities"):
        raise HTTPException(status_code=404, detail="unknown market")
    try:
        return set_multi_automation_enabled(market, body.enabled, operator=body.operator)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/n8n/workflows/import")
def n8n_import_workflows(
    market: str = "all",
    update: bool = True,
) -> dict[str, Any]:
    """Import workflow JSON exports from n8n_automation/workflows into n8n."""
    try:
        if market == "all":
            return import_all_workflows(update_if_exists=update)
        if market in ("crypto", "securities"):
            return import_market_workflows(market, update_if_exists=update)
        raise HTTPException(status_code=400, detail="unknown market")
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.post("/api/n8n/workflows/sync-profile")
def n8n_sync_profile(
    market: str,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    if market not in ("crypto", "securities"):
        raise HTTPException(status_code=404, detail="unknown market")
    try:
        return sync_market_workflows(market)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.post("/api/n8n/workflows/select")
def n8n_select_workflow(
    market: str,
    body: WorkflowSelectRequest,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    if market not in ("crypto", "securities"):
        raise HTTPException(status_code=404, detail="unknown market")
    try:
        margin_call = body.liquidate_on_margin_call
        if margin_call is None and body.liquidate_on_stop:
            margin_call = True
        runner = add_market_workflow if body.additive else start_market_workflow
        return runner(
            market,
            body.workflow_name.strip(),
            trading_mode=body.trading_mode,
            session_capital=body.session_capital,
            session_volume_mode=body.session_volume_mode,
            use_existing_holdings=body.use_existing_holdings,
            existing_holdings_unit=body.existing_holdings_unit,
            existing_holdings_use_pct=body.existing_holdings_use_pct,
            existing_holdings_use_qty=body.existing_holdings_use_qty,
            liquidate_on_stop=body.liquidate_on_stop,
            liquidate_on_margin_call=margin_call,
            operator=body.operator,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.post("/api/n8n/workflows/stop")
def n8n_stop_workflows(
    market: str,
    body: WorkflowStopOneRequest | None = Body(default=None),
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    if market not in ("crypto", "securities"):
        raise HTTPException(status_code=404, detail="unknown market")
    try:
        if body and body.workflow_name.strip():
            return stop_single_market_workflow(
                market,
                body.workflow_name.strip(),
                operator=body.operator,
            )
        return stop_market_workflows(market)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.get("/api/automation/schedule/{workflow_name}")
def automation_schedule_get(workflow_name: str) -> dict[str, Any]:
    from workflow_schedule_service import get_workflow_schedule

    try:
        return get_workflow_schedule(workflow_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/automation/schedule/{workflow_name}")
def automation_schedule_set(
    workflow_name: str,
    body: WorkflowScheduleRequest,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    from workflow_schedule_service import set_workflow_schedule

    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    try:
        return set_workflow_schedule(
            workflow_name,
            body.option_id,
            operator=body.operator,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.get("/api/automation/diagnostics/{market}")
def automation_diagnostics(market: str, days: int = 7) -> dict[str, Any]:
    if market not in ("crypto", "securities"):
        raise HTTPException(status_code=404, detail="unknown market")
    try:
        return get_market_diagnostics(market, days=days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/automation/run-once")
def automation_run_once(
    market: str,
    body: WorkflowRunOnceRequest,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    if market not in ("crypto", "securities"):
        raise HTTPException(status_code=404, detail="unknown market")
    try:
        return run_workflow_once(
            market,
            body.workflow_name.strip(),
            operator=body.operator,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.post("/api/n8n/workflows/{workflow_id}/activate")
def n8n_activate(
    workflow_id: str,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    try:
        w = activate_workflow(workflow_id)
        return {"status": "ok", "workflow": {"id": w.get("id"), "name": w.get("name"), "active": w.get("active")}}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.post("/api/n8n/workflows/{workflow_id}/deactivate")
def n8n_deactivate(
    workflow_id: str,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    try:
        w = deactivate_workflow(workflow_id)
        return {"status": "ok", "workflow": {"id": w.get("id"), "name": w.get("name"), "active": w.get("active")}}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.post("/api/n8n/workflows/{workflow_id}/cron")
def n8n_set_cron(
    workflow_id: str,
    body: N8nCronRequest,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    try:
        w = set_workflow_cron(
            workflow_id,
            cron_expression=body.cron_expression,
            node_id=body.node_id,
            node_name=body.node_name,
        )
        return {"status": "ok", "workflow": {"id": w.get("id"), "name": w.get("name")}}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.get("/api/news/for-symbol/{symbol}")
def news_for_symbol(
    symbol: str,
    limit: int = 8,
    market: str | None = None,
) -> list[dict[str, Any]]:
    if market is not None and market not in ("crypto", "securities"):
        raise HTTPException(status_code=400, detail="market must be crypto or securities")
    return list_news_for_symbol(symbol, limit=limit, market=market)


@app.get("/api/news/verification-stats")
def news_verification_stats_endpoint() -> dict[str, Any]:
    return news_verification_stats()


@app.get("/api/news/sources")
def news_sources() -> list[dict[str, Any]]:
    return list_sources_enriched()


@app.post("/api/admin/services/restart-plan")
def admin_restart_plan(
    body: dict[str, Any] | None = None,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    services = (body or {}).get("services")
    return services_restart_plan(services)


# --- Admin / console / telegram ---

@app.get("/api/system/status")
def system_status() -> dict[str, Any]:
    return get_system_status()


@app.get("/api/stats/digest")
def stats_digest_endpoint(days: int = 7) -> dict[str, Any]:
    return stats_digest(days=days)


@app.post("/api/admin/kill-switch")
def admin_kill_switch(
    body: KillSwitchRequest,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    return apply_kill_switch(enabled=body.enabled, operator=body.operator, source=body.source)


@app.post("/api/admin/trading-mode")
def admin_trading_mode(
    body: TradingModeRequest,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    try:
        if body.mode in ("demo", "live"):
            return apply_operation_mode(body.mode, operator=body.operator)
        return apply_trading_mode(
            normalize_trading_mode(body.mode),
            operator=body.operator,
            apply_workflows=body.apply_workflows,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/admin/trading-mode/reset")
def admin_trading_mode_reset(
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    return clear_trading_mode(operator="web:operator")


@app.post("/api/admin/markets/{market}/mode")
def admin_market_mode(
    market: str,
    body: MarketModeRequest,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(
        password=body.password or x_operator_password,
        admin_key=x_admin_key,
    )
    if market not in ("crypto", "securities"):
        raise HTTPException(status_code=404, detail="unknown market")
    try:
        return apply_market_operation_mode(
            market,
            body.mode,
            operator=body.operator,
            apply_workflows=body.apply_workflows,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/admin/markets/{market}/mode/reset")
def admin_market_mode_reset(
    market: str,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    if market not in ("crypto", "securities"):
        raise HTTPException(status_code=404, detail="unknown market")
    try:
        return clear_market_mode(market, operator="web:operator")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/admin/workflows/{workflow_name}/toggle")
def admin_workflow_toggle(
    workflow_name: str,
    body: WorkflowToggleRequest,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    try:
        return toggle_workflow_by_name(
            workflow_name,
            active=body.active,
            operator=body.operator,
        )
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.post("/api/admin/smoke-test")
def admin_smoke_test(
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    return run_smoke_test()


@app.post("/api/admin/confirmations")
def admin_create_confirmation(
    body: ConfirmationRequest,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    return create_confirmation(
        action_type=body.action_type,
        title=body.title,
        payload=body.payload,
        ttl_minutes=body.ttl_minutes,
        source=body.source,
    )


@app.get("/api/admin/confirmations/pending")
def admin_pending_confirmations() -> list[dict[str, Any]]:
    return list_pending_confirmations()


@app.post("/api/admin/confirmations/{conf_id}/resolve")
def admin_resolve_confirmation(
    conf_id: str,
    body: ConfirmationResolveRequest,
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    return resolve_confirmation(conf_id, decision=body.decision, operator=body.operator)


@app.post("/api/notify/telegram")
def api_notify_telegram(body: TelegramNotifyRequest) -> dict[str, Any]:
    return notify_telegram(level=body.level, message=body.message)


@app.get("/api/telegram/proxy/status")
def telegram_proxy_status() -> dict[str, Any]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or None
    return proxy_status(bot_token=token)


@app.post("/api/admin/telegram/proxy/reprobe")
def telegram_proxy_reprobe(
    x_operator_password: str | None = Header(None, alias="X-Operator-Password"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_operator_auth(password=x_operator_password, admin_key=x_admin_key)
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or None
    proxy = select_working_proxy(force=True, bot_token=token)
    return {"proxy": proxy, **proxy_status(bot_token=token)}
