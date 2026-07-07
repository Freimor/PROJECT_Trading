"""Merged config: YAML + runtime overrides."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from config_loader import load_config
from runtime_settings import is_kill_switch_active


def get_guardrails() -> dict[str, Any]:
    g = deepcopy(load_config("guardrails"))
    trading = dict(g.get("trading", {}))
    yaml_kill = bool(trading.get("kill_switch", False))
    trading["kill_switch"] = is_kill_switch_active(yaml_kill)
    g["trading"] = trading
    return g
