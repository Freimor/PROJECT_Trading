"""Per-automation wallet equity curve from session trades (stablecoin / RUB)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from db.connection import get_connection

_ORDER_OK = ("execute", "executed", "submitted", "approve")


def _to_unix_seconds(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        ts = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return int(ts.timestamp())
    except ValueError:
        return None


def _parse_payload(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        data = json.loads(str(raw))
        return data if isinstance(data, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _order_side(payload: dict[str, Any], *, row_decision: str | None = None) -> str:
    side = str(payload.get("side") or "").upper()
    if side in ("BUY", "SELL"):
        return side
    if payload.get("exit_reason"):
        return "SELL"
    if str(row_decision or "").lower() in ("sell",):
        return "SELL"
    return "BUY"


def _order_qty(payload: dict[str, Any]) -> float:
    for key in ("executedQty", "origQty", "qty", "quantity"):
        val = payload.get(key)
        if val is None:
            scalp = payload.get("scalp")
            if isinstance(scalp, dict):
                val = scalp.get("quantity") or scalp.get("qty")
        if val is None:
            continue
        try:
            q = float(val)
            if q > 0:
                return q
        except (TypeError, ValueError):
            pass
    return 0.0


def _order_price(payload: dict[str, Any], *, notional: float | None, qty: float) -> float | None:
    for key in ("price", "avgPrice", "exit_price", "entry_price"):
        val = payload.get(key)
        if val is None:
            scalp = payload.get("scalp")
            if isinstance(scalp, dict):
                val = scalp.get("entry_price")
        if val is None:
            continue
        try:
            p = float(val)
            if p > 0:
                return p
        except (TypeError, ValueError):
            pass
    if notional and qty > 0:
        return notional / qty
    return None


def resolve_order_notional(row: dict[str, Any], payload: dict[str, Any] | None = None) -> float | None:
    """Notional in quote currency (USDT / RUB) for feed and reports."""
    payload = payload if payload is not None else _parse_payload(row.get("payload_json"))
    raw = row.get("notional")
    try:
        if raw is not None:
            n = float(raw)
            if n > 0:
                return round(n, 2)
    except (TypeError, ValueError):
        pass
    qty = _order_qty(payload)
    price = _order_price(payload, notional=None, qty=qty)
    if qty > 0 and price and price > 0:
        return round(qty * price, 2)
    return None


def format_order_activity_message(
    *,
    symbol: str,
    side: str,
    notional: float | None,
    currency: str,
    market: str = "crypto",
) -> str:
    unit = "₽" if currency.upper() in ("RUB", "RUR") else currency
    sym = symbol or "?"
    if notional and notional > 0:
        amount = f"{notional:,.2f}".replace(",", " ").rstrip("0").rstrip(".")
        if side == "SELL":
            return f"Продажа {sym} на {amount} {unit}"
        return f"Покупка {sym} на {amount} {unit}"
    if side == "SELL":
        return f"Продажа {sym}"
    return f"Покупка {sym}"


def _fetch_session_orders(
    *,
    market: str,
    symbols: list[str],
    workflow_name: str,
    started_at: str,
) -> list[dict[str, Any]]:
    if not started_at or not symbols or not workflow_name:
        return []
    placeholders = ",".join("?" for _ in symbols)
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT event_at, symbol, decision, notional, currency, payload_json
            FROM trade_events
            WHERE market = ?
              AND event_at >= ?
              AND UPPER(COALESCE(symbol, '')) IN ({placeholders})
              AND workflow_name = ?
              AND stage = 'order'
              AND decision IN ({",".join("?" * len(_ORDER_OK))})
            ORDER BY event_at ASC
            """,
            (
                market,
                started_at,
                *[s.upper() for s in symbols],
                workflow_name,
                *_ORDER_OK,
            ),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def _current_mark_price(market: str, symbol: str) -> float | None:
    sym = symbol.upper()
    if market == "crypto":
        try:
            from binance_trading import get_market_price
            from effective_config import get_config_effective

            cfg = get_config_effective("crypto_config")
            return get_market_price(sym, testnet=True, cfg=cfg)
        except Exception:
            return None
    try:
        from bridges.tinvest_bridge import _moex_last_price

        px = _moex_last_price(sym)
        return px if px and px > 0 else None
    except Exception:
        return None


def build_automation_equity_curve(
    inst: dict[str, Any],
    *,
    market: str,
    symbols: list[str] | None = None,
) -> dict[str, Any]:
    """Wallet value in quote currency over session trades (cash + marked position)."""
    currency = "RUB" if market == "securities" else "USDT"
    sym_list = symbols or [str(inst.get("symbol") or "").upper()]
    sym_list = [s.upper() for s in sym_list if s]
    wf = str(inst.get("workflow_name") or "")
    started_at = str(inst.get("started_at") or "")
    cfg = dict(inst.get("session_config") or {})

    session_capital: float | None = None
    raw_cap = cfg.get("session_capital")
    if raw_cap is not None:
        try:
            session_capital = float(raw_cap)
        except (TypeError, ValueError):
            session_capital = None

    if not started_at:
        return {
            "status": "inactive",
            "currency": currency,
            "session_capital": session_capital,
            "points": [],
            "trades": [],
            "current_equity": session_capital,
            "pnl_abs": 0.0,
            "pnl_pct": None,
        }

    orders = _fetch_session_orders(
        market=market,
        symbols=sym_list,
        workflow_name=wf,
        started_at=started_at,
    )

    cash = float(session_capital or 0.0)
    position_qty = 0.0
    primary_symbol = sym_list[0] if sym_list else str(inst.get("symbol") or "").upper()

    points: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []

    start_ts = _to_unix_seconds(started_at)
    if start_ts is not None:
        points.append(
            {
                "time": start_ts,
                "equity": round(cash, 2),
                "cash": round(cash, 2),
                "position_value": 0.0,
                "event": "session_start",
                "symbol": primary_symbol,
            }
        )

    for row in orders:
        payload = _parse_payload(row.get("payload_json"))
        side = _order_side(payload, row_decision=row.get("decision"))
        qty = _order_qty(payload)
        notional = resolve_order_notional(row, payload)
        price = _order_price(payload, notional=notional, qty=qty)
        ts = _to_unix_seconds(row.get("event_at"))
        if ts is None:
            continue

        trade_row = {
            "event_at": row.get("event_at"),
            "time": ts,
            "symbol": row.get("symbol"),
            "side": side,
            "quantity": round(qty, 8) if qty else None,
            "price": round(price, 6) if price else None,
            "notional": notional,
            "currency": row.get("currency") or currency,
        }
        trades.append(trade_row)

        if side == "BUY":
            spend = float(notional or 0.0)
            if spend <= 0 and qty > 0 and price:
                spend = qty * price
            cash -= spend
            position_qty += qty
        else:
            proceeds = float(notional or 0.0)
            if proceeds <= 0 and qty > 0 and price:
                proceeds = qty * price
            cash += proceeds
            position_qty = max(0.0, position_qty - qty)

        mark = price or _current_mark_price(market, str(row.get("symbol") or primary_symbol))
        position_value = position_qty * float(mark or 0.0)
        equity = cash + position_value

        points.append(
            {
                "time": ts,
                "equity": round(equity, 2),
                "cash": round(cash, 2),
                "position_value": round(position_value, 2),
                "position_qty": round(position_qty, 8),
                "event": "sell" if side == "SELL" else "buy",
                "symbol": row.get("symbol"),
                "side": side,
                "notional": notional,
                "price": price,
            }
        )

    # Mark-to-market «сейчас»
    if position_qty > 1e-12:
        live = _current_mark_price(market, primary_symbol)
        if live and live > 0:
            now_ts = int(datetime.now(timezone.utc).timestamp())
            position_value = position_qty * live
            equity = cash + position_value
            if not points or points[-1].get("time") != now_ts:
                points.append(
                    {
                        "time": now_ts,
                        "equity": round(equity, 2),
                        "cash": round(cash, 2),
                        "position_value": round(position_value, 2),
                        "position_qty": round(position_qty, 8),
                        "event": "mark",
                        "symbol": primary_symbol,
                        "mark_price": round(live, 6),
                    }
                )

    current_equity = points[-1]["equity"] if points else (session_capital or 0.0)
    base = float(session_capital or current_equity or 0.0)
    pnl_abs = round(float(current_equity) - base, 2) if base else 0.0
    pnl_pct = round(pnl_abs / base * 100, 4) if base > 0 else None

    return {
        "status": "ok",
        "currency": currency,
        "session_capital": round(session_capital, 2) if session_capital is not None else None,
        "started_at": started_at,
        "points": points,
        "trades": trades,
        "current_equity": round(float(current_equity), 2),
        "pnl_abs": pnl_abs,
        "pnl_pct": pnl_pct,
    }


def trade_row_from_event(row: dict[str, Any], *, default_currency: str = "USDT") -> dict[str, Any]:
    payload = _parse_payload(row.get("payload_json"))
    side = _order_side(payload, row_decision=row.get("decision"))
    qty = _order_qty(payload)
    notional = resolve_order_notional(row, payload)
    price = _order_price(payload, notional=notional, qty=qty)
    return {
        "event_at": row.get("event_at"),
        "symbol": row.get("symbol"),
        "decision": row.get("decision"),
        "side": side,
        "quantity": round(qty, 8) if qty else None,
        "price": round(price, 6) if price else None,
        "notional": notional,
        "currency": row.get("currency") or default_currency,
    }


def get_crypto_instance_equity_curve(instance_id: str) -> dict[str, Any]:
    from crypto_automation_instance_service import get_instance

    inst = get_instance(instance_id)
    if not inst:
        raise ValueError("instance_not_found")
    return build_automation_equity_curve(inst, market="crypto")


def get_securities_instance_equity_curve(instance_id: str) -> dict[str, Any]:
    from securities_automation_instance_service import _instance_symbols, get_instance

    inst = get_instance(instance_id)
    if not inst:
        raise ValueError("instance_not_found")
    return build_automation_equity_curve(
        inst,
        market="securities",
        symbols=_instance_symbols(inst),
    )
