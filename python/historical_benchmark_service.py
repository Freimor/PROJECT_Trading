"""Historical LLM benchmark — real old candles + news at decision time."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import yaml

from config_loader import load_config, wiki_root
from db.connection import get_connection
from db.migrate import run_migrations
from indicators.technical import compute_indicators, rule_filter
from llm_client import reset_ollama_cache, validate_signal
from market_data import candles_for_benchmark
from news_service import news_context_as_of
from runtime_settings import get_runtime_value, set_runtime_value

HISTORICAL_SNAPSHOT_KEY = "benchmark_last_historical_snapshot"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _benchmark_cfg() -> dict[str, Any]:
    try:
        return load_config("benchmark_config")
    except FileNotFoundError:
        return {}


def _load_fixture_file(rel_path: str) -> dict[str, Any]:
    path = wiki_root() / rel_path
    if not path.exists():
        return {"cases": []}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _historical_files(market: str | None = None) -> list[tuple[str, str]]:
    cfg = _benchmark_cfg()
    hist = cfg.get("historical", {})
    files: list[tuple[str, str]] = []
    if market in (None, "crypto"):
        rel = hist.get("crypto_file", "benchmark/historical/crypto_historical_v1.yaml")
        files.append(("crypto", rel))
    if market in (None, "securities"):
        rel = hist.get("securities_file", "benchmark/historical/moex_historical_v1.yaml")
        files.append(("securities", rel))
    return files


def list_historical_cases(*, market: str | None = None) -> list[dict[str, Any]]:
    crypto_cfg = load_config("crypto_config")
    sec_cfg = load_config("securities_config")
    out: list[dict[str, Any]] = []
    for mkt, rel in _historical_files(market):
        data = _load_fixture_file(rel)
        pv = data.get("prompt_version") or (
            crypto_cfg.get("prompt_version")
            if mkt == "crypto"
            else sec_cfg.get("swing_signals", {}).get("prompt_version", "securities_validate_v1")
        )
        for case in data.get("cases") or []:
            out.append(
                {
                    "id": case.get("id"),
                    "market": mkt,
                    "symbol": case.get("symbol"),
                    "timeframe": case.get("timeframe"),
                    "as_of": case.get("as_of"),
                    "expected_action": case.get("expected_action"),
                    "summary": case.get("summary") or "",
                    "label_source": case.get("label_source", "expert"),
                    "prompt_version": pv,
                    "tier": "historical",
                }
            )
    return out


def _resolve_news(case: dict[str, Any], *, as_of: str, symbol: str) -> tuple[str, str]:
    """Return (news_text, news_source) where source is db|snapshot|none."""
    snap = (case.get("news_snapshot") or "").strip()
    db_news = news_context_as_of([symbol], as_of=as_of, limit=5)
    if db_news and db_news != "none":
        return db_news, "db"
    if snap:
        return snap, "snapshot"
    return "none", "none"


def run_one_historical_case(
    *,
    case_id: str,
    market: str,
    model: str | None = None,
    temperature: float | None = None,
) -> dict[str, Any]:
    crypto_cfg = load_config("crypto_config")
    sec_cfg = load_config("securities_config")
    default_model = model or crypto_cfg.get("ollama_model", "qwen3.5:9b")

    for mkt, rel in _historical_files(market):
        if mkt != market:
            continue
        data = _load_fixture_file(rel)
        pv = data.get("prompt_version") or (
            crypto_cfg.get("prompt_version")
            if mkt == "crypto"
            else sec_cfg.get("swing_signals", {}).get("prompt_version", "securities_validate_v1")
        )
        for case in data.get("cases") or []:
            if case.get("id") != case_id:
                continue
            as_of = case.get("as_of")
            if not as_of:
                return {"status": "error", "message": "missing_as_of", "id": case_id}
            symbol = case.get("symbol", "BTCUSDT")
            timeframe = case.get("timeframe") or ("4h" if mkt == "crypto" else "1d")

            candles = candles_for_benchmark(
                market=mkt,
                symbol=symbol,
                timeframe=timeframe,
                as_of=as_of,
            )
            if len(candles) < 30:
                return {
                    "status": "error",
                    "message": "insufficient_candles",
                    "id": case_id,
                    "candles": len(candles),
                }

            indicators = compute_indicators(candles)
            cfg = crypto_cfg if mkt == "crypto" else sec_cfg
            filtered = rule_filter(indicators, cfg)
            news_text, news_source = _resolve_news(case, as_of=as_of, symbol=symbol)

            result = validate_signal(
                market=mkt,
                symbol=symbol,
                indicators=filtered,
                prompt_version=pv,
                model=model or default_model,
                news_summary=news_text,
                timeframe=timeframe,
                temperature=temperature,
            )
            expected = case.get("expected_action", "reject")
            actual = result.get("action")
            return {
                "status": "ok",
                "tier": "historical",
                "id": case_id,
                "market": mkt,
                "symbol": symbol,
                "as_of": as_of,
                "summary": case.get("summary") or "",
                "label_source": case.get("label_source", "expert"),
                "expected": expected,
                "actual": actual,
                "pass": actual == expected,
                "confidence": result.get("confidence"),
                "counter_thesis": result.get("counter_thesis"),
                "latency_ms": result.get("latency_ms"),
                "news_source": news_source,
                "indicators_preview": {
                    "close": filtered.get("close"),
                    "rsi_14": filtered.get("rsi_14"),
                    "trend": filtered.get("trend"),
                },
            }
    return {"status": "error", "message": "historical_case_not_found", "id": case_id}


def run_historical_benchmark(
    *,
    model: str | None = None,
    market: str | None = None,
) -> dict[str, Any]:
    cases = list_historical_cases(market=market)
    details: list[dict[str, Any]] = []
    for case in cases:
        one = run_one_historical_case(
            case_id=case["id"],
            market=case["market"],
            model=model,
        )
        if one.get("status") == "ok":
            details.append(one)
        else:
            details.append(
                {
                    **one,
                    "market": case.get("market"),
                    "symbol": case.get("symbol"),
                    "pass": False,
                }
            )
    passed = sum(1 for d in details if d.get("pass"))
    total = len(details)
    payload = {
        "status": "ok",
        "tier": "historical",
        "model": model or load_config("crypto_config").get("ollama_model", "qwen3.5:9b"),
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if total else 0,
        "details": details,
    }
    set_runtime_value(
        HISTORICAL_SNAPSHOT_KEY,
        {**payload, "saved_at": _utc_now()},
        updated_by="api",
    )
    guardrails = load_config("guardrails")
    if guardrails.get("llm", {}).get("benchmark_unload_after", True):
        payload["ollama_unload"] = reset_ollama_cache(model)
    return payload


def save_historical_snapshot(payload: dict[str, Any], *, operator: str = "api") -> dict[str, Any]:
    data = {**payload, "saved_at": _utc_now()}
    set_runtime_value(HISTORICAL_SNAPSHOT_KEY, data, updated_by=operator)
    return data


def get_historical_snapshot() -> dict[str, Any] | None:
    val = get_runtime_value(HISTORICAL_SNAPSHOT_KEY)
    return val if isinstance(val, dict) else None


def promote_live_case_to_historical(
    inputs_hash: str,
    *,
    expected_action: str,
    summary: str,
    operator: str = "api",
) -> dict[str, Any]:
    """Create a historical fixture candidate from a labeled benchmark_cases row."""
    run_migrations()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM benchmark_cases WHERE inputs_hash = ?",
            (inputs_hash,),
        ).fetchone()
        if not row:
            return {"status": "error", "message": "case_not_found"}
        label = conn.execute(
            "SELECT label, forward_return_pct FROM benchmark_labels WHERE inputs_hash = ?",
            (inputs_hash,),
        ).fetchone()
        return {
            "status": "ok",
            "fixture_draft": {
                "id": f"live_{inputs_hash[:8]}",
                "market": row["market"],
                "symbol": row["symbol"],
                "as_of": row["decision_at"],
                "timeframe": "4h" if row["market"] == "crypto" else "1d",
                "expected_action": expected_action,
                "label_source": "outcome" if label else "expert",
                "summary": summary,
                "outcome_label": label["label"] if label else None,
                "forward_return_pct": label["forward_return_pct"] if label else None,
            },
            "operator": operator,
            "note": "Add fixture_draft to benchmark/historical/*.yaml after review",
        }
    finally:
        conn.close()
