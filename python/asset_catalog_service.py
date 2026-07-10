"""Asset search for workflow universe UI."""

from __future__ import annotations

import os
from typing import Any, Literal

from config_loader import load_config
from effective_config import get_guardrails

Market = Literal["crypto", "securities"]

# Common Binance USDT pairs for search (not all are tradable without guardrails).
CRYPTO_CATALOG = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "ADAUSDT",
    "DOGEUSDT",
    "AVAXUSDT",
    "DOTUSDT",
    "LINKUSDT",
    "MATICUSDT",
    "LTCUSDT",
    "TRXUSDT",
    "ATOMUSDT",
    "NEARUSDT",
    "APTUSDT",
    "ARBUSDT",
    "OPUSDT",
    "SUIUSDT",
    "TONUSDT",
]


def _crypto_catalog() -> list[str]:
    guard = get_guardrails().get("symbols", {})
    symbols: set[str] = set(CRYPTO_CATALOG)
    symbols.update(str(s).upper() for s in guard.get("crypto_whitelist", []))
    try:
        symbols.update(str(s).upper() for s in load_config("crypto_config").get("pairs", []))
    except FileNotFoundError:
        pass
    return sorted(symbols)


def _securities_catalog() -> list[str]:
    guard = get_guardrails().get("symbols", {})
    symbols: set[str] = set(str(s).upper() for s in guard.get("moex_whitelist", []))
    try:
        sec = load_config("securities_config")
        symbols.add(str(sec.get("index_dca", {}).get("ticker", "")).upper())
        symbols.update(str(s).upper() for s in sec.get("swing_signals", {}).get("universe", []))
    except FileNotFoundError:
        pass
    return sorted(s for s in symbols if s)


def search_assets(market: Market, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
    q = query.strip().upper()
    if not q:
        return []

    if market == "crypto":
        pool = _crypto_catalog()
        matches = [s for s in pool if q in s]
        return [{"symbol": s, "market": market, "label": s} for s in matches[:limit]]

    # securities
    pool = _securities_catalog()
    matches = [s for s in pool if q in s]
    results = [{"symbol": s, "market": market, "label": s} for s in matches[:limit]]

    if len(results) < limit and len(q) >= 2:
        tinvest = _tinvest_search(q, limit=limit - len(results))
        seen = {r["symbol"] for r in results}
        for row in tinvest:
            if row["symbol"] not in seen:
                results.append(row)
                seen.add(row["symbol"])
    return results[:limit]


def _tinvest_search(query: str, *, limit: int) -> list[dict[str, Any]]:
    token = os.environ.get("TINKOFF_SANDBOX_TOKEN") or os.environ.get("TINKOFF_TOKEN")
    if not token:
        return []
    try:
        from bridges.tinvest_rest import TinvestRestClient

        client = TinvestRestClient(token, sandbox=True)
        data = client._post(
            "/tinkoff.public.invest.api.contract.v1.InstrumentsService/FindInstrument",
            {"query": query},
        )
        out: list[dict[str, Any]] = []
        for inst in data.get("instruments") or []:
            ticker = str(inst.get("ticker", "")).upper()
            if not ticker or inst.get("classCode") not in (None, "", "TQBR"):
                cc = str(inst.get("classCode", ""))
                if cc and cc != "TQBR":
                    continue
            name = str(inst.get("name") or ticker)
            out.append(
                {
                    "symbol": ticker,
                    "market": "securities",
                    "label": f"{ticker} — {name}",
                    "class_code": inst.get("classCode"),
                }
            )
            if len(out) >= limit:
                break
        return out
    except Exception:
        return []
