"""Runtime overrides for crypto scalp universe pre-scan thresholds."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from config_loader import load_config
from runtime_settings import delete_runtime_value, get_runtime_meta, set_runtime_value

RUNTIME_KEY = "crypto_scalp_universe_scan_settings"

# Binance spot taker ~0.10% × 2 ≈ 0.20% round-trip; min ATR must exceed fees.
DEFAULT_ROUND_TRIP_FEE_PCT = 0.20

SCAN_PARAM_BOUNDS: dict[str, dict[str, float | int]] = {
    "top_n": {"min": 1, "max": 10, "type": "int"},
    "min_score": {"min": 0.1, "max": 0.95, "type": "float"},
    "atr_pct_min": {"min": 0.20, "max": 1.5, "type": "float"},
    "atr_pct_max": {"min": 0.5, "max": 5.0, "type": "float"},
    "atr_pct_sweet_min": {"min": 0.15, "max": 2.0, "type": "float"},
    "atr_pct_sweet_max": {"min": 0.3, "max": 3.0, "type": "float"},
    "volume_ratio_min": {"min": 0.5, "max": 3.0, "type": "float"},
    "momentum_min_pct": {"min": 0.02, "max": 1.0, "type": "float"},
    "max_pair_correlation": {"min": 0.5, "max": 0.99, "type": "float"},
    "rescan_interval_hours": {"min": 1, "max": 24, "type": "int"},
}


def _yaml_scan_defaults() -> dict[str, Any]:
    return deepcopy(load_config("crypto_scalp_hybrid").get("universe_scan") or {})


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
    merged["round_trip_fee_pct"] = DEFAULT_ROUND_TRIP_FEE_PCT
    merged["atr_pct_min_floor"] = float(SCAN_PARAM_BOUNDS["atr_pct_min"]["min"])
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
        if key == "rescan_during_session":
            out[key] = bool(val)
            continue
        if key not in SCAN_PARAM_BOUNDS:
            continue
        out[key] = _clamp_param(key, val)

    atr_min = float(out.get("atr_pct_min", SCAN_PARAM_BOUNDS["atr_pct_min"]["min"]))
    if atr_min < DEFAULT_ROUND_TRIP_FEE_PCT:
        raise ValueError(
            f"atr_pct_min_below_fees: need ≥ {DEFAULT_ROUND_TRIP_FEE_PCT}% (round-trip taker fees)"
        )

    if "atr_pct_sweet_min" in out and out["atr_pct_sweet_min"] < atr_min:
        out["atr_pct_sweet_min"] = atr_min
    if "atr_pct_max" in out and "atr_pct_min" in out and out["atr_pct_max"] <= out["atr_pct_min"]:
        out["atr_pct_max"] = out["atr_pct_min"] + 0.1
    sweet_lo = float(out.get("atr_pct_sweet_min", atr_min))
    sweet_hi = float(out.get("atr_pct_sweet_max", sweet_lo + 0.5))
    if sweet_hi <= sweet_lo:
        out["atr_pct_sweet_max"] = sweet_lo + 0.1

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
