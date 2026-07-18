"""Chart data for admin console — OHLCV candles and trade/LLM markers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from binance_client import fetch_klines
from config_loader import load_config
from db.connection import get_connection
from db.migrate import run_migrations
from indicators.technical import compute_indicator_series, parse_binance_klines
from market_data import fetch_moex_candles_as_of, moex_iss_interval, resample_ohlcv
from strategy_service import symbols_for_market

from event_summary import summarize_trade_event

MARKER_STAGES = ("signal", "filter", "llm", "guardrails", "order", "fill", "risk")


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _to_unix_seconds(t: Any) -> int:
    if isinstance(t, (int, float)):
        val = float(t)
        return int(val / 1000) if val > 1e12 else int(val)
    if isinstance(t, str):
        if t.isdigit():
            val = float(t)
            return int(val / 1000) if val > 1e12 else int(val)
        return int(_parse_dt(t).timestamp())
    raise ValueError(f"unsupported time: {t!r}")


def _normalize_candle(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "time": _to_unix_seconds(row["t"]),
        "open": float(row["o"]),
        "high": float(row["h"]),
        "low": float(row["l"]),
        "close": float(row["c"]),
        "volume": float(row.get("v", 0)),
    }


def _fetch_crypto_candles(
    *,
    symbol: str,
    timeframe: str,
    limit: int,
    testnet: bool,
) -> tuple[list[dict[str, Any]], str, bool]:
    """Fetch crypto OHLCV; on poor testnet feed use mainnet for chart display only."""
    from config_loader import load_config
    from scalp_klines import chart_klines_quality_poor, klines_quality_settings

    limit = min(limit, 1000)
    raw = fetch_klines(symbol, timeframe, limit=limit, testnet=testnet)
    parsed = parse_binance_klines(raw)
    candles = [_normalize_candle(c) for c in parsed]
    if not testnet:
        return candles, "mainnet", False

    scalp_cfg = load_config("crypto_scalp_hybrid")
    quality = klines_quality_settings(scalp_cfg)
    min_bars = quality["min_bars"]
    flat_max = quality["flat_range_pct_max"]
    testnet_poor = chart_klines_quality_poor(parsed, min_bars=min_bars, flat_range_pct_max=flat_max)
    use_fallback = bool(scalp_cfg.get("signal_klines_mainnet_fallback", True))

    if testnet_poor and use_fallback:
        try:
            raw_main = fetch_klines(symbol, timeframe, limit=limit, testnet=False)
            parsed_main = parse_binance_klines(raw_main)
            if not chart_klines_quality_poor(parsed_main, min_bars=min_bars, flat_range_pct_max=flat_max):
                return (
                    [_normalize_candle(c) for c in parsed_main],
                    "mainnet_metrics_fallback",
                    True,
                )
        except Exception:
            pass

    return candles, "testnet", testnet_poor


def _fetch_live_candles(
    *,
    market: str,
    symbol: str,
    timeframe: str,
    limit: int,
    testnet: bool,
) -> tuple[list[dict[str, Any]], str, bool]:
    if market == "crypto":
        return _fetch_crypto_candles(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            testnet=testnet,
        )

    as_of = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    tf = str(timeframe).strip().lower()
    iss_interval = moex_iss_interval(tf)
    fetch_limit = limit * 4 if tf == "4h" else limit
    moex = fetch_moex_candles_as_of(
        symbol, interval=iss_interval, as_of=as_of, limit=fetch_limit
    )
    if tf == "4h":
        moex = resample_ohlcv(moex, 4 * 3600)
        if limit > 0 and len(moex) > limit:
            moex = moex[-limit:]
    return [_normalize_candle(c) for c in moex], market, False


def _cache_max_age_seconds(market: str, interval: str) -> int:
    tf = str(interval).strip().lower()
    if market == "securities":
        if tf in ("1d", "24h", "d"):
            return 4 * 86400
        return 8 * 3600
    if tf in ("1d", "24h", "d"):
        return 2 * 86400
    return 6 * 3600


def _cache_is_fresh(
    candles: list[dict[str, Any]],
    *,
    market: str,
    interval: str,
) -> bool:
    if not candles:
        return False
    newest = max(c["time"] for c in candles)
    threshold = int(datetime.now(timezone.utc).timestamp()) - _cache_max_age_seconds(market, interval)
    return newest >= threshold


def _cached_candles_usable(
    candles: list[dict[str, Any]],
    *,
    market: str,
    interval: str,
    testnet: bool,
) -> bool:
    if not candles or not _cache_is_fresh(candles, market=market, interval=interval):
        return False
    if market != "crypto" or not testnet:
        return True
    from config_loader import load_config
    from scalp_klines import chart_klines_quality_poor, klines_quality_settings

    scalp_cfg = load_config("crypto_scalp_hybrid")
    quality = klines_quality_settings(scalp_cfg)
    parsed = [
        {
            "t": c["time"],
            "o": c["open"],
            "h": c["high"],
            "l": c["low"],
            "c": c["close"],
            "v": c.get("volume", 0),
        }
        for c in candles
    ]
    return not chart_klines_quality_poor(
        parsed,
        min_bars=quality["min_bars"],
        flat_range_pct_max=quality["flat_range_pct_max"],
    )


def get_chart_candles(
    *,
    market: str,
    symbol: str,
    interval: str = "4h",
    limit: int = 200,
    testnet: bool = True,
    use_cache: bool = True,
) -> dict[str, Any]:
    """OHLCV for chart widgets (cache + live fallback)."""
    from ohlcv_cache import get_candles_range, upsert_candles

    symbol = symbol.upper()
    limit = max(30, min(limit, 1000))
    candles: list[dict[str, Any]] = []
    data_source = "cache"
    testnet_poor = False

    if use_cache:
        cached = get_candles_range(
            market=market,
            symbol=symbol,
            timeframe=interval,
            limit=limit,
        )
        if len(cached) >= 30:
            normalized = [_normalize_candle(c) for c in cached]
            if _cached_candles_usable(
                normalized, market=market, interval=interval, testnet=testnet
            ):
                candles = normalized

    if len(candles) < 30:
        live, live_source, live_poor = _fetch_live_candles(
            market=market,
            symbol=symbol,
            timeframe=interval,
            limit=limit,
            testnet=testnet,
        )
        testnet_poor = live_poor
        if live and _cache_is_fresh(live, market=market, interval=interval):
            candles = live
            data_source = live_source
            if live_source == "testnet":
                raw_for_cache = []
                for c in live:
                    raw_for_cache.append(
                        {
                            "t": datetime.fromtimestamp(c["time"], tz=timezone.utc)
                            .replace(microsecond=0)
                            .isoformat(),
                            "o": c["open"],
                            "h": c["high"],
                            "l": c["low"],
                            "c": c["close"],
                            "v": c["volume"],
                        }
                    )
                if raw_for_cache:
                    from ohlcv_cache import upsert_candles

                    upsert_candles(
                        market=market,
                        symbol=symbol,
                        timeframe=interval,
                        candles=raw_for_cache,
                    )
        elif live:
            candles = live
            data_source = live_source

    return {
        "status": "ok",
        "market": market,
        "symbol": symbol,
        "interval": interval,
        "count": len(candles),
        "candles": candles,
        "data_source": data_source,
        "testnet_poor": testnet_poor,
    }


def get_chart_indicators(
    *,
    market: str,
    symbol: str,
    interval: str = "4h",
    limit: int = 200,
    testnet: bool = True,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Indicator time series aligned with chart candles."""
    candle_resp = get_chart_candles(
        market=market,
        symbol=symbol,
        interval=interval,
        limit=limit,
        testnet=testnet,
        use_cache=use_cache,
    )
    candles = candle_resp.get("candles") or []
    if len(candles) < 30:
        return {
            "status": "error",
            "message": "insufficient_candles",
            "market": market,
            "symbol": symbol.upper(),
            "interval": interval,
            "series": {},
            "levels": {},
        }

    raw_candles = [
        {
            "t": c["time"],
            "o": c["open"],
            "h": c["high"],
            "l": c["low"],
            "c": c["close"],
            "v": c.get("volume", 0),
        }
        for c in candles
    ]
    series = compute_indicator_series(raw_candles)

    levels: dict[str, float] = {}
    if market == "crypto":
        rf = load_config("crypto_config").get("rule_filter", {})
        levels["rsi_oversold"] = float(rf.get("rsi_oversold", 35))
        levels["rsi_overbought"] = float(rf.get("rsi_overbought", 65))
    elif market == "securities":
        levels["rsi_oversold"] = 40.0
        levels["rsi_overbought"] = 60.0

    return {
        "status": "ok",
        "market": market,
        "symbol": symbol.upper(),
        "interval": interval,
        "series": series,
        "levels": levels,
        "data_source": candle_resp.get("data_source"),
        "testnet_poor": candle_resp.get("testnet_poor"),
    }



def _symbol_in_matched(matched_raw: str | None, sym: str, full_symbol: str) -> bool:
    if not matched_raw:
        return False
    try:
        parsed = json.loads(matched_raw)
        if isinstance(parsed, list):
            upper = {str(x).upper() for x in parsed}
            return sym in upper or full_symbol.upper() in upper
    except (json.JSONDecodeError, TypeError):
        pass
    matched = matched_raw.upper()
    return sym in matched or full_symbol.upper() in matched


def _news_markers_for_symbol(*, market: str, symbol: str, limit: int = 40) -> list[dict[str, Any]]:
    """Significant news as chart markers."""
    sym = symbol.upper().replace("USDT", "")
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        rows = conn.execute(
            """
            SELECT id, title, published_at, fetched_at, source_name, trust_score, matched_symbols
            FROM news_items
            WHERE (expires_at IS NULL OR expires_at > ?)
              AND matched_symbols IS NOT NULL
              AND verification_status IN ('verified', 'trusted', 'pending')
            ORDER BY COALESCE(published_at, fetched_at) DESC
            LIMIT ?
            """,
            (now, limit * 3),
        ).fetchall()
    finally:
        conn.close()

    out: list[dict[str, Any]] = []
    for row in rows:
        if not _symbol_in_matched(row["matched_symbols"], sym, symbol):
            continue
        when = row["published_at"] or row["fetched_at"]
        if not when:
            continue
        title = (row["title"] or "News")[:40]
        out.append(
            {
                "id": f"news-{row['id']}",
                "time": _to_unix_seconds(when),
                "event_at": when,
                "env": "news",
                "stage": "news",
                "decision": "info",
                "symbol": symbol,
                "kind": "news",
                "shape": "circle",
                "position": "aboveBar",
                "color": "#c778ff",
                "short_label": "NEWS",
                "text": "NEWS",
                "summary": title,
                "source": row["source_name"],
                "trust_score": row["trust_score"],
            }
        )
        if len(out) >= limit:
            break
    return out


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("payload_json") or "{}"
    try:
        return json.loads(raw) if isinstance(raw, str) else (raw or {})
    except json.JSONDecodeError:
        return {}


def _env_display(env: str | None) -> str:
    if env and env.lower() in ("live",):
        return "Live"
    return "Demo"


def _order_side(payload: dict[str, Any], decision: str | None) -> str:
    side = str(payload.get("side") or payload.get("action_side") or "").upper()
    if side in ("BUY", "SELL"):
        return side
    if payload.get("exit_reason"):
        return "SELL"
    if decision in ("sell", "error", "reject"):
        return "SELL"
    return "BUY"


def _marker_short_label(
    *,
    stage: str,
    decision: str | None,
    payload: dict[str, Any],
    kind: str,
) -> str:
    side = _order_side(payload, decision)
    if stage == "order":
        if decision in ("error", "reject"):
            return "FAIL"
        if side == "SELL" or payload.get("exit_reason"):
            return "SOLD"
        return "BUY"
    if stage == "fill":
        return "SOLD" if side == "SELL" else "BUY"
    if stage == "guardrails":
        if decision == "approve":
            return "OK"
        return "BLOCK"
    if stage == "filter":
        if decision == "approve":
            return "PASS"
        if decision == "reject":
            return "REJECT"
        return "SKIP"
    if stage == "llm":
        if decision == "approve":
            return "LLM+"
        if decision == "reject":
            return "LLM-"
        return "LLM"
    if stage == "risk":
        return "SIZE"
    if stage == "signal":
        return "SIGNAL"
    if kind == "news" or stage == "news":
        return "NEWS"
    if decision:
        return f"{stage[:4].upper()}".strip() or stage.upper()
    return stage.upper()[:6]


def _marker_summary(row: dict[str, Any], payload: dict[str, Any]) -> str:
    summary_row = {**row, "payload_json": json.dumps(payload, ensure_ascii=False)}
    base = summarize_trade_event(summary_row)
    extras: list[str] = []
    reject = row.get("reject_reason")
    if reject and str(reject) not in base:
        extras.append(str(reject))
    if payload.get("notional") is not None:
        extras.append(f"объём {payload['notional']} USDT")
    if payload.get("quantity") is not None:
        extras.append(f"qty {payload['quantity']}")
    hybrid = payload.get("hybrid_path")
    if hybrid:
        extras.append(f"путь: {hybrid}")
    reasoning = payload.get("llm_reasoning") or payload.get("reasoning")
    if reasoning:
        extras.append(str(reasoning)[:160])
    rule = payload.get("rule_name")
    if rule:
        extras.append(f"правило: {rule}")
    exit_reason = payload.get("exit_reason")
    if exit_reason:
        extras.append(f"выход: {exit_reason}")
    conf = row.get("confidence")
    if conf is not None and "уверенность" not in base.lower():
        try:
            extras.append(f"confidence {float(conf):.0%}")
        except (TypeError, ValueError):
            pass
    if extras:
        return f"{base} · {' · '.join(extras)}"
    return base


def _marker_label(
    *,
    stage: str,
    decision: str | None,
    env: str | None,
    payload: dict[str, Any],
    kind: str,
) -> str:
    """Legacy combined label — prefer short_label in API."""
    return _marker_short_label(stage=stage, decision=decision, payload=payload, kind=kind)


def _marker_visual(stage: str, decision: str | None, payload: dict[str, Any]) -> dict[str, str]:
    side = _order_side(payload, decision)
    if stage == "signal":
        return {"kind": "signal", "shape": "circle", "position": "belowBar", "color": "#6e7681"}
    if stage == "filter":
        if decision == "approve":
            return {"kind": "filter_pass", "shape": "circle", "position": "belowBar", "color": "#6e7681"}
        if decision == "reject":
            return {"kind": "filter_reject", "shape": "square", "position": "aboveBar", "color": "#8b949e"}
        return {"kind": "filter_skip", "shape": "square", "position": "aboveBar", "color": "#8b949e"}
    if stage == "llm":
        if decision == "approve":
            return {"kind": "llm_approve", "shape": "arrowUp", "position": "belowBar", "color": "#3dd68c"}
        return {"kind": "llm_reject", "shape": "square", "position": "aboveBar", "color": "#ff6b6b"}
    if stage == "guardrails":
        if decision == "approve":
            return {"kind": "guardrails_ok", "shape": "circle", "position": "belowBar", "color": "#3dd68c"}
        return {"kind": "guardrails_block", "shape": "square", "position": "aboveBar", "color": "#f0a030"}
    if stage == "order":
        if side == "SELL" or payload.get("exit_reason"):
            return {"kind": "order_sell", "shape": "arrowDown", "position": "aboveBar", "color": "#ff6b6b"}
        if decision in ("error", "reject"):
            return {"kind": "order_fail", "shape": "square", "position": "aboveBar", "color": "#ff6b6b"}
        return {"kind": "order_buy", "shape": "arrowUp", "position": "belowBar", "color": "#3dd68c"}
    if stage == "fill":
        if side == "SELL":
            return {"kind": "fill_sell", "shape": "arrowDown", "position": "aboveBar", "color": "#e8c547"}
        return {"kind": "fill_buy", "shape": "arrowUp", "position": "belowBar", "color": "#e8c547"}
    if stage == "risk":
        return {"kind": "risk", "shape": "circle", "position": "belowBar", "color": "#9b7ede"}
    return {"kind": stage, "shape": "circle", "position": "inBar", "color": "#6e7681"}


def get_chart_markers(
    *,
    market: str,
    symbol: str,
    env: str | None = None,
    from_time: str | None = None,
    to_time: str | None = None,
    limit: int = 200,
    include_news: bool = False,
) -> dict[str, Any]:
    """Trade pipeline markers for chart overlay."""
    run_migrations()
    symbol = symbol.upper()
    conn = get_connection()
    try:
        query = """
            SELECT e.id, e.event_at, e.env, e.stage, e.symbol, e.decision,
                   e.confidence, e.reject_reason, e.workflow_name, e.inputs_hash,
                   e.model, e.latency_ms, e.payload_json,
                   l.counter_thesis, l.parsed_action AS llm_action
            FROM trade_events e
            LEFT JOIN llm_decisions l ON l.trade_event_id = e.id
            WHERE e.market = ? AND UPPER(COALESCE(e.symbol, '')) = ?
              AND e.stage IN ({})
        """.format(",".join("?" * len(MARKER_STAGES)))
        params: list[Any] = [market, symbol, *MARKER_STAGES]
        if env:
            query += " AND e.env = ?"
            params.append(env)
        if from_time:
            query += " AND e.event_at >= ?"
            params.append(from_time)
        if to_time:
            query += " AND e.event_at <= ?"
            params.append(to_time)
        query += " ORDER BY e.event_at ASC LIMIT ?"
        params.append(max(1, min(limit, 500)))
        rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    finally:
        conn.close()

    markers: list[dict[str, Any]] = []
    for row in rows:
        payload = _payload(row)
        vis = _marker_visual(row["stage"], row.get("decision"), payload)
        short = _marker_short_label(
            stage=row["stage"],
            decision=row.get("decision"),
            payload=payload,
            kind=vis["kind"],
        )
        summary = _marker_summary(row, payload)
        env_tag = _env_display(row.get("env"))
        if env_tag and env_tag not in summary:
            summary = f"[{env_tag}] {summary}"

        markers.append(
            {
                "id": row["id"],
                "time": _to_unix_seconds(row["event_at"]),
                "event_at": row["event_at"],
                "env": row["env"],
                "stage": row["stage"],
                "decision": row.get("decision"),
                "symbol": row.get("symbol"),
                "confidence": row.get("confidence"),
                "reject_reason": row.get("reject_reason"),
                "workflow_name": row.get("workflow_name"),
                "inputs_hash": row.get("inputs_hash"),
                "model": row.get("model"),
                "latency_ms": row.get("latency_ms"),
                "counter_thesis": row.get("counter_thesis"),
                "kind": vis["kind"],
                "shape": vis["shape"],
                "position": vis["position"],
                "color": vis["color"],
                "short_label": short,
                "text": short,
                "summary": summary[:500],
                "payload": payload,
            }
        )


    if include_news:
        markers.extend(_news_markers_for_symbol(market=market, symbol=symbol, limit=40))

    return {
        "status": "ok",
        "market": market,
        "symbol": symbol,
        "env": env,
        "count": len(markers),
        "markers": markers,
    }


def list_symbols_for_market(market: str) -> list[str]:
    try:
        return symbols_for_market(market)
    except Exception:
        if market == "crypto":
            return list(load_config("crypto_config").get("pairs", []))
        sec = load_config("securities_config")
        tickers = []
        dca = sec.get("index_dca", {}).get("ticker")
        if dca:
            tickers.append(dca)
        for t in sec.get("swing_signals", {}).get("universe", []):
            if t not in tickers:
                tickers.append(t)
        return tickers or ["SBER", "GAZP"]
