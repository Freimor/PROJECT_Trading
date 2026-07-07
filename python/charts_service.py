"""Chart data for admin console — OHLCV candles and trade/LLM markers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from binance_client import fetch_klines
from config_loader import load_config
from db.connection import get_connection
from db.migrate import run_migrations
from indicators.technical import parse_binance_klines
from market_data import fetch_moex_candles_as_of
from strategy_service import symbols_for_market

MARKER_STAGES = ("llm", "guardrails", "order", "fill", "risk")


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


def _fetch_live_candles(
    *,
    market: str,
    symbol: str,
    timeframe: str,
    limit: int,
    testnet: bool,
) -> list[dict[str, Any]]:
    if market == "crypto":
        raw = fetch_klines(symbol, timeframe, limit=min(limit, 1000), testnet=testnet)
        parsed = parse_binance_klines(raw)
        return [_normalize_candle(c) for c in parsed]

    as_of = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    interval = 24 if timeframe in ("1d", "24h", "d") else 60
    moex = fetch_moex_candles_as_of(symbol, interval=interval, as_of=as_of, limit=limit)
    return [_normalize_candle(c) for c in moex]


def _cache_is_fresh(candles: list[dict[str, Any]], *, max_age_seconds: int = 7 * 86400) -> bool:
    if not candles:
        return False
    newest = max(c["time"] for c in candles)
    threshold = int(datetime.now(timezone.utc).timestamp()) - max_age_seconds
    return newest >= threshold


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

    if use_cache:
        cached = get_candles_range(
            market=market,
            symbol=symbol,
            timeframe=interval,
            limit=limit,
        )
        if len(cached) >= 30:
            normalized = [_normalize_candle(c) for c in cached]
            if _cache_is_fresh(normalized):
                candles = normalized

    if len(candles) < 30:
        live = _fetch_live_candles(
            market=market,
            symbol=symbol,
            timeframe=interval,
            limit=limit,
            testnet=testnet,
        )
        if live:
            candles = live
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

    return {
        "status": "ok",
        "market": market,
        "symbol": symbol,
        "interval": interval,
        "count": len(candles),
        "candles": candles,
    }



def _news_markers_for_symbol(*, market: str, symbol: str, limit: int = 40) -> list[dict[str, Any]]:
    """Significant news as chart markers."""
    sym = symbol.upper().replace("USDT", "")
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        rows = conn.execute(
            """
            SELECT id, title, published_at, source_name, trust_score, matched_symbols
            FROM news_items
            WHERE (expires_at IS NULL OR expires_at > ?)
              AND matched_symbols IS NOT NULL
              AND verification_status IN ('verified', 'trusted', 'pending')
            ORDER BY published_at DESC
            LIMIT ?
            """,
            (now, limit * 3),
        ).fetchall()
    finally:
        conn.close()

    out: list[dict[str, Any]] = []
    for row in rows:
        matched = (row["matched_symbols"] or "").upper()
        if sym not in matched and symbol.upper() not in matched:
            continue
        title = (row["title"] or "News")[:40]
        out.append(
            {
                "id": f"news-{row['id']}",
                "time": _to_unix_seconds(row["published_at"]),
                "event_at": row["published_at"],
                "env": "news",
                "stage": "news",
                "decision": "info",
                "symbol": symbol,
                "kind": "news",
                "shape": "circle",
                "position": "aboveBar",
                "color": "#c778ff",
                "text": title[:24],
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


def _marker_visual(stage: str, decision: str | None, payload: dict[str, Any]) -> dict[str, str]:
    side = (payload.get("side") or payload.get("action_side") or "").lower()
    if stage == "llm":
        if decision == "approve":
            return {"kind": "llm_approve", "shape": "arrowUp", "position": "belowBar", "color": "#3dd68c"}
        return {"kind": "llm_reject", "shape": "circle", "position": "aboveBar", "color": "#8b949e"}
    if stage == "guardrails":
        return {"kind": "guardrails_block", "shape": "square", "position": "aboveBar", "color": "#f0a030"}
    if stage == "order":
        if side == "sell" or decision in ("sell", "execute"):
            return {"kind": "order_sell", "shape": "arrowDown", "position": "aboveBar", "color": "#5b9cf5"}
        return {"kind": "order_buy", "shape": "arrowUp", "position": "belowBar", "color": "#5b9cf5"}
    if stage == "fill":
        if side == "sell":
            return {"kind": "fill_sell", "shape": "arrowDown", "position": "aboveBar", "color": "#e8c547"}
        return {"kind": "fill_buy", "shape": "arrowUp", "position": "belowBar", "color": "#e8c547"}
    if stage == "risk":
        return {"kind": "risk", "shape": "circle", "position": "inBar", "color": "#9b7ede"}
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
        label = row["stage"]
        if row.get("decision"):
            label = f"{row['stage']}/{row['decision']}"
        if row.get("confidence") is not None:
            label += f" {row['confidence']:.2f}"

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
                "text": label[:24],
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
