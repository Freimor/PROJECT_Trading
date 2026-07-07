"""News digests + trade alerts for Telegram."""

from __future__ import annotations

import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from config_loader import load_config, load_prompt_body
from db.connection import get_connection
from db.migrate import run_migrations
from effective_config import get_guardrails
from llm_client import ollama_host
from news_verification import passes_llm_gate
from runtime_settings import get_runtime_value, set_runtime_value
from telegram_notify import send_telegram_message

_SETTINGS_KEY = "news_alerts_runtime"
_HTML_TAG = re.compile(r"<[^>]+>")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _alerts_yaml() -> dict[str, Any]:
    try:
        return load_config("news_alerts")
    except FileNotFoundError:
        return {}


def get_alert_settings() -> dict[str, Any]:
    yaml_cfg = _alerts_yaml()
    runtime = get_runtime_value(_SETTINGS_KEY) or {}
    news = {**yaml_cfg.get("news_digest", {}), **runtime.get("news_digest", {})}
    trades = {**yaml_cfg.get("trade_alerts", {}), **runtime.get("trade_alerts", {})}
    return {
        "news_digest": news,
        "trade_alerts": trades,
        "watch_symbols": runtime.get("watch_symbols") or yaml_cfg.get("watch_symbols") or [],
    }


def update_alert_settings(
    *,
    news_enabled: bool | None = None,
    trade_enabled: bool | None = None,
    trade_push: bool | None = None,
    operator: str = "api",
) -> dict[str, Any]:
    current = get_alert_settings()
    news = dict(current["news_digest"])
    trades = dict(current["trade_alerts"])
    if news_enabled is not None:
        news["enabled"] = news_enabled
    if trade_enabled is not None:
        trades["enabled"] = trade_enabled
    if trade_push is not None:
        trades["push_telegram"] = trade_push
    set_runtime_value(
        _SETTINGS_KEY,
        {"news_digest": news, "trade_alerts": trades},
        updated_by=operator,
    )
    return get_alert_settings()


def resolve_watch_symbols() -> list[str]:
    settings = get_alert_settings()
    explicit = settings.get("watch_symbols") or []
    if explicit:
        return [s.upper() for s in explicit]

    symbols: set[str] = set()
    guardrails = get_guardrails()
    symbols.update(guardrails.get("symbols", {}).get("moex_whitelist", []))
    symbols.update(guardrails.get("symbols", {}).get("crypto_whitelist", []))

    try:
        sec = load_config("securities_config")
        symbols.add(sec.get("index_dca", {}).get("ticker", ""))
        symbols.update(sec.get("swing_signals", {}).get("universe", []))
    except FileNotFoundError:
        pass
    try:
        crypto = load_config("crypto_config")
        for p in crypto.get("pairs", []):
            symbols.add(p.replace("USDT", ""))
            symbols.add(p)
    except FileNotFoundError:
        pass
    return sorted(s for s in symbols if s)


def _strip_html(text: str) -> str:
    return _HTML_TAG.sub("", text or "").strip()


def _delivery_exists(alert_type: str, ref_id: str) -> bool:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM news_alert_deliveries WHERE alert_type = ? AND ref_id = ?",
            (alert_type, ref_id),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def _mark_delivered(alert_type: str, ref_id: str, *, payload: dict | None = None) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO news_alert_deliveries
                (id, alert_type, ref_id, sent_at, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                alert_type,
                ref_id,
                _utc_now(),
                json.dumps(payload or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def analyze_news_significance(
    *,
    symbol: str,
    title: str,
    summary: str,
    source_name: str,
    source_tier: str,
) -> dict[str, Any]:
    cfg = get_alert_settings()["news_digest"]
    model = cfg.get("ollama_model", "qwen3.5:9b")
    prompt_version = cfg.get("prompt_version", "news_significance_v1")
    prompt_file = f"{prompt_version}.md" if not prompt_version.endswith(".md") else prompt_version
    system_raw = load_prompt_body(prompt_file)
    if system_raw.startswith("---"):
        parts = system_raw.split("---", 2)
        system_prompt = parts[2].strip() if len(parts) >= 3 else system_raw
    else:
        system_prompt = system_raw

    clean_summary = _strip_html(summary)[:1200]
    user_content = (
        f"Symbol: {symbol}\n"
        f"Source: {source_name} ({source_tier})\n"
        f"Title: {title}\n"
        f"Summary: {clean_summary or '(нет текста)'}"
    )

    guardrails = get_guardrails()
    timeout = guardrails.get("llm", {}).get("timeout_ms", 900000) / 1000
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.15,
            "num_predict": guardrails.get("llm", {}).get("max_tokens", 2048),
        },
    }

    start = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{ollama_host()}/api/chat", json=payload)
        latency_ms = int((time.perf_counter() - start) * 1000)
        if resp.status_code != 200:
            return {
                "significant": False,
                "confidence": 0,
                "reject_reason": "ollama_http_error",
                "model": model,
                "latency_ms": latency_ms,
            }
        content = resp.json().get("message", {}).get("content", "{}")
        parsed = json.loads(content)
        parsed["model"] = model
        parsed["latency_ms"] = latency_ms
        parsed["prompt_version"] = prompt_version
        return parsed
    except (json.JSONDecodeError, httpx.HTTPError) as exc:
        return {
            "significant": False,
            "confidence": 0,
            "reject_reason": str(exc)[:200],
            "model": model,
            "latency_ms": int((time.perf_counter() - start) * 1000),
        }


def format_news_digest_telegram(
    *,
    symbol: str,
    source_name: str,
    title: str,
    summary: str,
    analysis: dict[str, Any],
    source_url: str | None = None,
) -> str:
    cfg = get_alert_settings()["news_digest"]
    max_chars = int(cfg.get("max_body_chars", 600))
    body = _strip_html(summary) or analysis.get("lead_ru") or ""
    if len(body) > max_chars:
        body = body[: max_chars - 3].rsplit(" ", 1)[0] + "..."

    headline = analysis.get("headline_ru") or title
    model = analysis.get("model", cfg.get("ollama_model", "?"))
    conf = analysis.get("confidence", 0)
    sig = analysis.get("significance_score", conf)
    impact = analysis.get("impact", "unclear")
    impact_icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪", "unclear": "🟡"}.get(
        impact, "🟡"
    )
    lo = analysis.get("price_impact_pct_low") or 0
    hi = analysis.get("price_impact_pct_high") or 0
    horizon = analysis.get("horizon_months") or 0
    impact_line = ""
    if lo or hi:
        impact_line = f"\nОценка влияния: {impact_icon} {lo}–{hi}%"
        if horizon:
            impact_line += f" / ~{horizon} мес."

    lines = [
        f"📰 {symbol} · {source_name}",
        "",
        headline,
        "",
        body,
        "",
        "──────────────",
        f"🤖 Анализ LLM [{model}]",
        analysis.get("analysis_ru") or analysis.get("lead_ru") or "—",
        f"\nУверенность: {conf:.2f} · значимость: {sig:.2f}{impact_line}",
        "",
        "⚠️ Автоматический дайджест. Не инвестрекомендация.",
    ]
    if source_url:
        lines.insert(3, f"🔗 {source_url[:200]}")
    return "\n".join(lines)[:4096]


def format_trade_alert_telegram(event: dict[str, Any]) -> str:
    sym = event.get("symbol") or "?"
    market = event.get("market", "?")
    env = event.get("env", "?")
    decision = event.get("decision", "?")
    notional = event.get("notional")
    currency = event.get("currency") or ("RUB" if market == "securities" else "USD")
    wf = event.get("workflow_name") or "—"
    amount = f"{notional:,.0f} {currency}" if notional else ""
    return (
        f"💼 Операция автомата · {market.upper()} ({env})\n\n"
        f"{decision.upper()} {sym} {amount}\n"
        f"Workflow: {wf}\n"
        f"Время: {(event.get('event_at') or '')[:19]}\n\n"
        f"⚙️ Отключить: Новости → 💼 Сделки"
    )


def _parse_symbols(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def process_news_alerts(*, limit: int = 10) -> dict[str, Any]:
    run_migrations()
    settings = get_alert_settings()
    news_cfg = settings["news_digest"]
    if not news_cfg.get("enabled", True):
        return {"status": "disabled", "sent": 0}

    watch = set(resolve_watch_symbols())
    min_conf = float(news_cfg.get("min_confidence", 0.55))
    min_sig = float(news_cfg.get("min_significance_score", 0.6))

    conn = get_connection()
    stats = {"scanned": 0, "analyzed": 0, "sent": 0, "skipped": 0, "errors": []}
    try:
        now = datetime.now(timezone.utc).isoformat()
        rows = conn.execute(
            """
            SELECT id, title, summary, source_name, source_tier, source_url,
                   verification_status, trust_score, matched_symbols, published_at
            FROM news_items
            WHERE (expires_at IS NULL OR expires_at > ?)
            ORDER BY published_at DESC
            LIMIT 80
            """,
            (now,),
        ).fetchall()

        for row in rows:
            if stats["sent"] >= limit:
                break
            item = dict(row)
            if _delivery_exists("news", item["id"]):
                continue
            if not passes_llm_gate(
                item.get("verification_status", "pending"),
                float(item.get("trust_score") or 0),
            ):
                stats["skipped"] += 1
                continue

            matched = _parse_symbols(item.get("matched_symbols"))
            hit = [s for s in matched if s in watch or s.replace("USDT", "") in watch]
            if not hit:
                stats["skipped"] += 1
                continue

            stats["scanned"] += 1
            symbol = hit[0]
            analysis = analyze_news_significance(
                symbol=symbol,
                title=item["title"],
                summary=item.get("summary") or "",
                source_name=item["source_name"],
                source_tier=item["source_tier"],
            )
            stats["analyzed"] += 1

            significant = bool(analysis.get("significant"))
            conf = float(analysis.get("confidence") or 0)
            sig_score = float(analysis.get("significance_score") or conf)

            if not significant or conf < min_conf or sig_score < min_sig:
                _mark_delivered("news", item["id"], payload={"skipped": True, "analysis": analysis})
                stats["skipped"] += 1
                continue

            text = format_news_digest_telegram(
                symbol=symbol,
                source_name=item["source_name"],
                title=item["title"],
                summary=item.get("summary") or "",
                analysis=analysis,
                source_url=item.get("source_url"),
            )
            result = send_telegram_message(text)
            if result.get("ok"):
                _mark_delivered("news", item["id"], payload={"analysis": analysis, "symbol": symbol})
                stats["sent"] += 1
            else:
                stats["errors"].append({"id": item["id"], "error": result.get("error")})
    finally:
        conn.close()

    stats["status"] = "ok"
    stats["watch_symbols"] = sorted(watch)
    return stats


def maybe_trade_alert(
    *,
    event_id: str,
    market: str,
    env: str,
    stage: str,
    symbol: str | None,
    decision: str | None,
    workflow_name: str | None,
    notional: float | None,
    currency: str,
    event_at: str,
) -> dict[str, Any] | None:
    settings = get_alert_settings()
    trade_cfg = settings["trade_alerts"]
    if not trade_cfg.get("enabled", True):
        return None
    if stage not in trade_cfg.get("stages", ["order"]):
        return None
    if decision not in trade_cfg.get("decisions", ["approve", "submitted"]):
        return None
    if _delivery_exists("trade", event_id):
        return None

    event = {
        "id": event_id,
        "market": market,
        "env": env,
        "stage": stage,
        "symbol": symbol,
        "decision": decision,
        "workflow_name": workflow_name,
        "notional": notional,
        "currency": currency,
        "event_at": event_at,
    }
    _mark_delivered("trade", event_id, payload={"event": event})

    if not trade_cfg.get("push_telegram", True):
        return {"status": "logged", "push": False}

    result = send_telegram_message(format_trade_alert_telegram(event))
    return {"status": "sent" if result.get("ok") else "error", "push": True, "telegram": result}


def list_trade_news(*, limit: int = 8) -> list[dict[str, Any]]:
    settings = get_alert_settings()
    if not settings["trade_alerts"].get("enabled", True):
        return []

    trade_cfg = settings["trade_alerts"]
    stages = trade_cfg.get("stages", ["order"])
    decisions = trade_cfg.get("decisions", ["approve", "submitted"])

    conn = get_connection()
    try:
        placeholders_s = ",".join("?" for _ in stages)
        placeholders_d = ",".join("?" for _ in decisions)
        rows = conn.execute(
            f"""
            SELECT id, event_at, market, env, symbol, decision,
                   workflow_name, notional, currency
            FROM trade_events
            WHERE stage IN ({placeholders_s})
              AND decision IN ({placeholders_d})
            ORDER BY event_at DESC
            LIMIT ?
            """,
            (*stages, *decisions, limit),
        ).fetchall()
        items = []
        for row in rows:
            r = dict(row)
            items.append({
                "type": "trade",
                "title": f"💼 {r.get('decision', '').upper()} {r.get('symbol')} "
                f"({r.get('market')}/{r.get('env')})",
                "source_name": "Автомат",
                "published_at": r.get("event_at"),
                "verification_status": "verified",
                "matched_symbols": json.dumps([r.get("symbol")] if r.get("symbol") else []),
                "summary": f"Workflow: {r.get('workflow_name')}, "
                f"сумма: {r.get('notional') or '—'} {r.get('currency') or ''}",
            })
        return items
    finally:
        conn.close()

