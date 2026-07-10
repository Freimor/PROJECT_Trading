"""n8n Public API (v1) client helpers for workflow management.

Requires an API key with scopes:
- workflow:list, workflow:read, workflow:update, workflow:activate
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx


def _n8n_base() -> str:
    return os.environ.get("N8N_API_BASE", "http://n8n:5678/api/v1").rstrip("/")


def _n8n_key() -> str:
    return os.environ.get("N8N_API_KEY", "").strip()


def _client() -> httpx.Client:
    key = _n8n_key()
    if not key:
        raise RuntimeError(
            "missing_n8n_api_key: set N8N_API_KEY (n8n Settings → API keys), "
            "and optionally N8N_API_BASE (default http://n8n:5678/api/v1)"
        )
    return httpx.Client(
        base_url=_n8n_base(),
        headers={"X-N8N-API-KEY": key, "Accept": "application/json"},
        timeout=30.0,
    )


def list_workflows(*, active: bool | None = None) -> list[dict[str, Any]]:
    """Return lightweight workflow list."""
    with _client() as c:
        params: dict[str, Any] = {}
        if active is not None:
            params["active"] = "true" if active else "false"
        resp = c.get("/workflows", params=params)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "data" in data:
            return list(data.get("data") or [])
        if isinstance(data, list):
            return data
        return []


def get_workflow(workflow_id: str) -> dict[str, Any]:
    with _client() as c:
        resp = c.get(f"/workflows/{workflow_id}")
        resp.raise_for_status()
        return dict(resp.json())


def activate_workflow(workflow_id: str) -> dict[str, Any]:
    with _client() as c:
        resp = c.post(f"/workflows/{workflow_id}/activate", json={})
        resp.raise_for_status()
        return dict(resp.json())


def deactivate_workflow(workflow_id: str) -> dict[str, Any]:
    with _client() as c:
        resp = c.post(f"/workflows/{workflow_id}/deactivate", json={})
        resp.raise_for_status()
        return dict(resp.json())


def _schedule_nodes(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = workflow.get("nodes") or []
    return [n for n in nodes if n.get("type") == "n8n-nodes-base.scheduleTrigger"]


def set_workflow_cron(
    workflow_id: str,
    *,
    cron_expression: str,
    node_id: str | None = None,
    node_name: str | None = None,
) -> dict[str, Any]:
    """Update cron expression for a Schedule Trigger node in a workflow."""
    wf = get_workflow(workflow_id)
    nodes = _schedule_nodes(wf)
    if not nodes:
        raise RuntimeError("workflow_has_no_schedule_trigger")

    target: dict[str, Any] | None = None
    if node_id:
        target = next((n for n in nodes if str(n.get("id")) == str(node_id)), None)
    if target is None and node_name:
        target = next((n for n in nodes if str(n.get("name")) == str(node_name)), None)
    if target is None:
        target = nodes[0]

    params = target.get("parameters") or {}
    rule = params.get("rule") or {}
    interval = list(rule.get("interval") or [])
    if not interval:
        interval = [{"field": "cronExpression", "expression": cron_expression}]
    else:
        # Find an existing cronExpression entry; fallback to the first.
        idx = next((i for i, it in enumerate(interval) if it.get("field") == "cronExpression"), 0)
        interval[idx] = {**interval[idx], "field": "cronExpression", "expression": cron_expression}

    rule["interval"] = interval
    params["rule"] = rule
    target["parameters"] = params

    # Persist updated workflow definition
    wf["nodes"] = wf.get("nodes") or []
    for i, n in enumerate(wf["nodes"]):
        if str(n.get("id")) == str(target.get("id")):
            wf["nodes"][i] = target
            break

    with _client() as c:
        resp = c.put(f"/workflows/{workflow_id}", json=wf)
        resp.raise_for_status()
        return dict(resp.json())


def set_workflow_hours_interval(
    workflow_id: str,
    hours_interval: int,
    *,
    node_id: str | None = None,
    node_name: str | None = None,
) -> dict[str, Any]:
    """Update hoursInterval for a Schedule Trigger (crypto signal workflows)."""
    hours = max(1, min(int(hours_interval), 24))
    wf = get_workflow(workflow_id)
    nodes = _schedule_nodes(wf)
    if not nodes:
        raise RuntimeError("workflow_has_no_schedule_trigger")

    target: dict[str, Any] | None = None
    if node_id:
        target = next((n for n in nodes if str(n.get("id")) == str(node_id)), None)
    if target is None and node_name:
        target = next((n for n in nodes if str(n.get("name")) == str(node_name)), None)
    if target is None:
        target = nodes[0]

    params = target.get("parameters") or {}
    rule = params.get("rule") or {}
    rule["interval"] = [{"field": "hours", "hoursInterval": hours}]
    params["rule"] = rule
    target["parameters"] = params

    wf["nodes"] = wf.get("nodes") or []
    for i, n in enumerate(wf["nodes"]):
        if str(n.get("id")) == str(target.get("id")):
            wf["nodes"][i] = target
            break

    with _client() as c:
        resp = c.put(f"/workflows/{workflow_id}", json=wf)
        resp.raise_for_status()
        return dict(resp.json())


def set_workflow_minutes_interval(
    workflow_id: str,
    minutes_interval: int,
    *,
    node_id: str | None = None,
    node_name: str | None = None,
) -> dict[str, Any]:
    """Update minutesInterval for a Schedule Trigger (monitor workflows)."""
    minutes = max(5, min(int(minutes_interval), 120))
    wf = get_workflow(workflow_id)
    nodes = _schedule_nodes(wf)
    if not nodes:
        raise RuntimeError("workflow_has_no_schedule_trigger")

    target: dict[str, Any] | None = None
    if node_id:
        target = next((n for n in nodes if str(n.get("id")) == str(node_id)), None)
    if target is None and node_name:
        target = next((n for n in nodes if str(n.get("name")) == str(node_name)), None)
    if target is None:
        target = nodes[0]

    params = target.get("parameters") or {}
    rule = params.get("rule") or {}
    rule["interval"] = [{"field": "minutes", "minutesInterval": minutes}]
    params["rule"] = rule
    target["parameters"] = params

    wf["nodes"] = wf.get("nodes") or []
    for i, n in enumerate(wf["nodes"]):
        if str(n.get("id")) == str(target.get("id")):
            wf["nodes"][i] = target
            break

    with _client() as c:
        resp = c.put(f"/workflows/{workflow_id}", json=wf)
        resp.raise_for_status()
        return dict(resp.json())


WORKFLOW_EXPORT_FILES: dict[str, str] = {
    "shared-global-error-handler": "shared/shared-global-error-handler.json",
    "shared-health-check": "shared/shared-health-check.json",
    "shared-telegram-alert": "shared/shared-telegram-alert.json",
    "news-ingest": "news/news-ingest.json",
    "regulatory-monitor": "news/regulatory-monitor.json",
    "crypto-signal-dry-run": "crypto/crypto-signal-dry-run.json",
    "crypto-signal-paper": "crypto/crypto-signal-paper.json",
    "crypto-scalp-hybrid-dry-run": "crypto/crypto-scalp-hybrid-dry-run.json",
    "crypto-scalp-hybrid-paper": "crypto/crypto-scalp-hybrid-paper.json",
    "crypto-execute-testnet": "crypto/crypto-execute-testnet.json",
    "crypto-monitor-testnet": "crypto/crypto-monitor-testnet.json",
    "securities-dca-sandbox": "securities/securities-dca-sandbox.json",
    "securities-swing-dry-run": "securities/securities-swing-dry-run.json",
    "securities-swing-paper": "securities/securities-swing-paper.json",
    "securities-factor-sleeve": "securities/securities-factor-sleeve.json",
    "bond-ladder-flow": "securities/bond-ladder-flow.json",
    "analysis-llm-report": "analysis/analysis-llm-report.json",
    "deepfund-live-paper": "analysis/deepfund-live-paper.json",
    "neuratrade-harness": "analysis/neuratrade-harness.json",
    "papers-monitor-weekly": "analysis/papers-monitor-weekly.json",
    "finsaber-backtest-weekly": "analysis/finsaber-backtest-weekly.json",
    "llm-benchmark-weekly": "analysis/llm-benchmark-weekly.json",
}

MARKET_IMPORT_ORDER: dict[str, list[str]] = {
    "crypto": [
        "crypto-signal-dry-run",
        "crypto-signal-paper",
        "crypto-execute-testnet",
        "crypto-monitor-testnet",
    ],
    "securities": [
        "securities-dca-sandbox",
        "securities-swing-dry-run",
        "securities-swing-paper",
    ],
}

ALL_IMPORT_ORDER: list[str] = [
    "shared-global-error-handler",
    "shared-health-check",
    "shared-telegram-alert",
    "news-ingest",
    "regulatory-monitor",
    *MARKET_IMPORT_ORDER["crypto"],
    "crypto-scalp-hybrid-dry-run",
    "crypto-scalp-hybrid-paper",
    *MARKET_IMPORT_ORDER["securities"],
    "securities-factor-sleeve",
    "bond-ladder-flow",
    "analysis-llm-report",
    "deepfund-live-paper",
    "neuratrade-harness",
    "papers-monitor-weekly",
    "finsaber-backtest-weekly",
    "llm-benchmark-weekly",
]


def _workflows_root() -> Path:
    return Path(os.environ.get("N8N_WORKFLOWS_PATH", "/data/n8n_automation/workflows"))


def _workflow_path(name: str) -> Path:
    rel = WORKFLOW_EXPORT_FILES.get(name)
    if not rel:
        raise ValueError(f"unknown_workflow_export: {name}")
    path = _workflows_root() / rel
    if not path.is_file():
        raise FileNotFoundError(f"workflow_file_missing: {path}")
    return path


def _import_payload(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": str(raw.get("name") or ""),
        "nodes": raw.get("nodes") or [],
        "connections": raw.get("connections") or {},
        "settings": raw.get("settings") or {},
    }


def _find_workflow_by_name(name: str) -> dict[str, Any] | None:
    for wf in list_workflows():
        if str(wf.get("name")) == name:
            return wf
    return None


def import_workflow_by_name(name: str, *, update_if_exists: bool = True) -> dict[str, Any]:
    """Create or update a workflow in n8n from repo JSON export."""
    path = _workflow_path(name)
    raw = json.loads(path.read_text(encoding="utf-8"))
    payload = _import_payload(raw)
    if not payload["name"]:
        payload["name"] = name

    existing = _find_workflow_by_name(payload["name"])
    with _client() as c:
        if existing and update_if_exists:
            wf_id = str(existing["id"])
            current = get_workflow(wf_id)
            current["nodes"] = payload["nodes"]
            current["connections"] = payload["connections"]
            current["settings"] = payload.get("settings") or current.get("settings") or {}
            resp = c.put(f"/workflows/{wf_id}", json=current)
            resp.raise_for_status()
            body = dict(resp.json())
            return {
                "name": payload["name"],
                "action": "updated",
                "id": body.get("id") or wf_id,
            }

        if existing:
            return {
                "name": payload["name"],
                "action": "exists",
                "id": existing.get("id"),
            }

        resp = c.post("/workflows", json=payload)
        resp.raise_for_status()
        body = dict(resp.json())
        return {
            "name": payload["name"],
            "action": "created",
            "id": body.get("id"),
        }


def import_workflows(names: list[str], *, update_if_exists: bool = True) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for name in names:
        try:
            results.append(import_workflow_by_name(name, update_if_exists=update_if_exists))
        except Exception as exc:
            errors.append({"name": name, "error": str(exc)})
    return {"status": "ok" if not errors else "partial", "workflows": results, "errors": errors}


def import_market_workflows(market: str, *, update_if_exists: bool = True) -> dict[str, Any]:
    if market not in MARKET_IMPORT_ORDER:
        raise ValueError(f"unknown_market: {market}")
    return import_workflows(MARKET_IMPORT_ORDER[market], update_if_exists=update_if_exists)


def import_all_workflows(*, update_if_exists: bool = True) -> dict[str, Any]:
    return import_workflows(ALL_IMPORT_ORDER, update_if_exists=update_if_exists)
