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


def moex_iss_interval(timeframe: str) -> int:
    """Map UI timeframe to MOEX ISS candle interval (minutes as int: 10, 60, 24)."""
    tf = str(timeframe).strip().lower()
    if tf in ("1d", "24h", "d"):
        return 24
    if tf in ("10m",):
        return 10
    return 60


def resample_ohlcv(candles: list[dict[str, Any]], bucket_seconds: int) -> list[dict[str, Any]]:
    """Aggregate OHLCV rows (keys: t/time, o/open, h/high, l/low, c/close, v/volume)."""
    if bucket_seconds <= 0 or len(candles) < 2:
        return candles

    def _time(row: dict[str, Any]) -> int:
        raw = row.get("time", row.get("t"))
        if isinstance(raw, (int, float)):
            val = float(raw)
            return int(val / 1000) if val > 1e12 else int(val)
        if isinstance(raw, str) and raw.isdigit():
            val = float(raw)
            return int(val / 1000) if val > 1e12 else int(val)
        return int(_parse_dt(str(raw)).timestamp())

    def _float(row: dict[str, Any], key: str, alt: str) -> float:
        return float(row.get(key, row.get(alt, 0)))

    buckets: dict[int, list[dict[str, Any]]] = {}
    for row in sorted(candles, key=_time):
        key = (_time(row) // bucket_seconds) * bucket_seconds
        buckets.setdefault(key, []).append(row)

    out: list[dict[str, Any]] = []
    for key in sorted(buckets):
        grp = buckets[key]
        out.append(
            {
                "t": key,
                "o": _float(grp[0], "open", "o"),
                "h": max(_float(x, "high", "h") for x in grp),
                "l": min(_float(x, "low", "l") for x in grp),
                "c": _float(grp[-1], "close", "c"),
                "v": sum(_float(x, "volume", "v") for x in grp),
            }
        )
    return out


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
        from_dt = (till_dt - timedelta(days=max(limit + 10, 30))).strftime("%Y-%m-%d")
    else:
        from_dt = (till_dt - timedelta(hours=max(limit + 24, 72))).strftime("%Y-%m-%d")

    url = (
        f"https://iss.moex.com/iss/engines/stock/markets/shares/"
        f"boards/TQBR/securities/{secid.upper()}/candles.json"
    )
    cols: list[str] = []
    all_rows: list[list[Any]] = []
    start = 0
    page_size = 0

    with httpx.Client(timeout=45) as client:
        while True:
            resp = client.get(
                url,
                params={
                    "interval": interval,
                    "from": from_dt,
                    "till": till,
                    "start": start,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            block = data.get("candles") or {}
            if not cols:
                cols = list(block.get("columns") or [])
            rows = block.get("data") or []
            if not rows:
                break
            all_rows.extend(rows)
            if page_size == 0:
                page_size = len(rows)
            start += len(rows)
            if len(rows) < page_size:
                break
            if start > 50_000:
                break

    candles: list[dict[str, float]] = []
    for row in all_rows:
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
        iss_interval = moex_iss_interval(timeframe)
        fetch_limit = limit * 4 if str(timeframe).strip().lower() == "4h" else limit
        candles = fetch_moex_candles_as_of(
            symbol,
            interval=iss_interval,
            as_of=as_of,
            limit=fetch_limit,
        )
        if str(timeframe).strip().lower() == "4h":
            candles = resample_ohlcv(candles, 4 * 3600)
            if limit > 0 and len(candles) > limit:
                candles = candles[-limit:]

    if use_cache and candles:
        upsert_candles(market=market, symbol=symbol, timeframe=tf_key, candles=candles)
    return candles
