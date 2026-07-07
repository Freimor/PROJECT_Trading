"""Investment strategy catalog and runtime selection per market."""

from __future__ import annotations

from typing import Any, Literal

from config_loader import load_config
from effective_config import get_config_effective
from runtime_settings import get_runtime_value, set_runtime_value

Market = Literal["crypto", "securities"]


def _workflow_for_mode(config_name: str, *, dry_run: str, paper: str) -> str:
    mode = get_config_effective(config_name).get("mode", "dry_run")
    return paper if str(mode) != "dry_run" else dry_run


def _runtime_key(market: str) -> str:
    return f"strategy_{market}"


def get_active_strategy_id(market: str) -> str:
    runtime = get_runtime_value(_runtime_key(market))
    if runtime:
        return str(runtime)
    if market == "securities":
        return str(load_config("securities_config").get("active_mode", "swing_signals"))
    if market == "crypto":
        return str(load_config("crypto_config").get("active_strategy", "llm_swing"))
    return ""


def _securities_catalog() -> dict[str, dict[str, Any]]:
    sec = get_config_effective("securities_config")
    swing = sec.get("swing_signals", {})
    universe = list(swing.get("universe", ["SBER", "GAZP", "LKOH"]))
    return {
        "swing_signals": {
            "id": "swing_signals",
            "label": "Swing + LLM",
            "description": "Акции из universe: технический фильтр и LLM по будням",
            "workflow": _workflow_for_mode(
                "securities_config",
                dry_run="securities-swing-dry-run",
                paper="securities-swing-paper",
            ),
            "symbols": universe,
            "chart_default": universe[0] if universe else "SBER",
            "chart_interval": "1d",
            "uses_llm": True,
        },
    }


def _crypto_catalog() -> dict[str, dict[str, Any]]:
    crypto = get_config_effective("crypto_config")
    pairs = list(crypto.get("pairs", ["BTCUSDT", "ETHUSDT"]))
    return {
        "llm_swing": {
            "id": "llm_swing",
            "label": "LLM swing (4h)",
            "description": "Сигнал по индикаторам + проверка LLM на парах BTC/ETH",
            "workflow": _workflow_for_mode(
                "crypto_config",
                dry_run="crypto-signal-dry-run",
                paper="crypto-signal-paper",
            ),
            "symbols": pairs,
            "chart_default": pairs[0] if pairs else "BTCUSDT",
            "chart_interval": crypto.get("timeframe", "4h"),
            "uses_llm": True,
        },
    }


def get_strategy_catalog(market: str) -> dict[str, Any]:
    if market == "securities":
        strategies = _securities_catalog()
    elif market == "crypto":
        strategies = _crypto_catalog()
    else:
        raise ValueError(f"unknown market: {market}")

    active = get_active_strategy_id(market)
    if active not in strategies:
        active = next(iter(strategies))

    return {
        "market": market,
        "active": active,
        "strategies": list(strategies.values()),
    }


def get_strategy_state(market: str) -> dict[str, Any]:
    catalog = get_strategy_catalog(market)
    active_id = catalog["active"]
    strategies = {s["id"]: s for s in catalog["strategies"]}
    active = strategies.get(active_id, catalog["strategies"][0])
    return {
        "market": market,
        "active": active_id,
        "strategy": active,
        "strategies": catalog["strategies"],
    }


def set_active_strategy(
    market: str,
    strategy_id: str,
    *,
    operator: str = "web",
) -> dict[str, Any]:
    catalog = get_strategy_catalog(market)
    valid = {s["id"] for s in catalog["strategies"]}
    if strategy_id not in valid:
        raise ValueError(f"unknown strategy: {strategy_id}")

    set_runtime_value(_runtime_key(market), strategy_id, updated_by=operator)

    try:
        from activity_feed_service import log_system_activity

        label = next(s["label"] for s in catalog["strategies"] if s["id"] == strategy_id)
        log_system_activity(
            f"Стратегия {market}: {label}",
            category=market,
            level="info",
        )
    except Exception:
        pass

    return get_strategy_state(market)


def symbols_for_market(market: str) -> list[str]:
    state = get_strategy_state(market)
    return list(state["strategy"].get("symbols", []))
