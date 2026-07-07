"""n8n Public API (v1) client helpers for workflow management.

Requires an API key with scopes:
- workflow:list, workflow:read, workflow:update, workflow:activate
"""

from __future__ import annotations

from typing import Any

import os

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

