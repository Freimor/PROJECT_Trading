"""Regulatory monitor — ESRB/FSB/CBR keywords → macro context / kill_switch."""

from __future__ import annotations

import json
from typing import Any

from admin_service import apply_kill_switch
from config_loader import load_config
from db.connection import get_connection
from news_service import ingest_all, purge_expired


def _cfg() -> dict[str, Any]:
    return load_config("regulatory_monitor")


def _recent_regulatory_news(hours: int = 72) -> list[dict[str, Any]]:
    cfg = _cfg()
    source_ids = cfg.get("source_ids", ["esrb_press", "fsb_press", "cbr_press"])
    keywords = [k.lower() for k in cfg.get("alert_keywords", [])]
    conn = get_connection()
    try:
        placeholders = ",".join("?" * len(source_ids))
        rows = conn.execute(
            f"""
            SELECT ni.id, ni.title, ni.summary, ni.source_name, ni.published_at, ni.source_url
            FROM news_items ni
            INNER JOIN news_sources ns ON ni.source_name = ns.name
            WHERE ns.id IN ({placeholders})
            AND ni.published_at >= datetime('now', ?)
            AND ni.verification_status = 'verified'
            ORDER BY ni.published_at DESC LIMIT 50
            """,
            (*source_ids, f"-{hours} hours"),
        ).fetchall()
        out = []
        for r in rows:
            text = f"{r['title']} {r['summary'] or ''}".lower()
            matched = [k for k in keywords if k in text]
            if matched or not keywords:
                item = dict(r)
                item["matched_keywords"] = matched
                out.append(item)
        return out
    finally:
        conn.close()


def scan_regulatory_risk(*, auto_kill_switch: bool = False) -> dict[str, Any]:
    """Scan regulatory feeds; optionally trigger crypto kill_switch."""
    purge_expired()
    ingest_stats = ingest_all()
    cfg = _cfg()
    items = _recent_regulatory_news(hours=int(cfg.get("lookback_hours", 72)))
    critical_kw = [k.lower() for k in cfg.get("critical_keywords", [])]
    critical_hits: list[dict[str, Any]] = []

    for item in items:
        for kw in critical_kw:
            if kw in f"{item['title']} {item.get('summary', '')}".lower():
                critical_hits.append({**item, "critical_keyword": kw})
                break

    risk_level = "low"
    if critical_hits:
        risk_level = "critical"
    elif len(items) >= int(cfg.get("elevated_count", 5)):
        risk_level = "elevated"

    kill_applied = False
    if auto_kill_switch and risk_level == "critical" and cfg.get("auto_kill_switch_crypto", False):
        apply_kill_switch(enabled=True, operator="regulatory_monitor", source="regulatory_monitor")
        kill_applied = True

    return {
        "status": "ok",
        "risk_level": risk_level,
        "items_count": len(items),
        "critical_hits": critical_hits[:10],
        "ingest": ingest_stats,
        "kill_switch_applied": kill_applied,
        "references": [
            "https://www.esrb.europa.eu/pub/pdf/reports/esrb.report202510_cryptoassets.en.pdf",
            "https://www.fsb.org/uploads/P161025-1.pdf",
        ],
    }
