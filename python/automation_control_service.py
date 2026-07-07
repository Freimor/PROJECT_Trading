"""Runtime trading mode and n8n automation profile management."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from activity_feed_service import log_system_activity
from config_loader import load_config
from n8n_service import activate_workflow, deactivate_workflow, list_workflows
from runtime_settings import delete_runtime_value, get_runtime_value, set_runtime_value

VALID_MODES = ("dry_run", "paper", "shadow", "live")

TRADING_WORKFLOWS = (
    "crypto-signal-dry-run",
    "crypto-signal-paper",
    "crypto-monitor-testnet",
    "securities-swing-dry-run",
    "securities-swing-paper",
    "securities-dca-sandbox",
)

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
    runtime = get_runtime_value("trading_mode")
    if runtime is not None:
        return str(runtime)
    return _yaml_trading_mode()


def get_effective_market_mode(config_name: str) -> str:
    key = "crypto_mode" if config_name == "crypto_config" else "securities_mode"
    runtime = get_runtime_value(key)
    if runtime is not None:
        return str(runtime)
    global_runtime = get_runtime_value("trading_mode")
    if global_runtime is not None:
        return str(global_runtime)
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
    normalized = str(mode).strip().lower()
    if normalized not in VALID_MODES:
        raise ValueError(f"invalid_mode: {mode}")
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
        "workflows": workflow_results,
        "workflows_error": workflow_error,
    }


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
    mode = get_effective_trading_mode()
    crypto = get_config_effective("crypto_config")
    sec = get_config_effective("securities_config")
    runtime_mode = get_runtime_value("trading_mode")

    workflows: list[dict[str, Any]] = []
    n8n_status = "ok"
    n8n_message: str | None = None
    try:
        for wf in list_workflows():
            name = str(wf.get("name") or "")
            if name not in TRADING_WORKFLOWS:
                continue
            workflows.append(
                {
                    "id": wf.get("id"),
                    "name": name,
                    "active": bool(wf.get("active")),
                    "expected_for_mode": name in MODE_PROFILES.get(mode, {}).get("enable", []),
                }
            )
    except Exception as exc:
        n8n_status = "error"
        n8n_message = str(exc)

    return {
        "trading_mode": mode,
        "yaml_trading_mode": _yaml_trading_mode(),
        "runtime_override": runtime_mode is not None,
        "valid_modes": list(VALID_MODES),
        "live_flag": _live_flag_enabled(),
        "crypto": {
            "mode": crypto.get("mode"),
            "env": crypto.get("env"),
            "yaml_mode": _yaml_market_mode("crypto_config"),
        },
        "securities": {
            "mode": sec.get("mode"),
            "env": sec.get("env"),
            "active_mode": sec.get("active_mode"),
            "yaml_mode": _yaml_market_mode("securities_config"),
        },
        "schedules": _schedule_info(),
        "workflows": workflows,
        "n8n": {"status": n8n_status, "message": n8n_message},
        "mode_profiles": {
            m: {"enable": p["enable"], "disable": p["disable"]}
            for m, p in MODE_PROFILES.items()
        },
    }
