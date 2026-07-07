"""Offline LLM hyperparameter calibration — grid over temperature × min_confidence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from benchmark_service import (
    _maybe_unload_ollama_after_benchmark,
    list_golden_cases,
    run_one_golden_case,
)
from config_loader import load_config
from db.connection import get_connection
from db.migrate import run_migrations
from historical_benchmark_service import list_historical_cases, run_one_historical_case
from runtime_settings import get_runtime_value, set_runtime_value

CALIBRATION_SNAPSHOT_KEY = "benchmark_last_calibration"
CALIBRATION_PARTIAL_KEY = "benchmark_calibration_partial"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _benchmark_cfg() -> dict[str, Any]:
    try:
        return load_config("benchmark_config")
    except FileNotFoundError:
        return {}


def _calibration_cfg() -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "temperatures": [0.0, 0.05, 0.1, 0.15],
        "min_confidence": [0.60, 0.65, 0.70, 0.75, 0.80],
        "synthetic_holdout_ratio": 0.3,
        "outcome_days": 30,
        "min_outcome_cases": 5,
        "weights": {
            "historical": 0.40,
            "synthetic_train": 0.20,
            "synthetic_holdout": 0.15,
            "outcome_precision": 0.25,
        },
        "recall_floor": 0.0,
    }
    cfg = _benchmark_cfg().get("calibration") or {}
    return {**defaults, **cfg, "weights": {**defaults["weights"], **(cfg.get("weights") or {})}}


def effective_llm_action(
    llm: dict[str, Any],
    *,
    min_confidence: float,
    require_counter_thesis: bool | None = None,
    counter_thesis_min_chars: int | None = None,
) -> str:
    """Apply production-like confidence gate to raw LLM output."""
    guardrails = load_config("guardrails")
    llm_cfg = guardrails.get("llm", {})
    if require_counter_thesis is None:
        require_counter_thesis = bool(llm_cfg.get("require_counter_thesis", True))
    if counter_thesis_min_chars is None:
        counter_thesis_min_chars = int(llm_cfg.get("counter_thesis_min_chars", 10))

    action = llm.get("action", "reject")
    if action != "approve":
        return "reject"
    conf = llm.get("confidence")
    if conf is None or float(conf) < min_confidence:
        return "reject"
    if require_counter_thesis:
        ct = llm.get("counter_thesis") or ""
        if len(ct) < counter_thesis_min_chars:
            return "reject"
    return "approve"


def _split_holdout(cases: list[dict[str, Any]], holdout_ratio: float) -> tuple[list[str], list[str]]:
    if not cases or holdout_ratio <= 0:
        return [c["id"] for c in cases], []
    ordered = sorted(cases, key=lambda c: c.get("id", ""))
    n_holdout = max(1, int(len(ordered) * holdout_ratio))
    holdout_ids = {c["id"] for c in ordered[-n_holdout:]}
    train = [c["id"] for c in ordered if c["id"] not in holdout_ids]
    holdout = [c["id"] for c in ordered if c["id"] in holdout_ids]
    return train, holdout


def outcome_metrics_at_confidence(*, min_confidence: float, days: int = 30) -> dict[str, Any]:
    """Precision/recall on labeled benchmark_cases at a confidence threshold (no LLM)."""
    run_migrations()
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT c.original_action, c.confidence, l.label
            FROM benchmark_cases c
            INNER JOIN benchmark_labels l ON l.inputs_hash = c.inputs_hash
            WHERE c.decision_at >= datetime('now', ?)
              AND l.label NOT IN ('pending', 'neutral')
            """,
            (f"-{days} days",),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {"count": 0, "precision_approve": None, "recall": None, "approve_count": 0}

    good_app = bad_app = missed = good_rej = 0
    effective_approves = 0
    for row in rows:
        label = row["label"]
        conf = row["confidence"]
        orig = row["original_action"] or "reject"
        llm_stub = {"action": orig, "confidence": conf, "counter_thesis": "x" * 12}
        effective = effective_llm_action(llm_stub, min_confidence=min_confidence)

        if effective == "approve":
            effective_approves += 1
            if label == "good":
                good_app += 1
            elif label == "bad":
                bad_app += 1
        else:
            if label == "missed_opportunity":
                missed += 1
            elif label == "good_reject":
                good_rej += 1

    labeled_approves = good_app + bad_app
    precision = round(good_app / labeled_approves, 4) if labeled_approves else None
    opportunities = good_app + missed
    recall = round(good_app / opportunities, 4) if opportunities else None

    return {
        "count": len(rows),
        "precision_approve": precision,
        "recall": recall,
        "approve_count": effective_approves,
        "good_approves": good_app,
        "bad_approves": bad_app,
        "missed_opportunities": missed,
    }


def _pass_rate(
    runs: list[dict[str, Any]],
    *,
    min_confidence: float,
    case_ids: set[str] | None = None,
) -> float | None:
    if not runs:
        return None
    passed = total = 0
    for run in runs:
        if case_ids is not None and run.get("id") not in case_ids:
            continue
        llm = run.get("llm") or {}
        expected = run.get("expected", "reject")
        actual = effective_llm_action(llm, min_confidence=min_confidence)
        if actual == expected:
            passed += 1
        total += 1
    return round(passed / total, 4) if total else None


def _run_fixtures_at_temperature(
    *,
    temperature: float,
    model: str | None,
    synthetic: list[dict[str, Any]],
    historical: list[dict[str, Any]],
    on_case_done: Callable[[str, int, int], None] | None = None,
) -> list[dict[str, Any]]:
    all_cases = [(c, "synthetic") for c in synthetic] + [(c, "historical") for c in historical]
    total = len(all_cases)
    runs: list[dict[str, Any]] = []

    for i, (case, tier) in enumerate(all_cases, 1):
        cid = case["id"]
        mkt = case["market"]
        if on_case_done:
            on_case_done(cid, i, total)
        if tier == "synthetic":
            result = run_one_golden_case(
                case_id=cid,
                market=mkt,
                model=model,
                temperature=temperature,
            )
        else:
            result = run_one_historical_case(
                case_id=cid,
                market=mkt,
                model=model,
                temperature=temperature,
            )
        if result.get("status") != "ok":
            runs.append(
                {
                    "id": cid,
                    "tier": tier,
                    "market": mkt,
                    "expected": case.get("expected_action", "reject"),
                    "llm": {"action": "reject", "confidence": 0},
                    "error": result.get("message"),
                }
            )
            continue
        runs.append(
            {
                "id": cid,
                "tier": tier,
                "market": mkt,
                "expected": result.get("expected", "reject"),
                "llm": {
                    "action": result.get("actual"),
                    "confidence": result.get("confidence"),
                    "counter_thesis": result.get("counter_thesis"),
                },
                "latency_ms": result.get("latency_ms"),
            }
        )
    return runs


def _composite_score(
    *,
    historical_pass: float | None,
    syn_train_pass: float | None,
    syn_holdout_pass: float | None,
    outcome_precision: float | None,
    weights: dict[str, float],
) -> float | None:
    parts: list[tuple[float, float]] = []
    if historical_pass is not None:
        parts.append((weights.get("historical", 0.4), historical_pass))
    if syn_train_pass is not None:
        parts.append((weights.get("synthetic_train", 0.2), syn_train_pass))
    if syn_holdout_pass is not None:
        parts.append((weights.get("synthetic_holdout", 0.15), syn_holdout_pass))
    if outcome_precision is not None:
        parts.append((weights.get("outcome_precision", 0.25), outcome_precision))
    if not parts:
        return None
    w_sum = sum(w for w, _ in parts)
    if w_sum <= 0:
        return None
    return round(sum(w * v for w, v in parts) / w_sum, 4)


def get_calibration_plan(*, market: str | None = None) -> dict[str, Any]:
    cfg = _calibration_cfg()
    synthetic = list_golden_cases(market=market)
    historical = list_historical_cases(market=market)
    temps = list(cfg["temperatures"])
    confs = [float(x) for x in cfg["min_confidence"]]
    return {
        "status": "ok",
        "temperatures": temps,
        "min_confidence": confs,
        "grid_cells": len(temps) * len(confs),
        "llm_calls": len(temps) * (len(synthetic) + len(historical)),
        "fixtures": {"synthetic": len(synthetic), "historical": len(historical)},
    }


def run_calibration_temperature(
    *,
    temperature: float,
    model: str | None = None,
    market: str | None = None,
) -> dict[str, Any]:
    """Run LLM for all fixtures at one temperature; store partial results."""
    crypto_cfg = load_config("crypto_config")
    model = model or crypto_cfg.get("ollama_model", "qwen3.5:9b")
    synthetic = list_golden_cases(market=market)
    historical = list_historical_cases(market=market)
    runs = _run_fixtures_at_temperature(
        temperature=temperature,
        model=model,
        synthetic=synthetic,
        historical=historical,
    )
    partial = get_runtime_value(CALIBRATION_PARTIAL_KEY) or {"model": model, "by_temp": {}}
    if not isinstance(partial.get("by_temp"), dict):
        partial["by_temp"] = {}
    partial["model"] = model
    partial["by_temp"][str(temperature)] = runs
    partial["updated_at"] = _utc_now()
    set_runtime_value(CALIBRATION_PARTIAL_KEY, partial, updated_by="api")
    return {
        "status": "ok",
        "temperature": temperature,
        "cases_run": len(runs),
        "temperatures_done": list(partial["by_temp"].keys()),
    }


def _score_grid_from_raw(
    raw_by_temp: dict[str, list[dict[str, Any]]],
    *,
    model: str,
    temps: list[float],
    confs: list[float],
    synthetic: list[dict[str, Any]],
    market: str | None = None,
) -> dict[str, Any]:
    cfg = _calibration_cfg()
    weights = cfg["weights"]
    holdout_ratio = float(cfg.get("synthetic_holdout_ratio", 0.3))
    outcome_days = int(cfg.get("outcome_days", 30))
    min_outcome = int(cfg.get("min_outcome_cases", 5))
    recall_floor = float(cfg.get("recall_floor", 0.0))

    syn_train_ids, syn_holdout_ids = _split_holdout(synthetic, holdout_ratio)
    train_set = set(syn_train_ids)
    holdout_set = set(syn_holdout_ids)
    historical = list_historical_cases(market=market)
    hist_set = {c["id"] for c in historical}
    latencies: dict[str, list[int]] = {}

    grid: list[dict[str, Any]] = []
    heatmap_scores: list[list[float | None]] = []

    for temp in temps:
        key = str(temp)
        runs = raw_by_temp.get(key, [])
        latencies[key] = [int(r["latency_ms"]) for r in runs if r.get("latency_ms")]
        row_scores: list[float | None] = []
        for conf in confs:
            hist_pass = _pass_rate(runs, min_confidence=conf, case_ids=hist_set)
            train_pass = _pass_rate(runs, min_confidence=conf, case_ids=train_set) if train_set else None
            holdout_pass = (
                _pass_rate(runs, min_confidence=conf, case_ids=holdout_set) if holdout_set else None
            )
            outcome = outcome_metrics_at_confidence(min_confidence=conf, days=outcome_days)
            outcome_prec = outcome.get("precision_approve")
            if outcome.get("count", 0) < min_outcome:
                outcome_prec = None
            score = _composite_score(
                historical_pass=hist_pass,
                syn_train_pass=train_pass,
                syn_holdout_pass=holdout_pass,
                outcome_precision=outcome_prec,
                weights=weights,
            )
            lats = latencies.get(key, [])
            avg_lat = int(sum(lats) / len(lats)) if lats else None
            cell = {
                "temperature": temp,
                "min_confidence": conf,
                "historical_pass": hist_pass,
                "synthetic_train_pass": train_pass,
                "synthetic_holdout_pass": holdout_pass,
                "outcome_precision": outcome_prec,
                "outcome_recall": outcome.get("recall"),
                "outcome_labeled_count": outcome.get("count", 0),
                "composite_score": score,
                "avg_latency_ms": avg_lat,
            }
            grid.append(cell)
            row_scores.append(score)
        heatmap_scores.append(row_scores)

    eligible = [
        g
        for g in grid
        if g.get("composite_score") is not None
        and (g.get("outcome_recall") is None or g.get("outcome_recall", 0) >= recall_floor)
    ]
    eligible.sort(key=lambda g: (-(g.get("composite_score") or 0), -(g.get("historical_pass") or 0)))
    recommended = eligible[0] if eligible else (grid[0] if grid else None)
    current_gr = load_config("guardrails").get("llm", {})

    return {
        "status": "ok",
        "model": model,
        "grid_size": {"temperatures": len(temps), "min_confidence": len(confs), "cells": len(grid)},
        "fixtures": {
            "synthetic_total": len(synthetic),
            "synthetic_train": len(train_set),
            "synthetic_holdout": len(holdout_set),
            "historical": len(historical),
        },
        "current_guardrails": {
            "temperature": current_gr.get("temperature"),
            "min_confidence": current_gr.get("min_confidence"),
        },
        "grid": grid,
        "heatmap": {
            "temperatures": temps,
            "min_confidence": confs,
            "composite_scores": heatmap_scores,
        },
        "recommended": recommended,
        "recommendation_note": (
            "Примените вручную в trading_wiki/config/guardrails.yaml — auto-apply отключён."
            if recommended
            else "Недостаточно данных для рекомендации."
        ),
        "weights": weights,
    }


def finalize_calibration(
    *,
    model: str | None = None,
    market: str | None = None,
) -> dict[str, Any]:
    """Score grid from partial temperature runs."""
    cfg = _calibration_cfg()
    partial = get_runtime_value(CALIBRATION_PARTIAL_KEY) or {}
    raw_by_temp = partial.get("by_temp") if isinstance(partial.get("by_temp"), dict) else {}
    if not raw_by_temp:
        return {"status": "error", "message": "no_partial_calibration_data"}

    crypto_cfg = load_config("crypto_config")
    model = model or partial.get("model") or crypto_cfg.get("ollama_model", "qwen3.5:9b")
    temps = [float(t) for t in raw_by_temp.keys()]
    temps.sort()
    confs = [float(x) for x in cfg["min_confidence"]]
    synthetic = list_golden_cases(market=market)

    payload = _score_grid_from_raw(
        raw_by_temp,
        model=model,
        temps=temps,
        confs=confs,
        synthetic=synthetic,
        market=market,
    )
    set_runtime_value(CALIBRATION_SNAPSHOT_KEY, {**payload, "saved_at": _utc_now()}, updated_by="api")
    set_runtime_value(CALIBRATION_PARTIAL_KEY, {}, updated_by="api")
    unload = _maybe_unload_ollama_after_benchmark(model)
    if unload:
        payload["ollama_unload"] = unload
    return payload


def run_calibration(
    *,
    model: str | None = None,
    temperatures: list[float] | None = None,
    min_confidence_values: list[float] | None = None,
    market: str | None = None,
    on_temperature_start: Callable[[float, int, int], None] | None = None,
    on_case_done: Callable[[float, str, int, int], None] | None = None,
) -> dict[str, Any]:
    """Grid search: LLM re-run per temperature; confidence scored without extra LLM calls."""
    cfg = _calibration_cfg()
    crypto_cfg = load_config("crypto_config")
    model = model or crypto_cfg.get("ollama_model", "qwen3.5:9b")
    temps = temperatures if temperatures is not None else list(cfg["temperatures"])
    confs = (
        min_confidence_values
        if min_confidence_values is not None
        else [float(x) for x in cfg["min_confidence"]]
    )

    synthetic = list_golden_cases(market=market)
    historical = list_historical_cases(market=market)

    raw_by_temp: dict[str, list[dict[str, Any]]] = {}

    for ti, temp in enumerate(temps, 1):
        if on_temperature_start:
            on_temperature_start(temp, ti, len(temps))

        def _case_cb(cid: str, i: int, total: int, t: float = temp) -> None:
            if on_case_done:
                on_case_done(t, cid, i, total)

        runs = _run_fixtures_at_temperature(
            temperature=temp,
            model=model,
            synthetic=synthetic,
            historical=historical,
            on_case_done=_case_cb,
        )
        raw_by_temp[str(temp)] = runs

    payload = _score_grid_from_raw(
        raw_by_temp,
        model=model,
        temps=temps,
        confs=confs,
        synthetic=synthetic,
        market=market,
    )
    set_runtime_value(CALIBRATION_SNAPSHOT_KEY, {**payload, "saved_at": _utc_now()}, updated_by="api")
    unload = _maybe_unload_ollama_after_benchmark(model)
    if unload:
        payload["ollama_unload"] = unload
    return payload


def get_calibration_snapshot() -> dict[str, Any] | None:
    val = get_runtime_value(CALIBRATION_SNAPSHOT_KEY)
    return val if isinstance(val, dict) else None
