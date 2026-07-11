"""Workflow session reports — generated when automation stops or switches workflow."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from config_loader import load_config, load_prompt_body, wiki_root
from db.connection import get_connection
from db.migrate import run_migrations
from effective_config import get_config_effective
from llm_client import ollama_host
from workflow_session_service import get_workflow_session_stats
from workflow_universe_service import resolve_workflow_for_universe

_ORDER_OK = ("submitted", "execute", "executed", "approve")
_ORDER_FAIL = ("error", "reject", "skip")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _workflow_event_names(workflow_name: str | None) -> list[str] | None:
    if not workflow_name:
        return None
    canonical = resolve_workflow_for_universe(workflow_name)
    names = {workflow_name, canonical}
    if canonical.startswith("crypto-scalp-hybrid"):
        names.add("crypto-scalp-auto")
    if canonical == "crypto-signal-paper":
        names.add("crypto-paper-auto")
    return sorted(names)


def _parse_payload(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _session_wf_clause(workflow_name: str, *, alias: str = "") -> tuple[str, list[str]]:
    wf_names = _workflow_event_names(workflow_name) or [workflow_name]
    col = f"{alias}.workflow_name" if alias else "workflow_name"
    placeholders = ",".join("?" for _ in wf_names)
    return f" AND {col} IN ({placeholders})", wf_names


def _collect_account_actions(
    conn,
    market: str,
    started_at: str,
    ended_at: str,
    workflow_name: str,
) -> list[dict[str, Any]]:
    wf_clause, wf_names = _session_wf_clause(workflow_name, alias="o")
    params: list[Any] = [market, started_at, ended_at, *_ORDER_OK, *wf_names]
    ok_ph = ",".join("?" for _ in _ORDER_OK)
    rows = conn.execute(
        f"""
        SELECT o.event_at, o.symbol, o.decision, o.notional, o.currency, o.reject_reason,
               o.inputs_hash, o.payload_json AS order_json,
               r.payload_json AS risk_json
        FROM trade_events o
        LEFT JOIN trade_events r
          ON r.market = o.market AND r.inputs_hash = o.inputs_hash AND r.stage = 'risk'
        WHERE o.market = ? AND o.event_at >= ? AND o.event_at <= ?
          AND o.stage = 'order' AND o.decision IN ({ok_ph})
        {wf_clause}
        ORDER BY o.event_at ASC
        """,
        params,
    ).fetchall()

    actions: list[dict[str, Any]] = []
    for row in rows:
        order = _parse_payload(row["order_json"])
        risk = _parse_payload(row["risk_json"])
        side = str(order.get("side") or risk.get("side") or "BUY").upper()
        qty = risk.get("quantity") or order.get("executedQty") or order.get("origQty")
        price = risk.get("entry_price") or order.get("price") or order.get("fills", [{}])[0].get("price")
        actions.append(
            {
                "event_at": row["event_at"],
                "symbol": row["symbol"],
                "side": side,
                "quantity": qty,
                "price": price,
                "notional": row["notional"] or risk.get("notional"),
                "currency": row["currency"] or ("USDT" if market == "crypto" else "RUB"),
                "decision": row["decision"],
                "order_id": order.get("orderId"),
            }
        )
    return actions


def _collect_statistics(
    conn,
    market: str,
    started_at: str,
    ended_at: str,
    workflow_name: str,
) -> dict[str, Any]:
    wf_clause, wf_names = _session_wf_clause(workflow_name)
    base_params: list[Any] = [market, started_at, ended_at, *wf_names]

    def _count(stage: str | None = None, decision: str | None = None) -> int:
        clauses = ["market = ?", "event_at >= ?", "event_at <= ?"]
        params: list[Any] = [market, started_at, ended_at]
        if stage:
            clauses.append("stage = ?")
            params.append(stage)
        if decision:
            clauses.append("decision = ?")
            params.append(decision)
        params.extend(wf_names)
        sql = f"SELECT COUNT(*) AS c FROM trade_events WHERE {' AND '.join(clauses)}{wf_clause}"
        return int(conn.execute(sql, params).fetchone()["c"] or 0)

    stage_breakdown = conn.execute(
        f"""
        SELECT stage, decision, reject_reason, COUNT(*) AS cnt
        FROM trade_events
        WHERE market = ? AND event_at >= ? AND event_at <= ?
        {wf_clause}
        GROUP BY stage, decision, reject_reason
        ORDER BY cnt DESC
        """,
        base_params,
    ).fetchall()

    reject_rows = conn.execute(
        f"""
        SELECT reject_reason, COUNT(*) AS cnt
        FROM trade_events
        WHERE market = ? AND event_at >= ? AND event_at <= ?
          AND reject_reason IS NOT NULL AND reject_reason != ''
        {wf_clause}
        GROUP BY reject_reason
        ORDER BY cnt DESC
        LIMIT 20
        """,
        base_params,
    ).fetchall()

    signals = _count(stage="signal")
    filter_approve = _count(stage="filter", decision="approve")
    filter_skip = _count(stage="filter", decision="skip")
    filter_reject = _count(stage="filter", decision="reject")
    llm_approve = _count(stage="llm", decision="approve")
    llm_reject = _count(stage="llm", decision="reject")
    guard_approve = _count(stage="guardrails", decision="approve")
    guard_reject = _count(stage="guardrails", decision="reject")
    orders_ok = sum(_count(stage="order", decision=d) for d in _ORDER_OK)
    orders_failed = sum(_count(stage="order", decision=d) for d in _ORDER_FAIL)

    return {
        "signals": signals,
        "filter_approve": filter_approve,
        "filter_skip": filter_skip,
        "filter_reject": filter_reject,
        "llm_approve": llm_approve,
        "llm_reject": llm_reject,
        "guardrails_approve": guard_approve,
        "guardrails_reject": guard_reject,
        "orders_ok": orders_ok,
        "orders_failed": orders_failed,
        "stage_breakdown": [dict(r) for r in stage_breakdown],
        "reject_reasons": [dict(r) for r in reject_rows],
    }


def build_workflow_session_report(
    market: str,
    workflow_name: str,
    *,
    started_at: str,
    ended_at: str,
    reason: str = "stop",
    operator: str = "system",
) -> dict[str, Any]:
    """Aggregate session data before workflow_started_at is cleared."""
    from automation_control_service import trading_mode_to_operation
    from workflow_pnl_service import get_workflow_pnl

    config_name = "crypto_config" if market == "crypto" else "securities_config"
    cfg = get_config_effective(config_name)
    mode = str(cfg.get("mode", "dry_run"))
    operation_mode = trading_mode_to_operation(mode)

    wallet_pnl = get_workflow_pnl(market, active=True, operation_mode=operation_mode)
    session_stats = get_workflow_session_stats(
        market,
        started_at=started_at,
        active_workflow=workflow_name,
        workflow_pnl=wallet_pnl,
    )

    run_migrations()
    conn = get_connection()
    try:
        statistics = _collect_statistics(conn, market, started_at, ended_at, workflow_name)
        account_actions = _collect_account_actions(conn, market, started_at, ended_at, workflow_name)
    finally:
        conn.close()

    duration_sec: int | None = None
    try:
        start_ts = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
        end_ts = datetime.fromisoformat(str(ended_at).replace("Z", "+00:00"))
        if start_ts.tzinfo is None:
            start_ts = start_ts.replace(tzinfo=timezone.utc)
        if end_ts.tzinfo is None:
            end_ts = end_ts.replace(tzinfo=timezone.utc)
        duration_sec = max(0, int((end_ts - start_ts).total_seconds()))
    except ValueError:
        duration_sec = None

    return {
        "market": market,
        "workflow_name": workflow_name,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_sec": duration_sec,
        "reason": reason,
        "operator": operator,
        "trading_mode": mode,
        "operation_mode": operation_mode,
        "session_stats": session_stats,
        "wallet_pnl": wallet_pnl,
        "statistics": statistics,
        "account_actions": account_actions,
    }


def _fallback_narrative(report: dict[str, Any]) -> dict[str, Any]:
    stats = report.get("statistics") or {}
    actions = report.get("account_actions") or []
    rejects = stats.get("reject_reasons") or []
    session = report.get("session_stats") or {}
    top_reject = rejects[0]["reject_reason"] if rejects else "—"
    return {
        "success_rating": "medium",
        "headline": (
            f"Сессия {report.get('workflow_name')}: "
            f"{stats.get('signals', 0)} сигналов, {len(actions)} сделок на счёте"
        ),
        "success_factors": [
            f"Одобрено ордеров: {stats.get('orders_ok', 0)}",
            f"PnL по сделкам сессии: {session.get('pnl_delta')} {session.get('currency') or ''}".strip(),
        ],
        "failure_factors": [
            f"Отклонений LLM: {stats.get('llm_reject', 0)}",
            f"Ошибок ордеров: {stats.get('orders_failed', 0)}",
        ],
        "reject_analysis": (
            f"Основная причина отказов: {top_reject}. "
            f"Фильтр skip: {stats.get('filter_skip', 0)}, reject: {stats.get('filter_reject', 0)}."
        ),
        "recommendations": [
            "Проверьте топ reject_reason в таблице статистики перед следующим запуском.",
        ],
        "risk_notes": "LLM-анализ недоступен — сформирован шаблонный отчёт.",
        "source": "rules_fallback",
    }


def generate_llm_session_narrative(report: dict[str, Any]) -> dict[str, Any]:
    """LLM post-mortem; falls back to template if Ollama unavailable."""
    try:
        guardrails = load_config("guardrails")
        if guardrails.get("llm", {}).get("mode") == "disabled":
            out = _fallback_narrative(report)
            out["source"] = "llm_disabled"
            return out
    except Exception:
        pass

    market = str(report.get("market") or "crypto")
    cfg = get_config_effective("crypto_config" if market == "crypto" else "securities_config")
    model = cfg.get("ollama_model", "qwen3.5:9b")
    if "scalp" in str(report.get("workflow_name", "")):
        scalp = load_config("crypto_scalp_hybrid")
        if scalp.get("llm_enabled"):
            model = scalp.get("ollama_model_fast", model)

    compact = {
        "workflow": report.get("workflow_name"),
        "market": market,
        "duration_sec": report.get("duration_sec"),
        "statistics": report.get("statistics"),
        "session_pnl": report.get("session_stats"),
        "wallet_pnl": report.get("wallet_pnl"),
        "account_actions": report.get("account_actions"),
    }
    system_raw = load_prompt_body("workflow_session_report_v1.md")
    if system_raw.startswith("---"):
        parts = system_raw.split("---", 2)
        system_prompt = parts[2].strip() if len(parts) >= 3 else system_raw
    else:
        system_prompt = system_raw

    payload = {
        "model": model,
        "think": False,
        "format": "json",
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(compact, ensure_ascii=False, indent=2),
            },
        ],
        "options": {"temperature": 0.15, "num_predict": 1024},
    }
    if "qwen3.5" in str(model).lower():
        payload["think"] = False

    start = datetime.now(timezone.utc)
    try:
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(f"{ollama_host()}/api/chat", json=payload)
        latency_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        if resp.status_code != 200:
            out = _fallback_narrative(report)
            out["source"] = "ollama_http_error"
            out["llm_error"] = resp.text[:300]
            return {"narrative": out, "model": model, "latency_ms": latency_ms}

        content = resp.json().get("message", {}).get("content", "{}")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("invalid_json")
        parsed["source"] = "ollama"
        return {"narrative": parsed, "model": model, "latency_ms": latency_ms, "raw": content[:4000]}
    except Exception as exc:
        latency_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        out = _fallback_narrative(report)
        out["source"] = "ollama_error"
        out["llm_error"] = str(exc)[:300]
        return {"narrative": out, "model": model, "latency_ms": latency_ms}


def _report_to_markdown(report: dict[str, Any], narrative: dict[str, Any]) -> str:
    stats = report.get("statistics") or {}
    narr = narrative.get("narrative") or {}
    lines = [
        f"# Отчёт workflow: {report.get('workflow_name')}",
        "",
        f"- Рынок: {report.get('market')}",
        f"- Начало: {report.get('started_at')}",
        f"- Конец: {report.get('ended_at')}",
        f"- Длительность: {report.get('duration_sec')} с",
        f"- Причина завершения: {report.get('reason')}",
        "",
        "## Резюме LLM",
        "",
        f"**{narr.get('headline', '—')}** (рейтинг: {narr.get('success_rating', '—')})",
        "",
        narr.get("reject_analysis", ""),
        "",
        "## Статистика",
        "",
        f"- Сигналов: {stats.get('signals', 0)}",
        f"- Фильтр approve/skip/reject: {stats.get('filter_approve')}/{stats.get('filter_skip')}/{stats.get('filter_reject')}",
        f"- LLM approve/reject: {stats.get('llm_approve')}/{stats.get('llm_reject')}",
        f"- Guardrails approve/reject: {stats.get('guardrails_approve')}/{stats.get('guardrails_reject')}",
        f"- Ордера ok/fail: {stats.get('orders_ok')}/{stats.get('orders_failed')}",
        "",
        "## Действия на счёте",
        "",
    ]
    for act in report.get("account_actions") or []:
        lines.append(
            f"- {act.get('event_at')} | {act.get('side')} {act.get('symbol')} "
            f"qty={act.get('quantity')} @ {act.get('price')} "
            f"({act.get('notional')} {act.get('currency')})"
        )
    if not report.get("account_actions"):
        lines.append("- (нет исполненных ордеров)")
    lines.extend(["", "## Рекомендации", ""])
    for rec in narr.get("recommendations") or []:
        lines.append(f"- {rec}")
    return "\n".join(lines)


def persist_workflow_report(
    report: dict[str, Any],
    *,
    llm_result: dict[str, Any] | None = None,
) -> str:
    run_migrations()
    report_id = str(uuid.uuid4())
    narrative = llm_result or {}
    narr_body = narrative.get("narrative") if narrative else _fallback_narrative(report)
    full = {**report, "llm_narrative": narr_body, "llm_meta": narrative}

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO workflow_session_reports (
                id, market, workflow_name, started_at, ended_at, reason,
                report_json, llm_narrative_json, llm_model, llm_latency_ms, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                report.get("market"),
                report.get("workflow_name"),
                report.get("started_at"),
                report.get("ended_at"),
                report.get("reason"),
                json.dumps(full, ensure_ascii=False),
                json.dumps(narr_body, ensure_ascii=False),
                narrative.get("model"),
                narrative.get("latency_ms"),
                _utc_now(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    try:
        logs_dir = wiki_root() / "logs" / "executions" / "workflow_sessions"
        logs_dir.mkdir(parents=True, exist_ok=True)
        safe_ts = str(report.get("ended_at", "")).replace(":", "-")[:19]
        md_path = logs_dir / f"{safe_ts}_{report.get('workflow_name')}_{report_id[:8]}.md"
        md_path.write_text(_report_to_markdown(report, {"narrative": narr_body}), encoding="utf-8")
        full["markdown_path"] = str(md_path)
    except Exception:
        pass

    return report_id


def get_workflow_report(report_id: str) -> dict[str, Any] | None:
    run_migrations()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM workflow_session_reports WHERE id = ?", (report_id,)
        ).fetchone()
        if not row:
            return None
        out = dict(row)
        out["report"] = json.loads(out.pop("report_json", "{}") or "{}")
        out["llm_narrative"] = json.loads(out.pop("llm_narrative_json", "{}") or "{}")
        return out
    finally:
        conn.close()


def list_workflow_reports(
    *,
    market: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    run_migrations()
    capped = max(1, min(int(limit), 100))
    conn = get_connection()
    try:
        if market:
            rows = conn.execute(
                """
                SELECT id, market, workflow_name, started_at, ended_at, reason,
                       llm_model, llm_latency_ms, created_at
                FROM workflow_session_reports
                WHERE market = ?
                ORDER BY ended_at DESC
                LIMIT ?
                """,
                (market, capped),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, market, workflow_name, started_at, ended_at, reason,
                       llm_model, llm_latency_ms, created_at
                FROM workflow_session_reports
                ORDER BY ended_at DESC
                LIMIT ?
                """,
                (capped,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def finalize_workflow_session(
    market: str,
    *,
    started_at: str | None,
    workflow_name: str | None,
    reason: str = "stop",
    operator: str = "system",
    generate_llm: bool = True,
) -> dict[str, Any] | None:
    """Build, optionally LLM-summarize, and persist session report."""
    if not started_at or not workflow_name:
        return None

    ended_at = _utc_now()
    report = build_workflow_session_report(
        market,
        workflow_name,
        started_at=started_at,
        ended_at=ended_at,
        reason=reason,
        operator=operator,
    )
    llm_result = generate_llm_session_narrative(report) if generate_llm else None
    report_id = persist_workflow_report(report, llm_result=llm_result)
    return {
        "report_id": report_id,
        "market": market,
        "workflow_name": workflow_name,
        "started_at": started_at,
        "ended_at": ended_at,
        "reason": reason,
        "headline": (llm_result or {}).get("narrative", {}).get("headline"),
        "report": {**report, "id": report_id},
    }
