"""Merged config: YAML + runtime overrides."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from automation_control_service import (
    get_config_effective,
    get_effective_market_mode,
    get_effective_trading_mode,
)
from config_loader import load_config
from runtime_settings import is_kill_switch_active


def get_guardrails() -> dict[str, Any]:
    g = deepcopy(load_config("guardrails"))
    trading = dict(g.get("trading", {}))
    yaml_kill = bool(trading.get("kill_switch", False))
    trading["kill_switch"] = is_kill_switch_active(yaml_kill)
    trading["mode"] = get_effective_trading_mode()
    g["trading"] = trading
    llm = dict(g.get("llm") or {})
    try:
        from llm_assist_service import get_effective_guardrails_llm_mode

        llm["mode"] = get_effective_guardrails_llm_mode()
    except Exception:
        pass
    g["llm"] = llm
    return g


__all__ = [
    "get_guardrails",
    "get_config_effective",
    "get_effective_market_mode",
    "get_effective_trading_mode",
]
