"""Automated research paper discovery — arXiv, CrossRef, OpenAlex, Semantic Scholar, RSS."""

from __future__ import annotations

import json
import os
import re
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import feedparser
import httpx

from config_loader import load_config
from db.connection import get_connection

_ARXIV_API = "http://export.arxiv.org/api/query"
_CROSSREF_API = "https://api.crossref.org/works"
_OPENALEX_API = "https://api.openalex.org/works"
_SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"


def _cfg() -> dict[str, Any]:
    return load_config("papers_monitor")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _papers_inbox() -> Path:
    cfg = _cfg()
    rel = cfg.get("obsidian_inbox_path", "papers/inbox")
    custom = cfg.get("inbox_absolute_path")
    if custom:
        return Path(custom)
    return _repo_root() / rel


def _slugify(title: str) -> str:
    s = re.sub(r"[^\w\s-]", "", title.lower(), flags=re.UNICODE)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return (s[:60] or "paper").rstrip("-")


def _parse_arxiv_atom(xml_text: str) -> list[dict[str, Any]]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml_text)
    papers = []
    for entry in root.findall("atom:entry", ns):
        title = (entry.find("atom:title", ns).text or "").strip().replace("\n", " ")
        summary = (entry.find("atom:summary", ns).text or "").strip()[:800]
        published_el = entry.find("atom:published", ns)
        pub_date = published_el.text[:10] if published_el is not None and published_el.text else ""
        link = ""
        for link_el in entry.findall("atom:link", ns):
            if link_el.get("title") == "pdf":
                link = link_el.get("href", "")
                break
        if not link:
            id_el = entry.find("atom:id", ns)
            link = id_el.text if id_el is not None else ""
        arxiv_id = ""
        m = re.search(r"arxiv\.org/abs/([\d.]+v?\d*)", link or "")
        if m:
            arxiv_id = m.group(1)
        papers.append({
            "source": "arxiv",
            "title": title,
            "summary": summary,
            "published": pub_date,
            "url": link or f"https://arxiv.org/abs/{arxiv_id}",
            "arxiv_id": arxiv_id,
        })
    return papers


def fetch_arxiv_candidates(max_results: int = 20) -> list[dict[str, Any]]:
    cfg = _cfg()
    query = cfg.get("arxiv_query", "all:trading OR all:portfolio")
    params = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    }
    with httpx.Client(timeout=45) as client:
        resp = client.get(_ARXIV_API, params=params)
        resp.raise_for_status()
        return _parse_arxiv_atom(resp.text)


def fetch_crossref_candidates(rows: int = 10) -> list[dict[str, Any]]:
    cfg = _cfg()
    query = cfg.get("crossref_query", "algorithmic trading")
    with httpx.Client(timeout=45) as client:
        resp = client.get(
            _CROSSREF_API,
            params={"query": query, "rows": rows, "sort": "published", "order": "desc"},
            headers={"User-Agent": "PROJECT_Trading/1.0 (research-monitor; mailto:research@local)"},
        )
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])

    papers = []
    for item in items:
        title = (item.get("title") or [""])[0]
        doi = item.get("DOI", "")
        pub_parts = item.get("published", {}).get("date-parts", [[]])[0]
        pub = "-".join(str(p) for p in pub_parts)[:10] if pub_parts else ""
        papers.append({
            "source": "crossref",
            "title": title,
            "summary": (item.get("abstract") or "")[:800],
            "published": pub,
            "url": f"https://doi.org/{doi}" if doi else "",
            "doi": doi,
            "citation_count": item.get("is-referenced-by-count"),
        })
    return papers


def fetch_openalex_candidates(per_page: int = 15) -> list[dict[str, Any]]:
    cfg = _cfg()
    query = cfg.get("openalex_query", "algorithmic trading cryptocurrency")
    min_year = int(cfg.get("min_year", 2021))
    params = {
        "search": query,
        "filter": f"from_publication_date:{min_year}-01-01",
        "per_page": per_page,
        "sort": "publication_date:desc",
    }
    with httpx.Client(timeout=45) as client:
        resp = client.get(
            _OPENALEX_API,
            params=params,
            headers={"User-Agent": "PROJECT_Trading/1.0 (research-monitor)"},
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])

    papers = []
    for item in results:
        title = (item.get("display_name") or "").strip()
        pub = (item.get("publication_date") or "")[:10]
        url = item.get("doi") or item.get("id") or ""
        if url and not url.startswith("http"):
            url = f"https://doi.org/{url.replace('https://doi.org/', '')}"
        abstract = (item.get("abstract_inverted_index") or {})
        summary = ""
        if isinstance(abstract, dict) and abstract:
            words: list[tuple[int, str]] = []
            for word, positions in abstract.items():
                for pos in positions:
                    words.append((pos, word))
            summary = " ".join(w for _, w in sorted(words))[:800]
        papers.append({
            "source": "openalex",
            "title": title,
            "summary": summary,
            "published": pub,
            "url": url or item.get("id", ""),
            "openalex_id": item.get("id"),
            "doi": (item.get("doi") or "").replace("https://doi.org/", ""),
            "citation_count": item.get("cited_by_count"),
        })
    return papers


def fetch_semantic_scholar_candidates(limit: int = 15) -> list[dict[str, Any]]:
    cfg = _cfg()
    if not cfg.get("semantic_scholar_enabled", True):
        return []
    query = cfg.get("semantic_scholar_query", "algorithmic trading machine learning")
    headers: dict[str, str] = {"User-Agent": "PROJECT_Trading/1.0"}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    if api_key:
        headers["x-api-key"] = api_key

    with httpx.Client(timeout=45) as client:
        resp = client.get(
            _SEMANTIC_SCHOLAR_API,
            params={
                "query": query,
                "limit": limit,
                "fields": "title,abstract,url,year,citationCount,externalIds,publicationDate",
            },
            headers=headers,
        )
        if resp.status_code == 429:
            return []
        resp.raise_for_status()
        data = resp.json().get("data", [])

    papers = []
    for item in data:
        ext = item.get("externalIds") or {}
        doi = ext.get("DOI", "")
        url = item.get("url") or (f"https://doi.org/{doi}" if doi else "")
        pub = item.get("publicationDate") or str(item.get("year") or "")
        papers.append({
            "source": "semantic_scholar",
            "title": item.get("title", ""),
            "summary": (item.get("abstract") or "")[:800],
            "published": pub[:10],
            "url": url,
            "doi": doi,
            "semantic_scholar_id": item.get("paperId"),
            "citation_count": item.get("citationCount"),
        })
    return papers


def fetch_rss_candidates() -> list[dict[str, Any]]:
    cfg = _cfg()
    feeds = cfg.get("rss_feeds", [])
    papers: list[dict[str, Any]] = []
    for feed_cfg in feeds:
        url = feed_cfg.get("url")
        if not url:
            continue
        try:
            parsed = feedparser.parse(url)
        except Exception:
            continue
        source_id = feed_cfg.get("id", "rss")
        for entry in parsed.entries[: int(feed_cfg.get("max_items", 10))]:
            title = (entry.get("title") or "").strip()
            link = entry.get("link") or ""
            summary = (entry.get("summary") or entry.get("description") or "")[:800]
            pub = ""
            if entry.get("published_parsed"):
                tp = entry.published_parsed
                pub = f"{tp.tm_year:04d}-{tp.tm_mon:02d}-{tp.tm_mday:02d}"
            papers.append({
                "source": source_id,
                "title": title,
                "summary": summary,
                "published": pub,
                "url": link,
            })
    return papers


def _relevance_score(paper: dict[str, Any], keywords: list[str]) -> int:
    if not keywords:
        return 1
    text = f"{paper.get('title', '')} {paper.get('summary', '')}".lower()
    return sum(1 for k in keywords if k.lower() in text)


def _already_known(url: str) -> bool:
    if not url:
        return True
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM papers_candidates WHERE url = ? LIMIT 1", (url,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def _insert_candidate(paper: dict[str, Any], relevance: int) -> dict[str, Any]:
    pid = str(uuid.uuid4())
    metadata = {
        k: paper[k]
        for k in ("doi", "arxiv_id", "openalex_id", "semantic_scholar_id")
        if paper.get(k)
    }
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO papers_candidates
            (id, discovered_at, source, title, summary, published, url,
             relevance_score, citation_count, metadata_json, status)
            VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                pid,
                paper.get("source", "unknown"),
                paper.get("title", ""),
                paper.get("summary"),
                paper.get("published"),
                paper.get("url"),
                relevance,
                paper.get("citation_count"),
                json.dumps(metadata, ensure_ascii=False) if metadata else None,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return {**paper, "id": pid, "relevance_score": relevance}


def ingest_paper_candidates(*, create_drafts: bool = False) -> dict[str, Any]:
    """Fetch from all sources; store new candidates for human review."""
    cfg = _cfg()
    min_year = int(cfg.get("min_year", 2021))
    keywords = [k.lower() for k in cfg.get("relevance_keywords", [])]

    all_papers: list[dict[str, Any]] = []
    all_papers.extend(fetch_arxiv_candidates(int(cfg.get("arxiv_max", 15))))
    if cfg.get("crossref_enabled", True):
        all_papers.extend(fetch_crossref_candidates(int(cfg.get("crossref_max", 10))))
    if cfg.get("openalex_enabled", True):
        all_papers.extend(fetch_openalex_candidates(int(cfg.get("openalex_max", 15))))
    if cfg.get("semantic_scholar_enabled", True):
        all_papers.extend(fetch_semantic_scholar_candidates(int(cfg.get("semantic_scholar_max", 15))))
    if cfg.get("rss_enabled", True):
        all_papers.extend(fetch_rss_candidates())

    by_source: dict[str, int] = {}
    new_items: list[dict[str, Any]] = []

    for p in all_papers:
        url = (p.get("url") or "").strip()
        if not url or _already_known(url):
            continue
        pub_raw = p.get("published") or "2020"
        try:
            pub_year = int(str(pub_raw)[:4])
        except ValueError:
            pub_year = 2020
        if pub_year < min_year:
            continue
        relevance = _relevance_score(p, keywords)
        if relevance == 0:
            continue
        item = _insert_candidate(p, relevance)
        new_items.append(item)
        src = p.get("source", "unknown")
        by_source[src] = by_source.get(src, 0) + 1
        if create_drafts and cfg.get("auto_draft_on_ingest", False):
            create_obsidian_draft(item["id"])

    return {
        "status": "ok",
        "new_count": len(new_items),
        "by_source": by_source,
        "new_items": new_items[:30],
        "sources_active": ["arxiv", "crossref", "openalex", "semantic_scholar", "rss"],
        "note": "Human review required before moving to papers/",
    }


def list_candidates(
    *,
    status: str | None = "pending",
    limit: int = 50,
) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        if status and status != "all":
            rows = conn.execute(
                """
                SELECT * FROM papers_candidates
                WHERE status = ? ORDER BY discovered_at DESC LIMIT ?
                """,
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM papers_candidates
                ORDER BY discovered_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        out = []
        for r in rows:
            item = dict(r)
            if item.get("metadata_json"):
                try:
                    item["metadata"] = json.loads(item["metadata_json"])
                except json.JSONDecodeError:
                    item["metadata"] = {}
            out.append(item)
        return out
    finally:
        conn.close()


def list_pending_candidates(limit: int = 30) -> list[dict[str, Any]]:
    return list_candidates(status="pending", limit=limit)


def create_obsidian_draft(candidate_id: str) -> dict[str, Any]:
    """Create markdown draft in papers/inbox/ for Obsidian review."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM papers_candidates WHERE id = ?", (candidate_id,)
        ).fetchone()
        if not row:
            return {"status": "error", "message": "not_found"}
        cand = dict(row)
    finally:
        conn.close()

    inbox = _papers_inbox()
    inbox.mkdir(parents=True, exist_ok=True)
    slug = _slugify(cand.get("title", "paper"))
    path = inbox / f"{slug}.md"
    if path.exists():
        path = inbox / f"{slug}-{candidate_id[:8]}.md"

    metadata = {}
    if cand.get("metadata_json"):
        try:
            metadata = json.loads(cand["metadata_json"])
        except json.JSONDecodeError:
            pass

    body = f"""---
id: {candidate_id}
title: "{cand.get('title', '').replace('"', "'")}"
source: {cand.get('source')}
url: {cand.get('url')}
published: {cand.get('published') or ''}
citation_count: {cand.get('citation_count') or 0}
relevance_score: {cand.get('relevance_score') or 0}
status: draft
discovered_at: {cand.get('discovered_at')}
tier: pending_review
---

# {cand.get('title', 'Untitled')}

## Summary

{cand.get('summary') or '_No abstract available._'}

## Source link

[{cand.get('url')}]({cand.get('url')})

## Metadata

```json
{json.dumps(metadata, ensure_ascii=False, indent=2)}
```

## Review checklist

- [ ] URL opens and matches title
- [ ] Publication year ≥ 2021
- [ ] Credibility tier assigned (1–5)
- [ ] Added to `papers/papers_analysis.yaml`
- [ ] Wiki article updated if applicable

## Automation note

Created by `papers_monitor` → approve in web-console Research page.
"""
    path.write_text(body, encoding="utf-8")

    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE papers_candidates
            SET draft_path = ?, status = 'approved', reviewed_at = datetime('now')
            WHERE id = ?
            """,
            (str(path), candidate_id),
        )
        conn.commit()
    finally:
        conn.close()

    return {"status": "ok", "draft_path": str(path), "candidate_id": candidate_id}


def update_candidate_status(candidate_id: str, status: str) -> dict[str, Any]:
    allowed = {"pending", "approved", "rejected", "ingested"}
    if status not in allowed:
        return {"status": "error", "message": "invalid_status"}
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE papers_candidates
            SET status = ?, reviewed_at = datetime('now') WHERE id = ?
            """,
            (status, candidate_id),
        )
        conn.commit()
    finally:
        conn.close()
    return {"status": "ok", "candidate_id": candidate_id, "new_status": status}


def research_dashboard() -> dict[str, Any]:
    """Combined stats for web-console Research page."""
    conn = get_connection()
    try:
        pending = conn.execute(
            "SELECT COUNT(*) as c FROM papers_candidates WHERE status = 'pending'"
        ).fetchone()["c"]
        approved = conn.execute(
            "SELECT COUNT(*) as c FROM papers_candidates WHERE status = 'approved'"
        ).fetchone()["c"]
        by_source_rows = conn.execute(
            """
            SELECT source, COUNT(*) as c FROM papers_candidates
            GROUP BY source ORDER BY c DESC
            """
        ).fetchall()
    finally:
        conn.close()

    from neuratrade_harness import get_leaderboard, recommend_model

    return {
        "papers": {
            "pending_count": pending,
            "approved_count": approved,
            "by_source": {r["source"]: r["c"] for r in by_source_rows},
            "inbox_path": str(_papers_inbox()),
        },
        "neuratrade": {
            "leaderboard": get_leaderboard(),
            "recommended": recommend_model(),
        },
    }
