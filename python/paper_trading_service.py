"""Paper trading sessions, reset, and LLM effectiveness metrics."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from binance_trading import get_trading_equity, place_market_order
from binance_client import BinanceNetworkError, get_account_balances
from bridges.tinvest_bridge import check_tinvest_connection, get_portfolio_snapshot, post_dca_order
from config_loader import load_config
from crypto_product import cfg_for_symbol_trade
from crypto_pipeline import run_crypto_signal
from crypto_scalp_pipeline import _scalp_llm_enabled, run_crypto_scalp_signal
from db.connection import get_connection
from db.migrate import run_migrations
from effective_config import get_config_effective, get_guardrails
from workflow_session_config_service import resolve_securities_order_rub, resolve_workflow_equity
from evaluation.replay import evaluation_metrics
from backtest.metrics import dry_run_funnel, signal_summary
from securities_pipeline import run_securities_swing_dry_run
from event_log import log_event


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_paper_config() -> dict[str, Any]:
    guardrails = get_guardrails()
    crypto = get_config_effective("crypto_config")
    sec = get_config_effective("securities_config")
    return {
        "global_mode": guardrails.get("trading", {}).get("mode"),
        "crypto": {"env": crypto.get("env"), "mode": crypto.get("mode")},
        "securities": {
            "env": sec.get("env"),
            "mode": sec.get("mode"),
            "active_mode": sec.get("active_mode"),
        },
        "paper_ready": guardrails.get("trading", {}).get("mode") == "paper",
    }


def _active_session(conn) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT * FROM paper_sessions
        WHERE status = 'active'
        ORDER BY started_at DESC LIMIT 1
        """
    ).fetchone()
    return dict(row) if row else None


def _portfolio_snapshot() -> dict[str, Any]:
    crypto_bal = get_account_balances(testnet=True)
    crypto_usdt = 0.0
    crypto_btc = 0.0
    for b in crypto_bal:
        if b.get("asset") == "USDT":
            crypto_usdt = float(b.get("free", 0))
        if b.get("asset") == "BTC":
            crypto_btc = float(b.get("free", 0))
    moex = get_portfolio_snapshot(sandbox=True)
    rub = 0.0
    positions = []
    if moex.get("status") == "ok":
        for p in moex.get("positions") or []:
            if p.get("ticker") == "RUB000UTSTOM" or p.get("figi") == "RUB000UTSTOM":
                rub = float(p.get("quantity", 0))
            else:
                positions.append(p)
    return {
        "crypto_usdt": crypto_usdt,
        "crypto_btc": crypto_btc,
        "moex_rub": rub,
        "moex_positions": positions,
        "moex_status": moex.get("status"),
    }


def start_paper_session(*, label: str = "paper-test", operator: str = "api") -> dict[str, Any]:
    run_migrations()
    snap = _portfolio_snapshot()
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE paper_sessions SET status = 'closed', ended_at = ? WHERE status = 'active'",
            (_utc_now(),),
        )
        session_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO paper_sessions
                (id, label, status, started_at, started_by, baseline_json, notes)
            VALUES (?, ?, 'active', ?, ?, ?, ?)
            """,
            (
                session_id,
                label,
                _utc_now(),
                operator,
                json.dumps(snap, ensure_ascii=False),
                "Paper test session — baseline portfolio captured",
            ),
        )
        conn.execute(
            """
            INSERT INTO paper_portfolio_snapshots
                (id, session_id, captured_at, snapshot_json, trigger)
            VALUES (?, ?, ?, ?, 'session_start')
            """,
            (
                str(uuid.uuid4()),
                session_id,
                _utc_now(),
                json.dumps(snap, ensure_ascii=False),
            ),
        )
        conn.commit()
        return {
            "status": "ok",
            "session_id": session_id,
            "label": label,
            "baseline": snap,
        }
    finally:
        conn.close()


def reset_moex_sandbox(*, operator: str = "api") -> dict[str, Any]:
    """Close sandbox accounts and open a fresh one with 1M RUB."""
    from bridges.tinvest_rest import TinvestRestClient
    import os

    token = os.environ.get("TINKOFF_SANDBOX_TOKEN", os.environ.get("TINKOFF_TOKEN", ""))
    if not token:
        return {"status": "error", "reject_reason": "missing_tinkoff_token"}

    client = TinvestRestClient(token, sandbox=True)
    closed: list[str] = []
    try:
        for acc in client.get_accounts():
            aid = str(acc.get("id", ""))
            if aid:
                client.close_sandbox_account(aid)
                closed.append(aid)
    except Exception as exc:
        return {"status": "error", "message": str(exc), "closed": closed}

    try:
        new_id = client.ensure_sandbox_account()
        snap = _portfolio_snapshot()
        return {
            "status": "ok",
            "closed_accounts": closed,
            "new_account_id": new_id,
            "portfolio": snap,
            "operator": operator,
            "note": "MOEX sandbox сброшен: новый демо-счёт ~1M ₽",
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc), "closed": closed}


def reset_paper_session(*, reset_moex: bool = True, operator: str = "api") -> dict[str, Any]:
    """Start new paper session; optionally reset MOEX sandbox. Binance testnet cannot be zeroed."""
    moex_result = None
    if reset_moex:
        moex_result = reset_moex_sandbox(operator=operator)
        if moex_result.get("status") != "ok":
            return {"status": "partial", "moex": moex_result}

    session = start_paper_session(label="reset-paper", operator=operator)
    return {
        "status": "ok",
        "session": session,
        "moex": moex_result,
        "binance_note": (
            "Binance testnet нельзя обнулить вручную — сброс ~раз в месяц на стороне Binance. "
            "Метрики эффективности считаются от baseline сессии в SQLite."
        ),
    }


def capture_snapshot(*, session_id: str | None = None, trigger: str = "manual") -> dict[str, Any]:
    run_migrations()
    snap = _portfolio_snapshot()
    conn = get_connection()
    try:
        if not session_id:
            active = _active_session(conn)
            session_id = active["id"] if active else None
        if session_id:
            conn.execute(
                """
                INSERT INTO paper_portfolio_snapshots
                    (id, session_id, captured_at, snapshot_json, trigger)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    session_id,
                    _utc_now(),
                    json.dumps(snap, ensure_ascii=False),
                    trigger,
                ),
            )
            conn.commit()
        result = {"status": "ok", "session_id": session_id, "snapshot": snap}
        try:
            from portfolio_snapshot_service import capture_exchange_position_snapshots

            result["position_snapshots"] = capture_exchange_position_snapshots()
        except Exception as exc:
            result["position_snapshots"] = {"status": "error", "message": str(exc)}
        return result
    finally:
        conn.close()


def run_crypto_paper_trade(*, symbol: str = "BTCUSDT", skip_llm: bool = False) -> dict[str, Any]:
    """Full paper cycle: signal (paper) → testnet market order if approved."""
    guardrails = get_guardrails()
    if guardrails.get("trading", {}).get("kill_switch"):
        return {"status": "halted", "reject_reason": "kill_switch_active"}

    crypto_cfg = get_config_effective("crypto_config")
    if crypto_cfg.get("mode") != "paper" and guardrails.get("trading", {}).get("mode") != "paper":
        return {
            "status": "blocked",
            "reject_reason": "not_paper_mode",
            "hint": "Set mode: paper in crypto_config.yaml and guardrails.yaml",
        }

    balances = get_account_balances(testnet=True)
    from crypto_quote import wallet_quote_balance

    quote_cash = wallet_quote_balance(balances)
    equity = resolve_workflow_equity("crypto", wallet_equity=quote_cash)
    signal = run_crypto_signal(
        symbol=symbol,
        env="paper",
        workflow_name="crypto-paper-auto",
        skip_llm=skip_llm,
        equity=equity,
    )
    if signal.get("status") != "ready_for_order":
        return {"status": signal.get("status", "skipped"), "signal": signal}

    sizing = signal.get("sizing") or {}
    qty = float(sizing.get("quantity") or 0)
    if qty <= 0:
        return {"status": "error", "reject_reason": "zero_quantity", "signal": signal}

    entry_side = str(sizing.get("order_side") or signal.get("side") or "BUY").upper()
    order = place_market_order(
        symbol=symbol, side=entry_side, quantity=qty, testnet=True, cfg=crypto_cfg
    )
    submitted = order.get("orderId") is not None and order.get("http_status") == 200
    reject_reason = None
    if not submitted:
        reject_reason = (
            order.get("reject_reason")
            or order.get("msg")
            or order.get("message")
            or (f"http_{order.get('http_status')}" if order.get("http_status") is not None else None)
        )
    log_event(
        market="crypto",
        env="paper",
        stage="order",
        symbol=symbol,
        decision="execute" if submitted else "error",
        workflow_name="crypto-paper-auto",
        inputs_hash=signal.get("inputs_hash"),
        notional=sizing.get("notional"),
        reject_reason=reject_reason,
        payload=order,
    )
    capture_snapshot(trigger="crypto_order")
    return {
        "status": "executed" if submitted else "order_error",
        "signal": signal,
        "order": order,
        "reject_reason": reject_reason,
    }


def run_crypto_scalp_paper_trade(*, symbol: str = "BTCUSDT", skip_llm: bool = False) -> dict[str, Any]:
    """Scalp 5m: exit open leg → optional rules_engine entry → testnet MARKET order."""
    from crypto_scalp_positions import get_scalp_position, try_scalp_exit

    guardrails = get_guardrails()
    if guardrails.get("trading", {}).get("kill_switch"):
        return {"status": "halted", "reject_reason": "kill_switch_active"}

    try:
        from futures_margin_monitor import ensure_futures_margin_ok

        margin_block = ensure_futures_margin_ok(testnet=True)
        if margin_block:
            return {"status": "halted", **margin_block}
    except Exception:
        pass

    crypto_cfg = get_config_effective("crypto_config")
    if crypto_cfg.get("mode") != "paper" and guardrails.get("trading", {}).get("mode") != "paper":
        return {
            "status": "blocked",
            "reject_reason": "not_paper_mode",
            "hint": "Hybrid scalp runs in paper mode only at this stage",
        }

    scalp_cfg = load_config("crypto_scalp_hybrid")
    paper_cfg = scalp_cfg.get("paper") or {}
    wf = str(paper_cfg.get("workflow_name") or paper_cfg.get("auto_workflow_name") or "crypto-scalp-hybrid-paper")
    from crypto_scalp_pipeline import _scalp_cfg, _scalp_llm_enabled

    merged_scalp = _scalp_cfg(symbol=symbol.upper(), workflow_name=wf)

    try:
        from crypto_scalp_universe_scan import maybe_rescan_scalp_universe

        maybe_rescan_scalp_universe(wf, operator="auto", testnet=True)
    except Exception:
        pass

    _exchange_errors = (
        BinanceNetworkError,
        httpx.ConnectError,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.NetworkError,
    )

    try:
        exit_result = try_scalp_exit(symbol, workflow_name=wf, testnet=True)
        if exit_result.get("status") == "executed":
            capture_snapshot(trigger="crypto_scalp_exit")
            return exit_result

        if get_scalp_position(symbol, workflow_name=wf, testnet=True):
            return {
                "status": "skipped",
                "reject_reason": "scalp_position_open",
                "symbol": symbol,
                "exit_check": exit_result,
            }

        balances = get_account_balances(testnet=True)
        from crypto_quote import wallet_quote_balance

        quote_cash = wallet_quote_balance(balances)
        wallet_equity = get_trading_equity(testnet=True, cfg=crypto_cfg)
        if wallet_equity <= 0:
            wallet_equity = quote_cash
        equity = resolve_workflow_equity(
            "crypto",
            wallet_equity=wallet_equity,
            symbol=symbol,
            workflow_name=wf,
        )

        signal = run_crypto_scalp_signal(
            symbol=symbol,
            env="paper",
            workflow_name=wf,
            skip_llm=skip_llm or not _scalp_llm_enabled(merged_scalp),
            equity=equity,
        )
        if signal.get("status") != "ready_for_order":
            return {"status": signal.get("status", "skipped"), "signal": signal}

        sizing = signal.get("sizing") or {}
        qty = float(sizing.get("quantity") or 0)
        if qty <= 0:
            return {"status": "error", "reject_reason": "zero_quantity", "signal": signal}

        direction = str(signal.get("direction") or sizing.get("position_side") or "long").lower()
        entry_side = str(sizing.get("order_side") or signal.get("side") or "BUY").upper()
        trade_cfg = cfg_for_symbol_trade(crypto_cfg, symbol=symbol, workflow_name=wf)
        order = place_market_order(
            symbol=symbol,
            side=entry_side,
            quantity=qty,
            testnet=True,
            cfg=trade_cfg,
        )
        submitted = order.get("orderId") is not None and order.get("http_status") == 200
        reject_reason = None
        if not submitted:
            reject_reason = (
                order.get("reject_reason")
                or order.get("msg")
                or order.get("message")
                or (f"http_{order.get('http_status')}" if order.get("http_status") is not None else None)
            )
        exec_qty = float(order.get("executedQty") or order.get("origQty") or qty)
        log_event(
            market="crypto",
            env="paper",
            stage="order",
            symbol=symbol,
            decision="execute" if submitted else "error",
            workflow_name=wf,
            inputs_hash=signal.get("inputs_hash"),
            notional=sizing.get("notional"),
            reject_reason=reject_reason,
            payload={
                **order,
                "side": entry_side,
                "direction": direction,
                "position_side": direction,
                "market_type": signal.get("market_type"),
                "leverage": signal.get("leverage"),
                "hybrid_path": signal.get("hybrid_path"),
                "scalp": {
                    "entry_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    "entry_price": sizing.get("entry_price"),
                    "stop_price": sizing.get("stop_price"),
                    "take_profit_price": sizing.get("take_profit_price"),
                    "quantity": exec_qty,
                    "position_side": direction,
                },
            },
        )
        capture_snapshot(trigger="crypto_scalp_order")
        return {
            "status": "executed" if submitted else "order_error",
            "action": "entry",
            "signal": signal,
            "order": order,
            "reject_reason": reject_reason,
        }
    except _exchange_errors as exc:
        from activity_feed_service import log_system_activity

        sym = symbol.upper()
        detail = str(exc).split("\n", 1)[0][:180]
        log_system_activity(
            f"Binance testnet недоступен ({sym}): {detail}",
            category="crypto",
            level="warn",
        )
        return {
            "status": "error",
            "reject_reason": "exchange_unreachable",
            "symbol": sym,
            "workflow_name": wf,
            "message": detail,
        }


def run_securities_swing_paper(*, ticker: str = "SBER", skip_llm: bool = False) -> dict[str, Any]:
    """Swing pipeline (paper) + sandbox buy on LLM approve."""
    guardrails = get_guardrails()
    if guardrails.get("trading", {}).get("kill_switch"):
        return {"status": "halted", "reject_reason": "kill_switch_active"}

    sec_cfg = get_config_effective("securities_config")
    swing = run_securities_swing_dry_run(
        ticker=ticker,
        env="paper",
        workflow_name="securities-swing-paper",
        skip_llm=skip_llm,
    )
    if swing.get("status") != "dry_run_complete":
        return {"status": swing.get("status", "skipped"), "swing": swing}

    amount = float(sec_cfg.get("swing_signals", {}).get("paper_amount_rub", 5000))
    amount = resolve_securities_order_rub("securities", config_amount=amount)

    order = post_dca_order(
        ticker=ticker,
        amount_rub=amount,
        sandbox=sec_cfg.get("env") == "sandbox",
        dry_run=False,
    )
    submitted = order.get("status") == "submitted"
    reject_reason = None
    if not submitted:
        reject_reason = order.get("reject_reason") or order.get("message") or order.get("status")
    log_event(
        market="securities",
        env="paper",
        stage="order",
        symbol=ticker,
        decision="execute" if submitted else "error",
        workflow_name="securities-swing-paper",
        inputs_hash=swing.get("inputs_hash"),
        notional=amount,
        currency="RUB",
        reject_reason=reject_reason,
        payload=order,
    )
    capture_snapshot(trigger="securities_order")
    return {
        "status": "executed" if submitted else "order_error",
        "swing": swing,
        "order": order,
        "reject_reason": reject_reason,
    }


def paper_effectiveness(*, days: int = 7, session_id: str | None = None) -> dict[str, Any]:
    """LLM + paper trading effectiveness report."""
    run_migrations()
    conn = get_connection()
    try:
        session = None
        if session_id:
            row = conn.execute(
                "SELECT * FROM paper_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            session = dict(row) if row else None
        else:
            session = _active_session(conn)

        baseline = {}
        if session:
            baseline = json.loads(session.get("baseline_json") or "{}")

        paper_orders = conn.execute(
            """
            SELECT market, symbol, decision, notional, currency, event_at, confidence,
                   model, prompt_version, payload_json
            FROM trade_events
            WHERE env = 'paper' AND stage = 'order'
              AND event_at >= datetime('now', ?)
            ORDER BY event_at DESC
            """,
            (f"-{days} days",),
        ).fetchall()
        orders = [dict(r) for r in paper_orders]
        executed = [o for o in orders if o.get("decision") in ("submitted", "execute")]

        llm_crypto = evaluation_metrics(market="crypto", days=days)
        llm_sec = evaluation_metrics(market="securities", days=days)

        funnel_crypto = dry_run_funnel(market="crypto", days=days)
        funnel_sec = dry_run_funnel(market="securities", days=days)

        current = _portfolio_snapshot()
        pnl_estimate = {}
        if baseline:
            pnl_estimate = {
                "usdt_delta": round(current.get("crypto_usdt", 0) - baseline.get("crypto_usdt", 0), 2),
                "btc_delta": round(current.get("crypto_btc", 0) - baseline.get("crypto_btc", 0), 8),
                "rub_delta": round(current.get("moex_rub", 0) - baseline.get("moex_rub", 0), 2),
            }

        llm_approved_orders = conn.execute(
            """
            SELECT COUNT(*) AS cnt FROM trade_events e
            WHERE e.env = 'paper' AND e.stage = 'order'
              AND e.decision IN ('submitted','execute')
              AND e.event_at >= datetime('now', ?)
              AND EXISTS (
                SELECT 1 FROM trade_events l
                WHERE l.inputs_hash = e.inputs_hash AND l.stage = 'llm'
                  AND l.decision = 'approve'
              )
            """,
            (f"-{days} days",),
        ).fetchone()

        return {
            "days": days,
            "session": {
                "id": session.get("id") if session else None,
                "label": session.get("label") if session else None,
                "started_at": session.get("started_at") if session else None,
            },
            "config": get_paper_config(),
            "paper_orders_total": len(orders),
            "paper_orders_executed": len(executed),
            "llm_approved_then_executed": llm_approved_orders["cnt"] if llm_approved_orders else 0,
            "llm_eval": {"crypto": llm_crypto, "securities": llm_sec},
            "funnel": {"crypto": funnel_crypto, "securities": funnel_sec},
            "baseline": baseline,
            "current_portfolio": current,
            "pnl_vs_baseline": pnl_estimate,
            "recent_orders": orders[:10],
            "tinvest": check_tinvest_connection(sandbox=True),
        }
    finally:
        conn.close()
