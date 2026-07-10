"""TradingAgents multi-agent orchestration (arXiv:2412.20138)."""

from __future__ import annotations

import json
from typing import Any

import httpx

from config_loader import load_config
from llm_client import validate_signal


def _cfg() -> dict[str, Any]:
    return load_config("trading_agents_config")


def _ollama_generate(model: str, prompt: str, system: str = "") -> str:
    host = __import__("os").environ.get("OLLAMA_HOST", "http://ollama:11434")
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1},
    }
    if system:
        payload["system"] = system
    with httpx.Client(timeout=120) as client:
        resp = client.post(f"{host}/api/generate", json=payload)
        resp.raise_for_status()
        return resp.json().get("response", "")


def run_trading_agents(
    *,
    market: str,
    symbol: str,
    indicators: dict[str, Any],
    news_summary: str = "",
) -> dict[str, Any]:
    """
    Multi-agent pipeline: Analyst → Risk Manager → Validator (existing validate_signal).
    """
    cfg = _cfg()
    model = cfg.get("ollama_model", "qwen3.5:9b")

    analyst_prompt = cfg.get("analyst_prompt", "").format(
        symbol=symbol, indicators=json.dumps(indicators, ensure_ascii=False), news=news_summary[:1500]
    )
    analyst_out = _ollama_generate(model, analyst_prompt, system=cfg.get("analyst_system", ""))

    risk_prompt = cfg.get("risk_prompt", "").format(
        symbol=symbol, analyst_report=analyst_out[:2000], indicators=json.dumps(indicators, ensure_ascii=False)
    )
    risk_out = _ollama_generate(model, risk_prompt, system=cfg.get("risk_system", ""))

    risk_reject = any(
        phrase in risk_out.lower()
        for phrase in cfg.get("risk_reject_phrases", ["reject", "do not trade", "high risk", "отклон"])
    )
    if risk_reject:
        return {
            "status": "rejected",
            "stage": "risk_agent",
            "analyst": analyst_out[:500],
            "risk": risk_out[:500],
            "reference": "https://arxiv.org/abs/2412.20138",
        }

    validation = validate_signal(
        market=market,
        symbol=symbol,
        indicators={**indicators, "agent_analyst": analyst_out[:800], "agent_risk": risk_out[:800]},
        prompt_version=cfg.get("validator_prompt_version", "crypto_validate_v1"),
        news_summary=news_summary,
    )

    return {
        "status": "approved" if validation.get("action") == "approve" else "rejected",
        "stage": "validator",
        "analyst": analyst_out[:500],
        "risk": risk_out[:500],
        "validation": validation,
        "reference": "https://arxiv.org/abs/2412.20138",
    }
