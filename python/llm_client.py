"""Ollama LLM client."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from config_loader import load_config, load_prompt_body
from market_llm_config import get_market_llm_config, get_market_ollama_model
from runtime_settings import get_runtime_value


def _resolved_model(market: str, model: str | None) -> str:
    override = get_runtime_value("ollama_model_override")
    if isinstance(override, str) and override.strip():
        return override.strip()
    return model or get_market_ollama_model(market)


def ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def list_ollama_models() -> dict[str, Any]:
    """All models available in local Ollama (/api/tags)."""
    start = time.perf_counter()
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{ollama_host()}/api/tags")
        latency_ms = int((time.perf_counter() - start) * 1000)
        if resp.status_code != 200:
            return {
                "status": "error",
                "latency_ms": latency_ms,
                "models": [],
                "message": resp.text[:200],
            }
        models = []
        for item in resp.json().get("models", []):
            name = item.get("name")
            if not name:
                continue
            models.append(
                {
                    "name": name,
                    "size": item.get("size"),
                    "modified_at": item.get("modified_at"),
                    "digest": item.get("digest"),
                }
            )
        models.sort(key=lambda m: m["name"])
        return {"status": "ok", "latency_ms": latency_ms, "models": models}
    except httpx.HTTPError as exc:
        return {
            "status": "error",
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "models": [],
            "message": str(exc),
        }


def reset_ollama_cache(model: str | None = None) -> dict[str, Any]:
    """Unload model from Ollama RAM after benchmark (keep_alive=0)."""
    crypto_cfg = load_config("crypto_config")
    model = model or crypto_cfg.get("ollama_model", "qwen3.5:9b")
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{ollama_host()}/api/generate",
                json={"model": model, "prompt": " ", "keep_alive": 0},
            )
        ok = resp.status_code == 200
        return {
            "status": "ok" if ok else "error",
            "model": model,
            "http_status": resp.status_code,
            "action": "unload",
        }
    except Exception as exc:
        return {"status": "error", "model": model, "message": str(exc), "action": "unload"}


def _qwen35_disable_thinking(model: str) -> bool:
    """Qwen 3.5 thinking mode adds latency and can break JSON format."""
    name = model.lower().replace("_", ".")
    return "qwen3.5" in name or "qwen35" in name


def validate_signal(
    *,
    market: str,
    symbol: str,
    indicators: dict[str, Any],
    prompt_version: str,
    model: str | None = None,
    news_summary: str = "",
    timeframe: str = "4h",
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout_ms: int | None = None,
) -> dict[str, Any]:
    llm_cfg = get_market_llm_config(market)
    model = _resolved_model(market, model)
    prompt_file = f"{prompt_version}.md" if not prompt_version.endswith(".md") else prompt_version
    system_raw = load_prompt_body(prompt_file)

    # Strip YAML frontmatter if present
    if system_raw.startswith("---"):
        parts = system_raw.split("---", 2)
        system_prompt = parts[2].strip() if len(parts) >= 3 else system_raw
    else:
        system_prompt = system_raw

    candles_summary = (
        f"close={indicators.get('close')}, rsi={indicators.get('rsi_14')}, "
        f"trend={indicators.get('trend')}, macd_hist={indicators.get('macd_histogram')}"
    )
    user_content = (
        f"Symbol: {symbol}\nTimeframe: {timeframe}\n"
        f"Indicators: {json.dumps(indicators, ensure_ascii=False)}\n"
        f"Summary: {candles_summary}\n"
        f"News: {news_summary or 'none'}"
    )
    if market == "securities":
        session = indicators.get("session_status")
        if session:
            user_content += f"\nSession status: {session}"

    llm_cfg = get_market_llm_config(market)
    if timeout_ms is not None:
        timeout = timeout_ms / 1000
    else:
        timeout = llm_cfg.get("timeout_ms", 900000) / 1000
    temp = temperature if temperature is not None else llm_cfg.get("temperature", 0.1)
    num_predict = max_tokens if max_tokens is not None else llm_cfg.get("max_tokens", 2048)
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": temp,
            "num_predict": num_predict,
        },
    }
    if _qwen35_disable_thinking(model):
        payload["think"] = False

    start = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{ollama_host()}/api/chat", json=payload)
        latency_ms = int((time.perf_counter() - start) * 1000)
        if resp.status_code != 200:
            return {
                "action": "reject",
                "confidence": 0,
                "reject_reason": "ollama_http_error",
                "raw": resp.text,
                "latency_ms": latency_ms,
                "model": model,
            }
        content = resp.json().get("message", {}).get("content", "{}")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return {
                "action": "reject",
                "confidence": 0,
                "reject_reason": "invalid_json",
                "raw": content,
                "latency_ms": latency_ms,
                "model": model,
            }
        if parsed.get("action") not in ("approve", "reject"):
            parsed["action"] = "reject"
            parsed["reject_reason"] = "invalid_action"
        if parsed.get("action") == "reject" and not parsed.get("reject_reason"):
            parsed["reject_reason"] = parsed.get("reasoning") or "llm_rejected_no_reason"
        return {**parsed, "latency_ms": latency_ms, "model": model, "raw": content}
    except httpx.TimeoutException:
        return {
            "action": "reject",
            "confidence": 0,
            "reject_reason": "ollama_timeout",
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "model": model,
        }
