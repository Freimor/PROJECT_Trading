"""Runtime risk presets — conservative / balanced / aggressive."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from config_loader import load_config
from runtime_settings import get_runtime_meta, get_runtime_value, set_runtime_value
from risk_trading_state import risk_change_blocked_reason
from swing_conservatism_service import get_swing_signal_summary, swing_options_for_market

RUNTIME_KEY_PREFIX = "risk_profile:"

RISK_PROFILES: dict[str, dict[str, Any]] = {
    "conservative": {
        "id": "conservative",
        "label_ru": "Консервативный",
        "label_en": "Conservative",
        "description_ru": "Меньший риск на сделку + строже rule filter и LLM (RSI 32/68, MACD cross).",
        "description_en": "Lower per-trade risk + stricter rule filter and LLM (RSI 32/68, MACD cross).",
        "trading": {
            "risk_per_trade_pct": 0.005,
            "daily_loss_limit_pct": 0.02,
            "max_open_positions_crypto": 1,
            "max_open_positions_securities": 1,
            "max_notional_pct_equity": 0.03,
            "min_stop_distance_pct": 0.015,
        },
    },
    "balanced": {
        "id": "balanced",
        "label_ru": "Сбалансированный",
        "label_en": "Balanced",
        "description_ru": "Базовые пороги сигнала и риска из YAML (рекомендуется для paper).",
        "description_en": "Default signal and risk thresholds from YAML (recommended for paper).",
        "trading": {
            "risk_per_trade_pct": 0.01,
            "daily_loss_limit_pct": 0.03,
            "max_open_positions_crypto": 2,
            "max_open_positions_securities": 3,
            "max_notional_pct_equity": 0.05,
            "min_stop_distance_pct": 0.015,
        },
    },
    "aggressive": {
        "id": "aggressive",
        "label_ru": "Агрессивный",
        "label_en": "Aggressive",
        "description_ru": "Больше риска и мягче filter/LLM (RSI 38/62) — после стабильной статистики.",
        "description_en": "Higher risk and softer filter/LLM (RSI 38/62) — after stable paper stats.",
        "trading": {
            "risk_per_trade_pct": 0.015,
            "daily_loss_limit_pct": 0.05,
            "max_open_positions_crypto": 3,
            "max_open_positions_securities": 4,
            "max_notional_pct_equity": 0.08,
            "min_stop_distance_pct": 0.012,
        },
    },
}

DEFAULT_PROFILE_ID = "balanced"


def _runtime_key(market: str) -> str:
    return f"{RUNTIME_KEY_PREFIX}{market}"


def _yaml_default_profile_id() -> str:
    try:
        g = load_config("guardrails")
        return str(g.get("risk_profiles", {}).get("default", DEFAULT_PROFILE_ID))
    except FileNotFoundError:
        return DEFAULT_PROFILE_ID


def get_active_profile_id(market: str) -> str:
    stored = get_runtime_value(_runtime_key(market))
    if isinstance(stored, dict) and stored.get("profile_id") in RISK_PROFILES:
        return str(stored["profile_id"])
    if isinstance(stored, str) and stored in RISK_PROFILES:
        return stored
    default = _yaml_default_profile_id()
    return default if default in RISK_PROFILES else DEFAULT_PROFILE_ID


def get_profile_trading_limits(market: str) -> dict[str, Any]:
    """Effective trading limits for a market (YAML base + preset overlay)."""
    g = load_config("guardrails")
    trading = dict(g.get("trading", {}))
    profile_id = get_active_profile_id(market)
    preset = RISK_PROFILES[profile_id]["trading"]
    trading.update(preset)
    return trading


def get_max_open_positions(market: str, trading: dict[str, Any] | None = None) -> int:
    t = trading or get_profile_trading_limits(market)
    if market == "crypto":
        return int(t.get("max_open_positions_crypto", 2))
    return int(t.get("max_open_positions_securities", 3))


def apply_risk_profile_to_guardrails(guardrails: dict[str, Any], market: str) -> dict[str, Any]:
    """Return guardrails copy with market-specific trading limits from active preset."""
    out = deepcopy(guardrails)
    trading = dict(out.get("trading", {}))
    trading.update(get_profile_trading_limits(market))
    out["trading"] = trading
    out["active_risk_profile_id"] = get_active_profile_id(market)
    return out


def _limits_from_trading(trading: dict[str, Any], market: str) -> dict[str, Any]:
    return {
        "risk_per_trade_pct": trading.get("risk_per_trade_pct"),
        "daily_loss_limit_pct": trading.get("daily_loss_limit_pct"),
        "max_open_positions": get_max_open_positions(market, trading),
        "max_notional_pct_equity": trading.get("max_notional_pct_equity"),
        "min_stop_distance_pct": trading.get("min_stop_distance_pct"),
    }


def _options_for_market(market: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in RISK_PROFILES.values():
        trading = p["trading"]
        out.append(
            {
                "id": p["id"],
                "label_ru": p["label_ru"],
                "label_en": p["label_en"],
                "description_ru": p["description_ru"],
                "description_en": p["description_en"],
                "limits": _limits_from_trading(trading, market),
            }
        )
    return out


def get_risk_profile_state(market: str) -> dict[str, Any]:
    if market not in ("crypto", "securities"):
        raise ValueError(f"unknown_market: {market}")

    profile_id = get_active_profile_id(market)
    limits = get_profile_trading_limits(market)
    meta = get_runtime_meta(_runtime_key(market))
    block = risk_change_blocked_reason(market)
    active_preset = RISK_PROFILES[profile_id]

    return {
        "market": market,
        "profile_id": profile_id,
        "profile_label_ru": active_preset["label_ru"],
        "profile_label_en": active_preset["label_en"],
        "runtime_override": meta is not None,
        "updated_at": meta.get("updated_at") if meta else None,
        "updated_by": meta.get("updated_by") if meta else None,
        "options": _options_for_market(market),
        "effective_limits": _limits_from_trading(limits, market),
        "effective_swing_signals": get_swing_signal_summary(market, profile_id),
        "swing_signal_options": swing_options_for_market(market),
        "can_change": block is None,
        "change_blocked_reason": block,
    }


def set_risk_profile(
    market: str,
    profile_id: str,
    *,
    operator: str = "web",
) -> dict[str, Any]:
    if market not in ("crypto", "securities"):
        raise ValueError(f"unknown_market: {market}")
    if profile_id not in RISK_PROFILES:
        raise ValueError(f"unknown_profile: {profile_id}")

    block = risk_change_blocked_reason(market)
    if block:
        raise ValueError(f"risk_profile_change_blocked:{block}")

    set_runtime_value(
        _runtime_key(market),
        {"profile_id": profile_id, "market": market},
        updated_by=operator,
    )
    return get_risk_profile_state(market)


def reset_risk_profile(market: str, *, operator: str = "web") -> dict[str, Any]:
    block = risk_change_blocked_reason(market)
    if block:
        raise ValueError(f"risk_profile_change_blocked:{block}")

    from runtime_settings import delete_runtime_value

    delete_runtime_value(_runtime_key(market))
    return get_risk_profile_state(market)
