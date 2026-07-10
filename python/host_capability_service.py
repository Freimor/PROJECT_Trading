"""Host capability audit — Ollama throughput vs strategy requirements."""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

import httpx
import psutil

from config_loader import load_config
from db.connection import get_connection
from llm_client import list_ollama_models, ollama_host, validate_signal


def _cfg() -> dict[str, Any]:
    return load_config("host_capability")


def _sample_llm_latency(model: str, *, runs: int = 2) -> dict[str, Any]:
    """Measure validate_signal latency (real pipeline path)."""
    cfg = _cfg()
    bench_timeout = int(cfg.get("benchmark_llm_timeout_ms", 180_000))
    bench_tokens = int(cfg.get("benchmark_max_tokens", 768))
    latencies: list[int] = []
    errors: list[str] = []
    dummy_indicators = {
        "close": 65000.0,
        "rsi_14": 42.0,
        "ema50": 64000.0,
        "ema200": 62000.0,
        "trend": "up",
        "macd": 120.0,
        "macd_signal": 100.0,
        "macd_histogram": 20.0,
        "proceed": True,
        "rule_name": "rsi_oversold",
    }
    for _ in range(runs):
        start = time.perf_counter()
        try:
            from runtime_settings import set_runtime_value

            set_runtime_value("ollama_model_override", model)
            result = validate_signal(
                market="crypto",
                symbol="BTCUSDT",
                indicators=dummy_indicators,
                prompt_version="crypto_validate_v1",
                news_summary="Benchmark host capability probe.",
                timeframe="4h",
                model=model,
                timeout_ms=bench_timeout,
                max_tokens=bench_tokens,
            )
            ms = int((time.perf_counter() - start) * 1000)
            latencies.append(ms)
            if result.get("action") == "error":
                errors.append(str(result.get("raw", "llm_error"))[:200])
        except Exception as exc:
            errors.append(str(exc)[:200])
        finally:
            try:
                from runtime_settings import set_runtime_value

                set_runtime_value("ollama_model_override", None)
            except Exception:
                pass
    if not latencies:
        return {"model": model, "status": "error", "errors": errors}
    avg = sum(latencies) / len(latencies)
    return {
        "model": model,
        "status": "ok",
        "latency_ms_avg": int(avg),
        "latency_ms_max": max(latencies),
        "samples": len(latencies),
        "errors": errors,
    }


def _evaluate_strategy(
    strategy: dict[str, Any],
    *,
    avg_latency_ms: float,
    parallel_symbols: int,
) -> dict[str, Any]:
    interval_sec = float(strategy.get("interval_sec", 3600))
    llm_per_symbol = float(strategy.get("llm_calls_per_symbol", 1))
    symbols = int(strategy.get("symbols", 1))
    total_llm = llm_per_symbol * symbols
    budget_sec = interval_sec / max(parallel_symbols, 1)
    required_ms = total_llm * avg_latency_ms
    feasible = required_ms <= budget_sec * 1000 * float(strategy.get("safety_margin", 0.85))
    headroom = (budget_sec * 1000 - required_ms) / 1000 if budget_sec else 0
    return {
        "id": strategy.get("id"),
        "label": strategy.get("label"),
        "interval_sec": interval_sec,
        "symbols": symbols,
        "llm_calls_per_tick": total_llm,
        "budget_sec": round(budget_sec, 1),
        "required_sec": round(required_ms / 1000, 1),
        "feasible": feasible,
        "headroom_sec": round(headroom, 1),
        "note": strategy.get("note"),
    }


def run_host_capability_audit(
    *,
    models: list[str] | None = None,
    llm_samples: int = 2,
) -> dict[str, Any]:
    """Full host audit: CPU/RAM + Ollama latency + strategy feasibility matrix."""
    cfg = _cfg()
    cpu_count = psutil.cpu_count(logical=True) or 1
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    ollama_status = list_ollama_models()
    available = models or cfg.get("models") or [
        m["name"] for m in (ollama_status.get("models") or []) if m.get("name")
    ]
    if not available:
        crypto = load_config("crypto_config")
        available = [crypto.get("ollama_model", "qwen3.5:9b")]

    model_results: list[dict[str, Any]] = []
    for model in available[: int(cfg.get("max_models", 5))]:
        model_results.append(_sample_llm_latency(model, runs=llm_samples))

    strategies = cfg.get("strategies", [])
    feasibility: list[dict[str, Any]] = []
    for mr in model_results:
        if mr.get("status") != "ok":
            feasibility.append({"model": mr.get("model"), "strategies": [], "error": mr.get("errors")})
            continue
        avg_ms = float(mr["latency_ms_avg"])
        parallel = max(1, min(cpu_count // 2, int(cfg.get("max_parallel_llm", 1))))
        evaluated = [_evaluate_strategy(s, avg_latency_ms=avg_ms, parallel_symbols=parallel) for s in strategies]
        feasibility.append({
            "model": mr["model"],
            "latency_ms_avg": mr["latency_ms_avg"],
            "parallel_assumed": parallel,
            "strategies": evaluated,
        })

    report = {
        "status": "ok",
        "host": {
            "cpu_logical": cpu_count,
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "ram_available_gb": round(mem.available / (1024**3), 2),
            "ram_used_pct": mem.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
        },
        "ollama": {
            "host": ollama_host(),
            "status": ollama_status.get("status"),
            "models_count": len(ollama_status.get("models") or []),
        },
        "model_benchmarks": model_results,
        "feasibility": feasibility,
        "reference": "https://arxiv.org/abs/2505.07078",
    }
    _persist_audit(report)
    return report


def _persist_audit(report: dict[str, Any]) -> str:
    run_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO host_capability_audits (id, audited_at, report_json)
            VALUES (?, datetime('now'), ?)
            """,
            (run_id, json.dumps(report, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()
    report["audit_id"] = run_id
    return run_id


def get_last_host_audit() -> dict[str, Any] | None:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, audited_at, report_json FROM host_capability_audits
            ORDER BY audited_at DESC LIMIT 1
            """
        ).fetchone()
        if not row:
            return None
        out = dict(row)
        out["report"] = json.loads(out.pop("report_json", "{}") or "{}")
        return out
    finally:
        conn.close()
