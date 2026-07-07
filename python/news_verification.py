"""News authenticity verification and entity matching."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse

from config_loader import load_config


def _news_config() -> dict[str, Any]:
    try:
        return load_config("news_sources")
    except FileNotFoundError:
        return {"verification": {}, "tier_trust": {}, "sources": []}


def _entities_config() -> dict[str, Any]:
    try:
        return load_config("news_entities")
    except FileNotFoundError:
        return {"entities": {}}


def domain_from_url(url: str) -> str:
    if not url:
        return ""
    host = urlparse(url.strip()).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def domain_allowed(url: str, allowed_domains: list[str]) -> bool:
    if not url or not allowed_domains:
        return False
    host = domain_from_url(url)
    if not host:
        return False
    allowed = {d.lower().removeprefix("www.") for d in allowed_domains}
    if host in allowed:
        return True
    return any(host.endswith(f".{d}") for d in allowed)


def tier_trust_score(source_tier: str) -> float:
    tiers = _news_config().get("tier_trust", {})
    return float(tiers.get(source_tier, 0.4))


def verify_article(
    *,
    title: str,
    link: str,
    feed_url: str,
    source_tier: str,
    allowed_domains: list[str],
) -> dict[str, Any]:
    """Verify RSS item before storage."""
    reasons: list[str] = []
    if not title or len(title.strip()) < 8:
        return {
            "verification_status": "rejected",
            "trust_score": 0.0,
            "reject_reasons": ["title_too_short"],
            "feed_domain_ok": False,
            "link_domain_ok": False,
        }

    feed_domain_ok = domain_allowed(feed_url, allowed_domains) if allowed_domains else True
    link_domain_ok = domain_allowed(link, allowed_domains) if link else False
    cfg = _news_config().get("verification", {})
    reject_mismatch = cfg.get("reject_on_domain_mismatch", True)

    if not feed_domain_ok:
        reasons.append("feed_domain_mismatch")

    if not link:
        reasons.append("missing_link")
    elif not link_domain_ok:
        reasons.append("link_domain_mismatch")
        if reject_mismatch:
            return {
                "verification_status": "rejected",
                "trust_score": 0.0,
                "reject_reasons": reasons,
                "feed_domain_ok": feed_domain_ok,
                "link_domain_ok": False,
            }

    base = tier_trust_score(source_tier)
    if "missing_link" in reasons:
        base *= 0.85
    if not feed_domain_ok:
        base *= 0.7
        status = "pending"
    else:
        status = "verified"

    return {
        "verification_status": status,
        "trust_score": round(base, 3),
        "reject_reasons": reasons,
        "feed_domain_ok": feed_domain_ok,
        "link_domain_ok": link_domain_ok,
    }


def extract_matched_symbols(title: str, summary: str, default_symbols: list[str] | None = None) -> list[str]:
    entities = _entities_config().get("entities", {})
    haystack = f"{title} {summary}".upper()
    matched: set[str] = set()

    for ticker, meta in entities.items():
        for alias in meta.get("aliases", []):
            alias_u = alias.upper()
            if len(alias_u) < 3:
                continue
            if alias_u in haystack or _contains_word(haystack, alias_u):
                matched.add(ticker)
                break

    if default_symbols:
        for sym in default_symbols:
            sym_u = sym.upper()
            if sym_u in haystack or _contains_word(haystack, sym_u):
                matched.add(sym_u)

    return sorted(matched)


def _contains_word(haystack: str, needle: str) -> bool:
    if needle in haystack:
        return True
    pattern = r"(?<![\w\u0400-\u04FF])" + re.escape(needle) + r"(?![\w\u0400-\u04FF])"
    return bool(re.search(pattern, haystack, re.IGNORECASE))


def compute_relevance(
    *,
    matched_symbols: list[str],
    target_symbols: list[str] | None,
    trust_score: float,
    title: str,
) -> float:
    if not matched_symbols:
        return round(trust_score * 0.3, 3)
    if not target_symbols:
        return round(min(1.0, trust_score * (0.6 + 0.1 * min(len(matched_symbols), 4))), 3)
    targets = {s.upper().replace("USDT", "") for s in target_symbols}
    hits = [s for s in matched_symbols if s in targets or s.replace("USDT", "") in targets]
    if not hits:
        return round(trust_score * 0.25, 3)
    title_u = title.upper()
    boost = 1.15 if any(h in title_u for h in hits) else 1.0
    return round(min(1.0, trust_score * boost), 3)


def passes_llm_gate(verification_status: str, trust_score: float) -> bool:
    cfg = _news_config().get("verification", {})
    min_trust = float(cfg.get("min_trust_for_llm", 0.55))
    if cfg.get("require_verified", True) and verification_status != "verified":
        return False
    return trust_score >= min_trust


def load_sources_from_config() -> list[dict[str, Any]]:
    cfg = _news_config()
    sources: list[dict[str, Any]] = []
    for src in cfg.get("sources", []):
        sources.append({
            **src,
            "symbols_filter": json.dumps(src.get("default_symbols", []), ensure_ascii=False),
            "allowed_domains_json": json.dumps(src.get("allowed_domains", []), ensure_ascii=False),
        })
    return sources
