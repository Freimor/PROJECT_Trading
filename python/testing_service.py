"""Aggregated testing / sandbox dashboards for console and Telegram."""

from __future__ import annotations

from typing import Any

from admin_service import ping_ollama, stats_digest
from backtest.metrics import dry_run_funnel, signal_summary
from bridges.tinvest_bridge import check_tinvest_connection, get_portfolio_snapshot
from config_loader import load_config
from db.connection import get_connection
from effective_config import get_guardrails
from evaluation.replay import evaluation_metrics


def _recent_events(
    *,
    market: str,
    envs: tuple[str, ...] | None = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        query = "SELECT * FROM trade_events WHERE market = ?"
        params: list[Any] = [market]
        if envs:
            placeholders = ", ".join("?" for _ in envs)
            query += f" AND env IN ({placeholders})"
            params.extend(envs)
        query += " ORDER BY event_at DESC LIMIT ?"
        params.append(limit)
        return [dict(row) for row in conn.execute(query, params).fetchall()]
    finally:
        conn.close()


def _order_events(
    *,
    market: str,
    envs: tuple[str, ...],
    limit: int = 10,
) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        placeholders = ", ".join("?" for _ in envs)
        rows = conn.execute(
            f"""
            SELECT event_at, env, stage, decision, symbol, notional, reject_reason, payload_json
            FROM trade_events
            WHERE market = ? AND stage = 'order' AND env IN ({placeholders})
            ORDER BY event_at DESC
            LIMIT ?
            """,
            (market, *envs, limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_testing_overview(*, days: int = 7) -> dict[str, Any]:
    guardrails = get_guardrails()
    crypto = load_config("crypto_config")
    securities = load_config("securities_config")
    digest = stats_digest(days=days)
    return {
        "days": days,
        "ollama": ping_ollama(),
        "trading_mode": guardrails.get("trading", {}).get("mode", "dry_run"),
        "kill_switch": bool(guardrails.get("trading", {}).get("kill_switch")),
        "crypto": {
            "env": crypto.get("env"),
            "mode": crypto.get("mode"),
            "pairs": crypto.get("pairs", []),
            "llm_model": crypto.get("llm", {}).get("ollama_model"),
        },
        "securities": {
            "env": securities.get("env"),
            "mode": securities.get("mode"),
            "active_mode": securities.get("active_mode"),
        },
        "stats": digest,
        "funnel": digest.get("funnel", {}),
        "llm_eval": {
            "crypto": evaluation_metrics(market="crypto", days=days),
            "securities": evaluation_metrics(market="securities", days=days),
        },
    }


def get_tinvest_sandbox_dashboard(*, days: int = 7) -> dict[str, Any]:
    sec = load_config("securities_config")
    guardrails = get_guardrails()
    dca = sec.get("index_dca", sec.get("dca", {}))
    swing = sec.get("swing_signals", {})

    sandbox_envs = ("dry_run", "paper", "sandbox")
    return {
        "days": days,
        "connection": check_tinvest_connection(sandbox=True),
        "portfolio": get_portfolio_snapshot(sandbox=True),
        "automation": {
            "env": sec.get("env"),
            "mode": sec.get("mode"),
            "active_mode": sec.get("active_mode"),
            "trading_mode": guardrails.get("trading", {}).get("mode"),
            "index_dca": {
                "ticker": dca.get("ticker", "TMOS"),
                "amount_rub": dca.get("amount_rub", 10000),
                "order_type": dca.get("order_type", "MARKET"),
                "schedule_cron": dca.get("schedule_cron"),
            },
            "swing_signals": {
                "universe": swing.get("universe", []),
                "timeframe": swing.get("timeframe"),
                "schedule_cron": swing.get("schedule_cron"),
                "llm_model": swing.get("ollama_model"),
                "prompt_version": swing.get("prompt_version"),
                "llm_min_confidence": swing.get("llm_min_confidence"),
            },
            "workflows": [
                "securities-dca-sandbox",
                "securities-swing-dry-run",
            ],
        },
        "funnel": dry_run_funnel(market="securities", days=days),
        "summary": signal_summary(market="securities", days=days),
        "llm_eval": evaluation_metrics(market="securities", days=days),
        "llm_events": _recent_events(
            market="securities", envs=sandbox_envs, limit=8,
        ),
        "recent_events": _recent_events(
            market="securities", envs=sandbox_envs, limit=12,
        ),
        "orders": _order_events(
            market="securities", envs=sandbox_envs, limit=10,
        ),
    }
