"""Signals Engine — LLM analysis, news signals, user context for trading automaton."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from config_loader import load_config
from db.connection import get_connection
from db.migrate import run_migrations
from news_alert_service import analyze_news_significance
from news_filter import evaluate_trade_relevance, filter_meta_json, get_filter_settings
from news_verification import passes_llm_gate
from runtime_settings import get_runtime_value, set_runtime_value


_SETTINGS_KEY = "signals_engine_runtime"
_HTML_TAG = re.compile(r"<[^>]+>")
_CRYPTO_HINTS = {"BTC", "ETH", "CRYPTO", "DOGE", "BNB", "SOL", "USDT"}
_MOEX_HINTS = {"SBER", "GAZP", "LKOH", "MOEX", "GMKN", "YNDX", "TMOS", "RUB"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _engine_yaml() -> dict[str, Any]:
    try:
        return load_config("signals_engine")
    except FileNotFoundError:
        return {}


def get_engine_settings() -> dict[str, Any]:
    yaml_cfg = _engine_yaml()
    runtime = get_runtime_value(_SETTINGS_KEY) or {}
    analysis = {**yaml_cfg.get("analysis", {}), **runtime.get("analysis", {})}
    context = {**yaml_cfg.get("context", {}), **runtime.get("context", {})}
    filter_cfg = get_filter_settings()
    return {"analysis": analysis, "context": context, "filter": filter_cfg}


def update_engine_settings(
    *,
    analysis_enabled: bool | None = None,
    analyze_on_ingest: bool | None = None,
    batch_size: int | None = None,
    min_confidence: float | None = None,
    min_significance_score: float | None = None,
    max_signals_per_symbol: int | None = None,
    include_user_context: bool | None = None,
    filter_enabled: bool | None = None,
    active_tags: list[str] | None = None,
    keywords_include: list[str] | None = None,
    keywords_exclude: list[str] | None = None,
    require_symbol_or_keyword: bool | None = None,
    filter_mode: str | None = None,
    min_keywords: int | None = None,
    min_relevance_score: float | None = None,
    require_keyword_in_title: bool | None = None,
    operator: str = "api",
) -> dict[str, Any]:
    current = get_engine_settings()
    analysis = dict(current["analysis"])
    context = dict(current["context"])
    filter_cfg = dict(current["filter"])
    if analysis_enabled is not None:
        analysis["enabled"] = analysis_enabled
    if analyze_on_ingest is not None:
        analysis["analyze_on_ingest"] = analyze_on_ingest
    if batch_size is not None:
        analysis["batch_size"] = batch_size
    if min_confidence is not None:
        analysis["min_confidence"] = min_confidence
    if min_significance_score is not None:
        analysis["min_significance_score"] = min_significance_score
    if max_signals_per_symbol is not None:
        context["max_signals_per_symbol"] = max_signals_per_symbol
    if include_user_context is not None:
        context["include_user_context"] = include_user_context
    if filter_enabled is not None:
        filter_cfg["enabled"] = filter_enabled
    if active_tags is not None:
        filter_cfg["active_tags"] = active_tags
    if keywords_include is not None:
        filter_cfg["keywords_include"] = keywords_include
    if keywords_exclude is not None:
        filter_cfg["keywords_exclude"] = keywords_exclude
    if require_symbol_or_keyword is not None:
        filter_cfg["require_symbol_or_keyword"] = require_symbol_or_keyword
    if filter_mode is not None:
        mode = filter_mode.lower()
        if mode in ("loose", "balanced", "strict"):
            filter_cfg["mode"] = mode
    if min_keywords is not None:
        filter_cfg["min_keywords"] = min_keywords
    if min_relevance_score is not None:
        filter_cfg["min_relevance_score"] = min_relevance_score
    if require_keyword_in_title is not None:
        filter_cfg["require_keyword_in_title"] = require_keyword_in_title
    set_runtime_value(
        _SETTINGS_KEY,
        {"analysis": analysis, "context": context, "filter": filter_cfg},
        updated_by=operator,
    )
    return get_engine_settings()


def extract_body_raw(entry: dict[str, Any], *, title: str = "", summary: str = "") -> str:
    """Best-effort full text from RSS entry."""
    parts: list[str] = []
    for block in entry.get("content") or []:
        val = block.get("value") if isinstance(block, dict) else None
        if val:
            parts.append(str(val))
    if summary:
        parts.append(summary)
    elif entry.get("summary"):
        parts.append(str(entry["summary"]))
    raw = "\n\n".join(parts).strip()
    if not raw:
        return (title or "").strip()[:8000]
    text = _HTML_TAG.sub(" ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:8000]


def effective_source_trust(*, tier_trust: float, user_override: float | None) -> float:
    if user_override is not None:
        return round(float(user_override), 3)
    return round(float(tier_trust), 3)


def _infer_market(symbols: list[str]) -> str:
    norm = {s.upper().replace("USDT", "") for s in symbols}
    if norm & _CRYPTO_HINTS:
        return "crypto"
    if norm & _MOEX_HINTS:
        return "securities"
    return "macro"


def _upsert_signal(
    conn: Any,
    *,
    news_item_id: str,
    symbols: list[str],
    analysis: dict[str, Any],
    model: str,
    expires_at: str | None,
) -> str:
    existing = conn.execute(
        "SELECT id FROM news_signals WHERE news_item_id = ? ORDER BY created_at DESC LIMIT 1",
        (news_item_id,),
    ).fetchone()
    significant = bool(analysis.get("significant"))
    settings = get_engine_settings()["analysis"]
    min_conf = float(settings.get("min_confidence", 0.45))
    min_sig = float(settings.get("min_significance_score", 0.5))
    conf = float(analysis.get("confidence") or 0)
    sig_score = float(analysis.get("significance_score") or conf)
    if not significant or conf < min_conf or sig_score < min_sig:
        status = "rejected"
    else:
        status = "pending"

    payload = (
        str(uuid.uuid4()),
        news_item_id,
        _infer_market(symbols),
        json.dumps(symbols, ensure_ascii=False),
        analysis.get("impact"),
        conf,
        sig_score,
        analysis.get("headline_ru") or analysis.get("lead_ru"),
        analysis.get("analysis_ru") or analysis.get("lead_ru"),
        json.dumps(analysis, ensure_ascii=False),
        model,
        status,
        _utc_now(),
        expires_at,
    )
    if existing:
        conn.execute(
            """
            UPDATE news_signals SET
                market = ?, symbols = ?, impact = ?, confidence = ?,
                significance_score = ?, headline_ru = ?, analysis_ru = ?,
                reasoning_trace = ?, model = ?, status = ?, expires_at = ?
            WHERE id = ?
            """,
            (
                payload[2], payload[3], payload[4], payload[5], payload[6],
                payload[7], payload[8], payload[9], payload[10], payload[11],
                payload[13], existing["id"],
            ),
        )
        return existing["id"]
    conn.execute(
        """
        INSERT INTO news_signals
            (id, news_item_id, market, symbols, impact, confidence, significance_score,
             headline_ru, analysis_ru, reasoning_trace, model, status, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payload,
    )
    return payload[0]


def analyze_news_item(item_id: str) -> dict[str, Any]:
    """Run LLM significance analysis for one news item; persist signal."""
    run_migrations()
    settings = get_engine_settings()["analysis"]
    if not settings.get("enabled", True):
        return {"status": "disabled", "item_id": item_id}

    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM news_items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            return {"status": "not_found", "item_id": item_id}
        item = dict(row)
        if not int(item.get("trade_relevant") or 0):
            return {"status": "skipped", "reason": "not_trade_relevant", "item_id": item_id}
        if not passes_llm_gate(
            item.get("verification_status", "pending"),
            float(item.get("trust_score") or 0),
        ):
            return {"status": "skipped", "reason": "llm_gate", "item_id": item_id}

        matched = _parse_json_list(item.get("matched_symbols"))
        symbol = matched[0] if matched else "MACRO"
        model = settings.get("ollama_model", "qwen3.5:9b")
        body = item.get("body_raw") or item.get("summary") or ""
        analysis = analyze_news_significance(
            symbol=symbol,
            title=item["title"],
            summary=body,
            source_name=item["source_name"],
            source_tier=item["source_tier"],
        )
        now = _utc_now()
        conn.execute(
            """
            UPDATE news_items SET
                llm_analysis_json = ?, llm_model = ?, llm_analyzed_at = ?
            WHERE id = ?
            """,
            (json.dumps(analysis, ensure_ascii=False), model, now, item_id),
        )
        signal_id = _upsert_signal(
            conn,
            news_item_id=item_id,
            symbols=matched or [symbol],
            analysis=analysis,
            model=model,
            expires_at=item.get("expires_at"),
        )
        conn.commit()
        return {
            "status": "ok",
            "item_id": item_id,
            "signal_id": signal_id,
            "significant": bool(analysis.get("significant")),
            "analysis": analysis,
        }
    finally:
        conn.close()


def analyze_pending_news(*, limit: int | None = None) -> dict[str, Any]:
    """Analyze news items that passed verification but have no LLM analysis yet."""
    run_migrations()
    settings = get_engine_settings()["analysis"]
    if not settings.get("enabled", True):
        return {"status": "disabled", "analyzed": 0}

    cap = limit if limit is not None else int(settings.get("batch_size", 12))
    conn = get_connection()
    stats = {"scanned": 0, "analyzed": 0, "skipped": 0, "errors": []}
    try:
        now = datetime.now(timezone.utc).isoformat()
        rows = conn.execute(
            """
            SELECT id, verification_status, trust_score, trade_relevant
            FROM news_items
            WHERE llm_analyzed_at IS NULL
              AND trade_relevant = 1
              AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY published_at DESC
            LIMIT ?
            """,
            (now, cap * 3),
        ).fetchall()
        for row in rows:
            if stats["analyzed"] >= cap:
                break
            stats["scanned"] += 1
            item = dict(row)
            if not passes_llm_gate(
                item.get("verification_status", "pending"),
                float(item.get("trust_score") or 0),
            ):
                stats["skipped"] += 1
                continue
            try:
                result = analyze_news_item(item["id"])
                if result.get("status") == "ok":
                    stats["analyzed"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as exc:
                stats["errors"].append({"id": item["id"], "error": str(exc)})
    finally:
        conn.close()
    stats["status"] = "ok"
    return stats


def get_user_context(news_item_id: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM news_user_context WHERE news_item_id = ?",
            (news_item_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def save_user_context(
    news_item_id: str,
    context_text: str,
    *,
    operator: str = "console",
) -> dict[str, Any]:
    run_migrations()
    conn = get_connection()
    try:
        signal = conn.execute(
            "SELECT status FROM news_signals WHERE news_item_id = ? ORDER BY created_at DESC LIMIT 1",
            (news_item_id,),
        ).fetchone()
        if signal and signal["status"] == "consumed":
            return {"status": "locked", "message": "signal_already_consumed"}

        existing = conn.execute(
            "SELECT id, locked_at FROM news_user_context WHERE news_item_id = ?",
            (news_item_id,),
        ).fetchone()
        now = _utc_now()
        if existing and existing["locked_at"]:
            return {"status": "locked", "message": "context_locked"}

        text = (context_text or "").strip()[:2000]
        if existing:
            conn.execute(
                """
                UPDATE news_user_context SET context_text = ?, updated_at = ?, operator = ?
                WHERE news_item_id = ?
                """,
                (text, now, operator, news_item_id),
            )
            ctx_id = existing["id"]
        else:
            ctx_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO news_user_context
                    (id, news_item_id, operator, context_text, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (ctx_id, news_item_id, operator, text, now, now),
            )
        conn.commit()
        return {"status": "ok", "id": ctx_id, "context_text": text}
    finally:
        conn.close()


def _lock_user_context(conn: Any, news_item_id: str) -> None:
    now = _utc_now()
    conn.execute(
        """
        UPDATE news_user_context SET locked_at = ?, updated_at = ?
        WHERE news_item_id = ? AND locked_at IS NULL
        """,
        (now, now, news_item_id),
    )


def consume_signals(signal_ids: list[str], *, event_id: str) -> int:
    if not signal_ids:
        return 0
    conn = get_connection()
    try:
        now = _utc_now()
        count = 0
        for sid in signal_ids:
            row = conn.execute(
                "SELECT news_item_id FROM news_signals WHERE id = ? AND status = 'pending'",
                (sid,),
            ).fetchone()
            if not row:
                continue
            conn.execute(
                """
                UPDATE news_signals SET
                    status = 'consumed', consumed_by_event_id = ?, consumed_at = ?
                WHERE id = ?
                """,
                (event_id, now, sid),
            )
            _lock_user_context(conn, row["news_item_id"])
            count += 1
        conn.commit()
        return count
    finally:
        conn.close()


def signals_context_for_symbols(
    symbols: list[str],
    *,
    limit: int | None = None,
) -> tuple[str, list[str]]:
    """Pending news signals formatted for trading LLM; returns (text, signal_ids)."""
    run_migrations()
    cfg = get_engine_settings()
    ctx_cfg = cfg["context"]
    analysis_cfg = cfg["analysis"]
    cap = limit if limit is not None else int(ctx_cfg.get("max_signals_per_symbol", 5))
    include_user = bool(ctx_cfg.get("include_user_context", True))
    include_rejected = bool(ctx_cfg.get("include_non_significant", False))

    sym_norm = {s.upper().replace("USDT", "") for s in symbols}
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        status_filter = ("pending", "rejected") if include_rejected else ("pending",)
        placeholders = ",".join("?" for _ in status_filter)
        rows = conn.execute(
            f"""
            SELECT ns.id, ns.news_item_id, ns.market, ns.symbols, ns.impact,
                   ns.confidence, ns.significance_score, ns.headline_ru, ns.analysis_ru,
                   ns.status, ni.source_name, ni.source_tier, ni.trust_score, ni.title
            FROM news_signals ns
            JOIN news_items ni ON ni.id = ns.news_item_id
            WHERE ns.status IN ({placeholders})
              AND ni.trade_relevant = 1
              AND (ns.expires_at IS NULL OR ns.expires_at > ?)
            ORDER BY ns.significance_score DESC, ns.created_at DESC
            LIMIT ?
            """,
            (*status_filter, now, cap * 15),
        ).fetchall()

        scored: list[tuple[float, dict[str, Any], str]] = []
        for row in rows:
            item = dict(row)
            matched = _parse_json_list(item.get("symbols"))
            hit = [
                m
                for m in matched
                if m.upper() in sym_norm or m.upper().replace("USDT", "") in sym_norm
            ]
            if not hit and item.get("market") == "macro":
                continue
            if not hit and item.get("market") != "macro":
                continue
            rel = float(item.get("significance_score") or item.get("confidence") or 0)
            scored.append((rel, item, item["id"]))

        scored.sort(key=lambda x: -x[0])
        lines: list[str] = []
        signal_ids: list[str] = []
        for _, item, sid in scored[:cap]:
            user_line = ""
            if include_user:
                ctx = get_user_context(item["news_item_id"])
                if ctx and ctx.get("context_text") and not ctx.get("locked_at"):
                    user_line = f" | operator_note: {ctx['context_text'][:400]}"
            tickers = ", ".join(_parse_json_list(item.get("symbols"))) or "—"
            headline = item.get("headline_ru") or item.get("title") or "—"
            analysis = item.get("analysis_ru") or "—"
            lines.append(
                f"- [{item.get('impact', '?')}|conf={float(item.get('confidence') or 0):.2f}|"
                f"{tickers}] {item['source_name']}: {headline}. {analysis}{user_line}"
            )
            if item.get("status") == "pending":
                signal_ids.append(sid)

        if not lines:
            return "none", []
        return "\n".join(lines), signal_ids
    finally:
        conn.close()


def list_sources_enriched() -> list[dict[str, Any]]:
    run_migrations()
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, name, source_tier, feed_type, feed_url, enabled,
                   fetch_interval_min, ttl_hours, last_fetched_at, last_error,
                   tags, user_trust_override
            FROM news_sources
            ORDER BY name
            """
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            tier_default = {"official": 1.0, "media": 0.75, "aggregator": 0.5, "social": 0.2}.get(
                item.get("source_tier", ""), 0.4
            )
            item["tags_list"] = _parse_json_list(item.get("tags"))
            item["effective_trust"] = effective_source_trust(
                tier_trust=tier_default,
                user_override=item.get("user_trust_override"),
            )
            out.append(item)
        return out
    finally:
        conn.close()


def update_news_source(
    source_id: str,
    *,
    enabled: bool | None = None,
    tags: list[str] | None = None,
    user_trust_override: float | None = None,
    clear_trust_override: bool = False,
) -> dict[str, Any]:
    run_migrations()
    conn = get_connection()
    try:
        row = conn.execute("SELECT id FROM news_sources WHERE id = ?", (source_id,)).fetchone()
        if not row:
            return {"status": "not_found"}
        updates: list[str] = []
        params: list[Any] = []
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(1 if enabled else 0)
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags, ensure_ascii=False))
        if clear_trust_override:
            updates.append("user_trust_override = NULL")
        elif user_trust_override is not None:
            updates.append("user_trust_override = ?")
            params.append(round(float(user_trust_override), 3))
        if not updates:
            return {"status": "noop"}
        params.append(source_id)
        conn.execute(
            f"UPDATE news_sources SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        conn.commit()
        return {"status": "ok", "id": source_id}
    finally:
        conn.close()


def enrich_feed_item(item: dict[str, Any]) -> dict[str, Any]:
    """Attach LLM analysis, signal, user context to a news feed row."""
    conn = get_connection()
    try:
        analysis_raw = item.get("llm_analysis_json")
        if analysis_raw:
            try:
                item["llm_analysis"] = json.loads(analysis_raw)
            except json.JSONDecodeError:
                item["llm_analysis"] = None
        else:
            item["llm_analysis"] = None

        signal = conn.execute(
            """
            SELECT id, status, impact, confidence, significance_score,
                   headline_ru, analysis_ru, model, consumed_at, market
            FROM news_signals WHERE news_item_id = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (item.get("id"),),
        ).fetchone()
        item["signal"] = dict(signal) if signal else None

        ctx = conn.execute(
            "SELECT context_text, locked_at, updated_at FROM news_user_context WHERE news_item_id = ?",
            (item.get("id"),),
        ).fetchone()
        if ctx:
            item["user_context"] = dict(ctx)
            item["context_editable"] = ctx["locked_at"] is None and (
                not signal or signal["status"] != "consumed"
            )
        else:
            item["user_context"] = None
            item["context_editable"] = not signal or signal["status"] != "consumed"

        meta_raw = item.get("filter_meta")
        if meta_raw:
            try:
                item["filter_meta_parsed"] = json.loads(meta_raw)
            except json.JSONDecodeError:
                item["filter_meta_parsed"] = None
        return item
    finally:
        conn.close()


def reapply_trade_filters(*, limit: int = 400) -> dict[str, Any]:
    """Re-evaluate trade_relevant for existing news (after filter settings change)."""
    run_migrations()
    conn = get_connection()
    stats = {"scanned": 0, "relevant": 0, "filtered_out": 0}
    try:
        now = datetime.now(timezone.utc).isoformat()
        rows = conn.execute(
            """
            SELECT ni.id, ni.title, ni.summary, ni.body_raw, ni.matched_symbols, ni.source_name,
                   ns.tags AS source_tags
            FROM news_items ni
            LEFT JOIN news_sources ns ON ns.name = ni.source_name
            WHERE ni.expires_at IS NULL OR ni.expires_at > ?
            ORDER BY ni.published_at DESC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()
        for row in rows:
            stats["scanned"] += 1
            item = dict(row)
            matched = _parse_json_list(item.get("matched_symbols"))
            source_tags = _parse_json_list(item.get("source_tags"))
            body = item.get("body_raw") or item.get("summary") or ""
            result = evaluate_trade_relevance(
                title=item.get("title", ""),
                body=body,
                matched_symbols=matched,
                source_tags=source_tags,
            )
            relevant = 1 if result["relevant"] else 0
            conn.execute(
                """
                UPDATE news_items SET trade_relevant = ?, filter_meta = ?
                WHERE id = ?
                """,
                (relevant, filter_meta_json(result), item["id"]),
            )
            if relevant:
                stats["relevant"] += 1
            else:
                stats["filtered_out"] += 1
        conn.commit()
    finally:
        conn.close()
    stats["status"] = "ok"
    return stats
