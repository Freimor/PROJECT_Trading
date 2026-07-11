"""Pre-session universe scan for crypto scalp — vol, volume, diversification."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from asset_catalog_service import crypto_scan_candidates
from binance_client import fetch_klines
from config_loader import load_config
from crypto_quote import get_crypto_quote_asset, pair_with_quote, symbol_base_asset
from effective_config import get_guardrails
from indicators.technical import compute_indicators, parse_binance_klines
from workflow_universe_service import get_workflow_universe, save_workflow_universe

logger = logging.getLogger(__name__)


SCAN_PROGRESS_KEY = "crypto_scalp_scan_progress"


def _set_scan_progress(
    *,
    workflow_name: str,
    total: int,
    done: int = 0,
    current_base: str | None = None,
) -> None:
    from runtime_settings import set_runtime_value

    set_runtime_value(
        SCAN_PROGRESS_KEY,
        {
            "in_progress": True,
            "workflow_name": workflow_name,
            "total": total,
            "done": done,
            "current_base": current_base,
            "started_at": _utc_now(),
        },
        updated_by="scan",
    )


def _clear_scan_progress() -> None:
    from runtime_settings import delete_runtime_value

    delete_runtime_value(SCAN_PROGRESS_KEY)


def get_scalp_scan_progress() -> dict[str, Any]:
    from runtime_settings import get_runtime_value

    raw = get_runtime_value(SCAN_PROGRESS_KEY)
    if not isinstance(raw, dict) or not raw.get("in_progress"):
        return {"in_progress": False}
    return {
        "in_progress": True,
        "workflow_name": raw.get("workflow_name"),
        "total": int(raw.get("total") or 0),
        "done": int(raw.get("done") or 0),
        "current_base": raw.get("current_base"),
        "started_at": raw.get("started_at"),
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_scan_candidate_info(*, testnet: bool = True) -> dict[str, Any]:
    """How many base assets the pre-scan will evaluate."""
    cfg = _scan_cfg()
    bases = _resolve_candidate_bases(cfg, testnet=testnet)
    quote = get_crypto_quote_asset()
    catalog_pairs = crypto_scan_candidates() if cfg.get("use_catalog", True) else []
    guard = get_guardrails().get("symbols", {})
    whitelist = [str(s).upper() for s in guard.get("crypto_whitelist", [])]
    yaml_pairs = load_config("crypto_scalp_hybrid").get("pairs") or []
    extra = [str(s).strip().upper() for s in (cfg.get("candidates") or []) if str(s).strip()]
    mode = str(cfg.get("scan_pool_mode", "combined")).lower()
    catalog_bases = _catalog_only_bases(cfg)
    exchange_bases = _bases_from_exchange(cfg, testnet) if mode in ("exchange", "combined") else []
    return {
        "bases_count": len(bases),
        "bases": bases,
        "quote_asset": quote,
        "scan_pool_mode": mode,
        "max_scan_bases": int(cfg.get("max_scan_bases", 60)),
        "use_catalog": bool(cfg.get("use_catalog", True)),
        "catalog_pairs_count": len(catalog_pairs),
        "catalog_bases_count": len(catalog_bases),
        "exchange_bases_count": len(exchange_bases),
        "exchange_bases_added": max(0, len(bases) - len(set(catalog_bases) & set(bases))),
        "whitelist_count": len(whitelist),
        "yaml_pairs_count": len(yaml_pairs),
        "extra_candidates_count": len(extra),
        "metrics_markets_hint": "USDT/USDC/BTC/ETH — источник vol; торговля только в quote_asset",
    }


def _scan_cfg(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    from crypto_scalp_scan_settings_service import get_merged_scan_config

    cfg = dict(get_merged_scan_config())
    if overrides:
        cfg.update(overrides)
    return cfg


DEFAULT_SCAN_QUOTE_FALLBACKS = ["USDT", "USDC", "FDUSD", "BUSD"]
DEFAULT_SCAN_CROSS_QUOTES = ["BTC", "ETH", "BNB"]


def _exchange_scan_quotes(cfg: dict[str, Any]) -> set[str]:
    quotes: set[str] = set(DEFAULT_SCAN_QUOTE_FALLBACKS)
    quotes.update(str(q).upper() for q in (cfg.get("scan_quote_fallbacks") or []))
    quotes.update(str(q).upper() for q in (cfg.get("scan_cross_quotes") or DEFAULT_SCAN_CROSS_QUOTES))
    return quotes


def _bases_from_exchange(cfg: dict[str, Any], testnet: bool) -> list[str]:
    from binance_client import list_spot_exchange_symbols

    allowed = _exchange_scan_quotes(cfg)
    # Symbol list from mainnet is stable and faster; klines still use testnet when trading paper.
    listing_testnet = bool(testnet) and not bool(cfg.get("scan_exchange_listing_mainnet", True))
    try:
        rows = list_spot_exchange_symbols(listing_testnet)
    except Exception as exc:
        logger.warning("exchange_listing_failed testnet=%s err=%s", listing_testnet, exc)
        return []
    out: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if str(row.get("status", "")).upper() != "TRADING":
            continue
        if str(row.get("quoteAsset", "")).upper() not in allowed:
            continue
        base = str(row.get("baseAsset", "")).upper()
        if not base or base in seen:
            continue
        seen.add(base)
        out.append(base)
    return out


def _catalog_only_bases(cfg: dict[str, Any]) -> list[str]:
    raw: set[str] = set()
    if cfg.get("use_catalog", True):
        raw.update(crypto_scan_candidates())
    guard = get_guardrails().get("symbols", {})
    raw.update(str(s).upper() for s in guard.get("crypto_whitelist", []))
    yaml_pairs = load_config("crypto_scalp_hybrid").get("pairs") or []
    raw.update(str(s).upper() for s in yaml_pairs)
    for sym in cfg.get("candidates") or []:
        raw.add(str(sym).strip().upper())
    bases: list[str] = []
    seen: set[str] = set()
    for sym in sorted(raw):
        base = symbol_base_asset(sym)
        if base and base not in seen:
            seen.add(base)
            bases.append(base)
    return bases


def _resolve_candidate_bases(cfg: dict[str, Any], *, testnet: bool = True) -> list[str]:
    """Base assets to score. Metrics may use USDT/USDC/BTC markets; trading uses session quote."""
    mode = str(cfg.get("scan_pool_mode", "combined")).lower()
    max_bases = max(1, int(cfg.get("max_scan_bases", 60)))

    priority: list[str] = []
    seen: set[str] = set()

    def add_base(base: str) -> None:
        b = str(base).upper().strip()
        if b and b not in seen:
            seen.add(b)
            priority.append(b)

    if mode == "exchange":
        for sym in cfg.get("candidates") or []:
            add_base(symbol_base_asset(str(sym)))
        guard = get_guardrails().get("symbols", {})
        for s in guard.get("crypto_whitelist", []):
            add_base(symbol_base_asset(str(s)))
        for s in load_config("crypto_scalp_hybrid").get("pairs") or []:
            add_base(symbol_base_asset(str(s)))
        for b in _bases_from_exchange(cfg, testnet):
            add_base(b)
    else:
        if cfg.get("use_catalog", True):
            for sym in crypto_scan_candidates():
                add_base(symbol_base_asset(sym))
        for sym in cfg.get("candidates") or []:
            add_base(symbol_base_asset(str(sym)))
        guard = get_guardrails().get("symbols", {})
        for s in guard.get("crypto_whitelist", []):
            add_base(symbol_base_asset(str(s)))
        for s in load_config("crypto_scalp_hybrid").get("pairs") or []:
            add_base(symbol_base_asset(str(s)))
        if mode == "combined":
            for b in _bases_from_exchange(cfg, testnet):
                add_base(b)

    return priority[:max_bases]


def _resolve_candidates(cfg: dict[str, Any]) -> list[str]:
    """Trading symbols (base + session quote) for backward compatibility."""
    quote = get_crypto_quote_asset()
    return [pair_with_quote(base, quote=quote) for base in _resolve_candidate_bases(cfg)]


def _scan_market_symbols(base: str, session_quote: str, cfg: dict[str, Any]) -> list[str]:
    base = str(base).upper()
    q = str(session_quote).upper()
    quotes = cfg.get("scan_quote_fallbacks")
    if not isinstance(quotes, list):
        quotes = list(DEFAULT_SCAN_QUOTE_FALLBACKS)
    cross = cfg.get("scan_cross_quotes")
    if not isinstance(cross, list):
        cross = list(DEFAULT_SCAN_CROSS_QUOTES)
    ordered: list[str] = []
    seen: set[str] = set()
    for item in [q, *[str(x).upper() for x in quotes], *[str(x).upper() for x in cross]]:
        if not item or item == base or item in seen:
            continue
        seen.add(item)
        ordered.append(f"{base}{item}")
    trading = pair_with_quote(base, quote=q)
    if trading not in ordered:
        ordered.insert(0, trading)
    return ordered


def _candle_scan_quality(candles: list[dict[str, float]]) -> float:
    if len(candles) < 30:
        return -1.0
    atr = _atr_pct(candles) or 0.0
    vol = _volume_ratio(candles)
    return atr * max(vol, 0.05) + (0.001 if vol > 0 else 0)


def _fetch_best_scan_candles(
    base: str,
    *,
    session_quote: str,
    cfg: dict[str, Any],
    testnet: bool,
    timeframe: str,
    limit: int,
) -> tuple[str, str, str, list[dict[str, float]]]:
    """Pick best klines for metrics; trading always uses session quote stablecoin."""
    trading = pair_with_quote(base, quote=session_quote)
    markets = _scan_market_symbols(base, session_quote, cfg)
    best: tuple[str, str, list[dict[str, float]], float] | None = None

    def attempt(sym: str, env: str, use_testnet: bool) -> None:
        nonlocal best
        try:
            raw = fetch_klines(sym, timeframe, limit=limit, testnet=use_testnet)
            candles = parse_binance_klines(raw)
            quality = _candle_scan_quality(candles)
            if quality < 0:
                return
            if best is None or quality > best[3]:
                best = (sym, env, candles, quality)
        except Exception:
            return

    for sym in markets:
        attempt(sym, "testnet" if testnet else "mainnet", testnet)

    if testnet and cfg.get("scan_metrics_mainnet_fallback", True):
        for sym in markets:
            if sym.endswith(tuple(DEFAULT_SCAN_QUOTE_FALLBACKS)):
                attempt(sym, "mainnet", False)

    if best:
        return trading, best[0], best[1], best[2]

    try:
        raw = fetch_klines(trading, timeframe, limit=limit, testnet=testnet)
        candles = parse_binance_klines(raw)
        env = "testnet" if testnet else "mainnet"
        return trading, trading, env, candles
    except Exception:
        return trading, trading, "testnet" if testnet else "mainnet", []


def _atr_pct(candles: list[dict[str, float]], *, period: int = 14) -> float | None:
    if len(candles) < period + 1:
        return None
    trs: list[float] = []
    for i in range(1, len(candles)):
        h = candles[i]["h"]
        l = candles[i]["l"]
        prev_c = candles[i - 1]["c"]
        trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    if len(trs) < period:
        return None
    atr = sum(trs[-period:]) / period
    close = candles[-1]["c"]
    if close <= 0:
        return None
    return round(atr / close * 100, 4)


def _volume_ratio(candles: list[dict[str, float]], *, lookback: int = 20) -> float:
    volumes = [c["v"] for c in candles]
    if len(volumes) < 2:
        return 1.0
    lb = min(lookback, max(len(volumes) - 1, 1))
    avg = sum(volumes[-lb - 1 : -1]) / lb if lb else volumes[-1]
    if avg <= 0:
        return 1.0
    return round(volumes[-1] / avg, 4)


def _momentum_pct(candles: list[dict[str, float]], *, bars: int = 3) -> float:
    closes = [c["c"] for c in candles]
    n = int(bars)
    if len(closes) <= n or closes[-n - 1] <= 0:
        return 0.0
    return round((closes[-1] - closes[-n - 1]) / closes[-n - 1] * 100, 4)


def _atr_score(atr_pct: float, cfg: dict[str, Any]) -> tuple[float, str | None]:
    lo = float(cfg.get("atr_pct_min", 0.25))
    hi = float(cfg.get("atr_pct_max", 2.5))
    sweet_lo = float(cfg.get("atr_pct_sweet_min", 0.35))
    sweet_hi = float(cfg.get("atr_pct_sweet_max", 1.2))
    if atr_pct < lo:
        return 0.0, "atr_too_low"
    if atr_pct > hi:
        return 0.0, "atr_too_high"
    if sweet_lo <= atr_pct <= sweet_hi:
        mid = (sweet_lo + sweet_hi) / 2
        span = max(sweet_hi - sweet_lo, 0.01)
        return round(0.85 + 0.15 * (1 - abs(atr_pct - mid) / (span / 2)), 4), None
    if atr_pct < sweet_lo:
        return round(0.4 + 0.45 * (atr_pct - lo) / max(sweet_lo - lo, 0.01), 4), None
    return round(0.4 + 0.45 * (hi - atr_pct) / max(hi - sweet_hi, 0.01), 4), None


def _returns_series(candles: list[dict[str, float]]) -> list[float]:
    closes = [c["c"] for c in candles]
    out: list[float] = []
    for i in range(1, len(closes)):
        if closes[i - 1] <= 0:
            continue
        out.append((closes[i] - closes[i - 1]) / closes[i - 1])
    return out


def _pearson(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n < 8:
        return 0.0
    a = a[-n:]
    b = b[-n:]
    ma = sum(a) / n
    mb = sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a) ** 0.5
    db = sum((y - mb) ** 2 for y in b) ** 0.5
    if da <= 0 or db <= 0:
        return 0.0
    return num / (da * db)


def score_scalp_symbol(
    symbol: str,
    *,
    cfg: dict[str, Any] | None = None,
    testnet: bool = True,
    candles: list[dict[str, float]] | None = None,
    data_symbol: str | None = None,
    data_env: str | None = None,
    base_asset: str | None = None,
) -> dict[str, Any]:
    """Score one pair for scalp session (higher = better)."""
    cfg = cfg or _scan_cfg()
    sym = str(symbol).upper()
    timeframe = str(load_config("crypto_scalp_hybrid").get("timeframe", "5m"))
    limit = int(cfg.get("klines_limit", 120))

    if candles is None:
        raw = fetch_klines(sym, timeframe, limit=limit, testnet=testnet)
        candles = parse_binance_klines(raw)

    if len(candles) < 30:
        return {
            "symbol": sym,
            "base_asset": base_asset or symbol_base_asset(sym),
            "eligible": False,
            "score": 0.0,
            "reject_reason": "insufficient_bars",
            "bars": len(candles),
            "metrics": {
                "data_symbol": data_symbol or sym,
                "data_env": data_env or ("testnet" if testnet else "mainnet"),
            },
        }

    indicators = compute_indicators(candles)
    atr = _atr_pct(candles, period=int(cfg.get("atr_period", 14)))
    vol_ratio = _volume_ratio(candles)
    mom = _momentum_pct(candles, bars=int(cfg.get("momentum_bars", 3)))
    rsi = indicators.get("rsi_14")

    metrics_extra = {
        "data_symbol": data_symbol or sym,
        "data_env": data_env or ("testnet" if testnet else "mainnet"),
    }

    if atr is None:
        return {
            "symbol": sym,
            "base_asset": base_asset or symbol_base_asset(sym),
            "eligible": False,
            "score": 0.0,
            "reject_reason": "atr_unavailable",
            "metrics": metrics_extra,
        }

    atr_s, atr_reject = _atr_score(atr, cfg)
    if atr_reject:
        return {
            "symbol": sym,
            "base_asset": base_asset or symbol_base_asset(sym),
            "eligible": False,
            "score": 0.0,
            "reject_reason": atr_reject,
            "metrics": {
                "atr_pct": atr,
                "volume_ratio": vol_ratio,
                "momentum_pct": mom,
                **metrics_extra,
            },
        }

    vol_min = float(cfg.get("volume_ratio_min", 1.0))
    vol_s = min(1.0, vol_ratio / max(vol_min, 0.01))
    if vol_ratio < vol_min * 0.75:
        return {
            "symbol": sym,
            "base_asset": base_asset or symbol_base_asset(sym),
            "eligible": False,
            "score": 0.0,
            "reject_reason": "volume_too_low",
            "metrics": {
                "atr_pct": atr,
                "volume_ratio": vol_ratio,
                "momentum_pct": mom,
                **metrics_extra,
            },
        }

    mom_min = float(cfg.get("momentum_min_pct", 0.08))
    mom_s = min(1.0, abs(mom) / max(mom_min * 2, 0.01))

    rsi_s = 0.5
    if rsi is not None:
        rsi_lo = float(cfg.get("rsi_active_low", 38))
        rsi_hi = float(cfg.get("rsi_active_high", 62))
        if rsi < rsi_lo or rsi > rsi_hi:
            rsi_s = 0.85
        else:
            rsi_s = 0.35

    trend_s = 0.6
    if indicators.get("trend") == "up" and mom > 0:
        trend_s = 0.9
    elif indicators.get("trend") == "down" and mom < 0:
        trend_s = 0.75

    w_atr = float(cfg.get("weight_atr", 0.35))
    w_vol = float(cfg.get("weight_volume", 0.25))
    w_mom = float(cfg.get("weight_momentum", 0.2))
    w_rsi = float(cfg.get("weight_rsi", 0.1))
    w_trend = float(cfg.get("weight_trend", 0.1))
    score = round(
        w_atr * atr_s + w_vol * vol_s + w_mom * mom_s + w_rsi * rsi_s + w_trend * trend_s,
        4,
    )

    return {
        "symbol": sym,
        "base_asset": base_asset or symbol_base_asset(sym),
        "eligible": True,
        "score": score,
        "metrics": {
            "atr_pct": atr,
            "volume_ratio": vol_ratio,
            "momentum_pct": mom,
            "rsi_14": rsi,
            "trend": indicators.get("trend"),
            **metrics_extra,
        },
        "components": {
            "atr": atr_s,
            "volume": vol_s,
            "momentum": mom_s,
            "rsi": rsi_s,
            "trend": trend_s,
        },
    }


def _diversify(
    ranked: list[dict[str, Any]],
    *,
    candle_map: dict[str, list[dict[str, float]]],
    cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    top_n = int(cfg.get("top_n", 3))
    max_corr = float(cfg.get("max_pair_correlation", 0.85))
    min_score = float(cfg.get("min_score", 0.35))
    picked: list[dict[str, Any]] = []
    returns_map = {sym: _returns_series(candle_map[sym]) for sym in candle_map}

    for row in ranked:
        if not row.get("eligible") or float(row.get("score") or 0) < min_score:
            continue
        sym = row["symbol"]
        ok = True
        for other in picked:
            corr = abs(_pearson(returns_map.get(sym, []), returns_map.get(other["symbol"], [])))
            if corr >= max_corr:
                ok = False
                row = {**row, "skipped_diversify": True, "corr_with": other["symbol"], "corr": round(corr, 3)}
                break
        if ok:
            picked.append(row)
        if len(picked) >= top_n:
            break
    return picked


def scan_scalp_universe(
    workflow_name: str,
    *,
    top_n: int | None = None,
    testnet: bool = True,
    operator: str = "web:operator",
    config_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rank candidate pairs; optionally apply to workflow universe."""
    cfg = _scan_cfg(config_overrides)
    if top_n is not None:
        cfg["top_n"] = top_n
    if not cfg.get("enabled", True):
        return {"status": "skipped", "reason": "universe_scan_disabled"}

    if "scalp" not in workflow_name.lower():
        return {"status": "skipped", "reason": "not_scalp_workflow"}

    candidates = _resolve_candidates(cfg)
    bases = _resolve_candidate_bases(cfg, testnet=testnet)
    if not bases:
        return {"status": "error", "reason": "empty_candidates"}

    session_quote = get_crypto_quote_asset()
    timeframe = str(load_config("crypto_scalp_hybrid").get("timeframe", "5m"))
    klines_limit = int(cfg.get("klines_limit", 120))

    ranked: list[dict[str, Any]] = []
    candle_map: dict[str, list[dict[str, float]]] = {}
    errors: list[dict[str, Any]] = []

    _set_scan_progress(workflow_name=workflow_name, total=len(bases))
    try:
        for idx, base in enumerate(bases):
            _set_scan_progress(
                workflow_name=workflow_name,
                total=len(bases),
                done=idx,
                current_base=base,
            )
            try:
                trading_sym, data_sym, data_env, candles = _fetch_best_scan_candles(
                    base,
                    session_quote=session_quote,
                    cfg=cfg,
                    testnet=testnet,
                    timeframe=timeframe,
                    limit=klines_limit,
                )
                candle_map[trading_sym] = candles
                row = score_scalp_symbol(
                    trading_sym,
                    cfg=cfg,
                    testnet=testnet,
                    candles=candles,
                    data_symbol=data_sym,
                    data_env=data_env,
                    base_asset=base,
                )
                ranked.append(row)
            except Exception as exc:
                sym = pair_with_quote(base, quote=session_quote)
                logger.warning("scalp_scan_failed symbol=%s err=%s", sym, exc)
                errors.append({"symbol": sym, "base": base, "error": str(exc)[:200]})
    finally:
        _clear_scan_progress()

    ranked.sort(key=lambda r: float(r.get("score") or 0), reverse=True)
    selected = _diversify(ranked, candle_map=candle_map, cfg=cfg)

    result = {
        "status": "ok",
        "workflow": workflow_name,
        "scanned_at": _utc_now(),
        "quote_asset": session_quote,
        "scan_mode": "multi_market_metrics",
        "candidates_count": len(candidates),
        "ranked": ranked,
        "selected": selected,
        "selected_symbols": [r["symbol"] for r in selected],
        "errors": errors,
        "config": {
            "top_n": cfg.get("top_n", 3),
            "min_score": cfg.get("min_score", 0.35),
            "atr_pct_min": cfg.get("atr_pct_min"),
        },
    }
    _store_last_scan(workflow_name, result)
    return result


def apply_user_selected_symbols(
    workflow_name: str,
    symbols: list[str],
    *,
    scan_result: dict[str, Any] | None = None,
    operator: str = "web:operator",
) -> dict[str, Any]:
    """Enable user-picked symbols from scan (or manual); disable other scan candidates."""
    selected_syms = {str(s).upper().strip() for s in symbols if str(s).strip()}
    if not selected_syms:
        return {"status": "skipped", "reason": "no_symbols_selected"}

    candidate_syms: set[str] = set()
    if scan_result:
        candidate_syms = {str(r.get("symbol", "")).upper() for r in scan_result.get("ranked") or []}
        candidate_syms.discard("")
    else:
        candidate_syms = set(selected_syms)

    state = get_workflow_universe(workflow_name)
    by_symbol = {i["symbol"]: dict(i) for i in state.get("items") or []}
    now = _utc_now()
    score_by_sym = {}
    if scan_result:
        for r in scan_result.get("ranked") or []:
            if r.get("symbol"):
                score_by_sym[str(r["symbol"]).upper()] = r.get("score")

    for sym in candidate_syms | selected_syms:
        if sym in by_symbol:
            by_symbol[sym]["enabled"] = sym in selected_syms
            if sym in selected_syms:
                by_symbol[sym]["source"] = "scan"
                if sym in score_by_sym:
                    by_symbol[sym]["scan_score"] = score_by_sym[sym]
        elif sym in selected_syms:
            by_symbol[sym] = {
                "symbol": sym,
                "enabled": True,
                "source": "scan",
                "added_at": now,
                "scan_score": score_by_sym.get(sym),
            }

    for sym, row in list(by_symbol.items()):
        if row.get("source") == "scan" and sym in candidate_syms and sym not in selected_syms:
            row["enabled"] = False

    saved = save_workflow_universe(workflow_name, list(by_symbol.values()), operator=operator)
    stored_scan = scan_result or get_last_scan(workflow_name) or {"scanned_at": _utc_now(), "ranked": []}
    _store_last_scan(workflow_name, stored_scan, selected=sorted(selected_syms))
    last_saved = get_last_scan(workflow_name)
    return {
        "status": "ok",
        "workflow": workflow_name,
        "selected_symbols": sorted(selected_syms),
        "scanned_at": (last_saved or {}).get("scanned_at"),
        "last_scan": last_saved,
        "universe": saved,
    }


def _store_last_scan(
    workflow_name: str,
    scan_result: dict[str, Any] | None,
    *,
    selected: list[str] | None = None,
) -> None:
    from runtime_settings import set_runtime_value

    existing = get_last_scan(workflow_name) or {}
    if scan_result:
        base = scan_result
    elif selected is not None:
        base = existing if existing else {"scanned_at": _utc_now(), "ranked": []}
    else:
        return

    payload = {
        "workflow": workflow_name,
        "scanned_at": base.get("scanned_at") or existing.get("scanned_at") or _utc_now(),
        "selected_symbols": selected if selected is not None else base.get("selected_symbols"),
        "ranked": base.get("ranked") if base.get("ranked") is not None else existing.get("ranked"),
        "candidates_count": (
            base.get("candidates_count")
            if base.get("candidates_count") is not None
            else existing.get("candidates_count")
        ),
    }
    set_runtime_value(f"crypto_scalp_last_scan:{workflow_name}", payload, updated_by="scan")


def get_last_scan(workflow_name: str) -> dict[str, Any] | None:
    from runtime_settings import get_runtime_value

    val = get_runtime_value(f"crypto_scalp_last_scan:{workflow_name}")
    return val if isinstance(val, dict) else None


def apply_scalp_universe_scan(
    workflow_name: str,
    scan_result: dict[str, Any],
    *,
    operator: str = "web:operator",
) -> dict[str, Any]:
    """Enable top scan picks; disable other scan-candidate pairs in universe."""
    selected_syms = {str(s).upper() for s in scan_result.get("selected_symbols") or []}
    candidate_syms = {str(r.get("symbol", "")).upper() for r in scan_result.get("ranked") or []}
    if not selected_syms:
        return {"status": "skipped", "reason": "no_symbols_selected", "scan": scan_result}

    state = get_workflow_universe(workflow_name)
    by_symbol = {i["symbol"]: dict(i) for i in state.get("items") or []}
    now = _utc_now()

    for sym in candidate_syms:
        if not sym:
            continue
        if sym in by_symbol:
            by_symbol[sym]["enabled"] = sym in selected_syms
            if sym in selected_syms:
                by_symbol[sym]["source"] = "scan"
                by_symbol[sym]["scan_score"] = next(
                    (r.get("score") for r in scan_result.get("selected") or [] if r.get("symbol") == sym),
                    None,
                )
        elif sym in selected_syms:
            sel_row = next(
                (r for r in scan_result.get("selected") or [] if r.get("symbol") == sym),
                {},
            )
            by_symbol[sym] = {
                "symbol": sym,
                "enabled": True,
                "source": "scan",
                "added_at": now,
                "scan_score": sel_row.get("score"),
            }

    for sym, row in list(by_symbol.items()):
        if row.get("source") == "scan" and sym in candidate_syms and sym not in selected_syms:
            row["enabled"] = False

    saved = save_workflow_universe(workflow_name, list(by_symbol.values()), operator=operator)
    _store_last_scan(workflow_name, scan_result, selected=sorted(selected_syms))
    return {
        "status": "ok",
        "workflow": workflow_name,
        "selected_symbols": sorted(selected_syms),
        "universe": saved,
        "scan": scan_result,
    }


def run_pre_session_scalp_scan(
    workflow_name: str,
    *,
    operator: str = "web:operator",
    testnet: bool = True,
) -> dict[str, Any]:
    """Scan + apply universe before scalp session start."""
    scan = scan_scalp_universe(workflow_name, testnet=testnet, operator=operator)
    if scan.get("status") != "ok":
        return scan
    if not scan.get("selected_symbols"):
        return {
            **scan,
            "status": "warning",
            "apply": {"status": "skipped", "reason": "no_eligible_symbols"},
        }
    applied = apply_scalp_universe_scan(workflow_name, scan, operator=operator)
    return {**scan, "apply": applied}


def maybe_rescan_scalp_universe(
    workflow_name: str,
    *,
    operator: str = "system",
    testnet: bool = True,
) -> dict[str, Any] | None:
    """Re-scan during session if enabled and interval elapsed."""
    from crypto_scalp_scan_settings_service import get_merged_scan_config

    cfg = get_merged_scan_config()
    if not cfg.get("enabled", True) or not cfg.get("rescan_during_session", True):
        return None

    interval_h = float(cfg.get("rescan_interval_hours", 2))
    last_meta = get_last_scan(workflow_name) or {}
    last = last_meta.get("scanned_at")
    if last:
        try:
            last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            elapsed_h = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
            if elapsed_h < interval_h:
                return None
        except ValueError:
            pass

    result = run_pre_session_scalp_scan(workflow_name, operator=operator, testnet=testnet)
    return result
