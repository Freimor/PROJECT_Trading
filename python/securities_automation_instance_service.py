"""Per-automation MOEX/securities instances (tabs in console)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from db.connection import get_connection
from event_log import log_event
from securities_workflow_map import (
    allowed_operation_modes,
    resolve_securities_workflow,
    strategy_meta,
    supports_multi_symbol,
)

INSTANCE_STATUSES = ("stopped", "running", "error")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_table() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS securities_automation_instances (
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
            "CREATE INDEX IF NOT EXISTS idx_sec_auto_inst_status "
            "ON securities_automation_instances(status)"
        )
        conn.commit()
    finally:
        conn.close()


def _normalize_symbols(symbols: list[str] | str) -> list[str]:
    if isinstance(symbols, str):
        raw = [symbols]
    else:
        raw = list(symbols)
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        sym = str(item).upper().strip()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        out.append(sym)
    return out


def _symbols_fingerprint(symbols: list[str]) -> str:
    return "|".join(sorted(_normalize_symbols(symbols)))


def _instance_symbols(row: dict[str, Any]) -> list[str]:
    cfg = row.get("session_config") or {}
    syms = cfg.get("symbols")
    if isinstance(syms, list) and syms:
        return _normalize_symbols(syms)
    sym = str(row.get("symbol") or "").upper().strip()
    return [sym] if sym else []


def _row_to_dict(row: Any) -> dict[str, Any]:
    data = dict(row)
    try:
        data["session_config"] = json.loads(str(data.pop("session_config_json") or "{}"))
    except json.JSONDecodeError:
        data["session_config"] = {}
    data["collapsed"] = bool(data.get("collapsed"))
    syms = _instance_symbols(data)
    data["symbols"] = syms
    return data


def list_instances(*, include_stopped: bool = True) -> list[dict[str, Any]]:
    _ensure_table()
    conn = get_connection()
    try:
        q = "SELECT * FROM securities_automation_instances"
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
            "SELECT * FROM securities_automation_instances WHERE id = ?",
            (instance_id,),
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def find_instance_by_strategy_symbols(
    *, strategy_id: str, symbols: list[str]
) -> dict[str, Any] | None:
    sid = str(strategy_id).strip()
    fp = _symbols_fingerprint(symbols)
    if not sid or not fp:
        return None
    for row in list_instances(include_stopped=True):
        if str(row.get("strategy_id")) != sid:
            continue
        if _symbols_fingerprint(_instance_symbols(row)) == fp:
            return row
    return None


def _automation_label(strategy_id: str, symbols: list[str]) -> str:
    meta = strategy_meta(strategy_id)
    base = str(meta.get("label") or strategy_id)
    if len(symbols) == 1:
        tail = symbols[0]
    elif len(symbols) <= 3:
        tail = ", ".join(symbols)
    else:
        tail = f"{symbols[0]} +{len(symbols) - 1}"
    return f"{base} · {tail}"


def create_instance(
    *,
    strategy_id: str,
    symbols: list[str],
    operation_mode: str = "paper",
    name: str | None = None,
    session_capital: float | None = None,
    session_volume_mode: str = "stablecoin",
    use_existing_holdings: bool = False,
    existing_holdings_unit: str = "percent",
    existing_holdings_use_pct: float = 0,
    existing_holdings_use_qty: float | None = None,
    operator: str = "web:operator",
) -> dict[str, Any]:
    _ensure_table()
    sid = str(strategy_id).strip()
    syms = _normalize_symbols(symbols)
    if not syms:
        raise ValueError("symbols_required")
    if not supports_multi_symbol(sid) and len(syms) != 1:
        raise ValueError("single_symbol_strategy")
    if find_instance_by_strategy_symbols(strategy_id=sid, symbols=syms):
        raise ValueError("duplicate_automation")
    modes = allowed_operation_modes(sid)
    mode = str(operation_mode).strip().lower()
    if mode not in modes:
        raise ValueError(f"invalid_operation_mode:{mode}")
    wf = resolve_securities_workflow(strategy_id=sid, operation_mode=mode)
    label = str(name or "").strip() or _automation_label(sid, syms)
    primary = syms[0]

    from workflow_session_config_service import _normalize_session_params

    norm = _normalize_session_params(
        market="securities",
        session_volume_mode=session_volume_mode,
        session_capital=session_capital,
        use_existing_holdings=use_existing_holdings,
        existing_holdings_unit=existing_holdings_unit,
        existing_holdings_use_pct=existing_holdings_use_pct,
        existing_holdings_use_qty=existing_holdings_use_qty,
    )
    session_config: dict[str, Any] = {
        **norm,
        "liquidate_on_stop": False,
        "workflow_name": wf,
        "symbol": primary,
        "symbols": syms,
        "strategy_id": sid,
        "currency": "RUB",
    }

    now = _utc_now()
    inst_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        max_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM securities_automation_instances"
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO securities_automation_instances (
                id, name, strategy_id, symbol, workflow_name, operation_mode,
                status, session_config_json, collapsed, sort_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'stopped', ?, 0, ?, ?, ?)
            """,
            (
                inst_id,
                label,
                sid,
                primary,
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
        market="securities",
        env="paper",
        stage="reconcile",
        symbol=primary,
        decision="approve",
        workflow_name=wf,
        payload={
            "action": "automation_instance_created",
            "instance_id": inst_id,
            "symbols": syms,
            "operator": operator,
        },
    )
    return get_instance(inst_id) or {"id": inst_id, "status": "stopped"}


def update_instance(
    instance_id: str,
    *,
    name: str | None = None,
    collapsed: bool | None = None,
    sort_order: int | None = None,
    operator: str = "web:operator",
) -> dict[str, Any]:
    inst = get_instance(instance_id)
    if not inst:
        raise ValueError("instance_not_found")

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
    if not fields:
        return inst

    fields.append("updated_at = ?")
    params.append(_utc_now())
    params.append(instance_id)

    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE securities_automation_instances SET {', '.join(fields)} WHERE id = ?",
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
        conn.execute("DELETE FROM securities_automation_instances WHERE id = ?", (instance_id,))
        conn.commit()
    finally:
        conn.close()
    log_event(
        market="securities",
        env="paper",
        stage="reconcile",
        symbol=str(inst.get("symbol") or "").upper(),
        decision="halt",
        workflow_name=str(inst.get("workflow_name") or ""),
        payload={"action": "automation_instance_deleted", "instance_id": instance_id},
    )
    return {"status": "ok", "deleted": instance_id, "operator": operator, "stop": stop_result}


def _running_instance_symbols(*, exclude_id: str | None = None) -> set[str]:
    out: set[str] = set()
    for row in list_instances(include_stopped=False):
        if row.get("status") != "running":
            continue
        if exclude_id and str(row.get("id")) == exclude_id:
            continue
        out.update(_instance_symbols(row))
    return out


def _apply_instance_universe(
    workflow_name: str,
    symbols: list[str],
    *,
    operator: str,
    instance_id: str | None = None,
) -> None:
    from workflow_universe_service import add_symbols_to_workflow, save_workflow_universe

    syms = _normalize_symbols(symbols)
    peer_symbols = _running_instance_symbols(exclude_id=instance_id)
    merged = sorted(peer_symbols | set(syms))
    items = [{"symbol": s, "enabled": True, "source": "manual"} for s in merged]
    if peer_symbols:
        add_symbols_to_workflow(
            workflow_name,
            merged,
            source="manual",
            enabled=True,
            operator=operator,
            allow_active=True,
        )
        return
    save_workflow_universe(workflow_name, items, operator=operator)


def _push_instance_session_runtime(inst: dict[str, Any]) -> None:
    from runtime_settings import set_runtime_value

    cfg = dict(inst.get("session_config") or {})
    cfg["workflow_name"] = inst.get("workflow_name")
    cfg["symbol"] = inst.get("symbol")
    cfg["symbols"] = _instance_symbols(inst)
    cfg["instance_id"] = inst.get("id")
    set_runtime_value(
        f"securities_instance_session:{inst['id']}",
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
    syms = _instance_symbols(inst)
    primary = syms[0] if syms else str(inst.get("symbol") or "").upper()
    cfg = dict(inst.get("session_config") or {})

    from automation_control_service import (
        add_market_workflow,
        is_multi_automation_enabled,
        set_multi_automation_enabled,
    )

    if not is_multi_automation_enabled("securities"):
        running = [r for r in list_instances(include_stopped=False) if r.get("status") == "running"]
        if running:
            set_multi_automation_enabled("securities", True, operator=operator)

    _apply_instance_universe(wf, syms, operator=operator, instance_id=instance_id)

    from workflow_session_config_service import capture_securities_instance_baseline, set_workflow_session_config

    baseline_snapshot = capture_securities_instance_baseline(syms, sandbox=True)
    cfg.update(baseline_snapshot)
    now_cfg = _utc_now()
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE securities_automation_instances
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
        "securities",
        session_capital=cfg.get("session_capital"),
        session_volume_mode=cfg.get("session_volume_mode"),
        use_existing_holdings=bool(cfg.get("use_existing_holdings")),
        existing_holdings_unit=str(cfg.get("existing_holdings_unit") or "percent"),
        existing_holdings_use_pct=float(cfg.get("existing_holdings_use_pct") or 0),
        existing_holdings_use_qty=cfg.get("existing_holdings_use_qty"),
        liquidate_on_stop=False,
        workflow_name=wf,
        operator=operator,
    )

    mode_map = {"dry_run": "dry_run", "paper": "paper", "live": "live"}
    trading_mode = mode_map.get(str(inst.get("operation_mode")), "paper")
    from automation_control_service import set_market_mode

    try:
        set_market_mode("securities", trading_mode, operator=operator)
    except Exception:
        pass

    try:
        wf_result = add_market_workflow(
            "securities",
            wf,
            session_capital=cfg.get("session_capital"),
            session_volume_mode=cfg.get("session_volume_mode"),
            use_existing_holdings=bool(cfg.get("use_existing_holdings")),
            existing_holdings_unit=str(cfg.get("existing_holdings_unit") or "percent"),
            existing_holdings_use_pct=float(cfg.get("existing_holdings_use_pct") or 0),
            existing_holdings_use_qty=cfg.get("existing_holdings_use_qty"),
            liquidate_on_stop=False,
            operator=operator,
        )
    except ValueError as exc:
        if "multi_automation_disabled" in str(exc):
            set_multi_automation_enabled("securities", True, operator=operator)
            from automation_control_service import select_market_workflow

            wf_result = select_market_workflow(
                "securities",
                wf,
                trading_mode=trading_mode,
                session_capital=cfg.get("session_capital"),
                session_volume_mode=cfg.get("session_volume_mode"),
                use_existing_holdings=bool(cfg.get("use_existing_holdings")),
                existing_holdings_unit=str(cfg.get("existing_holdings_unit") or "percent"),
                existing_holdings_use_pct=float(cfg.get("existing_holdings_use_pct") or 0),
                existing_holdings_use_qty=cfg.get("existing_holdings_use_qty"),
                liquidate_on_stop=False,
                operator=operator,
            )
        else:
            raise

    now = _utc_now()
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE securities_automation_instances
            SET status = 'running', started_at = ?, stopped_at = NULL, updated_at = ?
            WHERE id = ?
            """,
            (now, now, instance_id),
        )
        conn.commit()
    finally:
        conn.close()

    log_event(
        market="securities",
        env="paper",
        stage="reconcile",
        symbol=primary,
        decision="approve",
        workflow_name=wf,
        payload={"action": "automation_instance_started", "instance_id": instance_id, "symbols": syms},
    )
    try:
        reconcile_n8n_workflows_for_running_instances()
    except Exception:
        pass
    return {"status": "ok", "instance": get_instance(instance_id), "workflow": wf_result}


def stop_instance(instance_id: str, *, operator: str = "web:operator") -> dict[str, Any]:
    inst = get_instance(instance_id)
    if not inst:
        raise ValueError("instance_not_found")
    if inst.get("status") != "running":
        return {"status": "ok", "already_stopped": True, "instance": inst}

    wf = str(inst.get("workflow_name"))
    primary = str(inst.get("symbol") or "").upper()

    from automation_control_service import stop_single_market_workflow

    others = [
        r
        for r in list_instances(include_stopped=False)
        if r.get("status") == "running" and r.get("id") != instance_id and r.get("workflow_name") == wf
    ]
    stop_result: dict[str, Any] | None = None
    if not others:
        stop_result = stop_single_market_workflow("securities", wf, operator=operator)

    now = _utc_now()
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE securities_automation_instances
            SET status = 'stopped', stopped_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (now, now, instance_id),
        )
        conn.commit()
    finally:
        conn.close()

    log_event(
        market="securities",
        env="paper",
        stage="reconcile",
        symbol=primary,
        decision="halt",
        workflow_name=wf,
        payload={"action": "automation_instance_stopped", "instance_id": instance_id},
    )
    return {"status": "ok", "instance": get_instance(instance_id), "stop": stop_result}


def get_instance_stats(instance_id: str, *, days: int = 7) -> dict[str, Any]:
    inst = get_instance(instance_id)
    if not inst:
        raise ValueError("instance_not_found")
    syms = _instance_symbols(inst)
    wf = str(inst.get("workflow_name"))
    placeholders = ",".join("?" for _ in syms)
    conn = get_connection()
    try:
        row = conn.execute(
            f"""
            SELECT
                COUNT(*) AS events,
                SUM(CASE WHEN stage = 'order' AND decision IN ('execute','submitted') THEN 1 ELSE 0 END) AS orders,
                SUM(COALESCE(pnl, 0)) AS pnl_sum
            FROM trade_events
            WHERE market = 'securities'
              AND UPPER(COALESCE(symbol, '')) IN ({placeholders})
              AND workflow_name = ?
              AND datetime(REPLACE(SUBSTR(event_at, 1, 19), 'T', ' ')) >= datetime('now', ?)
            """,
            (*syms, wf, f"-{int(days)} days"),
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
        "symbol": inst.get("symbol"),
        "symbols": syms,
        "workflow_name": wf,
        "days": days,
        "events": events,
        "orders": orders,
        "pnl_sum": round(pnl_sum, 4),
        "pnl_pct": pnl_pct,
        "status": inst.get("status"),
    }


def summarize_instances_for_overview() -> dict[str, Any]:
    """Aggregate running MOEX automation tabs for status bar / overview."""
    _ensure_table()
    all_inst = list_instances(include_stopped=True)
    if not all_inst:
        return {"has_instances": False}

    running = [i for i in all_inst if i.get("status") == "running"]
    running_symbols: list[str] = []
    for inst in running:
        for sym in _instance_symbols(inst):
            if sym and sym not in running_symbols:
                running_symbols.append(sym)
    running_symbols.sort()

    active_workflows = sorted(
        {str(i.get("workflow_name") or "") for i in running if i.get("workflow_name")}
    )
    started_times = [str(i.get("started_at")) for i in running if i.get("started_at")]
    earliest_started_at = min(started_times) if started_times else None

    total_capital = 0.0
    total_pnl = 0.0
    for inst in running:
        cap = (inst.get("session_config") or {}).get("session_capital")
        if cap is not None:
            try:
                total_capital += float(cap)
            except (TypeError, ValueError):
                pass
        stats = get_instance_stats(str(inst["id"]), days=7)
        total_pnl += float(stats.get("pnl_sum") or 0)

    pnl_pct: float | None = None
    if total_capital > 0:
        pnl_pct = round(total_pnl / total_capital * 100, 2)

    return {
        "has_instances": True,
        "total_count": len(all_inst),
        "running_count": len(running),
        "stopped_count": len(all_inst) - len(running),
        "running_symbols": running_symbols,
        "active_workflows": active_workflows,
        "earliest_started_at": earliest_started_at,
        "operation_mode": "demo",
        "workflow_session": {
            "status": "ok" if running else "inactive",
            "started_at": earliest_started_at,
            "instances_running": len(running),
            "instances_total": len(all_inst),
            "running_symbols": running_symbols,
            "pnl_pct": pnl_pct,
            "currency": "RUB",
        }
        if running
        else None,
    }


def reconcile_n8n_workflows_for_running_instances() -> list[str]:
    """Re-activate n8n workflows for instances marked running in DB."""
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
