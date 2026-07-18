"""Runtime overrides for MOEX ISS universe pre-scan (securities swing)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from config_loader import load_config
from runtime_settings import delete_runtime_value, get_runtime_meta, set_runtime_value

RUNTIME_KEY = "securities_universe_scan_settings"

SCAN_PARAM_BOUNDS: dict[str, dict[str, float | int | str]] = {
    "top_n": {"min": 1, "max": 15, "type": "int"},
    "min_score": {"min": 0.1, "max": 0.95, "type": "float"},
    "min_valtoday_mln": {"min": 1, "max": 5000, "type": "float"},
    "min_numtrades": {"min": 0, "max": 100_000, "type": "int"},
    "max_scan_tickers": {"min": 5, "max": 80, "type": "int"},
    "volume_ratio_min": {"min": 0.1, "max": 3.0, "type": "float"},
    "momentum_min_pct": {"min": 0.1, "max": 10.0, "type": "float"},
}


def _yaml_scan_defaults() -> dict[str, Any]:
    return deepcopy(load_config("securities_config").get("universe_scan") or {})


def _clamp_param(key: str, value: Any) -> Any:
    bounds = SCAN_PARAM_BOUNDS.get(key)
    if not bounds:
        return value
    lo = float(bounds["min"])
    hi = float(bounds["max"])
    if bounds.get("type") == "int":
        return int(max(lo, min(hi, round(float(value)))))
    return round(max(lo, min(hi, float(value))), 4)


def get_effective_scan_settings() -> dict[str, Any]:
    yaml_cfg = _yaml_scan_defaults()
    meta = get_runtime_meta(RUNTIME_KEY) or {}
    runtime = meta.get("value") if isinstance(meta.get("value"), dict) else {}
    merged = {**yaml_cfg, **(runtime or {})}
    param_meta: dict[str, dict[str, Any]] = {}
    for key, bounds in SCAN_PARAM_BOUNDS.items():
        param_meta[key] = {
            "min": bounds["min"],
            "max": bounds["max"],
            "recommended": yaml_cfg.get(key),
            "type": bounds.get("type", "float"),
        }
    return {
        "effective": merged,
        "yaml_defaults": yaml_cfg,
        "recommended": {k: yaml_cfg.get(k) for k in SCAN_PARAM_BOUNDS},
        "param_meta": param_meta,
        "runtime_override": bool(runtime),
        "bounds": SCAN_PARAM_BOUNDS,
        "editable_keys": list(SCAN_PARAM_BOUNDS.keys()),
    }


def get_merged_scan_config() -> dict[str, Any]:
    return dict(get_effective_scan_settings()["effective"])


def validate_scan_settings_patch(patch: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, val in patch.items():
        if key in ("equities_only", "use_whitelist"):
            out[key] = bool(val)
            continue
        if key not in SCAN_PARAM_BOUNDS:
            continue
        out[key] = _clamp_param(key, val)
    return out


def set_scan_settings(patch: dict[str, Any], *, operator: str = "web:operator") -> dict[str, Any]:
    validated = validate_scan_settings_patch(patch)
    if not validated:
        raise ValueError("empty_scan_settings_patch")
    current = get_runtime_meta(RUNTIME_KEY) or {}
    base = current.get("value") if isinstance(current.get("value"), dict) else {}
    merged = {**base, **validated}
    set_runtime_value(RUNTIME_KEY, merged, updated_by=operator)
    return get_effective_scan_settings()


def reset_scan_settings(*, operator: str = "web:operator") -> dict[str, Any]:
    delete_runtime_value(RUNTIME_KEY)
    return get_effective_scan_settings()
