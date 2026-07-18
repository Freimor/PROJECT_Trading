"""Strategy + operation mode → n8n workflow name (MOEX / securities)."""

from __future__ import annotations

from typing import Any

SECURITIES_STRATEGY_MODES: dict[str, list[str]] = {
    "swing_signals": ["dry_run", "paper", "live"],
    "index_dca": ["paper"],
    "factor_sleeve": ["paper"],
    "bond_ladder": ["paper"],
}

STRATEGY_WORKFLOW_MAP: dict[str, dict[str, str]] = {
    "swing_signals": {
        "dry_run": "securities-swing-dry-run",
        "paper": "securities-swing-paper",
        "live": "securities-swing-paper",
    },
    "index_dca": {
        "paper": "securities-dca-sandbox",
    },
    "factor_sleeve": {
        "paper": "securities-factor-sleeve",
    },
    "bond_ladder": {
        "paper": "bond-ladder-flow",
    },
}

MULTI_SYMBOL_STRATEGIES = frozenset({"swing_signals", "factor_sleeve"})

STRATEGY_CHART_INTERVAL: dict[str, str] = {
    "swing_signals": "1d",
    "index_dca": "1d",
    "factor_sleeve": "1d",
    "bond_ladder": "1d",
}


def resolve_securities_workflow(*, strategy_id: str, operation_mode: str) -> str:
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
    return list(SECURITIES_STRATEGY_MODES.get(str(strategy_id), STRATEGY_WORKFLOW_MAP.get(str(strategy_id), {}).keys()))


def supports_multi_symbol(strategy_id: str) -> bool:
    return str(strategy_id) in MULTI_SYMBOL_STRATEGIES


def strategy_meta(strategy_id: str) -> dict[str, Any]:
    from strategy_service import get_strategy_state

    state = get_strategy_state("securities")
    for item in state.get("strategies") or []:
        if str(item.get("id")) == strategy_id:
            return dict(item)
    catalog = state.get("strategy") or {}
    if str(catalog.get("id")) == strategy_id:
        return dict(catalog)
    return {"id": strategy_id}


def chart_interval_for_strategy(strategy_id: str) -> str:
    return STRATEGY_CHART_INTERVAL.get(str(strategy_id), "1d")
