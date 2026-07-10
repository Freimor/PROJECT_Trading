"""Human-readable filter reject details for trade events."""

from __future__ import annotations

import json
from typing import Any

_RULE_LABELS = {
    "rsi_oversold": "RSI перепродан",
    "rsi_overbought": "RSI перекуплен",
    "macd_bullish_cross": "MACD бычий",
    "golden_cross_context": "Золотой крест",
}


def filter_log_payload(filtered: dict[str, Any], *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Structured payload to store on filter stage events."""
    payload: dict[str, Any] = {
        "filter_thresholds": filtered.get("filter_thresholds"),
        "filter_checks": filtered.get("filter_checks"),
        "rule_name": filtered.get("rule_name"),
        "actual": {
            "rsi_14": filtered.get("rsi_14"),
            "macd": filtered.get("macd"),
            "macd_signal": filtered.get("macd_signal"),
            "macd_histogram": filtered.get("macd_histogram"),
            "close": filtered.get("close"),
            "ema50": filtered.get("ema50"),
            "ema200": filtered.get("ema200"),
        },
    }
    if context:
        for key in (
            "active_swing_profile_id",
            "active_risk_profile_id",
            "llm_min_confidence",
            "workflow_name",
        ):
            if context.get(key) is not None:
                payload[key] = context[key]
    return payload


def _parse_payload(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("payload_json") or row.get("payload")
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _current_thresholds_for_market(market: str) -> dict[str, Any] | None:
    try:
        from config_loader import load_config

        if market == "crypto":
            from swing_conservatism_service import apply_swing_conservatism_crypto
            from effective_config import get_config_effective

            cfg = apply_swing_conservatism_crypto(get_config_effective("crypto_config"))
            return cfg.get("rule_filter")
        if market == "securities":
            from swing_conservatism_service import apply_swing_conservatism_securities
            from effective_config import get_config_effective

            sec = apply_swing_conservatism_securities(get_config_effective("securities_config"))
            swing = sec.get("swing_signals", {})
            return swing.get("rule_filter") or {"rsi_oversold": 40, "rsi_overbought": 60}
    except Exception:
        return None
    return None


def _thresholds_for_row(row: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    thresholds = payload.get("filter_thresholds")
    if thresholds:
        return thresholds
    current = _current_thresholds_for_market(str(row.get("market") or ""))
    return current or {"rsi_oversold": 35, "rsi_overbought": 65}


def _fmt_num(val: Any) -> str:
    if val is None:
        return "—"
    if isinstance(val, float):
        return f"{val:.4f}" if abs(val) < 10 else f"{val:.2f}"
    return str(val)


def summarize_filter_activity(row: dict[str, Any]) -> str:
    """One short line for the system activity feed."""
    symbol = row.get("symbol") or "?"
    decision = str(row.get("decision") or "")
    if decision == "approve":
        payload = _parse_payload(row)
        rule_name = payload.get("rule_name")
        if rule_name:
            return f"Фильтр пройден {symbol}: {rule_name}"
        return f"Фильтр пройден {symbol}"
    return f"Фильтр отклонил {symbol}"


def summarize_filter_detail(row: dict[str, Any]) -> str:
    """Human-readable multi-line text for journal / expanded view."""
    symbol = row.get("symbol") or "?"
    decision = str(row.get("decision") or "")
    payload = _parse_payload(row)
    actual = payload.get("actual") or {}
    checks = payload.get("filter_checks") or []
    thresholds = _thresholds_for_row(row, payload)
    oversold = thresholds.get("rsi_oversold", 35)
    overbought = thresholds.get("rsi_overbought", 65)

    if decision == "approve":
        rule_name = payload.get("rule_name")
        if rule_name:
            return f"Фильтр пройден {symbol}.\nСработало правило: {rule_name}."
        return f"Фильтр пройден {symbol}."

    lines = [f"Фильтр отклонил {symbol}: {row.get('reject_reason') or 'no_rule_match'}."]

    rsi = actual.get("rsi_14")
    if rsi is not None:
        lines.append(
            f"RSI={_fmt_num(rsi)}, нужно RSI < {oversold} (перепродан) или RSI > {overbought} (перекуплен)"
        )
    elif checks:
        lines.append(f"RSI недоступен, пороги: < {oversold} / > {overbought}")

    check_by_rule = {str(c.get("rule")): c for c in checks}
    macd_check = check_by_rule.get("macd_bullish_cross")
    if macd_check and not macd_check.get("passed"):
        hist = actual.get("macd_histogram")
        macd_v = actual.get("macd")
        sig = actual.get("macd_signal")
        lines.append(
            f"MACD: hist={_fmt_num(hist)}, MACD={_fmt_num(macd_v)}, signal={_fmt_num(sig)} — "
            "нужны hist > 0 и MACD > signal"
        )

    golden = check_by_rule.get("golden_cross_context")
    if golden and not golden.get("passed"):
        detail = golden.get("detail") or "условие не выполнено"
        lines.append(f"Золотой крест: {detail}")

    for check in checks:
        rule = str(check.get("rule"))
        if rule in ("rsi_oversold", "rsi_overbought", "macd_bullish_cross", "golden_cross_context"):
            continue
        if not check.get("passed"):
            label = _RULE_LABELS.get(rule, rule)
            lines.append(f"{label}: {check.get('detail') or 'не выполнено'}")

    lines.append(f"Пороги фильтра: RSI перепродан < {oversold}, перекуплен > {overbought}")
    swing_profile = payload.get("active_swing_profile_id")
    risk_profile = payload.get("active_risk_profile_id")
    if swing_profile or risk_profile:
        parts = []
        if swing_profile:
            parts.append(f"swing={swing_profile}")
        if risk_profile:
            parts.append(f"risk={risk_profile}")
        lines.append(f"Пресеты: {', '.join(parts)}")
    return "\n".join(lines)


def summarize_filter_event(row: dict[str, Any], *, compact: bool = False) -> str:
    """Backward-compatible entry: feed=short, detail=human multi-line."""
    if compact:
        return summarize_filter_activity(row)
    return summarize_filter_detail(row)
