"""OHLCV cache — local store for historical benchmark replay."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from db.connection import get_connection
from db.migrate import run_migrations


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def upsert_candles(
    *,
    market: str,
    symbol: str,
    timeframe: str,
    candles: list[dict[str, Any]],
) -> int:
    """Store candles in ohlcv_candles (INSERT OR REPLACE)."""
    run_migrations()
    if not candles:
        return 0
    conn = get_connection()
    n = 0
    try:
        for c in candles:
            t = c.get("t")
            if t is None:
                continue
            candle_time = t if isinstance(t, str) else datetime.fromtimestamp(
                int(t) / 1000, tz=timezone.utc
            ).replace(microsecond=0).isoformat()
            conn.execute(
                """
                INSERT OR REPLACE INTO ohlcv_candles
                    (market, symbol, timeframe, candle_time, open, high, low, close, volume, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    market,
                    symbol.upper(),
                    timeframe,
                    candle_time,
                    float(c.get("o", 0)),
                    float(c.get("h", 0)),
                    float(c.get("l", 0)),
                    float(c.get("c", 0)),
                    float(c.get("v", 0)),
                ),
            )
            n += 1
        conn.commit()
    finally:
        conn.close()
    return n


def get_candles_before(
    *,
    market: str,
    symbol: str,
    timeframe: str,
    as_of: str,
    limit: int = 250,
) -> list[dict[str, float]]:
    """Candles with candle_time <= as_of, oldest-first."""
    run_migrations()
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT candle_time AS t, open AS o, high AS h, low AS l, close AS c, volume AS v
            FROM ohlcv_candles
            WHERE market = ? AND symbol = ? AND timeframe = ? AND candle_time <= ?
            ORDER BY candle_time DESC
            LIMIT ?
            """,
            (market, symbol.upper(), timeframe, as_of, limit),
        ).fetchall()
        out = [dict(r) for r in reversed(rows)]
        return out
    finally:
        conn.close()


def get_candles_range(
    *,
    market: str,
    symbol: str,
    timeframe: str,
    limit: int = 250,
    from_time: str | None = None,
    to_time: str | None = None,
) -> list[dict[str, Any]]:
    """Candles oldest-first, optional time bounds on candle_time."""
    run_migrations()
    conn = get_connection()
    try:
        query = """
            SELECT candle_time AS t, open AS o, high AS h, low AS l, close AS c, volume AS v
            FROM ohlcv_candles
            WHERE market = ? AND symbol = ? AND timeframe = ?
        """
        params: list[Any] = [market, symbol.upper(), timeframe]
        if from_time:
            query += " AND candle_time >= ?"
            params.append(from_time)
        if to_time:
            query += " AND candle_time <= ?"
            params.append(to_time)
        query += " ORDER BY candle_time DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in reversed(rows)]
    finally:
        conn.close()
