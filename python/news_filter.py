"""Trade-relevance filter for Signals Engine (tags + keywords + scoring)."""

from __future__ import annotations

import json
import re
from typing import Any

from config_loader import load_config
from runtime_settings import get_runtime_value

_SETTINGS_KEY = "signals_engine_runtime"
_FILTER_MODES = ("loose", "balanced", "strict")

# Макро-метки: сами по себе не дают проход в balanced/strict
_GENERIC_SYMBOLS = frozenset({"MOEX", "RUB", "CRYPTO", "DIVIDEND", "MACRO"})

_DEFAULT_INCLUDE = [
    "бирж",
    "акци",
    "облигаци",
    "офз",
    "фонд",
    "etf",
    "бпиф",
    "дивиденд",
    "котиров",
    "индекс",
    "imoex",
    "moex",
    "фьючерс",
    "опцион",
    "трейдин",
    "инвест",
    "портфел",
    "ключев",
    "ставк",
    "цб рф",
    "банк россии",
    "рубл",
    "доллар",
    "нефт",
    "газпром",
    "сбер",
    "bitcoin",
    "ethereum",
    "крипт",
    "crypto",
    "blockchain",
    "binance",
    "ipo",
    "эмисси",
    "купон",
    "yield",
    "санкци",
    "тариф",
    "бюджет",
    "инфляци",
    "ввп",
    "sec ",
    "fed ",
    "nasdaq",
    "s&p",
]

_DEFAULT_EXCLUDE = [
    "спорт",
    "футбол",
    "хоккей",
    "теннис",
    "кино",
    "сериал",
    "театр",
    "концерт",
    "погода",
    "гороскоп",
    "знаменитост",
    "мода",
    "рецепт",
    "кулинар",
    "развод звезд",
    "шоу-бизнес",
    "криминал",
    "дтп",
]


def _engine_yaml() -> dict[str, Any]:
    try:
        return load_config("signals_engine")
    except FileNotFoundError:
        return {}


def get_filter_settings() -> dict[str, Any]:
    yaml_cfg = _engine_yaml().get("filter", {})
    runtime = get_runtime_value(_SETTINGS_KEY) or {}
    merged = {**yaml_cfg, **runtime.get("filter", {})}
    if not merged.get("keywords_include"):
        merged["keywords_include"] = list(_DEFAULT_INCLUDE)
    if not merged.get("keywords_exclude"):
        merged["keywords_exclude"] = list(_DEFAULT_EXCLUDE)
    if not merged.get("active_tags"):
        merged["active_tags"] = ["crypto", "moex", "macro"]
    mode = str(merged.get("mode", "balanced")).lower()
    if mode not in _FILTER_MODES:
        mode = "balanced"
    merged["mode"] = mode
    merged.setdefault("min_keywords", 2)
    merged.setdefault("min_relevance_score", 2.5)
    merged.setdefault("require_keyword_in_title", True)
    return merged


def _resolve_universe() -> set[str]:
    symbols: set[str] = set()
    try:
        from workflow_universe_service import all_enabled_symbols

        symbols.update(s.upper().replace("USDT", "") for s in all_enabled_symbols())
    except Exception:
        pass
    if not symbols:
        try:
            from config_loader import load_config as lc

            crypto = lc("crypto_config")
            for p in crypto.get("pairs", []):
                symbols.add(p.replace("USDT", "").upper())
                symbols.add(p.upper())
            sec = lc("securities_config")
            symbols.update(sec.get("swing_signals", {}).get("universe", []))
        except Exception:
            pass
    return {s for s in symbols if s}


def _keyword_hit(haystack: str, keyword: str) -> bool:
    kw = keyword.strip().lower()
    if not kw or len(kw) < 2:
        return False
    if kw in haystack:
        return True
    if len(kw) < 4:
        return bool(re.search(rf"(?<![\w\u0400-\u04FF]){re.escape(kw)}(?![\w\u0400-\u04FF])", haystack))
    return False


def _symbol_in_title(title: str, symbols: set[str]) -> bool:
    title_u = title.upper()
    for sym in symbols:
        if sym in title_u or _keyword_hit(title_u, sym):
            return True
    return False


def _compute_score(
    *,
    tag_ok: bool,
    universe_hits: list[str],
    specific_symbols: set[str],
    generic_hits: set[str],
    matched_keywords: list[str],
    title_keywords: list[str],
    title_has_specific_symbol: bool,
) -> float:
    score = 0.0
    if tag_ok:
        score += 1.0
    if universe_hits:
        score += 3.0
    elif specific_symbols:
        score += 1.5
    elif generic_hits:
        score += 0.25
    score += min(len(matched_keywords), 4) * 0.6
    if title_keywords:
        score += 1.0
    if title_has_specific_symbol:
        score += 1.5
    if universe_hits and title_has_specific_symbol:
        score += 0.5
    return round(score, 2)


def evaluate_trade_relevance(
    *,
    title: str,
    body: str,
    matched_symbols: list[str],
    source_tags: list[str] | None = None,
) -> dict[str, Any]:
    """Multi-parameter trade relevance check.

    Modes:
    - loose: tag + (any symbol OR any include keyword) — прежняя логика
    - balanced: tag + (universe ticker OR ≥min_keywords OR title-kw + specific symbol)
    - strict: tag + universe ticker from enabled workflows
    """
    cfg = get_filter_settings()
    if not cfg.get("enabled", True):
        return {
            "relevant": True,
            "relevance_score": 10.0,
            "mode": cfg.get("mode", "balanced"),
            "reasons": [],
            "matched_keywords": [],
            "matched_tags": list(source_tags or []),
            "universe_symbols": [],
        }

    mode = cfg["mode"]
    title_lower = title.lower()
    haystack = f"{title} {body}".lower()
    reasons: list[str] = []

    for kw in cfg.get("keywords_exclude", []):
        if _keyword_hit(haystack, str(kw)):
            return {
                "relevant": False,
                "relevance_score": 0.0,
                "mode": mode,
                "reasons": [f"exclude:{kw}"],
                "matched_keywords": [],
                "matched_tags": [],
                "universe_symbols": [],
            }

    active_tags = {str(t).lower() for t in cfg.get("active_tags", []) if t}
    source_tags_norm = {str(t).lower() for t in (source_tags or []) if t}
    matched_tags = sorted(active_tags & source_tags_norm) if active_tags else sorted(source_tags_norm)
    tag_ok = not active_tags or bool(matched_tags)
    if not tag_ok:
        reasons.append("source_tag_mismatch")

    include_kws = [str(k) for k in cfg.get("keywords_include", []) if k]
    matched_keywords = [kw for kw in include_kws if _keyword_hit(haystack, kw)]
    title_keywords = [kw for kw in matched_keywords if _keyword_hit(title_lower, kw)]

    matched_norm = {str(s).upper().replace("USDT", "") for s in matched_symbols}
    generic_hits = matched_norm & _GENERIC_SYMBOLS
    specific_symbols = matched_norm - _GENERIC_SYMBOLS
    universe = _resolve_universe()
    universe_hits = sorted(s for s in specific_symbols if s in universe)
    title_has_specific = _symbol_in_title(title, specific_symbols)

    relevance_score = _compute_score(
        tag_ok=tag_ok,
        universe_hits=universe_hits,
        specific_symbols=specific_symbols,
        generic_hits=generic_hits,
        matched_keywords=matched_keywords,
        title_keywords=title_keywords,
        title_has_specific_symbol=title_has_specific,
    )

    min_kw = int(cfg.get("min_keywords", 2))
    min_score = float(cfg.get("min_relevance_score", 2.5))
    require_title_kw = bool(cfg.get("require_keyword_in_title", True))

    if mode == "strict":
        content_ok = bool(universe_hits)
        if not content_ok:
            reasons.append("no_universe_symbol")
    elif mode == "loose":
        symbol_passes = bool(cfg.get("symbol_match_passes", True))
        keyword_ok = bool(matched_keywords)
        symbol_ok = bool(matched_symbols)
        if symbol_ok and symbol_passes:
            content_ok = True
        elif bool(cfg.get("require_symbol_or_keyword", True)):
            content_ok = symbol_ok or keyword_ok
        else:
            content_ok = keyword_ok
        if not content_ok:
            reasons.append("no_symbol_or_keyword")
    else:
        # balanced — несколько независимых критериев, нужен хотя бы один «сильный»
        path_universe = bool(universe_hits)
        path_keywords = len(matched_keywords) >= min_kw and relevance_score >= min_score
        if require_title_kw:
            path_keywords = path_keywords and bool(title_keywords)
        path_title_symbol = bool(title_keywords) and bool(specific_symbols)
        content_ok = path_universe or path_keywords or path_title_symbol
        if not content_ok:
            if not path_universe:
                reasons.append("no_universe_symbol")
            if len(matched_keywords) < min_kw:
                reasons.append(f"keywords_lt_{min_kw}")
            if require_title_kw and not title_keywords:
                reasons.append("no_keyword_in_title")
            if relevance_score < min_score:
                reasons.append(f"score_lt_{min_score}")

    relevant = tag_ok and content_ok

    return {
        "relevant": relevant,
        "relevance_score": relevance_score,
        "mode": mode,
        "reasons": reasons,
        "matched_keywords": matched_keywords[:12],
        "matched_tags": matched_tags,
        "universe_symbols": universe_hits,
        "specific_symbols": sorted(specific_symbols),
    }


def filter_meta_json(result: dict[str, Any]) -> str:
    return json.dumps(
        {
            "relevant": result.get("relevant"),
            "relevance_score": result.get("relevance_score"),
            "mode": result.get("mode"),
            "reasons": result.get("reasons", []),
            "matched_keywords": result.get("matched_keywords", []),
            "matched_tags": result.get("matched_tags", []),
            "universe_symbols": result.get("universe_symbols", []),
        },
        ensure_ascii=False,
    )
