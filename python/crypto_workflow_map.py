"""Strategy + operation mode → n8n workflow name (crypto)."""

from __future__ import annotations

from typing import Any

STRATEGY_WORKFLOW_MAP: dict[str, dict[str, str]] = {
    "llm_swing": {
        "dry_run": "crypto-signal-dry-run",
        "paper": "crypto-signal-paper",
        "live": "crypto-signal-paper",
    },
    "crypto_scalp_hybrid": {
        "dry_run": "crypto-scalp-hybrid-dry-run",
        "paper": "crypto-scalp-hybrid-paper",
    },
    "deepfund_paper": {
        "paper": "deepfund-live-paper",
    },
}

STRATEGY_CHART_INTERVAL: dict[str, str] = {
    "llm_swing": "4h",
    "crypto_scalp_hybrid": "5m",
    "deepfund_paper": "4h",
}


def resolve_crypto_workflow(*, strategy_id: str, operation_mode: str) -> str:
    sid = str(strategy_id).strip()
    mode = str(operation_mode).strip().lower()
    mapping = STRATEGY_WORKFLOW_MAP.get(sid)
    if not mapping:
        raise ValueError(f"unknown_strategy: {sid}")
    wf = mapping.get(mode)
    if not wf:
        raise ValueError(f"unsupported_operation_mode:{sid}:{mode}")
    return wf


def allowed_operation_modes(strategy_id: str) -> list[str]:
    return list(STRATEGY_WORKFLOW_MAP.get(str(strategy_id), {}).keys())


def strategy_meta(strategy_id: str) -> dict[str, Any]:
    from strategy_service import get_strategy_state

    state = get_strategy_state("crypto")
    for item in state.get("strategies") or []:
        if str(item.get("id")) == strategy_id:
            return dict(item)
    catalog = state.get("strategy") or {}
    if str(catalog.get("id")) == strategy_id:
        return dict(catalog)
    return {"id": strategy_id}
