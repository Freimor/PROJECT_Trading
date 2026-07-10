"""News ingest, verification, and symbol-aware LLM context."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import feedparser

from db.connection import get_connection
from db.migrate import run_migrations
from news_verification import (
    compute_relevance,
    entity_market_map,
    extract_matched_symbols,
    load_sources_from_config,
    passes_llm_gate,
    verify_article,
)


def dedup_hash(title: str, url: str) -> str:
    return hashlib.sha256(f"{title}|{url}".encode()).hexdigest()


def _parse_json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def seed_sources() -> int:
    run_migrations()
    sources = load_sources_from_config()
    conn = get_connection()
    inserted = 0
    try:
        for src in sources:
            allowed = src.get("allowed_domains", [])
            tags = src.get("tags") or _infer_tags_from_symbols(src.get("default_symbols", []))
            cur = conn.execute("SELECT id FROM news_sources WHERE id = ?", (src["id"],))
            if cur.fetchone():
                conn.execute(
                    """
                    UPDATE news_sources SET
                        name = ?, source_tier = ?, feed_type = ?, feed_url = ?,
                        ttl_hours = ?, symbols_filter = ?, allowed_domains = ?,
                        fetch_interval_min = COALESCE(?, fetch_interval_min),
                        tags = COALESCE(?, tags)
                    WHERE id = ?
                    """,
                    (
                        src["name"], src["source_tier"], src["feed_type"], src["feed_url"],
                        src.get("ttl_hours", 48), src["symbols_filter"],
                        json.dumps(allowed, ensure_ascii=False),
                        src.get("fetch_interval_min"),
                        json.dumps(tags, ensure_ascii=False) if tags else None,
                        src["id"],
                    ),
                )
                continue
            conn.execute(
                """
                INSERT INTO news_sources
                    (id, name, source_tier, feed_type, feed_url, enabled,
                     fetch_interval_min, ttl_hours, symbols_filter, allowed_domains, tags)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
                """,
                (
                    src["id"], src["name"], src["source_tier"], src["feed_type"],
                    src["feed_url"], src.get("fetch_interval_min", 15),
                    src.get("ttl_hours", 48), src["symbols_filter"],
                    json.dumps(allowed, ensure_ascii=False),
                    json.dumps(tags, ensure_ascii=False),
                ),
            )
            inserted += 1
        conn.commit()
    finally:
        conn.close()
    return inserted


def _infer_tags_from_symbols(symbols: list[str]) -> list[str]:
    tags: set[str] = set()
    crypto = {"BTC", "ETH", "CRYPTO", "DOGE", "BNB", "SOL"}
    moex = {"SBER", "GAZP", "LKOH", "MOEX", "GMKN", "YNDX", "TMOS"}
    norm = {s.upper() for s in symbols}
    if norm & crypto:
        tags.add("crypto")
    if norm & moex or "MOEX" in norm:
        tags.add("moex")
    if "RUB" in norm:
        tags.add("macro")
    return sorted(tags)


def ingest_all() -> dict[str, Any]:
    seed_sources()
    conn = get_connection()
    stats: dict[str, Any] = {
        "fetched": 0,
        "inserted": 0,
        "skipped_dup": 0,
        "rejected_unverified": 0,
        "filtered_out": 0,
        "verified": 0,
        "errors": [],
    }
    try:
        rows = conn.execute("SELECT * FROM news_sources WHERE enabled = 1").fetchall()
        for row in rows:
            try:
                allowed = _parse_json_list(row["allowed_domains"])
                default_symbols = _parse_json_list(row["symbols_filter"])
                source_tags = _parse_json_list(row["tags"])
                feed = feedparser.parse(row["feed_url"])
                stats["fetched"] += len(feed.entries)
                for entry in feed.entries[:40]:
                    title = entry.get("title", "").strip()
                    link = entry.get("link", "")
                    if not title:
                        continue
                    dhash = dedup_hash(title, link)
                    if conn.execute(
                        "SELECT id FROM news_items WHERE dedup_hash = ?", (dhash,)
                    ).fetchone():
                        stats["skipped_dup"] += 1
                        continue

                    summary = (entry.get("summary") or "")[:800]
                    from signals_engine_service import extract_body_raw

                    body_raw = extract_body_raw(entry, title=title, summary=summary)
                    verification = verify_article(
                        title=title,
                        link=link,
                        feed_url=row["feed_url"],
                        source_tier=row["source_tier"],
                        allowed_domains=allowed,
                    )
                    matched = extract_matched_symbols(title, summary, default_symbols)
                    from news_filter import evaluate_trade_relevance, filter_meta_json

                    trade_eval = evaluate_trade_relevance(
                        title=title,
                        body=body_raw,
                        matched_symbols=matched,
                        source_tags=source_tags,
                    )
                    trade_relevant = 1 if trade_eval["relevant"] else 0
                    if not trade_relevant:
                        stats["filtered_out"] += 1
                    relevance = compute_relevance(
                        matched_symbols=matched,
                        target_symbols=None,
                        trust_score=verification["trust_score"],
                        title=title,
                    )

                    published = entry.get("published_parsed")
                    published_at = None
                    if published:
                        published_at = datetime(*published[:6], tzinfo=timezone.utc).isoformat()
                    ttl = row["ttl_hours"] or 48
                    expires = (datetime.now(timezone.utc) + timedelta(hours=ttl)).isoformat()

                    if verification["verification_status"] == "rejected":
                        stats["rejected_unverified"] += 1
                    elif verification["verification_status"] == "verified":
                        stats["verified"] += 1

                    conn.execute(
                        """
                        INSERT INTO news_items
                            (id, published_at, source_name, source_tier, source_url,
                             title, summary, body_raw, dedup_hash, relevance_score, symbols,
                             matched_symbols, verification_status, trust_score,
                             reject_reasons, expires_at, trade_relevant, filter_meta)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()), published_at, row["name"], row["source_tier"],
                            link, title, summary, body_raw, dhash, relevance,
                            row["symbols_filter"],
                            json.dumps(matched, ensure_ascii=False),
                            verification["verification_status"],
                            verification["trust_score"],
                            json.dumps(verification.get("reject_reasons", []), ensure_ascii=False),
                            expires, trade_relevant, filter_meta_json(trade_eval),
                        ),
                    )
                    stats["inserted"] += 1
                conn.execute(
                    "UPDATE news_sources SET last_fetched_at = datetime('now'), last_error = NULL WHERE id = ?",
                    (row["id"],),
                )
            except Exception as exc:
                stats["errors"].append({"source": row["id"], "error": str(exc)})
                conn.execute(
                    "UPDATE news_sources SET last_error = ? WHERE id = ?",
                    (str(exc)[:500], row["id"]),
                )
        conn.commit()
    finally:
        conn.close()

    from signals_engine_service import analyze_pending_news, get_engine_settings

    if get_engine_settings()["analysis"].get("analyze_on_ingest", True):
        stats["analysis"] = analyze_pending_news()
    return stats


def news_context_for_symbols(symbols: list[str], limit: int = 5) -> str:
    """Verified, symbol-relevant signals for LLM prompt (Signals Engine)."""
    text, _ = news_context_with_signals(symbols, limit=limit)
    return text


def news_context_with_signals(symbols: list[str], limit: int = 5) -> tuple[str, list[str]]:
    from signals_engine_service import signals_context_for_symbols

    text, signal_ids = signals_context_for_symbols(symbols, limit=limit)
    if text == "none":
        rows = _fetch_news_for_symbols(symbols, limit=limit, llm_only=True)
        if not rows:
            return "none", []
        return _format_news_lines(rows), []
    return text, signal_ids


def _format_news_lines(rows: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for row in rows:
        tickers = ", ".join(_parse_json_list(row.get("matched_symbols"))) or "—"
        trust = row.get("trust_score", 0)
        tier = row.get("source_tier", "?")
        lines.append(
            f"- [{tier}|trust={trust:.2f}|{tickers}] {row['source_name']}: {row['title']}"
        )
    return "\n".join(lines) if lines else "none"


def news_context_as_of(
    symbols: list[str],
    *,
    as_of: str,
    limit: int = 5,
) -> str:
    """Point-in-time news: published_at <= as_of (for historical benchmark)."""
    conn = get_connection()
    try:
        sym_norm = {s.upper().replace("USDT", "") for s in symbols}
        rows = conn.execute(
            """
            SELECT title, source_name, source_tier, published_at, source_url,
                   verification_status, trust_score, matched_symbols, relevance_score
            FROM news_items
            WHERE (published_at IS NULL OR published_at <= ?)
              AND (benchmark_retained = 1 OR expires_at IS NULL OR expires_at > ?)
              AND trade_relevant = 1
            ORDER BY published_at DESC
            LIMIT ?
            """,
            (as_of, as_of, limit * 30),
        ).fetchall()

        scored: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            item = dict(row)
            if not passes_llm_gate(
                item.get("verification_status", "pending"),
                float(item.get("trust_score") or 0),
            ):
                continue
            matched = _parse_json_list(item.get("matched_symbols"))
            hit = [m for m in matched if m in sym_norm or m.replace("USDT", "") in sym_norm]
            rel = compute_relevance(
                matched_symbols=matched,
                target_symbols=list(sym_norm),
                trust_score=float(item.get("trust_score") or 0),
                title=item.get("title", ""),
            )
            if not hit and rel < 0.35:
                continue
            item["relevance_score"] = rel
            scored.append((rel, item))

        scored.sort(key=lambda x: -x[0])
        return _format_news_lines([item for _, item in scored[:limit]])
    finally:
        conn.close()


def _symbol_hits(matched: list[str], sym_norm: set[str]) -> list[str]:
    return [
        m
        for m in matched
        if m.upper().replace("USDT", "") in sym_norm or m.upper() in sym_norm
    ]


def _matches_workspace_market(matched: list[str], market: str | None, hit: list[str]) -> bool:
    """Keep crypto desk news free of MOEX-only items (and vice versa)."""
    if not market or not matched:
        return True
    markets = {entity_market_map().get(m.upper().replace("USDT", ""), "macro") for m in matched}
    if market == "crypto":
        if hit:
            return True
        return "crypto" in markets
    if market == "securities":
        if hit:
            return True
        return bool(markets & {"securities", "macro"})
    return True


def _fetch_news_for_symbols(
    symbols: list[str],
    *,
    limit: int = 8,
    llm_only: bool = False,
    require_symbol_hit: bool = False,
    market: str | None = None,
) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        rows = conn.execute(
            """
            SELECT title, source_name, source_tier, published_at, source_url,
                   verification_status, trust_score, matched_symbols, relevance_score
            FROM news_items
            WHERE (expires_at IS NULL OR expires_at > ?)
              AND trade_relevant = 1
            ORDER BY published_at DESC
            LIMIT ?
            """,
            (now, limit * 20),
        ).fetchall()

        sym_norm = {s.upper().replace("USDT", "") for s in symbols}
        scored: list[tuple[float, dict[str, Any]]] = []

        for row in rows:
            item = dict(row)
            if llm_only and not passes_llm_gate(
                item.get("verification_status", "pending"),
                float(item.get("trust_score") or 0),
            ):
                continue
            matched = _parse_json_list(item.get("matched_symbols"))
            hit = _symbol_hits(matched, sym_norm)
            rel = compute_relevance(
                matched_symbols=matched,
                target_symbols=list(sym_norm),
                trust_score=float(item.get("trust_score") or 0),
                title=item.get("title", ""),
            )
            if require_symbol_hit and not hit:
                continue
            if not _matches_workspace_market(matched, market, hit):
                continue
            if llm_only and not hit and rel < 0.4:
                continue
            item["relevance_score"] = rel
            scored.append((rel, item))

        scored.sort(key=lambda x: (-x[0], x[1].get("published_at") or ""), reverse=False)
        scored.sort(key=lambda x: -x[0])
        return [item for _, item in scored[:limit]]
    finally:
        conn.close()


def list_news_for_symbol(
    symbol: str,
    limit: int = 8,
    *,
    market: str | None = None,
) -> list[dict[str, Any]]:
    sym = symbol.upper().replace("USDT", "")
    return _fetch_news_for_symbols(
        [sym],
        limit=limit,
        llm_only=False,
        require_symbol_hit=True,
        market=market,
    )


def news_verification_stats() -> dict[str, Any]:
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        rows = conn.execute(
            """
            SELECT verification_status, COUNT(*) AS cnt
            FROM news_items
            WHERE expires_at IS NULL OR expires_at > ?
            GROUP BY verification_status
            """,
            (now,),
        ).fetchall()
        by_status = {r["verification_status"]: r["cnt"] for r in rows}
        sources = conn.execute(
            "SELECT id, name, source_tier, enabled, last_fetched_at, last_error FROM news_sources ORDER BY name"
        ).fetchall()
        return {
            "by_status": by_status,
            "sources_count": len(sources),
            "sources": [dict(s) for s in sources],
        }
    finally:
        conn.close()


def purge_expired() -> int:
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            "DELETE FROM news_items WHERE expires_at IS NOT NULL AND expires_at < ? AND benchmark_retained = 0",
            (now,),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()
