"""Session holdings baseline, managed qty, and liquidation on stop."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal

from binance_client import get_account_balances
from binance_trading import normalize_order_quantity, place_market_order
from crypto_product import get_crypto_trading_product, order_side_for_exit
from crypto_quote import get_crypto_quote_asset, pair_with_quote, symbol_base_asset, wallet_quote_balance
from effective_config import get_config_effective
from event_log import log_event
from runtime_settings import delete_runtime_value, get_runtime_meta, set_runtime_value
from workflow_universe_service import enabled_symbols_for_workflow

WORKFLOW_SESSION_CONFIG_KEY = {
    "crypto": "crypto_workflow_session_config",
    "securities": "securities_workflow_session_config",
}

DEFAULT_SESSION_CAPITAL: dict[str, float] = {
    "crypto": 10_000.0,
    "securities": 100_000.0,
}

SessionVolumeMode = Literal["stablecoin", "existing_holdings"]
HoldingsUnit = Literal["percent", "absolute"]
LiquidateReason = Literal["stop", "margin_call"]


def _should_liquidate(cfg: dict[str, Any], reason: LiquidateReason) -> bool:
    if reason == "margin_call":
        if "liquidate_on_margin_call" in cfg:
            return bool(cfg.get("liquidate_on_margin_call"))
        return bool(cfg.get("liquidate_on_stop"))
    return bool(cfg.get("liquidate_on_stop"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_session_capital(market: str) -> float:
    return DEFAULT_SESSION_CAPITAL.get(market, 10_000.0)


def _wallet_base_qty(symbol: str, *, testnet: bool = True, quote: str | None = None) -> float:
    asset = symbol_base_asset(symbol, quote=quote)
    for row in get_account_balances(testnet=testnet):
        if str(row.get("asset") or "").upper() == asset:
            return float(row.get("free", 0) or 0) + float(row.get("locked", 0) or 0)
    return 0.0


def _normalize_session_params(
    *,
    market: str,
    session_volume_mode: str | None = None,
    session_capital: float | None = None,
    use_existing_holdings: bool | None = None,
    existing_holdings_unit: str | None = None,
    existing_holdings_use_pct: float = 0,
    existing_holdings_use_qty: float | None = None,
) -> dict[str, Any]:
    """Resolve mode + holdings unit from new or legacy request fields."""
    mode: SessionVolumeMode
    if session_volume_mode in ("stablecoin", "existing_holdings"):
        mode = session_volume_mode  # type: ignore[assignment]
    elif use_existing_holdings:
        mode = "existing_holdings"
    else:
        mode = "stablecoin"

    unit: HoldingsUnit = "percent"
    if existing_holdings_unit in ("percent", "absolute"):
        unit = existing_holdings_unit  # type: ignore[assignment]

    pct = max(0.0, min(100.0, float(existing_holdings_use_pct or 0)))
    abs_qty = float(existing_holdings_use_qty) if existing_holdings_use_qty is not None else 0.0

    cap: float | None = None
    if mode == "stablecoin":
        if session_capital is None or float(session_capital) <= 0:
            raise ValueError("session_capital_must_be_positive")
        cap = round(float(session_capital), 2)
    elif mode == "existing_holdings":
        if unit == "absolute":
            if abs_qty <= 0:
                raise ValueError("existing_holdings_qty_must_be_positive")
        elif pct <= 0:
            pct = 100.0
        if session_capital is not None and float(session_capital) > 0:
            cap = round(float(session_capital), 2)

    if market == "securities" and mode == "stablecoin" and cap is None:
        raise ValueError("session_capital_must_be_positive")

    return {
        "session_volume_mode": mode,
        "session_capital": cap,
        "existing_holdings_unit": unit,
        "existing_holdings_use_pct": round(pct, 2),
        "existing_holdings_use_qty": round(abs_qty, 8) if abs_qty > 0 else None,
        "use_existing_holdings": mode == "existing_holdings",
    }


def capture_holdings_baseline(
    market: str,
    *,
    workflow_name: str | None = None,
    testnet: bool = True,
    sandbox: bool = True,
    quote_asset: str | None = None,
) -> dict[str, float]:
    """Snapshot qty per symbol at session start (quote cash + pair base qty)."""
    out: dict[str, float] = {}
    if market == "crypto":
        quote = (quote_asset or get_crypto_quote_asset()).upper()
        balances = get_account_balances(testnet=testnet)
        cash = wallet_quote_balance(balances, quote=quote)
        if cash > 0:
            out[quote] = round(cash, 8)
        symbols = enabled_symbols_for_workflow(workflow_name) if workflow_name else []
        for sym in symbols:
            pair = pair_with_quote(sym, quote=quote)
            q = _wallet_base_qty(pair, testnet=testnet, quote=quote)
            if q > 0:
                out[str(pair).upper()] = round(q, 8)
        return out

    if market == "securities":
        try:
            from bridges.tinvest_bridge import get_portfolio_snapshot

            snap = get_portfolio_snapshot(sandbox=sandbox)
            if snap.get("status") == "ok":
                for p in snap.get("positions") or []:
                    ticker = str(p.get("ticker") or "").upper()
                    qty = float(p.get("quantity", 0) or 0)
                    if ticker and qty > 0:
                        out[ticker] = round(qty, 8)
                total = snap.get("total_amount")
                if total is not None:
                    out["RUB"] = round(float(total), 2)
        except Exception:
            pass
    return out


def set_workflow_session_config(
    market: str,
    *,
    session_capital: float | None = None,
    session_volume_mode: str | None = None,
    use_existing_holdings: bool = False,
    existing_holdings_unit: str = "percent",
    existing_holdings_use_pct: float = 0,
    existing_holdings_use_qty: float | None = None,
    liquidate_on_stop: bool = False,
    liquidate_on_margin_call: bool | None = None,
    pre_scan_universe: bool = False,
    universe_scan_meta: dict[str, Any] | None = None,
    workflow_name: str | None = None,
    operator: str = "web:operator",
) -> dict[str, Any]:
    if market not in WORKFLOW_SESSION_CONFIG_KEY:
        raise ValueError(f"unknown_market: {market}")

    norm = _normalize_session_params(
        market=market,
        session_volume_mode=session_volume_mode,
        session_capital=session_capital,
        use_existing_holdings=use_existing_holdings,
        existing_holdings_unit=existing_holdings_unit,
        existing_holdings_use_pct=existing_holdings_use_pct,
        existing_holdings_use_qty=existing_holdings_use_qty,
    )

    quote_asset = get_crypto_quote_asset() if market == "crypto" else "RUB"
    baseline = capture_holdings_baseline(
        market,
        workflow_name=workflow_name,
        quote_asset=quote_asset if market == "crypto" else None,
    )

    payload = {
        **norm,
        "liquidate_on_stop": bool(liquidate_on_stop),
        "liquidate_on_margin_call": (
            bool(liquidate_on_margin_call)
            if liquidate_on_margin_call is not None
            else bool(liquidate_on_stop)
        ),
        "pre_scan_universe": bool(pre_scan_universe),
        "quote_asset": quote_asset,
        "holdings_baseline": baseline,
        "baseline_captured_at": _utc_now(),
        "workflow_name": workflow_name,
    }
    if universe_scan_meta:
        payload.update(
            {
                "universe_scan_at": universe_scan_meta.get("scanned_at"),
                "universe_scan_selected": universe_scan_meta.get("selected_symbols"),
                "universe_scan_ranked": [
                    {
                        "symbol": r.get("symbol"),
                        "score": r.get("score"),
                        "eligible": r.get("eligible"),
                        "reject_reason": r.get("reject_reason"),
                    }
                    for r in (universe_scan_meta.get("ranked") or [])[:20]
                ],
            }
        )
    set_runtime_value(
        WORKFLOW_SESSION_CONFIG_KEY[market],
        json.dumps(payload),
        updated_by=operator,
    )
    return payload


def get_workflow_session_config(market: str) -> dict[str, Any]:
    if market not in WORKFLOW_SESSION_CONFIG_KEY:
        return {}
    meta = get_runtime_meta(WORKFLOW_SESSION_CONFIG_KEY[market]) or {}
    raw = meta.get("value")
    if not raw:
        return {}
    try:
        data = json.loads(str(raw))
        if isinstance(data, dict):
            if "session_volume_mode" not in data:
                data["session_volume_mode"] = (
                    "existing_holdings" if data.get("use_existing_holdings") else "stablecoin"
                )
            if "existing_holdings_unit" not in data:
                data["existing_holdings_unit"] = "percent"
            if "liquidate_on_margin_call" not in data:
                data["liquidate_on_margin_call"] = bool(data.get("liquidate_on_stop"))
            return data
    except json.JSONDecodeError:
        pass
    return {}


def clear_workflow_session_config(market: str) -> None:
    if market in WORKFLOW_SESSION_CONFIG_KEY:
        delete_runtime_value(WORKFLOW_SESSION_CONFIG_KEY[market])


def _baseline_qty(symbol: str, cfg: dict[str, Any]) -> float:
    base = cfg.get("holdings_baseline") or {}
    sym = str(symbol).upper()
    if sym in base:
        return float(base.get(sym) or 0)
    quote = cfg.get("quote_asset") or get_crypto_quote_asset()
    alt = pair_with_quote(sym, quote=str(quote))
    return float(base.get(alt, 0) or 0)


def _pre_session_allocated_qty(baseline: float, cfg: dict[str, Any]) -> float:
    if baseline <= 0:
        return 0.0
    if cfg.get("session_volume_mode", "stablecoin") != "existing_holdings":
        if not cfg.get("use_existing_holdings"):
            return 0.0
    unit = str(cfg.get("existing_holdings_unit") or "percent")
    if unit == "absolute":
        abs_qty = float(cfg.get("existing_holdings_use_qty") or 0)
        return min(baseline, abs_qty) if abs_qty > 0 else 0.0
    pct = float(cfg.get("existing_holdings_use_pct", 0) or 0)
    pct = max(0.0, min(100.0, pct))
    return baseline * (pct / 100.0)


def compute_managed_qty(
    symbol: str,
    *,
    wallet_qty: float,
    db_session_net: float = 0.0,
    cfg: dict[str, Any] | None = None,
    market: str = "crypto",
) -> dict[str, float]:
    cfg = cfg or get_workflow_session_config(market)
    baseline = _baseline_qty(symbol, cfg)
    mode = cfg.get("session_volume_mode", "stablecoin")

    wallet_delta = max(0.0, wallet_qty - baseline)
    session_acquired = max(wallet_delta, max(0.0, db_session_net))

    if mode == "existing_holdings" or cfg.get("use_existing_holdings"):
        pre_allocated = _pre_session_allocated_qty(baseline, cfg)
    else:
        pre_allocated = 0.0

    total = min(wallet_qty, session_acquired + pre_allocated)
    return {
        "managed_qty": round(total, 8),
        "session_acquired_qty": round(session_acquired, 8),
        "pre_session_allocated_qty": round(min(pre_allocated, wallet_qty), 8),
        "baseline_qty": round(baseline, 8),
        "wallet_qty": round(wallet_qty, 8),
    }


def resolve_workflow_equity(
    market: str,
    *,
    wallet_equity: float | None = None,
    default: float | None = None,
) -> float:
    fallback = default if default is not None else default_session_capital(market)
    session = get_workflow_session_config(market)
    mode = session.get("session_volume_mode", "stablecoin")

    if mode == "existing_holdings":
        cap = session.get("session_capital")
        if cap is not None:
            try:
                cap_f = float(cap)
            except (TypeError, ValueError):
                cap_f = 0.0
            if cap_f > 0:
                return min(cap_f, wallet_equity) if wallet_equity and wallet_equity > 0 else cap_f
        return 0.0

    cap = session.get("session_capital")
    if cap is not None:
        try:
            cap_f = float(cap)
        except (TypeError, ValueError):
            cap_f = 0.0
        if cap_f > 0:
            if wallet_equity is not None and wallet_equity > 0:
                return min(cap_f, wallet_equity)
            return cap_f
    if wallet_equity is not None and wallet_equity > 0:
        return wallet_equity
    return fallback


def resolve_securities_order_rub(market: str, *, config_amount: float) -> float:
    session = get_workflow_session_config(market)
    cap = session.get("session_capital")
    if cap is None:
        return float(config_amount)
    try:
        cap_f = float(cap)
    except (TypeError, ValueError):
        return float(config_amount)
    if cap_f <= 0:
        return float(config_amount)
    from guardrails import get_guardrails

    trading = get_guardrails().get("trading", {})
    pct = float(trading.get("max_notional_pct_equity", 0.05))
    per_trade = cap_f * pct
    if per_trade <= 0:
        return float(config_amount)
    return min(float(config_amount), per_trade)


def _liquidate_spot_session_holdings(
    *,
    market: str,
    cfg: dict[str, Any],
    workflow_name: str,
    operator: str,
    exit_reason: str,
    testnet: bool = True,
) -> list[dict[str, Any]]:
    quote = str(cfg.get("quote_asset") or get_crypto_quote_asset()).upper()
    symbols = enabled_symbols_for_workflow(str(workflow_name)) or []
    results: list[dict[str, Any]] = []

    from crypto_scalp_positions import _db_session_net_qty, _last_price

    for sym in symbols:
        sym_u = pair_with_quote(sym, quote=quote)
        wallet = _wallet_base_qty(sym_u, testnet=testnet, quote=quote)
        db_net = _db_session_net_qty(sym_u, workflow_name=str(workflow_name))
        breakdown = compute_managed_qty(
            sym_u, wallet_qty=wallet, db_session_net=db_net, cfg=cfg, market=market
        )
        sell_qty = float(breakdown["managed_qty"])
        if sell_qty <= 0:
            continue
        norm = normalize_order_quantity(sym_u, sell_qty, testnet=testnet, market_order=True)
        if not norm.get("valid"):
            results.append(
                {
                    "symbol": sym_u,
                    "status": "skipped",
                    "reject_reason": "below_min_lot",
                    "managed_qty": sell_qty,
                    "product": "spot",
                }
            )
            continue
        qty = float(norm["normalized_quantity"])
        order = place_market_order(symbol=sym_u, side="SELL", quantity=qty, testnet=testnet)
        submitted = order.get("orderId") is not None and order.get("http_status") == 200
        price = _last_price(sym_u) or 0.0
        log_event(
            market="crypto",
            env="paper" if testnet else "live",
            stage="order",
            symbol=sym_u,
            decision="execute" if submitted else "error",
            workflow_name=str(workflow_name),
            notional=round(qty * price, 2) if price else None,
            reject_reason=None if submitted else (order.get("msg") or order.get("reject_reason")),
            payload={
                **order,
                "side": "SELL",
                "exit_reason": exit_reason,
                "quote_asset": quote,
                "operator": operator,
                "session_breakdown": breakdown,
                "product": "spot",
            },
        )
        results.append(
            {
                "symbol": sym_u,
                "status": "executed" if submitted else "error",
                "qty": qty,
                "order": order,
                "product": "spot",
            }
        )
    return results


def _liquidate_futures_positions(
    *,
    workflow_name: str,
    operator: str,
    exit_reason: str,
    testnet: bool = True,
    scope: Literal["session", "all"] = "session",
) -> list[dict[str, Any]]:
    crypto_cfg = get_config_effective("crypto_config")
    product = get_crypto_trading_product(cfg=crypto_cfg)
    if not product.get("is_futures"):
        return []

    quote = str(get_crypto_quote_asset()).upper()
    sym_filter: set[str] | None = None
    if scope == "session":
        enabled = enabled_symbols_for_workflow(str(workflow_name)) or []
        if enabled:
            sym_filter = {pair_with_quote(s, quote=quote).upper() for s in enabled}

    results: list[dict[str, Any]] = []
    from binance_futures_client import get_futures_positions

    for pos in get_futures_positions(testnet=testnet):
        sym = str(pos.get("symbol") or "").upper()
        if sym_filter and sym not in sym_filter:
            continue
        amt = float(pos.get("position_amt") or 0)
        if abs(amt) < 1e-12:
            continue
        side_label = str(pos.get("position_side") or ("long" if amt > 0 else "short"))
        close_side = order_side_for_exit(side_label)  # type: ignore[arg-type]
        qty = abs(amt)
        norm = normalize_order_quantity(
            sym, qty, testnet=testnet, market_order=True, cfg=crypto_cfg
        )
        if not norm.get("valid"):
            results.append(
                {
                    "symbol": sym,
                    "status": "skipped",
                    "reject_reason": norm.get("reject_reason", "below_min_lot"),
                    "managed_qty": qty,
                    "product": "usdt_futures",
                }
            )
            continue
        close_qty = float(norm["normalized_quantity"])
        order = place_market_order(
            symbol=sym,
            side=close_side,
            quantity=close_qty,
            testnet=testnet,
            reduce_only=True,
            cfg=crypto_cfg,
        )
        submitted = order.get("orderId") is not None and order.get("http_status") == 200
        log_event(
            market="crypto",
            env="paper" if testnet else "live",
            stage="order",
            symbol=sym,
            decision="execute" if submitted else "error",
            workflow_name=str(workflow_name),
            reject_reason=None if submitted else (order.get("msg") or order.get("reject_reason")),
            payload={
                **order,
                "side": close_side,
                "exit_reason": exit_reason,
                "operator": operator,
                "position_side": side_label,
                "product": "usdt_futures",
            },
        )
        results.append(
            {
                "symbol": sym,
                "status": "executed" if submitted else "error",
                "qty": close_qty,
                "side": close_side,
                "order": order,
                "product": "usdt_futures",
            }
        )
    return results


def liquidate_session_holdings(
    market: str,
    *,
    workflow_name: str | None = None,
    operator: str = "web:operator",
    reason: LiquidateReason = "stop",
    testnet: bool | None = None,
    close_all_futures: bool = False,
) -> dict[str, Any]:
    cfg = get_workflow_session_config(market)
    if not _should_liquidate(cfg, reason):
        return {"status": "skipped", "reason": f"liquidate_disabled_for_{reason}"}

    if market != "crypto":
        return {"status": "skipped", "reason": "liquidate_crypto_only_for_now"}

    crypto_cfg = get_config_effective("crypto_config")
    if testnet is None:
        testnet = str(crypto_cfg.get("env") or "testnet") != "live"

    wf = workflow_name or cfg.get("workflow_name") or "crypto-scalp-hybrid-paper"
    exit_reason = (
        "session_liquidate_on_margin_call"
        if reason == "margin_call"
        else "session_liquidate_on_stop"
    )
    quote = str(cfg.get("quote_asset") or get_crypto_quote_asset()).upper()
    product = get_crypto_trading_product(cfg=crypto_cfg)
    results: list[dict[str, Any]] = []

    if product.get("is_futures"):
        results.extend(
            _liquidate_futures_positions(
                workflow_name=str(wf),
                operator=operator,
                exit_reason=exit_reason,
                testnet=testnet,
                scope="all" if close_all_futures else "session",
            )
        )
    else:
        results.extend(
            _liquidate_spot_session_holdings(
                market=market,
                cfg=cfg,
                workflow_name=str(wf),
                operator=operator,
                exit_reason=exit_reason,
                testnet=testnet,
            )
        )

    return {
        "status": "ok",
        "market": market,
        "quote_asset": quote,
        "reason": reason,
        "product": product.get("market_type", "spot"),
        "liquidated": sum(1 for r in results if r.get("status") == "executed"),
        "results": results,
    }
