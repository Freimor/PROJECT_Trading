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
            cur = conn.execute("SELECT id FROM news_sources WHERE id = ?", (src["id"],))
            if cur.fetchone():
                conn.execute(
                    """
                    UPDATE news_sources SET
                        name = ?, source_tier = ?, feed_type = ?, feed_url = ?,
                        ttl_hours = ?, symbols_filter = ?, allowed_domains = ?,
                        fetch_interval_min = COALESCE(?, fetch_interval_min)
                    WHERE id = ?
                    """,
                    (
                        src["name"], src["source_tier"], src["feed_type"], src["feed_url"],
                        src.get("ttl_hours", 48), src["symbols_filter"],
                        json.dumps(allowed, ensure_ascii=False),
                        src.get("fetch_interval_min"), src["id"],
                    ),
                )
                continue
            conn.execute(
                """
                INSERT INTO news_sources
                    (id, name, source_tier, feed_type, feed_url, enabled,
                     fetch_interval_min, ttl_hours, symbols_filter, allowed_domains)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                """,
                (
                    src["id"], src["name"], src["source_tier"], src["feed_type"],
                    src["feed_url"], src.get("fetch_interval_min", 15),
                    src.get("ttl_hours", 48), src["symbols_filter"],
                    json.dumps(allowed, ensure_ascii=False),
                ),
            )
            inserted += 1
        conn.commit()
    finally:
        conn.close()
    return inserted


def ingest_all() -> dict[str, Any]:
    seed_sources()
    conn = get_connection()
    stats: dict[str, Any] = {
        "fetched": 0,
        "inserted": 0,
        "skipped_dup": 0,
        "rejected_unverified": 0,
        "verified": 0,
        "errors": [],
    }
    try:
        rows = conn.execute("SELECT * FROM news_sources WHERE enabled = 1").fetchall()
        for row in rows:
            try:
                allowed = _parse_json_list(row["allowed_domains"])
                default_symbols = _parse_json_list(row["symbols_filter"])
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
                    verification = verify_article(
                        title=title,
                        link=link,
                        feed_url=row["feed_url"],
                        source_tier=row["source_tier"],
                        allowed_domains=allowed,
                    )
                    matched = extract_matched_symbols(title, summary, default_symbols)
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
                             title, summary, dedup_hash, relevance_score, symbols,
                             matched_symbols, verification_status, trust_score,
                             reject_reasons, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()), published_at, row["name"], row["source_tier"],
                            link, title, summary, dhash, relevance,
                            row["symbols_filter"],
                            json.dumps(matched, ensure_ascii=False),
                            verification["verification_status"],
                            verification["trust_score"],
                            json.dumps(verification.get("reject_reasons", []), ensure_ascii=False),
                            expires,
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
    return stats


def news_context_for_symbols(symbols: list[str], limit: int = 5) -> str:
    """Verified, symbol-relevant headlines for LLM prompt."""
    rows = _fetch_news_for_symbols(symbols, limit=limit, llm_only=True)
    if not rows:
        return "none"
    lines: list[str] = []
    for row in rows:
        tickers = ", ".join(_parse_json_list(row.get("matched_symbols"))) or "—"
        trust = row.get("trust_score", 0)
        tier = row.get("source_tier", "?")
        lines.append(
            f"- [{tier}|trust={trust:.2f}|{tickers}] {row['source_name']}: {row['title']}"
        )
    return "\n".join(lines)


def _fetch_news_for_symbols(
    symbols: list[str],
    *,
    limit: int = 8,
    llm_only: bool = False,
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
            hit = [m for m in matched if m in sym_norm or m.replace("USDT", "") in sym_norm]
            rel = compute_relevance(
                matched_symbols=matched,
                target_symbols=list(sym_norm),
                trust_score=float(item.get("trust_score") or 0),
                title=item.get("title", ""),
            )
            if llm_only and not hit and rel < 0.4:
                continue
            item["relevance_score"] = rel
            scored.append((rel, item))

        scored.sort(key=lambda x: (-x[0], x[1].get("published_at") or ""), reverse=False)
        scored.sort(key=lambda x: -x[0])
        return [item for _, item in scored[:limit]]
    finally:
        conn.close()


def list_news_for_symbol(symbol: str, limit: int = 8) -> list[dict[str, Any]]:
    sym = symbol.upper().replace("USDT", "")
    return _fetch_news_for_symbols([sym], limit=limit, llm_only=False)


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
            "DELETE FROM news_items WHERE expires_at IS NOT NULL AND expires_at < ?",
            (now,),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()
