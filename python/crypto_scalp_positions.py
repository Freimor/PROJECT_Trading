"""Scalp position tracking, exit rules, and market orders for paper/testnet (spot + futures)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from binance_trading import (
    get_market_price,
    get_open_position,
    normalize_order_quantity,
    place_market_order,
)
from config_loader import load_config
from crypto_product import get_crypto_trading_product, order_side_for_exit
from db.connection import get_connection
from effective_config import get_config_effective
from event_log import log_event
from crypto_quote import symbol_base_asset
from workflow_universe_service import enabled_symbols_for_workflow

_SCALP_WF_PREFIX = "crypto-scalp"
_ORDER_OK = ("execute", "executed", "submitted", "approve")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_ts(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        ts = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
    except ValueError:
        return None


def _order_qty(payload: dict[str, Any]) -> float:
    for key in ("executedQty", "origQty", "qty", "quantity"):
        val = payload.get(key)
        if val is not None:
            try:
                q = float(val)
                if q > 0:
                    return q
            except (TypeError, ValueError):
                pass
    return 0.0


def _wallet_base_qty(symbol: str, *, testnet: bool = True) -> float:
    from binance_client import get_account_balances

    asset = symbol_base_asset(symbol)
    for row in get_account_balances(testnet=testnet):
        if str(row.get("asset") or "").upper() == asset:
            return float(row.get("free", 0) or 0) + float(row.get("locked", 0) or 0)
    return 0.0


def _last_price(symbol: str, *, testnet: bool = True, cfg: dict[str, Any] | None = None) -> float | None:
    return get_market_price(symbol, testnet=testnet, cfg=cfg)


def _db_session_net_qty(
    symbol: str,
    *,
    workflow_name: str | None = None,
    position_side: str = "long",
) -> float:
    """Net open qty from trade_events since session baseline (long: BUY−SELL, short: SELL−BUY)."""
    from workflow_session_config_service import get_workflow_session_config

    sym = symbol.upper()
    side = str(position_side).lower()
    cfg = get_workflow_session_config("crypto")
    since = cfg.get("baseline_captured_at")
    conn = get_connection()
    try:
        if since:
            rows = conn.execute(
                """
                SELECT o.payload_json, o.decision
                FROM trade_events o
                WHERE o.market = 'crypto' AND o.stage = 'order' AND o.symbol = ?
                  AND o.decision IN ('execute', 'executed', 'submitted', 'approve')
                  AND o.workflow_name LIKE 'crypto-scalp%'
                  AND o.event_at >= ?
                ORDER BY o.event_at ASC
                """,
                (sym, since),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT o.payload_json, o.decision
                FROM trade_events o
                WHERE o.market = 'crypto' AND o.stage = 'order' AND o.symbol = ?
                  AND o.decision IN ('execute', 'executed', 'submitted', 'approve')
                  AND o.workflow_name LIKE 'crypto-scalp%'
                ORDER BY o.event_at ASC
                """,
                (sym,),
            ).fetchall()
    finally:
        conn.close()

    net = 0.0
    entry_side = "SELL" if side == "short" else "BUY"
    exit_side = "BUY" if side == "short" else "SELL"
    for row in rows:
        d = dict(row)
        payload: dict[str, Any] = {}
        try:
            payload = json.loads(d.get("payload_json") or "{}")
        except json.JSONDecodeError:
            pass
        order_side = str(payload.get("side") or "BUY").upper()
        pos_side = str((payload.get("scalp") or {}).get("position_side") or payload.get("position_side") or "").lower()
        if pos_side and pos_side != side:
            continue
        qty = _order_qty(payload)
        if qty <= 0:
            continue
        if order_side == exit_side:
            net = max(0.0, net - qty)
        elif order_side == entry_side:
            net += qty
    return net


def _last_entry_from_db(
    symbol: str,
    *,
    position_side: str,
    since: str | None,
) -> dict[str, Any] | None:
    sym = symbol.upper()
    side = str(position_side).lower()
    entry_side = "SELL" if side == "short" else "BUY"
    params: list[Any] = [sym, entry_side]
    since_clause = ""
    if since:
        since_clause = " AND o.event_at >= ?"
        params.append(since)

    conn = get_connection()
    try:
        row = conn.execute(
            f"""
            SELECT o.event_at, o.payload_json, o.inputs_hash, r.payload_json AS risk_json
            FROM trade_events o
            LEFT JOIN trade_events r
              ON r.market = o.market AND r.inputs_hash = o.inputs_hash AND r.stage = 'risk'
            WHERE o.market = 'crypto' AND o.stage = 'order' AND o.symbol = ?
              AND o.decision IN ('execute', 'executed', 'submitted', 'approve')
              AND o.workflow_name LIKE 'crypto-scalp%'
              AND json_extract(o.payload_json, '$.side') = ?
              {since_clause}
            ORDER BY o.event_at DESC
            LIMIT 1
            """,
            params,
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    d = dict(row)
    payload: dict[str, Any] = {}
    risk_data: dict[str, Any] = {}
    try:
        payload = json.loads(d.get("payload_json") or "{}")
        risk_data = json.loads(d.get("risk_json") or "{}")
    except json.JSONDecodeError:
        pass
    scalp_meta = payload.get("scalp") or {}
    return {
        "entry_at": d.get("event_at"),
        "entry_price": float(scalp_meta.get("entry_price") or risk_data.get("entry_price") or 0),
        "stop_price": float(scalp_meta.get("stop_price") or risk_data.get("stop_price") or 0),
        "take_profit_price": float(
            scalp_meta.get("take_profit_price") or risk_data.get("take_profit_price") or 0
        ),
        "inputs_hash": d.get("inputs_hash"),
        "position_side": side,
    }


def _get_futures_scalp_position(
    symbol: str,
    *,
    workflow_name: str | None = None,
    testnet: bool = True,
    cfg: dict[str, Any] | None = None,
    product: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    from workflow_session_config_service import get_workflow_session_config

    sym = symbol.upper()
    crypto_cfg = cfg or get_config_effective("crypto_config")
    product = product or get_crypto_trading_product(cfg=crypto_cfg)
    exch = get_open_position(sym, testnet=testnet, cfg=crypto_cfg)
    if not exch:
        return None

    qty = abs(float(exch.get("position_amt") or 0))
    if qty <= 0:
        return None

    position_side = str(exch.get("position_side") or "long").lower()
    session_cfg = get_workflow_session_config("crypto")
    last_entry = _last_entry_from_db(
        sym, position_side=position_side, since=session_cfg.get("baseline_captured_at")
    )

    entry_price = float(exch.get("entry_price") or 0)
    stop_price = 0.0
    take_profit_price = 0.0
    entry_at = None
    inputs_hash = None
    synthetic = False

    if last_entry and last_entry.get("entry_price"):
        entry_at = last_entry.get("entry_at")
        entry_price = float(last_entry.get("entry_price") or entry_price)
        stop_price = float(last_entry.get("stop_price") or 0)
        take_profit_price = float(last_entry.get("take_profit_price") or 0)
        inputs_hash = last_entry.get("inputs_hash")
    elif entry_price <= 0:
        px = _last_price(sym, testnet=testnet, cfg=crypto_cfg) or 0.0
        entry_price = px
        risk_cfg = load_config("crypto_scalp_hybrid").get("risk", {})
        stop_pct = float(risk_cfg.get("min_stop_distance_pct", 0.008))
        if position_side == "short":
            stop_price = round(px * (1 + stop_pct), 6) if px else 0
            take_profit_price = round(px * (1 - stop_pct * 2), 6) if px else 0
        else:
            stop_price = round(px * (1 - stop_pct), 6) if px else 0
            take_profit_price = round(px * (1 + stop_pct * 2), 6) if px else 0
        entry_at = session_cfg.get("baseline_captured_at") or _utc_now()
        synthetic = True

    norm = normalize_order_quantity(
        sym, qty, testnet=testnet, market_order=True, cfg=crypto_cfg
    )
    if not norm.get("valid"):
        return None

    return {
        "symbol": sym,
        "qty": round(float(norm["normalized_quantity"]), 8),
        "position_side": position_side,
        "direction": position_side,
        "entry_at": entry_at,
        "entry_price": entry_price,
        "stop_price": stop_price,
        "take_profit_price": take_profit_price,
        "inputs_hash": inputs_hash,
        "synthetic": synthetic,
        "market_type": product.get("market_type"),
        "leverage": exch.get("leverage") or product.get("leverage"),
        "unrealized_pnl": exch.get("unrealized_pnl"),
        "mark_price": exch.get("mark_price"),
        "exchange_qty": qty,
    }


def get_scalp_position(
    symbol: str,
    *,
    workflow_name: str | None = None,
    testnet: bool = True,
) -> dict[str, Any] | None:
    """Open scalp leg — spot long or futures long/short."""
    crypto_cfg = get_config_effective("crypto_config")
    product = get_crypto_trading_product(cfg=crypto_cfg)
    if product.get("is_futures"):
        return _get_futures_scalp_position(
            symbol, workflow_name=workflow_name, testnet=testnet, cfg=crypto_cfg, product=product
        )

    from workflow_session_config_service import compute_managed_qty, get_workflow_session_config

    sym = symbol.upper()
    cfg = get_workflow_session_config("crypto")
    wallet_qty = _wallet_base_qty(sym, testnet=testnet)
    db_net = _db_session_net_qty(sym, workflow_name=workflow_name, position_side="long")
    breakdown = compute_managed_qty(
        sym, wallet_qty=wallet_qty, db_session_net=db_net, cfg=cfg, market="crypto"
    )
    qty = float(breakdown["managed_qty"])
    if qty <= 0:
        return None

    norm = normalize_order_quantity(sym, qty, testnet=testnet, market_order=True, cfg=crypto_cfg)
    if not norm.get("valid"):
        return None

    last_entry = _last_entry_from_db(sym, position_side="long", since=cfg.get("baseline_captured_at"))

    last_buy: dict[str, Any] | None = last_entry
    if not last_buy or not last_buy.get("entry_price"):
        px = _last_price(sym, testnet=testnet, cfg=crypto_cfg) or 0.0
        risk_cfg = load_config("crypto_scalp_hybrid").get("risk", {})
        stop_pct = float(risk_cfg.get("min_stop_distance_pct", 0.008))
        pre = float(breakdown.get("pre_session_allocated_qty") or 0) > 0
        last_buy = {
            "entry_at": cfg.get("baseline_captured_at") or _utc_now(),
            "entry_price": px,
            "stop_price": round(px * (1 - stop_pct), 6) if px else 0,
            "take_profit_price": round(px * (1 + stop_pct * 2), 6) if px else 0,
            "inputs_hash": None,
            "synthetic": pre or breakdown.get("session_acquired_qty", 0) <= 0,
        }

    entry = last_buy or {}
    return {
        "symbol": sym,
        "qty": round(float(norm["normalized_quantity"]), 8),
        "position_side": "long",
        "direction": "long",
        "entry_at": entry.get("entry_at"),
        "entry_price": entry.get("entry_price"),
        "stop_price": entry.get("stop_price"),
        "take_profit_price": entry.get("take_profit_price"),
        "inputs_hash": entry.get("inputs_hash"),
        "synthetic": entry.get("synthetic", False),
        "market_type": "spot",
        "wallet_qty": wallet_qty,
        "db_net_qty": db_net,
        **breakdown,
    }


def evaluate_scalp_exit(
    position: dict[str, Any],
    *,
    current_price: float,
    cfg: dict[str, Any] | None = None,
) -> str | None:
    """Return exit reason or None to hold (long and short)."""
    cfg = cfg or load_config("crypto_scalp_hybrid")
    exit_cfg = cfg.get("exit") or {}
    entry = float(position.get("entry_price") or 0)
    if entry <= 0:
        return None

    position_side = str(position.get("position_side") or position.get("direction") or "long").lower()
    stop = float(position.get("stop_price") or 0)
    tp = float(position.get("take_profit_price") or 0)

    if exit_cfg.get("use_stop", True) and stop > 0:
        if position_side == "short" and current_price >= stop:
            return "scalp_stop_loss"
        if position_side == "long" and current_price <= stop:
            return "scalp_stop_loss"

    if exit_cfg.get("use_take_profit", True) and tp > 0:
        if position_side == "short" and current_price <= tp:
            return "scalp_take_profit"
        if position_side == "long" and current_price >= tp:
            return "scalp_take_profit"

    max_bars = int(exit_cfg.get("max_hold_bars", 6))
    if position.get("synthetic"):
        max_bars = int(exit_cfg.get("synthetic_max_hold_bars", 2))
    entry_at = _parse_ts(position.get("entry_at"))
    if entry_at and max_bars > 0:
        hold_sec = max_bars * int(cfg.get("schedule_minutes", 5)) * 60
        age = (datetime.now(timezone.utc) - entry_at).total_seconds()
        if age >= hold_sec:
            return "scalp_max_hold"

    if exit_cfg.get("exit_on_momentum_flip", True):
        from binance_trading import fetch_market_klines
        from crypto_scalp_pipeline import _compute_scalp_extras
        from indicators.technical import parse_binance_klines

        crypto_cfg = get_config_effective("crypto_config")
        raw = fetch_market_klines(
            position["symbol"],
            str(cfg.get("timeframe", "5m")),
            limit=30,
            testnet=True,
            cfg=crypto_cfg,
        )
        candles = parse_binance_klines(raw)
        extras = _compute_scalp_extras(candles, cfg.get("scalp_rules", {}))
        mom = float(extras.get("momentum_pct", 0))
        flip_pct = float(exit_cfg.get("momentum_flip_pct", -0.05))
        flip_short_pct = float(exit_cfg.get("momentum_flip_short_pct", abs(flip_pct)))
        if position_side == "short" and mom >= flip_short_pct:
            return "scalp_momentum_flip"
        if position_side == "long" and mom <= flip_pct:
            return "scalp_momentum_flip"

    return None


def try_scalp_exit(
    symbol: str,
    *,
    workflow_name: str,
    testnet: bool = True,
) -> dict[str, Any]:
    """Close scalp leg if exit rules fire (spot SELL or futures reduce-only)."""
    crypto_cfg = get_config_effective("crypto_config")
    product = get_crypto_trading_product(cfg=crypto_cfg)
    pos = get_scalp_position(symbol, workflow_name=workflow_name, testnet=testnet)
    if not pos:
        return {"status": "no_position", "symbol": symbol}

    price = _last_price(symbol, testnet=testnet, cfg=crypto_cfg)
    if not price or price <= 0:
        return {"status": "skipped", "reject_reason": "no_price", "symbol": symbol}

    reason = evaluate_scalp_exit(pos, current_price=price)
    if not reason:
        return {"status": "holding", "symbol": symbol, "position": pos, "price": price}

    position_side = str(pos.get("position_side") or "long").lower()
    exit_side = order_side_for_exit(position_side)  # type: ignore[arg-type]
    qty = float(pos["qty"])
    norm = normalize_order_quantity(
        symbol, qty, testnet=testnet, market_order=True, cfg=crypto_cfg
    )
    if not norm.get("valid"):
        return {"status": "error", "reject_reason": "exit_qty_below_min_lot", "position": pos}

    sell_qty = float(norm["normalized_quantity"])
    reduce_only = bool(product.get("is_futures") and product.get("use_reduce_only_on_exit"))
    order = place_market_order(
        symbol=symbol,
        side=exit_side,
        quantity=sell_qty,
        testnet=testnet,
        reduce_only=reduce_only,
        cfg=crypto_cfg,
    )
    submitted = order.get("orderId") is not None and order.get("http_status") == 200
    reject_reason = None if submitted else (
        order.get("reject_reason") or order.get("msg") or order.get("message")
    )

    pnl_pct = None
    entry = float(pos.get("entry_price") or 0)
    if entry > 0:
        if position_side == "short":
            pnl_pct = round((entry - price) / entry * 100, 3)
        else:
            pnl_pct = round((price - entry) / entry * 100, 3)

    log_event(
        market="crypto",
        env="paper",
        stage="order",
        symbol=symbol.upper(),
        decision="execute" if submitted else "error",
        workflow_name=workflow_name,
        inputs_hash=pos.get("inputs_hash"),
        notional=round(sell_qty * price, 2),
        reject_reason=reject_reason if not submitted else None,
        payload={
            **order,
            "side": exit_side,
            "position_side": position_side,
            "exit_reason": reason,
            "entry_price": entry,
            "exit_price": price,
            "pnl_pct": pnl_pct,
            "reduce_only": reduce_only,
            "scalp": {
                "qty": sell_qty,
                "position_side": position_side,
                **{k: pos.get(k) for k in ("entry_at", "stop_price", "take_profit_price")},
            },
        },
    )

    return {
        "status": "executed" if submitted else "order_error",
        "action": "exit",
        "exit_reason": reason,
        "symbol": symbol,
        "order": order,
        "position": pos,
        "pnl_pct": pnl_pct,
        "reject_reason": reject_reason,
    }


def scalp_open_symbols(*, workflow_name: str) -> list[str]:
    """Symbols with open scalp position (universe ∩ wallet/DB or futures exchange)."""
    universe = enabled_symbols_for_workflow(workflow_name) or []
    open_syms: list[str] = []
    for sym in universe:
        if get_scalp_position(sym, workflow_name=workflow_name):
            open_syms.append(sym.upper())
    return open_syms
