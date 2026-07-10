"""Quick probe for universe LLM suggest latency."""
import json
import time

import httpx

from config_loader import load_prompt_body
from llm_client import ollama_host
from market_llm_config import get_market_ollama_model

model = get_market_ollama_model("crypto")
system_raw = load_prompt_body("universe_suggest_v1.md")
if system_raw.startswith("---"):
    parts = system_raw.split("---", 2)
    system_prompt = parts[2].strip() if len(parts) >= 3 else system_raw
else:
    system_prompt = system_raw

for num_predict in (256, 4096):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Market: crypto\nMax symbols: 5\nOperator hint: liquid altcoins\n"},
        ],
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": num_predict},
    }
    t0 = time.perf_counter()
    try:
        with httpx.Client(timeout=120) as client:
            resp = client.post(f"{ollama_host()}/api/chat", json=payload)
        elapsed = time.perf_counter() - t0
        print(f"num_predict={num_predict} status={resp.status_code} elapsed={elapsed:.1f}s")
        print(resp.text[:300])
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        print(f"num_predict={num_predict} error={exc} elapsed={elapsed:.1f}s")
