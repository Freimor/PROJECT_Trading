"""Per-workflow session stats since automation start (for status bar)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx

from db.connection import get_connection
from effective_config import get_guardrails
from risk_profile_service import get_max_open_positions
from risk_trading_state import count_open_positions
from workflow_universe_service import resolve_workflow_for_universe

_ORDER_OK = ("submitted", "execute", "executed", "approve")


def _direction_from_delta(delta: float | None) -> str:
    if delta is None:
        return "flat"
    if delta > 0:
        return "up"
    if delta < 0:
        return "down"
    return "flat"


def _pct_from_delta(delta: float, base: float) -> float | None:
    if base <= 0:
        return None
    return round(delta / base * 100, 2)


def _parse_payload(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _fetch_crypto_last_prices(symbols: set[str]) -> dict[str, float]:
    if not symbols:
        return {}
    from binance_client import _credentials

    _, _, base_url = _credentials(testnet=True)
    prices: dict[str, float] = {}
    try:
        with httpx.Client(timeout=12) as client:
            resp = client.get(f"{base_url}/api/v3/ticker/price")
            if resp.status_code == 200:
                for row in resp.json():
                    sym = str(row.get("symbol", ""))
                    if sym in symbols:
                        prices[sym] = float(row.get("price", 0) or 0)
    except Exception:
        pass
    return prices


def _compute_session_trade_pnl(
    conn,
    market: str,
    *,
    wf_clause: str,
    params: list[Any],
) -> dict[str, Any]:
    """Unrealized PnL on orders submitted since session start (not wallet delta)."""
    currency = "USDT" if market == "crypto" else "RUB"
    ok_ph = ",".join("?" for _ in _ORDER_OK)
    rows = conn.execute(
        f"""
        SELECT o.symbol, o.notional AS order_notional, o.inputs_hash,
               r.notional AS risk_notional, r.payload_json AS risk_json
        FROM trade_events o
        LEFT JOIN trade_events r
          ON r.market = o.market AND r.inputs_hash = o.inputs_hash AND r.stage = 'risk'
        WHERE o.market = ? AND o.event_at >= ?
          AND o.stage = 'order' AND o.decision IN ({ok_ph})
        {wf_clause}
        ORDER BY o.event_at ASC
        """,
        params,
    ).fetchall()

    if not rows:
        return {
            "pnl_delta": 0.0,
            "pnl_pct": 0.0,
            "pnl_direction": "flat",
            "currency": currency,
            "invested_notional": 0.0,
            "pnl_source": "session_trades",
        }

    symbols: set[str] = set()
    legs: list[dict[str, float | str]] = []
    invested = 0.0

    for row in rows:
        symbol = row["symbol"]
        if not symbol:
            continue
        risk = _parse_payload(row["risk_json"])
        notional = row["order_notional"] or row["risk_notional"] or risk.get("notional")
        try:
            notional_f = float(notional) if notional is not None else 0.0
        except (TypeError, ValueError):
            notional_f = 0.0
        if notional_f > 0:
            invested += notional_f

        qty = risk.get("quantity")
        entry = risk.get("entry_price")
        try:
            qty_f = float(qty) if qty is not None else 0.0
            entry_f = float(entry) if entry is not None else 0.0
        except (TypeError, ValueError):
            continue
        if qty_f <= 0 or entry_f <= 0:
            continue
        symbols.add(str(symbol))
        legs.append(
            {
                "symbol": str(symbol),
                "qty": qty_f,
                "entry": entry_f,
                "notional": notional_f or round(qty_f * entry_f, 2),
            }
        )

    prices: dict[str, float] = {}
    if market == "crypto" and symbols:
        prices = _fetch_crypto_last_prices(symbols)

    unrealized = 0.0
    mark_base = 0.0
    for leg in legs:
        sym = str(leg["symbol"])
        qty_f = float(leg["qty"])
        entry_f = float(leg["entry"])
        leg_notional = float(leg["notional"])
        current = prices.get(sym)
        if current and current > 0:
            unrealized += (current - entry_f) * qty_f
            mark_base += leg_notional
        elif leg_notional > 0:
            mark_base += leg_notional

    pnl_delta = round(unrealized, 2)
    base = mark_base or invested
    pnl_pct = _pct_from_delta(pnl_delta, base) if base > 0 else 0.0

    return {
        "pnl_delta": pnl_delta,
        "pnl_pct": pnl_pct if pnl_pct is not None else 0.0,
        "pnl_direction": _direction_from_delta(pnl_delta),
        "currency": currency,
        "invested_notional": round(invested, 2),
        "pnl_source": "session_trades",
    }


def _workflow_event_names(workflow_name: str | None) -> list[str] | None:
    if not workflow_name:
        return None
    canonical = resolve_workflow_for_universe(workflow_name)
    names = {workflow_name, canonical}
    if canonical.startswith("crypto-scalp-hybrid"):
        names.add("crypto-scalp-auto")
    if canonical == "crypto-signal-paper":
        names.add("crypto-paper-auto")
    return sorted(names)


def get_workflow_session_stats(
    market: str,
    *,
    started_at: str | None,
    active_workflow: str | None = None,
    workflow_pnl: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Activity counters and session trade PnL since workflow_started_at."""
    if not started_at:
        return {"status": "inactive"}

    wf_names = _workflow_event_names(active_workflow)
    conn = get_connection()
    try:
        params: list[Any] = [market, started_at]
        wf_clause = ""
        if wf_names:
            placeholders = ",".join("?" for _ in wf_names)
            wf_clause = f" AND workflow_name IN ({placeholders})"
            params.extend(wf_names)

        signals = conn.execute(
            f"""
            SELECT COUNT(*) AS c FROM trade_events
            WHERE market = ? AND event_at >= ? AND stage = 'signal'
            {wf_clause}
            """,
            params,
        ).fetchone()["c"]

        orders_ok = conn.execute(
            f"""
            SELECT COUNT(*) AS c FROM trade_events
            WHERE market = ? AND event_at >= ? AND stage = 'order'
              AND decision IN ('submitted','execute','executed','approve')
            {wf_clause}
            """,
            params,
        ).fetchone()["c"]

        orders_failed = conn.execute(
            f"""
            SELECT COUNT(*) AS c FROM trade_events
            WHERE market = ? AND event_at >= ? AND stage = 'order'
              AND decision IN ('error','reject')
            {wf_clause}
            """,
            params,
        ).fetchone()["c"]

        last = conn.execute(
            f"""
            SELECT event_at, symbol, stage, decision, reject_reason
            FROM trade_events
            WHERE market = ? AND event_at >= ?
            {wf_clause}
            ORDER BY event_at DESC
            LIMIT 1
            """,
            params,
        ).fetchone()

        trade_pnl = _compute_session_trade_pnl(conn, market, wf_clause=wf_clause, params=params)
    finally:
        conn.close()

    guardrails = get_guardrails()
    trading = guardrails.get("trading", {})
    open_positions = count_open_positions(market)
    max_open = get_max_open_positions(market, trading)

    _ = workflow_pnl  # wallet PnL kept on workflow_pnl; session strip uses trade PnL only

    last_event_at = last["event_at"] if last else None
    ago_sec: int | None = None
    if last_event_at:
        try:
            ts = datetime.fromisoformat(str(last_event_at).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            ago_sec = max(0, int((datetime.now(timezone.utc) - ts).total_seconds()))
        except ValueError:
            ago_sec = None

    return {
        "status": "ok",
        "started_at": started_at,
        "active_workflow": active_workflow,
        "signals": int(signals or 0),
        "orders_ok": int(orders_ok or 0),
        "orders_failed": int(orders_failed or 0),
        "open_positions": open_positions,
        "max_open_positions": max_open,
        "pnl_delta": trade_pnl.get("pnl_delta"),
        "pnl_pct": trade_pnl.get("pnl_pct"),
        "pnl_direction": trade_pnl.get("pnl_direction", "flat"),
        "currency": trade_pnl.get("currency"),
        "invested_notional": trade_pnl.get("invested_notional"),
        "pnl_source": trade_pnl.get("pnl_source"),
        "last_event_at": last_event_at,
        "last_event_ago_sec": ago_sec,
        "last_event_symbol": last["symbol"] if last else None,
        "last_event_stage": last["stage"] if last else None,
        "last_event_decision": last["decision"] if last else None,
        "last_event_reject_reason": last["reject_reason"] if last else None,
    }
