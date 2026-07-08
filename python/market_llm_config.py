"""Per-market LLM parameters — crypto and MOEX use different prompts and thresholds."""

from __future__ import annotations

from typing import Any, Literal

from config_loader import load_config

Market = Literal["crypto", "securities"]
MARKETS: tuple[Market, Market] = ("crypto", "securities")


def normalize_market(market: str | None) -> Market:
    if market == "securities":
        return "securities"
    return "crypto"


def _market_local_llm(market: Market) -> dict[str, Any]:
    if market == "crypto":
        cfg = load_config("crypto_config")
        local = dict(cfg.get("llm") or {})
        if "min_confidence" not in local and cfg.get("llm_min_confidence") is not None:
            local["min_confidence"] = cfg["llm_min_confidence"]
        if "temperature" not in local and cfg.get("llm_temperature") is not None:
            local["temperature"] = cfg["llm_temperature"]
        return local
    cfg = load_config("securities_config")
    swing = cfg.get("swing_signals") or {}
    local = dict(swing.get("llm") or cfg.get("llm") or {})
    if "min_confidence" not in local and swing.get("llm_min_confidence") is not None:
        local["min_confidence"] = swing["llm_min_confidence"]
    if "temperature" not in local and swing.get("llm_temperature") is not None:
        local["temperature"] = swing["llm_temperature"]
    return local


def get_market_llm_config(market: str) -> dict[str, Any]:
    """Shared guardrails.llm merged with market-specific overrides."""
    mkt = normalize_market(market)
    shared = load_config("guardrails").get("llm", {})
    return {**shared, **_market_local_llm(mkt)}


def get_market_ollama_model(market: str) -> str:
    mkt = normalize_market(market)
    if mkt == "crypto":
        return load_config("crypto_config").get("ollama_model", "qwen3.5:9b")
    swing = load_config("securities_config").get("swing_signals") or {}
    return swing.get("ollama_model", "qwen3.5:9b")


def get_market_prompt_version(market: str) -> str:
    mkt = normalize_market(market)
    if mkt == "crypto":
        return load_config("crypto_config").get("prompt_version", "crypto_validate_v1")
    swing = load_config("securities_config").get("swing_signals") or {}
    return swing.get("prompt_version", "securities_validate_v1")


def market_config_apply_hint(market: str) -> str:
    mkt = normalize_market(market)
    if mkt == "crypto":
        return "trading_wiki/config/crypto_config.yaml → llm.temperature / llm.min_confidence"
    return "trading_wiki/config/securities_config.yaml → swing_signals.llm"
