"""Ollama LLM client."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from config_loader import load_config, load_prompt_body


def ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def validate_signal(
    *,
    market: str,
    symbol: str,
    indicators: dict[str, Any],
    prompt_version: str,
    model: str | None = None,
    news_summary: str = "",
    timeframe: str = "4h",
) -> dict[str, Any]:
    crypto_cfg = load_config("crypto_config") if market == "crypto" else load_config("securities_config")
    guardrails = load_config("guardrails")
    model = model or crypto_cfg.get("ollama_model", "qwen3.5:9b")
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

    timeout = guardrails.get("llm", {}).get("timeout_ms", 900000) / 1000
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": guardrails.get("llm", {}).get("temperature", 0.1),
            "num_predict": guardrails.get("llm", {}).get("max_tokens", 2048),
        },
    }

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
        return {**parsed, "latency_ms": latency_ms, "model": model, "raw": content}
    except httpx.TimeoutException:
        return {
            "action": "reject",
            "confidence": 0,
            "reject_reason": "ollama_timeout",
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "model": model,
        }
