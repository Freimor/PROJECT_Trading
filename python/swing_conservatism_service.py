"""Swing signal conservatism — rule filter + LLM thresholds per risk preset."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from config_loader import load_config
from effective_config import get_config_effective


def _cfg() -> dict[str, Any]:
    try:
        return load_config("swing_conservatism")
    except FileNotFoundError:
        return {"profiles": {}}


def _active_profile(market: str) -> str:
    from risk_profile_service import get_active_profile_id

    return get_active_profile_id(market)


def _profile_overlay(profile_id: str) -> dict[str, Any]:
    profiles = _cfg().get("profiles") or {}
    return dict(profiles.get(profile_id) or profiles.get("balanced") or {})


def _merge_section(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    if not overlay:
        return dict(base)
    return {**base, **overlay}


def get_swing_signal_summary(market: str, profile_id: str | None = None) -> dict[str, Any]:
    """Human-readable effective swing thresholds for UI."""
    pid = profile_id or _active_profile(market)
    overlay = _profile_overlay(pid)
    if market == "crypto":
        base = get_config_effective("crypto_config")
        rf = _merge_section(dict(base.get("rule_filter") or {}), dict(overlay.get("rule_filter") or {}))
        llm = _merge_section(dict(base.get("llm") or {}), dict(overlay.get("llm") or {}))
        rg = _merge_section(dict(base.get("retail_guard") or {}), dict(overlay.get("retail_guard") or {}))
    else:
        sec = get_config_effective("securities_config")
        swing = dict(sec.get("swing_signals") or {})
        rf = _merge_section(
            dict(swing.get("rule_filter") or {"rsi_oversold": 40, "rsi_overbought": 60}),
            dict(overlay.get("rule_filter") or {}),
        )
        llm = _merge_section(dict(swing.get("llm") or sec.get("llm") or {}), dict(overlay.get("llm") or {}))
        rg = {}

    return {
        "profile_id": pid,
        "rule_filter": rf,
        "llm": llm,
        "retail_guard": rg if rg else None,
        "notes_ru": overlay.get("notes_ru"),
        "notes_en": overlay.get("notes_en"),
        "signal_label_ru": overlay.get("label_ru"),
        "signal_label_en": overlay.get("label_en"),
    }


def apply_swing_conservatism_crypto(crypto_cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge active risk preset overlays into crypto_config copy."""
    cfg = deepcopy(crypto_cfg or get_config_effective("crypto_config"))
    overlay = _profile_overlay(_active_profile("crypto"))
    cfg["rule_filter"] = _merge_section(dict(cfg.get("rule_filter") or {}), dict(overlay.get("rule_filter") or {}))
    cfg["llm"] = _merge_section(dict(cfg.get("llm") or {}), dict(overlay.get("llm") or {}))
    if overlay.get("retail_guard"):
        cfg["retail_guard"] = _merge_section(
            dict(cfg.get("retail_guard") or {}),
            dict(overlay.get("retail_guard") or {}),
        )
    cfg["active_swing_profile_id"] = _active_profile("crypto")
    return cfg


def apply_swing_conservatism_securities(sec_cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge preset into securities swing_signals block."""
    cfg = deepcopy(sec_cfg or get_config_effective("securities_config"))
    overlay = _profile_overlay(_active_profile("securities"))
    swing = dict(cfg.get("swing_signals") or {})
    swing["rule_filter"] = _merge_section(
        dict(swing.get("rule_filter") or {"rsi_oversold": 40, "rsi_overbought": 60}),
        dict(overlay.get("rule_filter") or {}),
    )
    swing["llm"] = _merge_section(dict(swing.get("llm") or {}), dict(overlay.get("llm") or {}))
    cfg["swing_signals"] = swing
    cfg["active_swing_profile_id"] = _active_profile("securities")
    return cfg


def swing_options_for_market(market: str) -> list[dict[str, Any]]:
    """Per-preset signal summary for risk profile picker."""
    from risk_profile_service import RISK_PROFILES

    out: list[dict[str, Any]] = []
    for pid in RISK_PROFILES:
        summary = get_swing_signal_summary(market, pid)
        rf = summary.get("rule_filter") or {}
        llm = summary.get("llm") or {}
        out.append(
            {
                "profile_id": pid,
                "signal_label_ru": summary.get("signal_label_ru"),
                "signal_label_en": summary.get("signal_label_en"),
                "notes_ru": summary.get("notes_ru"),
                "notes_en": summary.get("notes_en"),
                "rsi_oversold": rf.get("rsi_oversold"),
                "rsi_overbought": rf.get("rsi_overbought"),
                "require_macd_cross": rf.get("require_macd_cross"),
                "min_confidence": llm.get("min_confidence"),
            }
        )
    return out
