"""Aggregated data for Telegram bot menus."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from admin_service import get_live_checklist, get_system_status, ping_ollama, services_restart_plan, stats_digest
from automation_docs import get_automat_doc_section, get_automat_docs_index
from backtest.metrics import dry_run_funnel, signal_summary
from bridges.tinvest_bridge import check_tinvest_connection, get_portfolio_snapshot
from config_loader import load_config, wiki_root
from strategy_service import get_active_strategy_id, get_strategy_state
from db.connection import get_connection
from effective_config import get_config_effective, get_guardrails
from evaluation.replay import evaluation_metrics
from testing_service import get_tinvest_sandbox_dashboard


def list_news_sources() -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, name, source_tier, enabled, last_fetched_at, fetch_interval_min
            FROM news_sources ORDER BY name
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def list_recent_news(*, limit: int = 8, include_trades: bool | None = None) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        rows = conn.execute(
            """
            SELECT title, source_name, source_tier, published_at, source_url,
                   verification_status, trust_score, matched_symbols, relevance_score
            FROM news_items
            WHERE expires_at IS NULL OR expires_at > ?
            ORDER BY published_at DESC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()
        news = [{**dict(r), "type": "news"} for r in rows]
    finally:
        conn.close()

    if include_trades is None:
        try:
            from news_alert_service import get_alert_settings, list_trade_news

            include_trades = get_alert_settings()["trade_alerts"].get("enabled", True)
        except Exception:
            include_trades = False

    if include_trades:
        try:
            from news_alert_service import list_trade_news

            trades = list_trade_news(limit=limit)
            merged = news + trades
            merged.sort(key=lambda x: x.get("published_at") or "", reverse=True)
            return merged[:limit]
        except Exception:
            pass
    return news


def wiki_table_of_contents() -> dict[str, Any]:
    root = wiki_root()
    sections: list[dict[str, Any]] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir() or not path.name[:1].isdigit():
            continue
        md_count = len(list(path.glob("*.md")))
        sections.append({"folder": path.name, "files": md_count})
    structure_file = root / "Wiki_structure.md"
    intro = ""
    if structure_file.exists():
        text = structure_file.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("База знаний"):
                intro = line.strip()
                break
    return {
        "wiki_path": str(root),
        "intro": intro or "Trading Wiki — база знаний системы",
        "sections": sections,
        "glossary": (root / "Financial_glossary.md").exists(),
    }


def get_system_summary() -> dict[str, Any]:
    guardrails = get_guardrails()
    crypto = get_config_effective("crypto_config")
    securities = get_config_effective("securities_config")
    status = get_system_status()
    trading = guardrails.get("trading", {})
    return {
        "trading_mode": trading.get("mode"),
        "kill_switch": trading.get("kill_switch"),
        "allowed_envs": trading.get("allowed_envs", []),
        "live_enabled": os.environ.get("LIVE_TRADING_ENABLED", "false").lower() == "true",
        "crypto": {
            "env": crypto.get("env"),
            "mode": crypto.get("mode"),
            "pairs": crypto.get("pairs", []),
            "llm_model": crypto.get("llm", {}).get("ollama_model"),
            "schedule": crypto.get("schedule", {}).get("cron"),
        },
        "securities": {
            "env": securities.get("env"),
            "mode": securities.get("mode"),
            "active_mode": securities.get("active_mode"),
            "dca_ticker": securities.get("index_dca", {}).get("ticker"),
            "swing_model": securities.get("swing_signals", {}).get("ollama_model"),
        },
        "ollama": status.get("ollama"),
        "last_event": status.get("last_event"),
    }


def _moex_next_open(session: dict[str, Any]) -> dict[str, Any] | None:
    """When MOEX is closed, return next open time in MSK."""
    from datetime import date, timedelta

    msk = datetime.now(ZoneInfo("Europe/Moscow"))
    start_h = int(session.get("moex_start_hour", 10))
    end_h = int(session.get("moex_end_hour", 19))

    if msk.weekday() < 5 and start_h <= msk.hour < end_h:
        return None

    def at_open(d: date) -> datetime:
        return datetime(d.year, d.month, d.day, start_h, 0, tzinfo=msk.tzinfo)

    today = msk.date()
    if msk.weekday() < 5 and msk.hour < start_h:
        nxt = at_open(today)
        kind = "today"
    else:
        for offset in range(1, 8):
            cand = today + timedelta(days=offset)
            if cand.weekday() < 5:
                nxt = at_open(cand)
                if offset == 1:
                    kind = "tomorrow"
                else:
                    kind = "weekday"
                break
        else:
            return None

    return {
        "kind": kind,
        "time_msk": nxt.strftime("%H:%M"),
        "weekday": nxt.weekday(),
        "at_iso": nxt.isoformat(),
    }


def get_host_status() -> dict[str, Any]:
    guardrails = get_guardrails()
    session = guardrails.get("session", {})
    msk = datetime.now(ZoneInfo("Europe/Moscow"))
    utc = datetime.now(timezone.utc)
    host: dict[str, Any] = {"available": False}
    try:
        import psutil

        mem = psutil.virtual_memory()
        host = {
            "available": True,
            "cpu_pct": psutil.cpu_percent(interval=0.1),
            "ram_used_gb": round(mem.used / (1024**3), 1),
            "ram_total_gb": round(mem.total / (1024**3), 1),
            "ram_pct": mem.percent,
        }
    except ImportError:
        host["note"] = "psutil не установлен — метрики CPU/RAM недоступны"

    conn = get_connection()
    try:
        health = [
            dict(r)
            for r in conn.execute(
                """
                SELECT service_name, status, checked_at
                FROM system_health_checks
                ORDER BY checked_at DESC LIMIT 8
                """
            ).fetchall()
        ]
    finally:
        conn.close()

    return {
        "utc_time": utc.replace(microsecond=0).isoformat(),
        "moscow_time": msk.strftime("%Y-%m-%d %H:%M MSK"),
        "moex_session": (
            f"{session.get('moex_start_hour', 10)}:00–"
            f"{session.get('moex_end_hour', 19)}:00 MSK"
        ),
        "in_moex_session": (
            session.get("moex_start_hour", 10)
            <= msk.hour
            < session.get("moex_end_hour", 19)
            and msk.weekday() < 5
        ),
        "moex_next_open": _moex_next_open(session),
        "ollama": ping_ollama(),
        "host": host,
        "services_health": health,
        "proxy": os.environ.get("TELEGRAM_AWESOME_VPN_ENABLED", "false"),
    }


def get_automation_overview(*, days: int = 7) -> dict[str, Any]:
    crypto_cfg = load_config("crypto_config")
    sec_cfg = load_config("securities_config")
    guardrails = get_guardrails()
    trading = guardrails.get("trading", {})
    digest = stats_digest(days=days)
    tinvest = check_tinvest_connection(sandbox=True)
    funnel = digest.get("funnel", {})

    crypto_strategy = get_strategy_state("crypto")
    sec_strategy = get_strategy_state("securities")

    return {
        "kill_switch": bool(trading.get("kill_switch")),
        "trading_mode": trading.get("mode", "dry_run"),
        "live_flag": os.environ.get("LIVE_TRADING_ENABLED", "false").lower() == "true",
        "crypto": {
            "env": crypto_cfg.get("env"),
            "mode": crypto_cfg.get("mode"),
            "pairs": crypto_cfg.get("pairs", []),
            "active_strategy": crypto_strategy["active"],
            "strategy_label": crypto_strategy["strategy"].get("label"),
            "workflow": crypto_strategy["strategy"].get("workflow"),
            "funnel_signal": funnel.get("crypto", {}).get("signal"),
        },
        "securities": {
            "env": sec_cfg.get("env"),
            "mode": sec_cfg.get("mode"),
            "active_mode": sec_strategy["active"],
            "strategy_label": sec_strategy["strategy"].get("label"),
            "workflows": [s.get("workflow") for s in sec_strategy["strategies"]],
            "tinvest_api": tinvest.get("status"),
            "workflow": sec_strategy["strategy"].get("workflow"),
            "funnel_signal": funnel.get("securities", {}).get("signal"),
        },
        "ollama": ping_ollama(),
        "dry_run_signals_7d": digest.get("dry_run_signals", 0),
        "last_event": get_system_status().get("last_event"),
    }


def get_crypto_testnet_dashboard(*, days: int = 7) -> dict[str, Any]:
    crypto = load_config("crypto_config")
    return {
        "days": days,
        "config": {
            "env": crypto.get("env"),
            "mode": crypto.get("mode"),
            "pairs": crypto.get("pairs", []),
            "llm_model": crypto.get("llm", {}).get("ollama_model"),
            "prompt_version": crypto.get("llm", {}).get("prompt_version"),
            "schedule": crypto.get("schedule", {}).get("cron"),
        },
        "funnel": dry_run_funnel(market="crypto", days=days),
        "summary": signal_summary(market="crypto", days=days),
        "llm_eval": evaluation_metrics(market="crypto", days=days),
        "ollama": ping_ollama(),
    }


def get_live_readiness() -> dict[str, Any]:
    return get_live_checklist()


def services_restart_plan_for_bot(services: list[str] | None = None) -> dict[str, Any]:
    return services_restart_plan(services)


def automat_documentation(section: str | None = None) -> dict[str, Any]:
    if section:
        return get_automat_doc_section(section)
    return get_automat_docs_index()
