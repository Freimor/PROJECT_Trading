"""Workflow trigger frequency — presets, runtime overrides, n8n schedule sync."""

from __future__ import annotations

from typing import Any

from n8n_service import (
    _find_workflow_by_name,
    _schedule_nodes,
    get_workflow,
    set_workflow_cron,
    set_workflow_hours_interval,
)
from runtime_settings import get_runtime_value, set_runtime_value
from workflow_universe_service import WORKFLOW_REGISTRY

SCHEDULE_KEY_PREFIX = "workflow_schedule:"

# Crypto signal workflows use n8n hoursInterval.
CRYPTO_HOUR_OPTIONS: list[dict[str, Any]] = [
    {"id": "1h", "hours": 1, "label_ru": "каждый час", "label_en": "every hour"},
    {"id": "2h", "hours": 2, "label_ru": "каждые 2 часа", "label_en": "every 2 hours"},
    {"id": "4h", "hours": 4, "label_ru": "каждые 4 часа", "label_en": "every 4 hours"},
    {"id": "6h", "hours": 6, "label_ru": "каждые 6 часов", "label_en": "every 6 hours"},
    {"id": "8h", "hours": 8, "label_ru": "каждые 8 часов", "label_en": "every 8 hours"},
    {"id": "12h", "hours": 12, "label_ru": "каждые 12 часов", "label_en": "every 12 hours"},
    {"id": "24h", "hours": 24, "label_ru": "раз в сутки", "label_en": "once per day"},
]

# MOEX swing / DCA use cron (weekdays unless noted).
CRON_OPTIONS: list[dict[str, Any]] = [
    {"id": "15m", "cron": "*/15 * * * 1-5", "label_ru": "каждые 15 мин (будни)", "label_en": "every 15 min (weekdays)"},
    {"id": "30m", "cron": "*/30 * * * 1-5", "label_ru": "каждые 30 мин (будни)", "label_en": "every 30 min (weekdays)"},
    {"id": "1h", "cron": "0 * * * 1-5", "label_ru": "каждый час (будни)", "label_en": "every hour (weekdays)"},
    {"id": "2h", "cron": "0 */2 * * 1-5", "label_ru": "каждые 2 часа (будни)", "label_en": "every 2 hours (weekdays)"},
    {"id": "4h", "cron": "0 */4 * * 1-5", "label_ru": "каждые 4 часа (будни)", "label_en": "every 4 hours (weekdays)"},
    {"id": "daily_1815", "cron": "15 18 * * 1-5", "label_ru": "будни 18:15 MSK", "label_en": "weekdays 18:15 MSK"},
    {"id": "monthly_dca", "cron": "0 10 1 * *", "label_ru": "1-е число 10:00 MSK", "label_en": "1st of month 10:00 MSK"},
]

_CRYPTO_SIGNAL_WORKFLOWS = frozenset({"crypto-signal-dry-run", "crypto-signal-paper"})
_CRYPTO_SCALP_WORKFLOWS = frozenset(
    {"crypto-scalp-hybrid-dry-run", "crypto-scalp-hybrid-paper"}
)
_CRYPTO_MONITOR_WORKFLOWS = frozenset({"crypto-monitor-testnet"})

MINUTE_OPTIONS: list[dict[str, Any]] = [
    {"id": "5m", "minutes": 5, "label_ru": "каждые 5 минут", "label_en": "every 5 minutes"},
    {"id": "15m", "minutes": 15, "label_ru": "каждые 15 минут", "label_en": "every 15 minutes"},
    {"id": "30m", "minutes": 30, "label_ru": "каждые 30 минут", "label_en": "every 30 minutes"},
    {"id": "60m", "minutes": 60, "label_ru": "каждый час", "label_en": "every hour"},
]
_CRON_WORKFLOWS = frozenset(
    {
        "securities-swing-dry-run",
        "securities-swing-paper",
        "securities-dca-sandbox",
    }
)


def _schedule_key(workflow: str) -> str:
    return f"{SCHEDULE_KEY_PREFIX}{workflow}"


def _default_option_id(workflow: str) -> str:
    if workflow in _CRYPTO_SIGNAL_WORKFLOWS:
        return "4h"
    if workflow in _CRYPTO_SCALP_WORKFLOWS:
        return "5m"
    if workflow in _CRYPTO_MONITOR_WORKFLOWS:
        return "15m"
    if workflow == "securities-dca-sandbox":
        return "monthly_dca"
    return "daily_1815"


def _option_by_id(workflow: str, option_id: str) -> dict[str, Any] | None:
    options = get_schedule_options(workflow)
    return next((o for o in options if o.get("id") == option_id), None)


def get_schedule_options(workflow: str) -> list[dict[str, Any]]:
    WORKFLOW_REGISTRY.get(workflow)  # validate
    if workflow in _CRYPTO_SIGNAL_WORKFLOWS:
        return [{**o, "kind": "hours"} for o in CRYPTO_HOUR_OPTIONS]
    if workflow in _CRYPTO_SCALP_WORKFLOWS:
        return [{**o, "kind": "minutes"} for o in MINUTE_OPTIONS if o["minutes"] <= 30]
    if workflow in _CRYPTO_MONITOR_WORKFLOWS:
        return [{**o, "kind": "minutes"} for o in MINUTE_OPTIONS]
    if workflow in _CRON_WORKFLOWS:
        if workflow == "securities-dca-sandbox":
            return [{**CRON_OPTIONS[-1], "kind": "cron"}]
        return [{**o, "kind": "cron"} for o in CRON_OPTIONS if o["id"] != "monthly_dca"]
    return []


def _read_n8n_schedule(workflow_name: str) -> dict[str, Any] | None:
    wf = _find_workflow_by_name(workflow_name)
    if not wf:
        return None
    full = get_workflow(str(wf["id"]))
    nodes = _schedule_nodes(full)
    if not nodes:
        return None
    interval = (nodes[0].get("parameters") or {}).get("rule", {}).get("interval") or []
    if not interval:
        return None
    first = interval[0]
    field = first.get("field")
    if field == "hours":
        hours = int(first.get("hoursInterval") or 4)
        opt_id = next((o["id"] for o in CRYPTO_HOUR_OPTIONS if o["hours"] == hours), f"{hours}h")
        return {"option_id": opt_id, "kind": "hours", "hours": hours}
    if field == "cronExpression":
        cron = str(first.get("expression") or "")
        opt_id = next((o["id"] for o in CRON_OPTIONS if o["cron"] == cron), "custom")
        return {"option_id": opt_id, "kind": "cron", "cron": cron}
    if field == "minutes":
        mins = int(first.get("minutesInterval") or 15)
        return {"option_id": f"{mins}m", "kind": "minutes", "minutes": mins}
    return None


def get_workflow_schedule(workflow: str) -> dict[str, Any]:
    WORKFLOW_REGISTRY.get(workflow)
    stored = get_runtime_value(_schedule_key(workflow))
    option_id = _default_option_id(workflow)
    if isinstance(stored, dict) and stored.get("option_id"):
        option_id = str(stored["option_id"])

    option = _option_by_id(workflow, option_id)
    n8n = _read_n8n_schedule(workflow)
    return {
        "status": "ok",
        "workflow": workflow,
        "option_id": option_id,
        "kind": option.get("kind") if option else (n8n or {}).get("kind"),
        "label_ru": option.get("label_ru") if option else None,
        "label_en": option.get("label_en") if option else None,
        "hours": option.get("hours") if option and option.get("kind") == "hours" else None,
        "cron": option.get("cron") if option and option.get("kind") == "cron" else None,
        "n8n": n8n,
        "options": get_schedule_options(workflow),
    }


def set_workflow_schedule(
    workflow: str,
    option_id: str,
    *,
    operator: str = "web",
) -> dict[str, Any]:
    WORKFLOW_REGISTRY.get(workflow)
    option = _option_by_id(workflow, option_id)
    if not option:
        raise ValueError(f"invalid_schedule_option: {option_id}")

    wf = _find_workflow_by_name(workflow)
    if not wf:
        raise ValueError(f"missing_in_n8n: {workflow}")
    wf_id = str(wf["id"])

    if option.get("kind") == "hours":
        set_workflow_hours_interval(wf_id, int(option["hours"]))
    elif option.get("kind") == "cron":
        set_workflow_cron(wf_id, cron_expression=str(option["cron"]))
    elif option.get("kind") == "minutes":
        from n8n_service import set_workflow_minutes_interval

        set_workflow_minutes_interval(wf_id, int(option["minutes"]))
    else:
        raise ValueError(f"unsupported_schedule_kind: {option.get('kind')}")

    payload = {
        "workflow": workflow,
        "option_id": option_id,
        "kind": option.get("kind"),
        "hours": option.get("hours"),
        "cron": option.get("cron"),
        "label_ru": option.get("label_ru"),
        "label_en": option.get("label_en"),
    }
    set_runtime_value(_schedule_key(workflow), payload, updated_by=operator)
    return {"status": "ok", **payload, "n8n_workflow_id": wf_id}
