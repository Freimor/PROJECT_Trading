"""Historical and live market data for benchmarks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from binance_client import _credentials, fetch_klines
from indicators.technical import parse_binance_klines

_MSK = ZoneInfo("Europe/Moscow")


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def fetch_crypto_klines_as_of(
    symbol: str,
    *,
    interval: str = "4h",
    as_of: str,
    limit: int = 250,
    testnet: bool = False,
) -> list[dict[str, float]]:
    """Binance klines ending at as_of (inclusive bar selection done by caller)."""
    end_ms = int(_parse_dt(as_of).timestamp() * 1000)
    _, _, base = _credentials(testnet)
    url = f"{base}/api/v3/klines"
    with httpx.Client(timeout=45) as client:
        resp = client.get(
            url,
            params={
                "symbol": symbol,
                "interval": interval,
                "endTime": end_ms,
                "limit": min(limit, 1000),
            },
        )
        resp.raise_for_status()
        raw = resp.json()
    return parse_binance_klines(raw)


def _moex_begin_to_iso(begin: Any) -> str:
    """Normalize MOEX ISS `begin` to UTC ISO string."""
    if begin is None:
        return ""
    if isinstance(begin, (int, float)):
        val = float(begin)
        ts = val / 1000 if val > 1e12 else val
        return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=0).isoformat()
    s = str(begin).strip()
    if s.isdigit():
        val = float(s)
        ts = val / 1000 if val > 1e12 else val
        return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=0).isoformat()
    dt = datetime.fromisoformat(s.replace(" ", "T"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_MSK)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def fetch_moex_candles_as_of(
    secid: str,
    *,
    interval: int = 24,
    as_of: str,
    limit: int = 120,
) -> list[dict[str, float]]:
    """MOEX ISS candles ending at as_of (recent window, not history from 2009)."""
    till_dt = _parse_dt(as_of)
    till = till_dt.strftime("%Y-%m-%d")
    if interval >= 24:
        from_dt = (till_dt - timedelta(days=max(limit * 2, 30))).strftime("%Y-%m-%d")
    else:
        from_dt = (till_dt - timedelta(hours=max(limit * 2, 48))).strftime("%Y-%m-%d")

    url = (
        f"https://iss.moex.com/iss/engines/stock/markets/shares/"
        f"boards/TQBR/securities/{secid.upper()}/candles.json"
    )
    with httpx.Client(timeout=45) as client:
        resp = client.get(
            url,
            params={"interval": interval, "from": from_dt, "till": till},
        )
        resp.raise_for_status()
        data = resp.json()
    cols = data["candles"]["columns"]
    rows = data["candles"]["data"]
    candles: list[dict[str, float]] = []
    for row in rows:
        rec = dict(zip(cols, row))
        candles.append(
            {
                "t": _moex_begin_to_iso(rec.get("begin")),
                "o": float(rec.get("open", 0)),
                "h": float(rec.get("high", 0)),
                "l": float(rec.get("low", 0)),
                "c": float(rec.get("close", 0)),
                "v": float(rec.get("volume", 0)),
            }
        )
    if limit > 0 and len(candles) > limit:
        candles = candles[-limit:]
    return candles


def candles_for_benchmark(
    *,
    market: str,
    symbol: str,
    timeframe: str,
    as_of: str,
    limit: int = 250,
    use_cache: bool = True,
) -> list[dict[str, float]]:
    """Fetch candles for historical benchmark; optionally read/write ohlcv cache."""
    from ohlcv_cache import get_candles_before, upsert_candles

    tf_key = timeframe
    if use_cache:
        cached = get_candles_before(
            market=market,
            symbol=symbol,
            timeframe=tf_key,
            as_of=as_of,
            limit=limit,
        )
        if len(cached) >= 60:
            return cached

    if market == "crypto":
        candles = fetch_crypto_klines_as_of(
            symbol,
            interval=timeframe,
            as_of=as_of,
            limit=limit,
        )
    else:
        interval = 24 if timeframe in ("1d", "24h", "d") else 60
        candles = fetch_moex_candles_as_of(
            symbol,
            interval=interval,
            as_of=as_of,
            limit=limit,
        )

    if use_cache and candles:
        upsert_candles(market=market, symbol=symbol, timeframe=tf_key, candles=candles)
    return candles
