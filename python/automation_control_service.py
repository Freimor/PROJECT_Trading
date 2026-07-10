"""Runtime trading mode and n8n automation profile management."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from activity_feed_service import log_system_activity
from config_loader import load_config
from n8n_service import activate_workflow, deactivate_workflow, list_workflows
from runtime_settings import delete_runtime_value, get_runtime_meta, get_runtime_value, set_runtime_value

VALID_MODES = ("dry_run", "paper", "shadow", "live")
OPERATION_MODES = ("demo", "live")

# UI-facing modes: demo = testnet/sandbox trading; live = real money.
# dry_run/shadow remain internal (CI, signal-only); selecting Demo always uses paper.
OPERATION_TO_TRADING: dict[str, str] = {
    "demo": "paper",
    "live": "live",
}


def normalize_trading_mode(mode: str) -> str:
    normalized = str(mode).strip().lower()
    if normalized == "demo":
        return "paper"
    if normalized not in VALID_MODES:
        raise ValueError(f"invalid_mode: {mode}")
    return normalized


def trading_mode_to_operation(mode: str) -> str:
    if str(mode).strip().lower() == "live":
        return "live"
    return "demo"


def operation_mode_detail(trading_mode: str) -> str:
    """Human hint: paper testnet vs signal-only dry_run."""
    tm = str(trading_mode).strip().lower()
    if tm == "live":
        return "live"
    if tm == "dry_run":
        return "signals_only"
    if tm == "shadow":
        return "shadow"
    return "testnet_sandbox"

TRADING_WORKFLOWS = (
    "crypto-signal-dry-run",
    "crypto-signal-paper",
    "crypto-scalp-hybrid-dry-run",
    "crypto-scalp-hybrid-paper",
    "crypto-monitor-testnet",
    "securities-swing-dry-run",
    "securities-swing-paper",
    "securities-dca-sandbox",
)

MARKET_CONFIG = {
    "crypto": "crypto_config",
    "securities": "securities_config",
}

MARKET_RUNTIME_KEY = {
    "crypto": "crypto_mode",
    "securities": "securities_mode",
}

WORKFLOW_STARTED_KEY = {
    "crypto": "crypto_workflow_started_at",
    "securities": "securities_workflow_started_at",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_active_market_workflow(market: str) -> str | None:
    """Return the active primary (exclusive) n8n workflow for the market, if any."""
    if market not in MARKET_CONFIG:
        return None
    exclusive = MARKET_EXCLUSIVE_WORKFLOWS.get(market, frozenset())
    concurrent = MARKET_CONCURRENT_WORKFLOWS.get(market, frozenset())
    try:
        active_exclusive: list[str] = []
        for wf in list_workflows():
            name = str(wf.get("name") or "")
            if not wf.get("active"):
                continue
            if name in exclusive:
                active_exclusive.append(name)
            elif name in concurrent:
                continue
            elif name in MARKET_WORKFLOW_SET.get(market, frozenset()):
                active_exclusive.append(name)
        if len(active_exclusive) == 1:
            return active_exclusive[0]
        if len(active_exclusive) > 1:
            primary = _primary_workflow_for_market(market)
            if primary in active_exclusive:
                return primary
            return sorted(active_exclusive)[0]
    except Exception:
        return None
    return None


def _mark_workflow_started(market: str, *, operator: str) -> str:
    ts = _utc_now()
    set_runtime_value(WORKFLOW_STARTED_KEY[market], ts, updated_by=operator)
    try:
        from workflow_pnl_service import capture_workflow_baseline

        cfg = get_config_effective(MARKET_CONFIG[market])
        mode = str(cfg.get("mode", "dry_run"))
        capture_workflow_baseline(
            market,
            operator=operator,
            operation_mode=trading_mode_to_operation(mode),
        )
    except Exception:
        pass
    return ts


def _backfill_workflow_started_at(market: str) -> str | None:
    """If workflow is active but uptime key missing, infer or create timestamp."""
    active = get_active_market_workflow(market)
    if not active:
        return None
    meta = get_runtime_meta(WORKFLOW_STARTED_KEY[market])
    if meta and meta.get("value"):
        return str(meta["value"])

    from db.connection import get_connection

    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT MIN(event_at) AS first_at
            FROM trade_events
            WHERE market = ? AND workflow_name = ?
              AND event_at >= datetime('now', '-14 days')
            """,
            (market, active),
        ).fetchone()
        if row and row["first_at"]:
            ts = str(row["first_at"])
            set_runtime_value(WORKFLOW_STARTED_KEY[market], ts, updated_by="backfill")
            return ts
    finally:
        conn.close()

    return _mark_workflow_started(market, operator="backfill")


def _workflow_started_at(market: str) -> str | None:
    active = get_active_market_workflow(market)
    if not active:
        return None
    meta = get_runtime_meta(WORKFLOW_STARTED_KEY[market]) or {}
    val = meta.get("value")
    if val:
        return str(val)
    return _backfill_workflow_started_at(market)


def _clear_workflow_started(market: str) -> None:
    delete_runtime_value(WORKFLOW_STARTED_KEY[market])
    try:
        from workflow_pnl_service import clear_workflow_baseline

        clear_workflow_baseline(market)
    except Exception:
        pass


MARKET_WORKFLOW_SET = {
    "crypto": frozenset(
        {
            "crypto-signal-dry-run",
            "crypto-signal-paper",
            "crypto-scalp-hybrid-dry-run",
            "crypto-scalp-hybrid-paper",
            "crypto-monitor-testnet",
        }
    ),
    "securities": frozenset(
        {"securities-swing-dry-run", "securities-swing-paper", "securities-dca-sandbox"}
    ),
}

# Only one primary trading workflow per market at a time (strategy selection).
MARKET_EXCLUSIVE_WORKFLOWS: dict[str, frozenset[str]] = {
    "crypto": frozenset(
        {
            "crypto-signal-dry-run",
            "crypto-signal-paper",
            "crypto-scalp-hybrid-dry-run",
            "crypto-scalp-hybrid-paper",
        }
    ),
    "securities": frozenset(
        {
            "securities-swing-dry-run",
            "securities-swing-paper",
            "securities-dca-sandbox",
        }
    ),
}

# May run alongside the primary workflow (e.g. portfolio monitor).
MARKET_CONCURRENT_WORKFLOWS: dict[str, frozenset[str]] = {
    "crypto": frozenset({"crypto-monitor-testnet"}),
    "securities": frozenset(),
}

MARKET_MODE_PROFILES: dict[str, dict[str, dict[str, list[str]]]] = {
    "crypto": {
        "paper": {
            "enable": ["crypto-signal-paper", "crypto-monitor-testnet"],
            "disable": [
                "crypto-signal-dry-run",
                "crypto-scalp-hybrid-dry-run",
                "crypto-scalp-hybrid-paper",
            ],
        },
        "dry_run": {
            "enable": ["crypto-signal-dry-run"],
            "disable": [
                "crypto-signal-paper",
                "crypto-monitor-testnet",
                "crypto-scalp-hybrid-dry-run",
                "crypto-scalp-hybrid-paper",
            ],
        },
        "shadow": {
            "enable": ["crypto-signal-dry-run"],
            "disable": [
                "crypto-signal-paper",
                "crypto-monitor-testnet",
                "crypto-scalp-hybrid-dry-run",
                "crypto-scalp-hybrid-paper",
            ],
        },
        "live": {
            "enable": [],
            "disable": [
                "crypto-signal-dry-run",
                "crypto-signal-paper",
                "crypto-monitor-testnet",
                "crypto-scalp-hybrid-dry-run",
                "crypto-scalp-hybrid-paper",
            ],
        },
    },
    "securities": {
        "paper": {
            "enable": ["securities-swing-paper", "securities-dca-sandbox"],
            "disable": ["securities-swing-dry-run"],
        },
        "dry_run": {
            "enable": ["securities-swing-dry-run"],
            "disable": ["securities-swing-paper", "securities-dca-sandbox"],
        },
        "shadow": {
            "enable": ["securities-swing-dry-run"],
            "disable": ["securities-swing-paper", "securities-dca-sandbox"],
        },
        "live": {
            "enable": [],
            "disable": [
                "securities-swing-dry-run",
                "securities-swing-paper",
                "securities-dca-sandbox",
            ],
        },
    },
}

# Legacy global profiles (used only by deprecated global switch).
MODE_PROFILES: dict[str, dict[str, list[str]]] = {
    "dry_run": {
        "enable": ["crypto-signal-dry-run", "securities-swing-dry-run"],
        "disable": ["crypto-signal-paper", "securities-swing-paper", "crypto-monitor-testnet"],
    },
    "paper": {
        "enable": [
            "crypto-signal-paper",
            "securities-swing-paper",
            "crypto-monitor-testnet",
            "securities-dca-sandbox",
        ],
        "disable": ["crypto-signal-dry-run", "securities-swing-dry-run"],
    },
    "shadow": {
        "enable": ["crypto-signal-dry-run", "securities-swing-dry-run"],
        "disable": ["crypto-signal-paper", "securities-swing-paper", "crypto-monitor-testnet"],
    },
    "live": {
        "enable": [],
        "disable": list(TRADING_WORKFLOWS),
    },
}


def _yaml_trading_mode() -> str:
    return str(load_config("guardrails").get("trading", {}).get("mode", "dry_run"))


def _yaml_market_mode(config_name: str) -> str:
    return str(load_config(config_name).get("mode", "dry_run"))


def get_effective_trading_mode() -> str:
    """Aggregate label for status bar; per-market modes are authoritative."""
    crypto = get_effective_market_mode("crypto_config")
    sec = get_effective_market_mode("securities_config")
    modes = {crypto, sec}
    if "live" in modes:
        return "live"
    if len(modes) > 1:
        return "mixed"
    return crypto if modes else _yaml_trading_mode()


def get_effective_market_mode(config_name: str) -> str:
    key = "crypto_mode" if config_name == "crypto_config" else "securities_mode"
    runtime = get_runtime_value(key)
    if runtime is not None:
        return str(runtime)
    return _yaml_market_mode(config_name)


def get_config_effective(name: str) -> dict[str, Any]:
    cfg = deepcopy(load_config(name))
    if name == "guardrails":
        trading = dict(cfg.get("trading", {}))
        trading["mode"] = get_effective_trading_mode()
        cfg["trading"] = trading
    elif name in ("crypto_config", "securities_config"):
        cfg["mode"] = get_effective_market_mode(name)
    return cfg


def _validate_mode(mode: str) -> str:
    normalized = normalize_trading_mode(mode)
    if normalized == "live" and not _live_flag_enabled():
        raise ValueError("live_disabled: set LIVE_TRADING_ENABLED=true in .env")
    return normalized


def _live_flag_enabled() -> bool:
    import os

    return os.environ.get("LIVE_TRADING_ENABLED", "false").lower() == "true"


def set_trading_mode(
    mode: str,
    *,
    operator: str,
    sync_markets: bool = True,
) -> dict[str, Any]:
    normalized = _validate_mode(mode)
    set_runtime_value("trading_mode", normalized, updated_by=operator)
    if sync_markets:
        set_runtime_value("crypto_mode", normalized, updated_by=operator)
        set_runtime_value("securities_mode", normalized, updated_by=operator)
    log_system_activity(
        f"Режим торговли: {normalized}",
        category="control",
        level="info",
        payload={"mode": normalized, "operator": operator},
    )
    return {
        "status": "ok",
        "trading_mode": normalized,
        "runtime_override": True,
    }


def clear_trading_mode(*, operator: str) -> dict[str, Any]:
    for key in ("trading_mode", "crypto_mode", "securities_mode"):
        delete_runtime_value(key)
    log_system_activity(
        "Режим торговли сброшен к YAML",
        category="control",
        level="info",
        payload={"operator": operator},
    )
    return {
        "status": "ok",
        "trading_mode": _yaml_trading_mode(),
        "runtime_override": False,
    }


def _primary_workflow_for_market(market: str) -> str | None:
    from strategy_service import get_strategy_state

    wf = str(get_strategy_state(market).get("strategy", {}).get("workflow", "")).strip()
    return wf or None


def _concurrent_workflows_for_mode(market: str, mode: str) -> frozenset[str]:
    base = MARKET_CONCURRENT_WORKFLOWS.get(market, frozenset())
    if market == "crypto" and mode in ("paper", "shadow"):
        return base
    return frozenset()


def _apply_exclusive_workflow_selection(
    market: str,
    workflow_name: str,
    *,
    by_name: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Activate one primary workflow; deactivate other exclusive workflows for the market."""
    allowed = MARKET_WORKFLOW_SET.get(market, frozenset())
    exclusive = MARKET_EXCLUSIVE_WORKFLOWS.get(market, frozenset())
    concurrent = MARKET_CONCURRENT_WORKFLOWS.get(market, frozenset())
    if workflow_name not in allowed:
        raise ValueError(f"unknown_workflow: {workflow_name}")
    if by_name is None:
        by_name = {str(w.get("name")): w for w in list_workflows()}
    if workflow_name not in by_name:
        raise ValueError(f"missing_in_n8n: {workflow_name}")

    results: list[dict[str, Any]] = []
    for name in sorted(allowed):
        wf = by_name.get(name)
        if not wf:
            continue
        wid = str(wf["id"])
        if name == workflow_name:
            if not wf.get("active"):
                activate_workflow(wid)
                results.append({"name": name, "action": "activated", "id": wid})
        elif name in exclusive and wf.get("active"):
            deactivate_workflow(wid)
            results.append({"name": name, "action": "deactivated", "id": wid})
        elif name in concurrent:
            continue
    return results


def _market_workflow_actions(market: str, mode: str) -> list[dict[str, Any]]:
    profile = MARKET_MODE_PROFILES.get(market, {}).get(
        mode, MARKET_MODE_PROFILES[market]["dry_run"]
    )
    workflows = list_workflows()
    by_name = {str(w.get("name")): w for w in workflows}
    results: list[dict[str, Any]] = []

    for name in profile.get("disable", []):
        wf = by_name.get(name)
        if not wf or not wf.get("active"):
            continue
        deactivate_workflow(str(wf["id"]))
        results.append({"name": name, "action": "deactivated", "id": wf.get("id")})

    for name in profile.get("enable", []):
        wf = by_name.get(name)
        if not wf or wf.get("active"):
            continue
        activate_workflow(str(wf["id"]))
        results.append({"name": name, "action": "activated", "id": wf.get("id")})

    if any(r.get("action") == "activated" for r in results):
        _mark_workflow_started(market, operator="sync")

    return results


def sync_market_workflows(market: str) -> dict[str, Any]:
    """Sync n8n workflows to active strategy + trading mode (one exclusive primary workflow)."""
    if market not in MARKET_CONFIG:
        raise ValueError(f"unknown_market: {market}")
    config_name = MARKET_CONFIG[market]
    mode = str(get_config_effective(config_name).get("mode", "dry_run"))
    by_name = {str(w.get("name")): w for w in list_workflows()}
    primary = _primary_workflow_for_market(market)
    results: list[dict[str, Any]] = []

    if primary and primary in by_name:
        results.extend(_apply_exclusive_workflow_selection(market, primary, by_name=by_name))
        concurrent = _concurrent_workflows_for_mode(market, mode)
        for name in MARKET_CONCURRENT_WORKFLOWS.get(market, frozenset()):
            wf = by_name.get(name)
            if not wf:
                continue
            wid = str(wf["id"])
            if name in concurrent:
                if not wf.get("active"):
                    activate_workflow(wid)
                    results.append({"name": name, "action": "activated", "id": wid})
            elif wf.get("active"):
                deactivate_workflow(wid)
                results.append({"name": name, "action": "deactivated", "id": wid})
        expected_enable = [primary, *sorted(concurrent)]
        expected_disable = [
            n
            for n in sorted(MARKET_EXCLUSIVE_WORKFLOWS.get(market, frozenset()))
            if n != primary
        ]
    else:
        profile = MARKET_MODE_PROFILES.get(market, {}).get(
            mode, MARKET_MODE_PROFILES[market]["dry_run"]
        )
        expected_enable = list(profile.get("enable", []))
        expected_disable = list(profile.get("disable", []))
        results = _market_workflow_actions(market, mode)

    if any(r.get("action") == "activated" for r in results):
        _mark_workflow_started(market, operator="sync")

    by_name = {str(w.get("name")): w for w in list_workflows()}
    missing = [n for n in expected_enable if n not in by_name]
    active_now = [name for name, wf in by_name.items() if wf.get("active")]
    return {
        "status": "ok",
        "market": market,
        "trading_mode": mode,
        "operation_mode": trading_mode_to_operation(mode),
        "primary_workflow": primary,
        "expected_enable": expected_enable,
        "expected_disable": expected_disable,
        "missing": missing,
        "workflows": results,
        "active_workflows": active_now,
    }


def start_market_workflow(
    market: str,
    workflow_name: str,
    *,
    trading_mode: str | None = None,
    operator: str = "web:operator",
) -> dict[str, Any]:
    """Set market trading mode (optional) and activate exactly one workflow."""
    mode_result: dict[str, Any] | None = None
    if trading_mode:
        normalized = _validate_mode(trading_mode)
        mode_result = set_market_mode(market, normalized, operator=operator)
    wf_result = select_market_workflow(market, workflow_name, operator=operator)
    if mode_result:
        wf_result["trading_mode"] = mode_result["trading_mode"]
        wf_result["operation_mode"] = mode_result["operation_mode"]
    return wf_result


def select_market_workflow(
    market: str, workflow_name: str, *, operator: str = "web:operator"
) -> dict[str, Any]:
    """Activate one primary workflow; deactivate other exclusive workflows (keep concurrent)."""
    if market not in MARKET_CONFIG:
        raise ValueError(f"unknown_market: {market}")
    allowed = MARKET_WORKFLOW_SET.get(market, frozenset())
    if workflow_name not in allowed:
        raise ValueError(f"unknown_workflow: {workflow_name}")

    by_name = {str(w.get("name")): w for w in list_workflows()}
    if workflow_name not in by_name:
        raise ValueError(f"missing_in_n8n: {workflow_name}")

    results = _apply_exclusive_workflow_selection(market, workflow_name, by_name=by_name)

    log_system_activity(
        f"{'Crypto' if market == 'crypto' else 'MOEX'}: запущен workflow {workflow_name}",
        category=market,
        level="info",
        payload={"market": market, "workflow": workflow_name},
    )
    started_at = _mark_workflow_started(market, operator=operator)
    config_name = MARKET_CONFIG[market]
    mode = str(get_config_effective(config_name).get("mode", "dry_run"))
    concurrent = _concurrent_workflows_for_mode(market, mode)
    return {
        "status": "ok",
        "market": market,
        "selected": workflow_name,
        "workflow_started_at": started_at,
        "workflows": results,
        "active_workflows": [workflow_name, *sorted(concurrent)],
    }


def stop_market_workflows(market: str) -> dict[str, Any]:
    """Deactivate all workflows for the market."""
    if market not in MARKET_CONFIG:
        raise ValueError(f"unknown_market: {market}")
    allowed = MARKET_WORKFLOW_SET.get(market, frozenset())
    workflows = list_workflows()
    by_name = {str(w.get("name")): w for w in workflows}
    results: list[dict[str, Any]] = []
    for name in sorted(allowed):
        wf = by_name.get(name)
        if not wf or not wf.get("active"):
            continue
        deactivate_workflow(str(wf["id"]))
        results.append({"name": name, "action": "deactivated", "id": wf.get("id")})

    log_system_activity(
        f"{'Crypto' if market == 'crypto' else 'MOEX'}: workflow остановлены",
        category=market,
        level="warn",
        payload={"market": market},
    )
    _clear_workflow_started(market)
    return {"status": "ok", "market": market, "workflows": results, "active_workflows": []}


def set_market_mode(
    market: str,
    mode: str,
    *,
    operator: str,
) -> dict[str, Any]:
    if market not in MARKET_CONFIG:
        raise ValueError(f"unknown_market: {market}")
    normalized = _validate_mode(mode)
    key = MARKET_RUNTIME_KEY[market]
    set_runtime_value(key, normalized, updated_by=operator)
    log_system_activity(
        f"{'Crypto' if market == 'crypto' else 'MOEX'}: режим {normalized}",
        category=market,
        level="info",
        payload={"market": market, "mode": normalized, "operator": operator},
    )
    return {
        "status": "ok",
        "market": market,
        "trading_mode": normalized,
        "operation_mode": trading_mode_to_operation(normalized),
        "runtime_override": True,
    }


def apply_market_operation_mode(
    market: str,
    operation_mode: str,
    *,
    operator: str,
    apply_workflows: bool = True,
) -> dict[str, Any]:
    op = str(operation_mode).strip().lower()
    if op not in OPERATION_TO_TRADING:
        raise ValueError(f"invalid_operation_mode: {operation_mode}")
    mode_result = set_market_mode(
        market, OPERATION_TO_TRADING[op], operator=operator
    )
    workflow_results: list[dict[str, Any]] = []
    workflow_error: str | None = None
    if apply_workflows:
        try:
            workflow_results = _market_workflow_actions(market, mode_result["trading_mode"])
        except Exception as exc:
            workflow_error = str(exc)
    return {
        **mode_result,
        "workflows": workflow_results,
        "workflows_error": workflow_error,
    }


def clear_market_mode(market: str, *, operator: str) -> dict[str, Any]:
    if market not in MARKET_CONFIG:
        raise ValueError(f"unknown_market: {market}")
    delete_runtime_value(MARKET_RUNTIME_KEY[market])
    config_name = MARKET_CONFIG[market]
    yaml_mode = _yaml_market_mode(config_name)
    log_system_activity(
        f"{'Crypto' if market == 'crypto' else 'MOEX'}: режим сброшен к YAML",
        category=market,
        level="info",
        payload={"market": market, "operator": operator},
    )
    return {
        "status": "ok",
        "market": market,
        "trading_mode": yaml_mode,
        "operation_mode": trading_mode_to_operation(yaml_mode),
        "runtime_override": False,
    }


def get_market_control_state(market: str) -> dict[str, Any]:
    if market not in MARKET_CONFIG:
        raise ValueError(f"unknown_market: {market}")
    config_name = MARKET_CONFIG[market]
    cfg = get_config_effective(config_name)
    mode = str(cfg.get("mode", "dry_run"))
    runtime_key = MARKET_RUNTIME_KEY[market]

    workflows: list[dict[str, Any]] = []
    n8n_status = "ok"
    n8n_message: str | None = None
    profile = MARKET_MODE_PROFILES.get(market, {}).get(mode, {})
    try:
        for wf in list_workflows():
            name = str(wf.get("name") or "")
            if name not in MARKET_WORKFLOW_SET.get(market, frozenset()):
                continue
            workflows.append(
                {
                    "id": wf.get("id"),
                    "name": name,
                    "active": bool(wf.get("active")),
                    "expected_for_mode": name in profile.get("enable", []),
                }
            )
    except Exception as exc:
        n8n_status = "error"
        n8n_message = str(exc)

    active_wf = get_active_market_workflow(market)
    started_at = _workflow_started_at(market) if active_wf else None
    workflow_pnl: dict[str, Any] | None = None
    if active_wf:
        try:
            from workflow_pnl_service import get_workflow_pnl

            workflow_pnl = get_workflow_pnl(
                market,
                active=True,
                operation_mode=trading_mode_to_operation(mode),
            )
        except Exception as exc:
            workflow_pnl = {
                "status": "error",
                "message": str(exc),
                "pnl_pct": None,
                "direction": "flat",
            }

    workflow_session: dict[str, Any] | None = None
    if active_wf and started_at:
        try:
            from workflow_session_service import get_workflow_session_stats

            workflow_session = get_workflow_session_stats(
                market,
                started_at=started_at,
                active_workflow=active_wf,
                workflow_pnl=workflow_pnl,
            )
        except Exception:
            workflow_session = None

    return {
        "market": market,
        "operation_mode": trading_mode_to_operation(mode),
        "operation_detail": operation_mode_detail(mode),
        "trading_mode": mode,
        "yaml_mode": _yaml_market_mode(config_name),
        "runtime_override": get_runtime_value(runtime_key) is not None,
        "live_flag": _live_flag_enabled(),
        "env": cfg.get("env"),
        "active_workflow": active_wf,
        "workflow_started_at": started_at,
        "workflow_pnl": workflow_pnl,
        "workflow_session": workflow_session,
        "workflows": workflows,
        "n8n": {"status": n8n_status, "message": n8n_message},
    }


def _workflow_actions(mode: str) -> list[dict[str, Any]]:
    profile = MODE_PROFILES.get(mode, MODE_PROFILES["dry_run"])
    workflows = list_workflows()
    by_name = {str(w.get("name")): w for w in workflows}
    results: list[dict[str, Any]] = []

    for name in profile.get("disable", []):
        wf = by_name.get(name)
        if not wf or not wf.get("active"):
            continue
        deactivate_workflow(str(wf["id"]))
        results.append({"name": name, "action": "deactivated", "id": wf.get("id")})

    for name in profile.get("enable", []):
        wf = by_name.get(name)
        if not wf or wf.get("active"):
            continue
        activate_workflow(str(wf["id"]))
        results.append({"name": name, "action": "activated", "id": wf.get("id")})

    return results


def apply_trading_mode(
    mode: str,
    *,
    operator: str,
    apply_workflows: bool = True,
) -> dict[str, Any]:
    mode_result = set_trading_mode(mode, operator=operator)
    workflow_results: list[dict[str, Any]] = []
    workflow_error: str | None = None
    if apply_workflows:
        try:
            workflow_results = _workflow_actions(mode_result["trading_mode"])
        except Exception as exc:
            workflow_error = str(exc)
    return {
        **mode_result,
        "operation_mode": trading_mode_to_operation(mode_result["trading_mode"]),
        "workflows": workflow_results,
        "workflows_error": workflow_error,
    }


def apply_operation_mode(
    operation_mode: str,
    *,
    operator: str,
) -> dict[str, Any]:
    op = str(operation_mode).strip().lower()
    if op not in OPERATION_TO_TRADING:
        raise ValueError(f"invalid_operation_mode: {operation_mode}")
    return apply_trading_mode(
        OPERATION_TO_TRADING[op],
        operator=operator,
        apply_workflows=True,
    )


def toggle_workflow_by_name(
    name: str,
    *,
    active: bool,
    operator: str,
) -> dict[str, Any]:
    workflows = list_workflows()
    wf = next((w for w in workflows if str(w.get("name")) == name), None)
    if not wf:
        return {"status": "error", "message": f"workflow_not_found: {name}"}

    wf_id = str(wf["id"])
    if active and not wf.get("active"):
        updated = activate_workflow(wf_id)
        action = "activated"
    elif not active and wf.get("active"):
        updated = deactivate_workflow(wf_id)
        action = "deactivated"
    else:
        return {
            "status": "ok",
            "name": name,
            "active": bool(wf.get("active")),
            "unchanged": True,
        }

    log_system_activity(
        f"Workflow {name}: {action}",
        category="control",
        level="info",
        payload={"name": name, "active": active, "operator": operator},
    )
    return {
        "status": "ok",
        "name": name,
        "action": action,
        "active": bool(updated.get("active")),
        "id": wf_id,
    }


def _schedule_info() -> dict[str, Any]:
    crypto = load_config("crypto_config")
    sec = load_config("securities_config")
    swing = sec.get("swing_signals", {})
    return {
        "crypto": {
            "interval": "4h",
            "cron": crypto.get("schedule_cron", "5 */4 * * *"),
            "timeframe": crypto.get("timeframe", "4h"),
            "pairs": list(crypto.get("pairs", [])),
            "llm_model": crypto.get("ollama_model"),
            "summary_ru": "Каждые 4 часа: индикаторы → LLM → ордер (paper) или только лог (dry_run)",
        },
        "securities_swing": {
            "cron": swing.get("schedule_cron", "15 18 * * 1-5"),
            "timeframe": swing.get("timeframe", "1d"),
            "universe": list(swing.get("universe", [])),
            "llm_model": swing.get("ollama_model"),
            "summary_ru": "Будни 18:15 MSK: дневной график → LLM по каждому тикеру universe",
        },
        "securities_dca": {
            "cron": sec.get("index_dca", {}).get("schedule_cron", "0 10 1 * *"),
            "ticker": sec.get("index_dca", {}).get("ticker", "TMOS"),
            "summary_ru": "1-е число месяца 10:00 MSK — DCA без LLM",
        },
    }


def get_automation_control_state() -> dict[str, Any]:
    crypto = get_config_effective("crypto_config")
    sec = get_config_effective("securities_config")
    crypto_mode = str(crypto.get("mode", "dry_run"))
    sec_mode = str(sec.get("mode", "dry_run"))
    global_mode = get_effective_trading_mode()

    workflows: list[dict[str, Any]] = []
    n8n_status = "ok"
    n8n_message: str | None = None
    try:
        for wf in list_workflows():
            name = str(wf.get("name") or "")
            if name not in TRADING_WORKFLOWS:
                continue
            market = "crypto" if name in MARKET_WORKFLOW_SET["crypto"] else "securities"
            market_mode = crypto_mode if market == "crypto" else sec_mode
            profile = MARKET_MODE_PROFILES.get(market, {}).get(market_mode, {})
            workflows.append(
                {
                    "id": wf.get("id"),
                    "name": name,
                    "market": market,
                    "active": bool(wf.get("active")),
                    "expected_for_mode": name in profile.get("enable", []),
                }
            )
    except Exception as exc:
        n8n_status = "error"
        n8n_message = str(exc)

    return {
        "operation_mode": trading_mode_to_operation(global_mode)
        if global_mode not in ("mixed",)
        else "mixed",
        "trading_mode": global_mode,
        "yaml_trading_mode": _yaml_trading_mode(),
        "runtime_override": any(
            get_runtime_value(k) is not None for k in MARKET_RUNTIME_KEY.values()
        ),
        "valid_modes": list(VALID_MODES),
        "valid_operation_modes": list(OPERATION_MODES),
        "live_flag": _live_flag_enabled(),
        "crypto": get_market_control_state("crypto"),
        "securities": get_market_control_state("securities"),
        "schedules": _schedule_info(),
        "workflows": workflows,
        "n8n": {"status": n8n_status, "message": n8n_message},
    }


def get_market_diagnostics(market: str, *, days: int = 7) -> dict[str, Any]:
    """Pipeline health: funnel, recent orders, blockers — for workspace testing."""
    from backtest.metrics import dry_run_funnel
    from db.connection import get_connection

    if market not in MARKET_CONFIG:
        raise ValueError(f"unknown_market: {market}")

    ctrl = get_market_control_state(market)
    funnel = dry_run_funnel(market=market, days=days)
    active_wf = ctrl.get("active_workflow")

    conn = get_connection()
    try:
        stage_rows = conn.execute(
            """
            SELECT stage, decision, reject_reason, COUNT(*) AS cnt
            FROM trade_events
            WHERE market = ? AND event_at >= datetime('now', ?)
            GROUP BY stage, decision, reject_reason
            ORDER BY cnt DESC
            """,
            (market, f"-{days} days"),
        ).fetchall()
        orders = conn.execute(
            """
            SELECT event_at, symbol, decision, reject_reason, workflow_name, notional, payload_json
            FROM trade_events
            WHERE market = ? AND stage = 'order'
              AND event_at >= datetime('now', ?)
            ORDER BY event_at DESC
            LIMIT 15
            """,
            (market, f"-{days} days"),
        ).fetchall()
        last_signal = conn.execute(
            """
            SELECT event_at, symbol, workflow_name
            FROM trade_events
            WHERE market = ? AND stage = 'signal'
            ORDER BY event_at DESC LIMIT 1
            """,
            (market,),
        ).fetchone()
    finally:
        conn.close()

    executed = sum(
        1
        for o in orders
        if dict(o).get("decision") in ("submitted", "execute", "executed")
    )
    errors = [dict(o) for o in orders if dict(o).get("decision") == "error"]

    schedule = None
    if active_wf:
        try:
            from workflow_schedule_service import get_workflow_schedule

            schedule = get_workflow_schedule(active_wf)
        except Exception:
            schedule = None

    hints: list[str] = []
    if not active_wf:
        hints.append("workflow_not_active")
    if market == "securities" and schedule and schedule.get("option_id") == "daily_1815":
        hints.append("moex_runs_once_daily_1815_weekdays")
    if executed == 0:
        hints.append("no_executed_orders_in_period_use_test_run")

    return {
        "status": "ok",
        "market": market,
        "days": days,
        "active_workflow": active_wf,
        "workflow_started_at": ctrl.get("workflow_started_at"),
        "schedule": schedule,
        "funnel": funnel,
        "stage_counts": [dict(r) for r in stage_rows],
        "orders_total": len(orders),
        "orders_executed": executed,
        "recent_orders": [dict(r) for r in orders[:8]],
        "recent_errors": errors[:5],
        "last_signal": dict(last_signal) if last_signal else None,
        "hints": hints,
    }


def run_workflow_once(
    market: str,
    workflow_name: str,
    *,
    operator: str = "web",
) -> dict[str, Any]:
    """Manual one-shot: run paper/dry pipeline for each enabled symbol (like n8n tick)."""
    from crypto_pipeline import run_crypto_signal
    from paper_trading_service import run_crypto_paper_trade, run_crypto_scalp_paper_trade, run_securities_swing_paper
    from crypto_scalp_pipeline import run_crypto_scalp_signal
    from securities_pipeline import run_securities_dca_dry_run, run_securities_swing_dry_run
    from workflow_universe_service import enabled_symbols_for_workflow

    if market not in MARKET_CONFIG:
        raise ValueError(f"unknown_market: {market}")
    if workflow_name not in MARKET_WORKFLOW_SET.get(market, frozenset()):
        raise ValueError(f"unknown_workflow: {workflow_name}")

    symbols = enabled_symbols_for_workflow(workflow_name)
    if not symbols:
        return {"status": "error", "message": "empty_universe", "workflow": workflow_name}

    results: list[dict[str, Any]] = []
    for sym in symbols:
        try:
            if workflow_name == "crypto-signal-paper":
                results.append(run_crypto_paper_trade(symbol=sym))
            elif workflow_name == "crypto-signal-dry-run":
                results.append(
                    run_crypto_signal(
                        symbol=sym,
                        env="dry_run",
                        workflow_name=workflow_name,
                    )
                )
            elif workflow_name == "crypto-scalp-hybrid-paper":
                results.append(run_crypto_scalp_paper_trade(symbol=sym))
            elif workflow_name == "crypto-scalp-hybrid-dry-run":
                results.append(
                    run_crypto_scalp_signal(
                        symbol=sym,
                        env="dry_run",
                        workflow_name=workflow_name,
                    )
                )
            elif workflow_name == "securities-swing-paper":
                results.append(run_securities_swing_paper(ticker=sym))
            elif workflow_name == "securities-swing-dry-run":
                results.append(
                    run_securities_swing_dry_run(
                        ticker=sym,
                        env="dry_run",
                        workflow_name=workflow_name,
                    )
                )
            elif workflow_name == "securities-dca-sandbox":
                results.append(
                    run_securities_dca_dry_run(env="paper", workflow_name=workflow_name)
                )
            else:
                results.append({"status": "skipped", "message": "unsupported_workflow", "symbol": sym})
        except Exception as exc:
            results.append({"status": "error", "symbol": sym, "message": str(exc)})

    executed = sum(1 for r in results if r.get("status") == "executed")
    log_system_activity(
        f"{'Crypto' if market == 'crypto' else 'MOEX'}: пробный запуск {workflow_name} ({len(symbols)} активов, сделок: {executed})",
        category=market,
        level="info",
        payload={"workflow": workflow_name, "symbols": symbols, "executed": executed},
    )
    return {
        "status": "ok",
        "market": market,
        "workflow": workflow_name,
        "symbols": symbols,
        "executed_count": executed,
        "results": results,
    }
