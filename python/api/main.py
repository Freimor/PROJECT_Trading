"""HTTP API for n8n workflows — full trading automation backend."""

from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backtest.metrics import dry_run_funnel, signal_summary
from binance_client import get_account_balances, get_open_orders, place_market_order
from bridges.tinvest_bridge import check_tinvest_connection, get_portfolio_snapshot, post_dca_order
from testing_service import get_testing_overview, get_tinvest_sandbox_dashboard
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
    list_news_sources,
    list_recent_news,
    wiki_table_of_contents,
)
from config_loader import load_config, wiki_root
from crypto_pipeline import run_crypto_signal
from effective_config import get_guardrails
from db.connection import get_connection, get_db_path
from db.init_db import init_database
from evaluation.replay import champion_challenger_report, evaluation_metrics, replay_by_inputs_hash
from event_log import log_event
from guardrails import enforce_guardrails, position_size_dry_run
from indicators.technical import compute_indicators, parse_binance_klines, rule_filter
from llm_client import validate_signal
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
from paper_trading_service import (
    capture_snapshot,
    get_paper_config,
    paper_effectiveness,
    reset_paper_session,
    run_crypto_paper_trade,
    run_securities_swing_paper,
    start_paper_session,
)
from n8n_service import (
    activate_workflow,
    deactivate_workflow,
    list_workflows,
    set_workflow_cron,
)
from benchmark_service import (
    aggregate_golden_results,
    benchmark_report,
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
from securities_pipeline import run_securities_dca_dry_run, run_securities_swing_dry_run
from telegram_proxy import proxy_status, select_working_proxy


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    seed_sources()
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


class KillSwitchRequest(BaseModel):
    enabled: bool
    operator: str = "api"
    source: str = "web"


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


def _check_admin_key(admin_key: str | None) -> None:
    expected = os.environ.get("ADMIN_API_KEY", "").strip()
    if expected and admin_key != expected:
        raise HTTPException(status_code=401, detail="invalid admin key")


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
    env: str | None = None,
    decision: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        query = "SELECT * FROM trade_events WHERE 1=1"
        params: list[Any] = []
        if market:
            query += " AND market = ?"
            params.append(market)
        if stage:
            query += " AND stage = ?"
            params.append(stage)
        if env:
            query += " AND env = ?"
            params.append(env)
        if decision:
            query += " AND decision = ?"
            params.append(decision)
        query += " ORDER BY event_at DESC LIMIT ?"
        params.append(limit)
        return [dict(row) for row in conn.execute(query, params).fetchall()]
    finally:
        conn.close()


# --- Config ---

@app.get("/api/config/{name}")
def get_config(name: str) -> dict[str, Any]:
    allowed = {"guardrails", "crypto_config", "securities_config"}
    if name not in allowed:
        raise HTTPException(status_code=404, detail="unknown config")
    return load_config(name)


# --- Crypto pipeline (этап 2) ---

@app.post("/api/crypto/signal")
def crypto_signal(body: CryptoSignalRequest) -> dict[str, Any]:
    return run_crypto_signal(
        symbol=body.symbol, env=body.env,
        skip_llm=body.skip_llm, equity=body.equity,
    )


@app.get("/api/crypto/pairs")
def crypto_pairs() -> list[str]:
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
    if body.env == "live" and guardrails.get("trading", {}).get("live_requires_manual_flag"):
        live_flag = os.environ.get("LIVE_TRADING_ENABLED", "false").lower() == "true"
        if not live_flag:
            return {"status": "blocked", "reject_reason": "live_requires_manual_flag"}

    rid = body.request_id or str(uuid.uuid4())
    result = place_market_order(
        symbol=body.symbol, side=body.side, quantity=body.quantity,
        testnet=body.testnet, request_id=rid,
    )
    log_event(
        market="crypto", env="paper" if body.testnet else "live",
        stage="order", symbol=body.symbol,
        decision="submitted" if result.get("orderId") and result.get("http_status") == 200 else "error",
        request_id=rid, payload=result,
        workflow_name="crypto-execute-testnet",
    )
    return {"request_id": rid, **result}


@app.get("/api/binance/open-orders")
def binance_open_orders(symbol: str | None = None, testnet: bool = True) -> list[dict]:
    return get_open_orders(symbol, testnet=testnet)


@app.get("/api/binance/balances")
def binance_balances(testnet: bool = True) -> list[dict]:
    return get_account_balances(testnet=testnet)


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
    return load_config("securities_config").get("swing_signals", {}).get("universe", [])


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
    return get_tinvest_sandbox_dashboard(days=days)


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


@app.get("/api/wiki/toc")
def wiki_toc() -> dict[str, Any]:
    return wiki_table_of_contents()


@app.get("/api/news/latest")
def news_latest(limit: int = 8, include_trades: bool = True) -> list[dict[str, Any]]:
    return list_recent_news(limit=limit, include_trades=include_trades)


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


@app.post("/api/n8n/workflows/{workflow_id}/activate")
def n8n_activate(workflow_id: str) -> dict[str, Any]:
    try:
        w = activate_workflow(workflow_id)
        return {"status": "ok", "workflow": {"id": w.get("id"), "name": w.get("name"), "active": w.get("active")}}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.post("/api/n8n/workflows/{workflow_id}/deactivate")
def n8n_deactivate(workflow_id: str) -> dict[str, Any]:
    try:
        w = deactivate_workflow(workflow_id)
        return {"status": "ok", "workflow": {"id": w.get("id"), "name": w.get("name"), "active": w.get("active")}}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.post("/api/n8n/workflows/{workflow_id}/cron")
def n8n_set_cron(workflow_id: str, body: N8nCronRequest) -> dict[str, Any]:
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
def news_for_symbol(symbol: str, limit: int = 8) -> list[dict[str, Any]]:
    return list_news_for_symbol(symbol, limit=limit)


@app.get("/api/news/verification-stats")
def news_verification_stats_endpoint() -> dict[str, Any]:
    return news_verification_stats()


@app.get("/api/news/sources")
def news_sources() -> list[dict[str, Any]]:
    return list_news_sources()


@app.post("/api/admin/services/restart-plan")
def admin_restart_plan(
    body: dict[str, Any] | None = None,
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_admin_key(x_admin_key)
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
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_admin_key(x_admin_key)
    return apply_kill_switch(enabled=body.enabled, operator=body.operator, source=body.source)


@app.post("/api/admin/smoke-test")
def admin_smoke_test(x_admin_key: str | None = Header(None, alias="X-Admin-Key")) -> dict[str, Any]:
    _check_admin_key(x_admin_key)
    return run_smoke_test()


@app.post("/api/admin/confirmations")
def admin_create_confirmation(
    body: ConfirmationRequest,
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_admin_key(x_admin_key)
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
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    _check_admin_key(x_admin_key)
    return resolve_confirmation(conf_id, decision=body.decision, operator=body.operator)


@app.post("/api/notify/telegram")
def api_notify_telegram(body: TelegramNotifyRequest) -> dict[str, Any]:
    return notify_telegram(level=body.level, message=body.message)


@app.get("/api/telegram/proxy/status")
def telegram_proxy_status() -> dict[str, Any]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or None
    return proxy_status(bot_token=token)


@app.post("/api/admin/telegram/proxy/reprobe")
def telegram_proxy_reprobe(x_admin_key: str | None = Header(None, alias="X-Admin-Key")) -> dict[str, Any]:
    _check_admin_key(x_admin_key)
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or None
    proxy = select_working_proxy(force=True, bot_token=token)
    return {"proxy": proxy, **proxy_status(bot_token=token)}
