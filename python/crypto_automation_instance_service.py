"""Per-pair crypto automation instances (tabs in console)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from crypto_workflow_map import allowed_operation_modes, resolve_crypto_workflow, strategy_meta
from db.connection import get_connection
from event_log import log_event

INSTANCE_STATUSES = ("stopped", "running", "error")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_table() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS crypto_automation_instances (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                strategy_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                workflow_name TEXT NOT NULL,
                operation_mode TEXT NOT NULL DEFAULT 'paper',
                status TEXT NOT NULL DEFAULT 'stopped',
                session_config_json TEXT NOT NULL DEFAULT '{}',
                collapsed INTEGER NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                stopped_at TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_crypto_auto_inst_status "
            "ON crypto_automation_instances(status)"
        )
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(row: Any) -> dict[str, Any]:
    data = dict(row)
    try:
        data["session_config"] = json.loads(str(data.pop("session_config_json") or "{}"))
    except json.JSONDecodeError:
        data["session_config"] = {}
    data["collapsed"] = bool(data.get("collapsed"))
    return data


def list_instances(*, include_stopped: bool = True) -> list[dict[str, Any]]:
    _ensure_table()
    conn = get_connection()
    try:
        q = "SELECT * FROM crypto_automation_instances"
        if not include_stopped:
            q += " WHERE status = 'running'"
        q += " ORDER BY sort_order ASC, created_at ASC"
        return [_row_to_dict(r) for r in conn.execute(q).fetchall()]
    finally:
        conn.close()


def get_instance(instance_id: str) -> dict[str, Any] | None:
    _ensure_table()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM crypto_automation_instances WHERE id = ?",
            (instance_id,),
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def find_running_instance(*, symbol: str, workflow_name: str) -> dict[str, Any] | None:
    sym = str(symbol).upper()
    wf = str(workflow_name).strip()
    for row in list_instances(include_stopped=False):
        if row.get("status") != "running":
            continue
        if str(row.get("symbol") or "").upper() == sym and str(row.get("workflow_name")) == wf:
            return row
    return None


def find_instance_by_strategy_symbol(*, strategy_id: str, symbol: str) -> dict[str, Any] | None:
    """Existing automation with the same strategy and pair (legacy — any market)."""
    return find_instance_by_strategy_symbol_market(
        strategy_id=strategy_id,
        symbol=symbol,
        market_type="spot",
    )


def _instance_market_type(row: dict[str, Any]) -> str:
    cfg = row.get("session_config") or {}
    mt = str(cfg.get("market_type") or "spot").strip().lower()
    return mt if mt in ("spot", "usdt_futures") else "spot"


def find_instance_by_strategy_symbol_market(
    *,
    strategy_id: str,
    symbol: str,
    market_type: str = "spot",
) -> dict[str, Any] | None:
    """Existing automation with the same strategy, pair and market (spot/futures)."""
    sid = str(strategy_id).strip()
    sym = str(symbol).upper().strip()
    mt = str(market_type or "spot").strip().lower()
    if mt not in ("spot", "usdt_futures"):
        mt = "spot"
    if not sid or not sym:
        return None
    for row in list_instances(include_stopped=True):
        if str(row.get("strategy_id")) != sid:
            continue
        if str(row.get("symbol") or "").upper() != sym:
            continue
        if _instance_market_type(row) == mt:
            return row
    return None


def running_instance_symbols() -> list[str]:
    syms = sorted(
        {
            str(r.get("symbol") or "").upper()
            for r in list_instances(include_stopped=False)
            if r.get("status") == "running" and r.get("symbol")
        }
    )
    return syms


def create_instance(
    *,
    strategy_id: str,
    symbol: str,
    operation_mode: str = "paper",
    name: str | None = None,
    session_capital: float | None = None,
    session_volume_mode: str = "stablecoin",
    use_existing_holdings: bool = False,
    existing_holdings_unit: str = "percent",
    existing_holdings_use_pct: float = 0,
    existing_holdings_use_qty: float | None = None,
    liquidate_on_stop: bool = False,
    market_type: str = "spot",
    allow_short: bool = False,
    leverage: int = 3,
    margin_mode: str = "isolated",
    llm_assist_enabled: bool | None = None,
    llm_assist_mode: str | None = None,
    llm_assist_sample_pct: int | None = None,
    operator: str = "web:operator",
) -> dict[str, Any]:
    _ensure_table()
    sid = str(strategy_id).strip()
    sym = str(symbol).upper().strip()
    if not sym:
        raise ValueError("symbol_required")
    mt = str(market_type or "spot").strip().lower()
    if mt not in ("spot", "usdt_futures"):
        raise ValueError(f"invalid_market_type:{market_type}")
    if find_instance_by_strategy_symbol_market(strategy_id=sid, symbol=sym, market_type=mt):
        raise ValueError("duplicate_automation")
    modes = allowed_operation_modes(sid)
    mode = str(operation_mode).strip().lower()
    if mode not in modes:
        raise ValueError(f"invalid_operation_mode:{mode}")
    wf = resolve_crypto_workflow(strategy_id=sid, operation_mode=mode)

    meta = strategy_meta(sid)
    suffix = sym.replace("USDT", "")
    market_tag = "Futures" if mt == "usdt_futures" else "Spot"
    label = str(name or "").strip() or f"{meta.get('label', sid)} · {suffix} · {market_tag}"
    mm = str(margin_mode or "isolated").strip().lower()
    if mm not in ("isolated", "cross"):
        mm = "isolated"
    lev = max(1, min(int(leverage or 1), 20))
    short_ok = bool(allow_short) and mt == "usdt_futures"

    from workflow_session_config_service import _normalize_session_params

    norm = _normalize_session_params(
        market="crypto",
        session_volume_mode=session_volume_mode,
        session_capital=session_capital,
        use_existing_holdings=use_existing_holdings,
        existing_holdings_unit=existing_holdings_unit,
        existing_holdings_use_pct=existing_holdings_use_pct,
        existing_holdings_use_qty=existing_holdings_use_qty,
    )
    session_config: dict[str, Any] = {
        **norm,
        "liquidate_on_stop": bool(liquidate_on_stop),
        "liquidate_on_margin_call": bool(liquidate_on_stop),
        "workflow_name": wf,
        "symbol": sym,
        "strategy_id": sid,
        "market_type": mt,
        "allow_short": short_ok,
        "leverage": lev,
        "margin_mode": mm,
    }

    from llm_assist_service import default_llm_assist_for_strategy

    llm_defaults = default_llm_assist_for_strategy(sid)
    session_config["llm_assist_enabled"] = (
        bool(llm_assist_enabled) if llm_assist_enabled is not None else llm_defaults["enabled"]
    )
    mode = str(llm_assist_mode or llm_defaults["mode"] or "validate_only").strip()
    if mode not in ("disabled", "advisory", "validate_only"):
        mode = "validate_only"
    if not session_config["llm_assist_enabled"]:
        mode = "disabled"
    session_config["llm_assist_mode"] = mode
    sample = llm_assist_sample_pct if llm_assist_sample_pct is not None else llm_defaults["sample_pct"]
    session_config["llm_assist_sample_pct"] = max(0, min(100, int(sample or 0)))

    now = _utc_now()
    inst_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        max_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM crypto_automation_instances"
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO crypto_automation_instances (
                id, name, strategy_id, symbol, workflow_name, operation_mode,
                status, session_config_json, collapsed, sort_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'stopped', ?, 0, ?, ?, ?)
            """,
            (
                inst_id,
                label,
                sid,
                sym,
                wf,
                mode,
                json.dumps(session_config, ensure_ascii=False),
                int(max_order) + 1,
                now,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    log_event(
        market="crypto",
        env="paper",
        stage="reconcile",
        symbol=sym,
        decision="approve",
        workflow_name=wf,
        payload={"action": "automation_instance_created", "instance_id": inst_id, "operator": operator},
    )
    inst = get_instance(inst_id)
    return inst or {"id": inst_id, "status": "stopped"}


def update_instance(
    instance_id: str,
    *,
    name: str | None = None,
    collapsed: bool | None = None,
    sort_order: int | None = None,
    session_config: dict[str, Any] | None = None,
    operator: str = "web:operator",
) -> dict[str, Any]:
    inst = get_instance(instance_id)
    if not inst:
        raise ValueError("instance_not_found")
    if inst.get("status") == "running" and session_config is not None:
        raise ValueError("cannot_edit_session_while_running")

    fields: list[str] = []
    params: list[Any] = []
    if name is not None:
        fields.append("name = ?")
        params.append(str(name).strip())
    if collapsed is not None:
        fields.append("collapsed = ?")
        params.append(1 if collapsed else 0)
    if sort_order is not None:
        fields.append("sort_order = ?")
        params.append(int(sort_order))
    if session_config is not None:
        merged = {**(inst.get("session_config") or {}), **session_config}
        fields.append("session_config_json = ?")
        params.append(json.dumps(merged, ensure_ascii=False))
    if not fields:
        return inst

    fields.append("updated_at = ?")
    params.append(_utc_now())
    params.append(instance_id)

    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE crypto_automation_instances SET {', '.join(fields)} WHERE id = ?",
            params,
        )
        conn.commit()
    finally:
        conn.close()
    out = get_instance(instance_id)
    if not out:
        raise ValueError("instance_not_found")
    return out


def delete_instance(instance_id: str, *, operator: str = "web:operator") -> dict[str, Any]:
    inst = get_instance(instance_id)
    if not inst:
        raise ValueError("instance_not_found")
    stop_result: dict[str, Any] | None = None
    if inst.get("status") == "running":
        stop_result = stop_instance(instance_id, operator=operator)

    conn = get_connection()
    try:
        conn.execute("DELETE FROM crypto_automation_instances WHERE id = ?", (instance_id,))
        conn.commit()
    finally:
        conn.close()
    log_event(
        market="crypto",
        env="paper",
        stage="reconcile",
        symbol=str(inst.get("symbol") or "").upper(),
        decision="halt",
        workflow_name=str(inst.get("workflow_name") or ""),
        payload={"action": "automation_instance_deleted", "instance_id": instance_id},
    )
    return {
        "status": "ok",
        "deleted": instance_id,
        "operator": operator,
        "stop": stop_result,
    }


def _running_instance_symbols(*, exclude_id: str | None = None) -> set[str]:
    out: set[str] = set()
    for row in list_instances(include_stopped=False):
        if row.get("status") != "running":
            continue
        if exclude_id and str(row.get("id")) == exclude_id:
            continue
        sym = str(row.get("symbol") or "").upper().strip()
        if sym:
            out.add(sym)
    return out


def _apply_instance_universe(
    workflow_name: str,
    symbol: str,
    *,
    operator: str,
    instance_id: str | None = None,
) -> None:
    from workflow_universe_service import add_symbols_to_workflow, save_workflow_universe

    sym = symbol.upper()
    peer_symbols = _running_instance_symbols(exclude_id=instance_id)
    if peer_symbols:
        add_symbols_to_workflow(
            workflow_name,
            sorted(peer_symbols | {sym}),
            source="manual",
            enabled=True,
            operator=operator,
            allow_active=True,
        )
        return
    save_workflow_universe(
        workflow_name,
        [{"symbol": sym, "enabled": True, "source": "manual"}],
        operator=operator,
    )


def _push_instance_session_runtime(inst: dict[str, Any]) -> None:
    from runtime_settings import set_runtime_value

    cfg = dict(inst.get("session_config") or {})
    cfg["workflow_name"] = inst.get("workflow_name")
    cfg["symbol"] = inst.get("symbol")
    cfg["instance_id"] = inst.get("id")
    set_runtime_value(
        f"crypto_instance_session:{inst['id']}",
        cfg,
        updated_by="automation_instance",
    )


def start_instance(instance_id: str, *, operator: str = "web:operator") -> dict[str, Any]:
    inst = get_instance(instance_id)
    if not inst:
        raise ValueError("instance_not_found")
    if inst.get("status") == "running":
        return {"status": "ok", "already_running": True, "instance": inst}

    wf = str(inst.get("workflow_name"))
    sym = str(inst.get("symbol")).upper()
    cfg = dict(inst.get("session_config") or {})

    from automation_control_service import (
        add_market_workflow,
        is_multi_automation_enabled,
        set_multi_automation_enabled,
    )

    if not is_multi_automation_enabled("crypto"):
        running = [r for r in list_instances(include_stopped=False) if r.get("status") == "running"]
        if running:
            set_multi_automation_enabled("crypto", True, operator=operator)

    _apply_instance_universe(wf, sym, operator=operator, instance_id=instance_id)

    from workflow_session_config_service import capture_instance_baseline, set_workflow_session_config

    baseline_snapshot = capture_instance_baseline(sym, testnet=True)
    cfg.update(baseline_snapshot)
    now_cfg = _utc_now()
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE crypto_automation_instances
            SET session_config_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (json.dumps(cfg, ensure_ascii=False), now_cfg, instance_id),
        )
        conn.commit()
    finally:
        conn.close()
    inst = dict(inst)
    inst["session_config"] = cfg
    _push_instance_session_runtime(inst)

    set_workflow_session_config(
        "crypto",
        session_capital=cfg.get("session_capital"),
        session_volume_mode=cfg.get("session_volume_mode"),
        use_existing_holdings=bool(cfg.get("use_existing_holdings")),
        existing_holdings_unit=str(cfg.get("existing_holdings_unit") or "percent"),
        existing_holdings_use_pct=float(cfg.get("existing_holdings_use_pct") or 0),
        existing_holdings_use_qty=cfg.get("existing_holdings_use_qty"),
        liquidate_on_stop=bool(cfg.get("liquidate_on_stop")),
        liquidate_on_margin_call=cfg.get("liquidate_on_margin_call"),
        workflow_name=wf,
        operator=operator,
    )

    mode_map = {"dry_run": "dry_run", "paper": "paper", "live": "live"}
    trading_mode = mode_map.get(str(inst.get("operation_mode")), "paper")
    from automation_control_service import set_market_mode

    try:
        set_market_mode("crypto", trading_mode, operator=operator)
    except Exception:
        pass

    try:
        wf_result = add_market_workflow(
            "crypto",
            wf,
            session_capital=cfg.get("session_capital"),
            session_volume_mode=cfg.get("session_volume_mode"),
            use_existing_holdings=bool(cfg.get("use_existing_holdings")),
            existing_holdings_unit=str(cfg.get("existing_holdings_unit") or "percent"),
            existing_holdings_use_pct=float(cfg.get("existing_holdings_use_pct") or 0),
            existing_holdings_use_qty=cfg.get("existing_holdings_use_qty"),
            liquidate_on_stop=bool(cfg.get("liquidate_on_stop")),
            liquidate_on_margin_call=cfg.get("liquidate_on_margin_call"),
            operator=operator,
        )
    except ValueError as exc:
        if "multi_automation_disabled" in str(exc):
            from automation_control_service import select_market_workflow

            set_multi_automation_enabled("crypto", True, operator=operator)
            wf_result = select_market_workflow(
                "crypto",
                wf,
                trading_mode=trading_mode,
                session_capital=cfg.get("session_capital"),
                session_volume_mode=cfg.get("session_volume_mode"),
                use_existing_holdings=bool(cfg.get("use_existing_holdings")),
                existing_holdings_unit=str(cfg.get("existing_holdings_unit") or "percent"),
                existing_holdings_use_pct=float(cfg.get("existing_holdings_use_pct") or 0),
                existing_holdings_use_qty=cfg.get("existing_holdings_use_qty"),
                liquidate_on_stop=bool(cfg.get("liquidate_on_stop")),
                liquidate_on_margin_call=cfg.get("liquidate_on_margin_call"),
                operator=operator,
            )
        else:
            raise

    now = _utc_now()
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE crypto_automation_instances
            SET status = 'running', started_at = ?, stopped_at = NULL, updated_at = ?
            WHERE id = ?
            """,
            (now, now, instance_id),
        )
        conn.commit()
    finally:
        conn.close()

    log_event(
        market="crypto",
        env="paper",
        stage="reconcile",
        symbol=sym,
        decision="approve",
        workflow_name=wf,
        payload={"action": "automation_instance_started", "instance_id": instance_id},
    )
    try:
        reconcile_n8n_workflows_for_running_instances()
    except Exception:
        pass
    updated = get_instance(instance_id)
    return {"status": "ok", "instance": updated, "workflow": wf_result}


def stop_instance(instance_id: str, *, operator: str = "web:operator") -> dict[str, Any]:
    inst = get_instance(instance_id)
    if not inst:
        raise ValueError("instance_not_found")
    if inst.get("status") != "running":
        report = build_instance_session_report(instance_id)
        return {"status": "ok", "already_stopped": True, "instance": inst, "session_report": report}

    wf = str(inst.get("workflow_name"))
    sym = str(inst.get("symbol")).upper()

    from automation_control_service import stop_single_market_workflow

    others = [
        r
        for r in list_instances(include_stopped=False)
        if r.get("status") == "running" and r.get("id") != instance_id and r.get("workflow_name") == wf
    ]
    stop_result: dict[str, Any] | None = None
    if not others:
        stop_result = stop_single_market_workflow("crypto", wf, operator=operator)
    else:
        from workflow_session_config_service import liquidate_session_holdings

        stop_result = liquidate_session_holdings(
            "crypto",
            workflow_name=wf,
            operator=operator,
            reason="stop",
        )

    now = _utc_now()
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE crypto_automation_instances
            SET status = 'stopped', stopped_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (now, now, instance_id),
        )
        conn.commit()
    finally:
        conn.close()

    log_event(
        market="crypto",
        env="paper",
        stage="reconcile",
        symbol=sym,
        decision="halt",
        workflow_name=wf,
        payload={"action": "automation_instance_stopped", "instance_id": instance_id},
    )
    report = build_instance_session_report(instance_id)
    return {
        "status": "ok",
        "instance": get_instance(instance_id),
        "stop": stop_result,
        "session_report": report,
    }


def _instance_events_since_start(
    inst: dict[str, Any],
    *,
    stage: str | None = None,
    decisions: list[str] | None = None,
) -> int:
    started_at = str(inst.get("started_at") or inst.get("created_at") or "")
    sym = str(inst.get("symbol") or "").upper()
    wf = str(inst.get("workflow_name") or "")
    if not started_at or not sym or not wf:
        return 0
    params: list[Any] = [started_at, sym, wf]
    sql = """
        SELECT COUNT(*) AS c FROM trade_events
        WHERE market = 'crypto' AND event_at >= ?
          AND UPPER(COALESCE(symbol, '')) = ?
          AND workflow_name = ?
    """
    if stage:
        sql += " AND stage = ?"
        params.append(stage)
    if decisions:
        sql += f" AND decision IN ({','.join('?' for _ in decisions)})"
        params.extend(decisions)
    conn = get_connection()
    try:
        return int(conn.execute(sql, params).fetchone()["c"] or 0)
    finally:
        conn.close()


def _instance_sum_since_start(
    inst: dict[str, Any],
    column: str,
    *,
    stage: str | None = None,
    decisions: list[str] | None = None,
) -> float:
    started_at = str(inst.get("started_at") or inst.get("created_at") or "")
    sym = str(inst.get("symbol") or "").upper()
    wf = str(inst.get("workflow_name") or "")
    if not started_at or not sym or not wf:
        return 0.0
    if column not in ("notional", "pnl"):
        return 0.0
    params: list[Any] = [started_at, sym, wf]
    sql = f"""
        SELECT COALESCE(SUM(COALESCE({column}, 0)), 0) AS s FROM trade_events
        WHERE market = 'crypto' AND event_at >= ?
          AND UPPER(COALESCE(symbol, '')) = ?
          AND workflow_name = ?
    """
    if stage:
        sql += " AND stage = ?"
        params.append(stage)
    if decisions:
        sql += f" AND decision IN ({','.join('?' for _ in decisions)})"
        params.extend(decisions)
    conn = get_connection()
    try:
        return float(conn.execute(sql, params).fetchone()["s"] or 0.0)
    finally:
        conn.close()


def _session_duration_sec(inst: dict[str, Any]) -> int | None:
    started_at = str(inst.get("started_at") or "")
    if not started_at:
        return None
    end_raw = inst.get("stopped_at") if inst.get("status") != "running" else _utc_now()
    if not end_raw:
        end_raw = _utc_now()
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(end_raw).replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return max(0, int((end - start).total_seconds()))
    except ValueError:
        return None


def _instance_activity_since_start(inst: dict[str, Any]) -> dict[str, Any]:
    started_at = str(inst.get("started_at") or inst.get("created_at") or "")
    sym = str(inst.get("symbol") or "").upper()
    wf = str(inst.get("workflow_name") or "")
    if not started_at or not sym or not wf:
        return {
            "signals": 0,
            "orders_ok": 0,
            "orders_failed": 0,
            "pnl_sum": 0.0,
            "last_event_at": None,
            "last_event_symbol": None,
            "last_event_stage": None,
        }

    conn = get_connection()
    try:
        base_params = [started_at, sym, wf]
        signals = int(
            conn.execute(
                """
                SELECT COUNT(*) AS c FROM trade_events
                WHERE market = 'crypto' AND event_at >= ?
                  AND UPPER(COALESCE(symbol, '')) = ?
                  AND workflow_name = ?
                  AND stage = 'signal'
                """,
                base_params,
            ).fetchone()["c"]
            or 0
        )
        orders_ok = int(
            conn.execute(
                """
                SELECT COUNT(*) AS c FROM trade_events
                WHERE market = 'crypto' AND event_at >= ?
                  AND UPPER(COALESCE(symbol, '')) = ?
                  AND workflow_name = ?
                  AND stage = 'order'
                  AND decision IN ('submitted','execute','executed','approve')
                """,
                base_params,
            ).fetchone()["c"]
            or 0
        )
        orders_failed = int(
            conn.execute(
                """
                SELECT COUNT(*) AS c FROM trade_events
                WHERE market = 'crypto' AND event_at >= ?
                  AND UPPER(COALESCE(symbol, '')) = ?
                  AND workflow_name = ?
                  AND stage = 'order'
                  AND decision IN ('error','reject')
                """,
                base_params,
            ).fetchone()["c"]
            or 0
        )
        pnl_sum = float(
            conn.execute(
                """
                SELECT COALESCE(SUM(pnl), 0) AS s FROM trade_events
                WHERE market = 'crypto' AND event_at >= ?
                  AND UPPER(COALESCE(symbol, '')) = ?
                  AND workflow_name = ?
                """,
                base_params,
            ).fetchone()["s"]
            or 0.0
        )
        last = conn.execute(
            """
            SELECT event_at, symbol, stage FROM trade_events
            WHERE market = 'crypto' AND event_at >= ?
              AND UPPER(COALESCE(symbol, '')) = ?
              AND workflow_name = ?
            ORDER BY event_at DESC
            LIMIT 1
            """,
            base_params,
        ).fetchone()
    finally:
        conn.close()

    return {
        "signals": signals,
        "orders_ok": orders_ok,
        "orders_failed": orders_failed,
        "pnl_sum": pnl_sum,
        "last_event_at": last["event_at"] if last else None,
        "last_event_symbol": last["symbol"] if last else None,
        "last_event_stage": last["stage"] if last else None,
    }


def _instance_order_qty(payload: dict[str, Any]) -> float:
    for key in ("executedQty", "origQty", "qty", "quantity"):
        val = payload.get(key)
        if val is None:
            continue
        try:
            q = float(val)
            if q > 0:
                return q
        except (TypeError, ValueError):
            pass
    return 0.0


def _instance_net_base_qty(inst: dict[str, Any]) -> float:
    """Net base-asset qty bought/sold by this automation since session start."""
    started_at = str(inst.get("started_at") or "")
    if not started_at:
        return 0.0
    sym = str(inst.get("symbol") or "").upper()
    wf = str(inst.get("workflow_name") or "")
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT payload_json FROM trade_events
            WHERE market = 'crypto' AND event_at >= ?
              AND UPPER(COALESCE(symbol, '')) = ?
              AND workflow_name = ?
              AND stage = 'order'
              AND decision IN ('execute', 'executed', 'submitted', 'approve')
            ORDER BY event_at ASC
            """,
            (started_at, sym, wf),
        ).fetchall()
    finally:
        conn.close()

    net = 0.0
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            continue
        side = str(payload.get("side") or "BUY").upper()
        qty = _instance_order_qty(payload)
        if qty <= 0:
            continue
        if side == "SELL":
            net = max(0.0, net - qty)
        elif side == "BUY":
            net += qty
    return round(net, 8)


def _instance_managed_base_qty(
    inst: dict[str, Any],
    *,
    sym: str,
    cfg: dict[str, Any],
    wf: str,
    quote: str,
    testnet: bool = True,
) -> float:
    """Session-scoped base qty — excludes pre-session exchange holdings."""
    if not inst.get("started_at"):
        return 0.0

    db_net = _instance_net_base_qty(inst)
    merged_cfg = dict(cfg)
    if inst.get("status") == "running":
        from workflow_session_config_service import get_workflow_session_config

        runtime = get_workflow_session_config("crypto", symbol=sym, workflow_name=wf)
        for key in ("holdings_baseline", "baseline_captured_at", "session_volume_mode"):
            if key in runtime:
                merged_cfg[key] = runtime[key]

    if merged_cfg.get("holdings_baseline") or merged_cfg.get("baseline_captured_at"):
        from workflow_session_config_service import compute_managed_qty, _wallet_base_qty

        wallet = _wallet_base_qty(sym, testnet=testnet, quote=quote)
        breakdown = compute_managed_qty(
            sym,
            wallet_qty=wallet,
            db_session_net=db_net,
            cfg=merged_cfg,
            market="crypto",
        )
        return float(breakdown.get("managed_qty") or 0.0)
    return db_net

def get_instance_session_stats(instance_id: str) -> dict[str, Any]:
    """Activity since instance started_at (live session scope)."""
    inst = get_instance(instance_id)
    if not inst:
        raise ValueError("instance_not_found")

    activity = _instance_activity_since_start(inst)
    pnl_sum = float(activity.get("pnl_sum") or 0.0)
    cap_raw = (inst.get("session_config") or {}).get("session_capital")
    cap: float | None = None
    if cap_raw is not None:
        try:
            cap = float(cap_raw)
        except (TypeError, ValueError):
            cap = None

    pnl_pct: float | None = None
    if cap and cap > 0:
        pnl_pct = round(pnl_sum / cap * 100, 4)

    if pnl_sum > 0:
        pnl_direction = "up"
    elif pnl_sum < 0:
        pnl_direction = "down"
    else:
        pnl_direction = "flat"

    invested = _instance_sum_since_start(
        inst,
        "notional",
        stage="order",
        decisions=["execute", "submitted", "executed", "approve"],
    )

    return {
        "instance_id": instance_id,
        "symbol": str(inst.get("symbol") or "").upper(),
        "workflow_name": str(inst.get("workflow_name") or ""),
        "scope": "session",
        "started_at": inst.get("started_at"),
        "stopped_at": inst.get("stopped_at"),
        "duration_sec": _session_duration_sec(inst),
        "session_capital": round(cap, 2) if cap else None,
        "events": int(activity.get("signals") or 0)
        + _instance_events_since_start(inst, stage="filter")
        + _instance_events_since_start(inst, stage="order"),
        "signals": int(activity.get("signals") or 0),
        "orders": int(activity.get("orders_ok") or 0),
        "orders_ok": int(activity.get("orders_ok") or 0),
        "orders_failed": int(activity.get("orders_failed") or 0),
        "filter_approve": _instance_events_since_start(inst, stage="filter", decisions=["approve"]),
        "filter_skip": _instance_events_since_start(inst, stage="filter", decisions=["skip"]),
        "filter_reject": _instance_events_since_start(inst, stage="filter", decisions=["reject"]),
        "guardrails_reject": _instance_events_since_start(inst, stage="guardrails", decisions=["reject"]),
        "invested_notional": round(invested, 2),
        "pnl_sum": round(pnl_sum, 4),
        "pnl_pct": pnl_pct,
        "pnl_direction": pnl_direction,
        "currency": "USDT",
        "status": inst.get("status"),
        "last_event_at": activity.get("last_event_at"),
    }


def _instance_trades_since_start(inst: dict[str, Any], *, limit: int = 30) -> list[dict[str, Any]]:
    started_at = str(inst.get("started_at") or inst.get("created_at") or "")
    sym = str(inst.get("symbol") or "").upper()
    wf = str(inst.get("workflow_name") or "")
    if not started_at:
        return []
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT event_at, symbol, decision, notional, currency, payload_json
            FROM trade_events
            WHERE market = 'crypto' AND event_at >= ?
              AND UPPER(COALESCE(symbol, '')) = ?
              AND workflow_name = ?
              AND stage = 'order'
              AND decision IN ('execute', 'submitted', 'executed', 'approve', 'error', 'reject')
            ORDER BY event_at DESC
            LIMIT ?
            """,
            (started_at, sym, wf, int(limit)),
        ).fetchall()
    finally:
        conn.close()

    out: list[dict[str, Any]] = []
    for row in rows:
        from automation_equity_service import trade_row_from_event

        out.append(trade_row_from_event(row, default_currency="USDT"))
    return out


def build_instance_session_report(instance_id: str) -> dict[str, Any]:
    inst = get_instance(instance_id)
    if not inst:
        raise ValueError("instance_not_found")
    stats = get_instance_session_stats(instance_id)
    return {
        "instance_id": instance_id,
        "name": inst.get("name"),
        "strategy_id": inst.get("strategy_id"),
        "symbol": stats.get("symbol"),
        "workflow_name": stats.get("workflow_name"),
        "started_at": stats.get("started_at"),
        "ended_at": inst.get("stopped_at") or _utc_now(),
        "duration_sec": stats.get("duration_sec"),
        "session_capital": stats.get("session_capital"),
        "statistics": {
            "signals": stats.get("signals"),
            "filter_approve": stats.get("filter_approve"),
            "filter_skip": stats.get("filter_skip"),
            "filter_reject": stats.get("filter_reject"),
            "guardrails_reject": stats.get("guardrails_reject"),
            "orders_ok": stats.get("orders_ok"),
            "orders_failed": stats.get("orders_failed"),
            "invested_notional": stats.get("invested_notional"),
        },
        "pnl_sum": stats.get("pnl_sum"),
        "pnl_pct": stats.get("pnl_pct"),
        "pnl_direction": stats.get("pnl_direction"),
        "currency": stats.get("currency"),
        "trades": _instance_trades_since_start(inst),
    }


def get_instance_wallet(instance_id: str) -> dict[str, Any]:
    inst = get_instance(instance_id)
    if not inst:
        raise ValueError("instance_not_found")

    sym = str(inst.get("symbol") or "").upper()
    cfg = dict(inst.get("session_config") or {})
    wf = str(inst.get("workflow_name") or "")

    from crypto_product import get_crypto_trading_product_for_trade
    from crypto_quote import get_crypto_quote_asset, symbol_base_asset
    from effective_config import get_config_effective

    crypto_cfg = get_config_effective("crypto_config")
    product = get_crypto_trading_product_for_trade(
        cfg=crypto_cfg, symbol=sym, workflow_name=wf, session_config=cfg
    )
    quote = str(cfg.get("quote_asset") or get_crypto_quote_asset()).upper()
    cap = cfg.get("session_capital")
    rows: list[dict[str, Any]] = []

    if cap is not None:
        try:
            cap_f = float(cap)
            if cap_f > 0:
                rows.append(
                    {
                        "asset": quote,
                        "label": "session_budget",
                        "quantity": round(cap_f, 2),
                        "usdt_value": round(cap_f, 2),
                    }
                )
        except (TypeError, ValueError):
            pass

    if product.get("is_futures"):
        from binance_futures_client import get_futures_positions

        for pos in get_futures_positions(testnet=True, symbol=sym):
            if str(pos.get("symbol") or "").upper() != sym:
                continue
            amt = float(pos.get("position_amt") or 0)
            if abs(amt) < 1e-12:
                continue
            if not inst.get("started_at"):
                continue
            mark = float(pos.get("mark_price") or pos.get("entry_price") or 0)
            rows.append(
                {
                    "asset": sym,
                    "label": "futures_position",
                    "quantity": round(amt, 8),
                    "entry_price": pos.get("entry_price"),
                    "unrealized_pnl": pos.get("unrealized_profit"),
                    "usdt_value": round(abs(amt) * mark, 2) if mark else None,
                }
            )
    else:
        base = symbol_base_asset(sym, quote=quote)
        managed_qty = _instance_managed_base_qty(
            inst, sym=sym, cfg=cfg, wf=wf, quote=quote, testnet=True
        )
        if managed_qty > 0:
            from binance_trading import get_market_price

            price = get_market_price(sym, testnet=True, cfg=crypto_cfg)
            usdt_val = round(managed_qty * price, 2) if price else None
            rows.append(
                {
                    "asset": base,
                    "label": "session_position",
                    "quantity": round(managed_qty, 8),
                    "usdt_value": usdt_val,
                }
            )

        if inst.get("started_at") and cap is not None:
            try:
                cap_f = float(cap)
            except (TypeError, ValueError):
                cap_f = 0.0
            if cap_f > 0 and cfg.get("session_volume_mode", "stablecoin") in ("stablecoin", "combined"):
                invested = _instance_sum_since_start(
                    inst,
                    "notional",
                    stage="order",
                    decisions=["execute", "submitted", "executed", "approve"],
                )
                remaining = max(0.0, cap_f - float(invested or 0))
                if remaining < cap_f - 1e-6 or managed_qty > 0:
                    rows.append(
                        {
                            "asset": quote,
                            "label": "session_quote_available",
                            "quantity": round(remaining, 2),
                            "usdt_value": round(remaining, 2),
                        }
                    )

    return {
        "status": "ok",
        "instance_id": instance_id,
        "symbol": sym,
        "market_type": product.get("market_type"),
        "session_capital": cap,
        "rows": rows,
    }


def get_instance_stats(instance_id: str, *, days: int = 7, session: bool = False) -> dict[str, Any]:
    if session:
        return get_instance_session_stats(instance_id)
    inst = get_instance(instance_id)
    if not inst:
        raise ValueError("instance_not_found")
    sym = str(inst.get("symbol")).upper()
    wf = str(inst.get("workflow_name"))
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS events,
                SUM(CASE WHEN stage = 'order' AND decision IN ('execute','submitted') THEN 1 ELSE 0 END) AS orders,
                SUM(COALESCE(pnl, 0)) AS pnl_sum
            FROM trade_events
            WHERE market = 'crypto'
              AND UPPER(COALESCE(symbol, '')) = ?
              AND workflow_name = ?
              AND datetime(REPLACE(SUBSTR(event_at, 1, 19), 'T', ' ')) >= datetime('now', ?)
            """,
            (sym, wf, f"-{int(days)} days"),
        ).fetchone()
    finally:
        conn.close()

    events = int(row["events"] or 0) if row else 0
    orders = int(row["orders"] or 0) if row else 0
    pnl_sum = float(row["pnl_sum"] or 0) if row else 0.0

    pnl_pct: float | None = None
    cap = (inst.get("session_config") or {}).get("session_capital")
    if cap and float(cap) > 0:
        pnl_pct = round(pnl_sum / float(cap) * 100, 4)

    return {
        "instance_id": instance_id,
        "symbol": sym,
        "workflow_name": wf,
        "days": days,
        "events": events,
        "orders": orders,
        "pnl_sum": round(pnl_sum, 4),
        "pnl_pct": pnl_pct,
        "status": inst.get("status"),
    }


_MODE_RANK = {"dry_run": 1, "paper": 2, "live": 3}


def _dominant_operation_mode(modes: list[str]) -> str | None:
    if not modes:
        return None
    return max(modes, key=lambda m: _MODE_RANK.get(str(m).lower(), 0))


def summarize_instances_for_overview() -> dict[str, Any]:
    """Aggregate running automation tabs for status bar / overview."""
    _ensure_table()
    all_inst = list_instances(include_stopped=True)
    if not all_inst:
        return {"has_instances": False}

    running = [i for i in all_inst if i.get("status") == "running"]
    running_symbols = sorted({str(i.get("symbol") or "").upper() for i in running if i.get("symbol")})
    active_workflows = sorted({str(i.get("workflow_name") or "") for i in running if i.get("workflow_name")})

    started_times = [str(i.get("started_at")) for i in running if i.get("started_at")]
    earliest_started_at = min(started_times) if started_times else None

    total_signals = 0
    total_orders_ok = 0
    total_orders_failed = 0
    total_pnl = 0.0
    total_capital = 0.0
    last_event_at: str | None = None
    last_event_symbol: str | None = None
    last_event_stage: str | None = None

    for inst in running:
        act = _instance_activity_since_start(inst)
        total_signals += int(act["signals"])
        total_orders_ok += int(act["orders_ok"])
        total_orders_failed += int(act["orders_failed"])
        total_pnl += float(act["pnl_sum"])
        cap = (inst.get("session_config") or {}).get("session_capital")
        if cap is not None:
            try:
                total_capital += float(cap)
            except (TypeError, ValueError):
                pass
        ev_at = act.get("last_event_at")
        if ev_at and (last_event_at is None or str(ev_at) > str(last_event_at)):
            last_event_at = str(ev_at)
            last_event_symbol = act.get("last_event_symbol")
            last_event_stage = act.get("last_event_stage")

    pnl_pct: float | None = None
    if total_capital > 0:
        pnl_pct = round(total_pnl / total_capital * 100, 2)

    if total_pnl > 0:
        pnl_direction = "up"
    elif total_pnl < 0:
        pnl_direction = "down"
    else:
        pnl_direction = "flat"

    ago_sec: int | None = None
    if last_event_at:
        try:
            ts = datetime.fromisoformat(str(last_event_at).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            ago_sec = max(0, int((datetime.now(timezone.utc) - ts).total_seconds()))
        except ValueError:
            ago_sec = None

    open_positions = 0
    max_open = 0
    if running:
        try:
            from effective_config import get_guardrails
            from risk_profile_service import get_max_open_positions
            from risk_trading_state import count_open_positions

            guardrails = get_guardrails()
            trading = guardrails.get("trading", {})
            open_positions = count_open_positions("crypto")
            max_open = get_max_open_positions("crypto", trading)
        except Exception:
            pass

    workflow_session: dict[str, Any] | None = None
    if running:
        workflow_session = {
            "status": "ok",
            "started_at": earliest_started_at,
            "active_workflow": active_workflows[0] if len(active_workflows) == 1 else None,
            "signals": total_signals,
            "orders_ok": total_orders_ok,
            "orders_failed": total_orders_failed,
            "open_positions": open_positions,
            "max_open_positions": max_open,
            "pnl_delta": round(total_pnl, 4),
            "pnl_pct": pnl_pct,
            "pnl_direction": pnl_direction,
            "currency": "USDT",
            "pnl_source": "session_trades",
            "session_capital": round(total_capital, 2) if total_capital > 0 else None,
            "last_event_at": last_event_at,
            "last_event_ago_sec": ago_sec,
            "last_event_symbol": last_event_symbol,
            "last_event_stage": last_event_stage,
            "instances_running": len(running),
            "instances_total": len(all_inst),
            "running_symbols": running_symbols,
        }

    return {
        "has_instances": True,
        "total_count": len(all_inst),
        "running_count": len(running),
        "stopped_count": len(all_inst) - len(running),
        "running_symbols": running_symbols,
        "active_workflows": active_workflows,
        "earliest_started_at": earliest_started_at,
        "operation_mode": _dominant_operation_mode(
            [str(i.get("operation_mode") or "") for i in running]
        ),
        "workflow_session": workflow_session,
    }


def reconcile_n8n_workflows_for_running_instances() -> list[str]:
    """Re-activate n8n workflows for crypto instances marked running in DB."""
    _ensure_table()
    running = [i for i in list_instances(include_stopped=False) if i.get("status") == "running"]
    if not running:
        return []

    from n8n_service import activate_workflow, list_workflows

    try:
        by_name = {str(w.get("name")): w for w in list_workflows()}
    except Exception:
        return []

    activated: list[str] = []
    for wf_name in sorted({str(i.get("workflow_name") or "") for i in running if i.get("workflow_name")}):
        wf = by_name.get(wf_name)
        if not wf or wf.get("active"):
            continue
        try:
            activate_workflow(str(wf["id"]))
            activated.append(wf_name)
        except Exception:
            continue

    handler = by_name.get("shared-global-error-handler")
    if handler and not handler.get("active"):
        try:
            activate_workflow(str(handler["id"]))
        except Exception:
            pass

    return activated
