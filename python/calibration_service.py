"""Offline LLM hyperparameter calibration — grid over temperature × min_confidence."""

from __future__ import annotations

import threading
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
from market_llm_config import (
    MARKETS,
    get_market_llm_config,
    get_market_ollama_model,
    get_market_prompt_version,
    market_config_apply_hint,
    normalize_market,
)
from runtime_settings import get_runtime_value, set_runtime_value

CALIBRATION_SNAPSHOT_KEY = "benchmark_last_calibration"
CALIBRATION_PARTIAL_KEY = "benchmark_calibration_partial"

_cancel_events: dict[str, threading.Event] = {}
_worker_threads: dict[str, threading.Thread] = {}
_calib_llm_lock = threading.Lock()


def _calibration_snapshot_key(market: str | None) -> str:
    return f"benchmark_last_calibration_{normalize_market(market)}"


def _calibration_partial_key(market: str | None) -> str:
    return f"benchmark_calibration_partial_{normalize_market(market)}"


def _calibration_job_key(market: str | None) -> str:
    return f"benchmark_calibration_job_{normalize_market(market)}"


def _cancel_event(mkt: str) -> threading.Event:
    if mkt not in _cancel_events:
        _cancel_events[mkt] = threading.Event()
    return _cancel_events[mkt]


def _clear_calibration_partial(mkt: str) -> None:
    partial_key = _calibration_partial_key(mkt)
    set_runtime_value(partial_key, {}, updated_by="calibration_cancel")
    if mkt == "crypto":
        set_runtime_value(CALIBRATION_PARTIAL_KEY, {}, updated_by="calibration_cancel")


def _abort_calibration_job(mkt: str, *, message: str = "Калибровка отменена") -> None:
    _clear_calibration_partial(mkt)
    _worker_threads.pop(mkt, None)
    _write_job(
        mkt,
        state="cancelled",
        phase="idle",
        message=message,
        error=None,
        result=None,
        finished_at=_utc_now(),
    )


def _worker_alive(mkt: str) -> bool:
    worker = _worker_threads.get(mkt)
    return worker is not None and worker.is_alive()


def _parse_iso_age_ms(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int((datetime.now(timezone.utc) - dt).total_seconds() * 1000)
    except ValueError:
        return None


def _reconcile_stale_job(mkt: str) -> None:
    """Fix jobs stuck after container restart, hung Ollama, or incomplete cancel."""
    job = _read_job(mkt)
    state = job.get("state")
    if state not in ("running", "cancelling"):
        return

    if not _worker_alive(mkt):
        if state == "cancelling":
            _abort_calibration_job(mkt)
        else:
            _clear_calibration_partial(mkt)
            _write_job(
                mkt,
                state="error",
                phase="idle",
                message="Калибровка прервана (процесс недоступен)",
                error="worker_lost",
                finished_at=_utc_now(),
            )
        return

    stall_ms = int(_calibration_cfg().get("stall_after_ms", 1200000))
    age_ms = _parse_iso_age_ms(job.get("updated_at"))
    if age_ms is not None and age_ms > stall_ms:
        _cancel_event(mkt).set()
        _clear_calibration_partial(mkt)
        _write_job(
            mkt,
            state="error",
            phase="idle",
            message="Калибровка зависла — сброшена автоматически",
            error="stalled",
            finished_at=_utc_now(),
        )


def _other_running_market(mkt: str) -> str | None:
    for other in MARKETS:
        if other == mkt:
            continue
        other_job = _read_job(other)
        if other_job.get("state") in ("running", "cancelling"):
            return other
    return None


def get_calibration_stages(*, market: str | None = None) -> list[dict[str, Any]]:
    """Human-readable stages for the benchmark UI."""
    mkt = normalize_market(market)
    cfg = _calibration_cfg()
    synthetic = list_golden_cases(market=mkt)
    historical = list_historical_cases(market=mkt)
    syn_n = len(synthetic)
    hist_n = len(historical)
    temps = list(cfg["temperatures"])
    confs = [float(x) for x in cfg["min_confidence"]]
    llm_calls = len(temps) * (syn_n + hist_n)
    return [
        {
            "id": "outcome_sample",
            "group": "outcome",
            "title_ru": "Сбор live-кейсов",
            "title_en": "Collect live cases",
            "description_ru": (
                "Берёт реальные решения LLM из журнала за 30 дней (approve/reject, confidence, "
                "индикаторы) и добавляет новые записи в benchmark_cases. Нужен для метрик "
                "precision/recall на фактических исходах."
            ),
            "description_en": (
                "Pulls real LLM decisions from the last 30 days (approve/reject, confidence, "
                "indicators) into benchmark_cases. Feeds precision/recall on actual outcomes."
            ),
        },
        {
            "id": "outcome_label",
            "group": "outcome",
            "title_ru": "Разметка исходов",
            "title_en": "Label outcomes",
            "description_ru": (
                "Для каждого кейса смотрит цену после решения: good (верный approve), bad "
                "(ошибочный approve), missed_opportunity (пропущенная сделка), good_reject "
                "(верный отказ). Без этой разметки outcome_precision в калибровке недоступен."
            ),
            "description_en": (
                "Labels each case by post-decision price: good approve, bad approve, "
                "missed opportunity, good reject. Required for outcome_precision in calibration."
            ),
        },
        {
            "id": "calib_synthetic",
            "group": "calibration",
            "title_ru": f"Синтетические фикстуры ({syn_n})",
            "title_en": f"Synthetic fixtures ({syn_n})",
            "description_ru": (
                "Заранее заданные сценарии (RSI, тренд, новости) с эталонным approve/reject. "
                "Проверяет, что модель стабильно следует правилам стратегии на контролируемых "
                "примерах. Часть кейсов уходит в holdout (не участвует в подборе порога)."
            ),
            "description_en": (
                "Predefined scenarios (RSI, trend, news) with expected approve/reject. "
                "Checks strategy rule-following on controlled examples. Part goes to holdout."
            ),
        },
        {
            "id": "calib_historical",
            "group": "calibration",
            "title_ru": f"Исторические фикстуры ({hist_n})",
            "title_en": f"Historical fixtures ({hist_n})",
            "description_ru": (
                "Реальные ситуации, перенесённые в golden set (в т.ч. из live). "
                "Проверяет поведение на рыночных данных, близких к production."
            ),
            "description_en": (
                "Real situations promoted to the golden set (including from live). "
                "Tests behavior on market data close to production."
            ),
        },
        {
            "id": "calib_temperature",
            "group": "calibration",
            "title_ru": f"Перебор temperature ({len(temps)} значений)",
            "title_en": f"Temperature sweep ({len(temps)} values)",
            "description_ru": (
                f"Для каждой temperature модель вызывается на всех {syn_n + hist_n} фикстурах "
                f"({llm_calls} вызовов LLM). Сравнивается фактический ответ с "
                "ожидаемым после применения min_confidence и counter-thesis."
            ),
            "description_en": (
                f"At each temperature the model runs all {syn_n + hist_n} fixtures "
                f"({llm_calls} LLM calls). Actual vs expected after "
                "min_confidence and counter-thesis gates."
            ),
        },
        {
            "id": "calib_finalize",
            "group": "calibration",
            "title_ru": f"Сетка min_confidence ({len(confs)} порогов)",
            "title_en": f"Min_confidence grid ({len(confs)} thresholds)",
            "description_ru": (
                "Без новых вызовов LLM: для каждой пары temperature × min_confidence считается "
                "составной score (история 40%, synthetic train 20%, holdout 15%, outcome 25%). "
                "Лучшая ячейка — рекомендация для YAML."
            ),
            "description_en": (
                "No extra LLM calls: scores each temperature × min_confidence cell "
                "(historical 40%, synthetic train 20%, holdout 15%, outcome 25%). "
                "Best cell becomes the YAML recommendation."
            ),
        },
    ]


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
        "llm_timeout_ms": 180000,
        "stall_after_ms": 1200000,
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


def outcome_metrics_at_confidence(
    *,
    min_confidence: float,
    days: int = 30,
    market: str | None = None,
) -> dict[str, Any]:
    """Precision/recall on labeled benchmark_cases at a confidence threshold (no LLM)."""
    run_migrations()
    conn = get_connection()
    try:
        query = """
            SELECT c.original_action, c.confidence, l.label
            FROM benchmark_cases c
            INNER JOIN benchmark_labels l ON l.inputs_hash = c.inputs_hash
            WHERE c.decision_at >= datetime('now', ?)
              AND l.label NOT IN ('pending', 'neutral')
        """
        params: list[Any] = [f"-{days} days"]
        if market:
            query += " AND c.market = ?"
            params.append(normalize_market(market))
        rows = conn.execute(query, params).fetchall()
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
    should_cancel: Callable[[], bool] | None = None,
    timeout_ms: int | None = None,
) -> list[dict[str, Any]]:
    all_cases = [(c, "synthetic") for c in synthetic] + [(c, "historical") for c in historical]
    total = len(all_cases)
    runs: list[dict[str, Any]] = []

    for i, (case, tier) in enumerate(all_cases, 1):
        if should_cancel and should_cancel():
            break
        cid = case["id"]
        mkt = case["market"]
        if on_case_done:
            on_case_done(cid, i, total)
        with _calib_llm_lock:
            if should_cancel and should_cancel():
                break
            if tier == "synthetic":
                result = run_one_golden_case(
                    case_id=cid,
                    market=mkt,
                    model=model,
                    temperature=temperature,
                    timeout_ms=timeout_ms,
                )
            else:
                result = run_one_historical_case(
                    case_id=cid,
                    market=mkt,
                    model=model,
                    temperature=temperature,
                    timeout_ms=timeout_ms,
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
        "market": normalize_market(market),
        "temperatures": temps,
        "min_confidence": confs,
        "grid_cells": len(temps) * len(confs),
        "llm_calls": len(temps) * (len(synthetic) + len(historical)),
        "fixtures": {"synthetic": len(synthetic), "historical": len(historical)},
        "stages": get_calibration_stages(market=market),
    }


def run_calibration_temperature(
    *,
    temperature: float,
    model: str | None = None,
    market: str | None = None,
) -> dict[str, Any]:
    """Run LLM for all fixtures at one temperature; store partial results."""
    mkt = normalize_market(market)
    model = model or get_market_ollama_model(mkt)
    synthetic = list_golden_cases(market=mkt)
    historical = list_historical_cases(market=mkt)
    runs = _run_fixtures_at_temperature(
        temperature=temperature,
        model=model,
        synthetic=synthetic,
        historical=historical,
    )
    partial_key = _calibration_partial_key(mkt)
    partial = get_runtime_value(partial_key) or {"model": model, "market": mkt, "by_temp": {}}
    if partial.get("market") not in (None, mkt):
        partial = {"model": model, "market": mkt, "by_temp": {}}
    if not isinstance(partial.get("by_temp"), dict):
        partial["by_temp"] = {}
    partial["model"] = model
    partial["market"] = mkt
    partial["by_temp"][str(temperature)] = runs
    partial["updated_at"] = _utc_now()
    set_runtime_value(partial_key, partial, updated_by="api")
    return {
        "status": "ok",
        "market": mkt,
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
            outcome = outcome_metrics_at_confidence(
                min_confidence=conf,
                days=outcome_days,
                market=market,
            )
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
    mkt = normalize_market(market)
    current_llm = get_market_llm_config(mkt)
    apply_hint = market_config_apply_hint(mkt)

    return {
        "status": "ok",
        "market": mkt,
        "model": model,
        "prompt_version": get_market_prompt_version(mkt),
        "grid_size": {"temperatures": len(temps), "min_confidence": len(confs), "cells": len(grid)},
        "fixtures": {
            "synthetic_total": len(synthetic),
            "synthetic_train": len(train_set),
            "synthetic_holdout": len(holdout_set),
            "historical": len(historical),
        },
        "current_llm": {
            "temperature": current_llm.get("temperature"),
            "min_confidence": current_llm.get("min_confidence"),
        },
        "current_guardrails": {
            "temperature": current_llm.get("temperature"),
            "min_confidence": current_llm.get("min_confidence"),
        },
        "grid": grid,
        "heatmap": {
            "temperatures": temps,
            "min_confidence": confs,
            "composite_scores": heatmap_scores,
        },
        "recommended": recommended,
        "recommendation_note": (
            f"Примените вручную в {apply_hint} — auto-apply отключён."
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
    mkt = normalize_market(market)
    cfg = _calibration_cfg()
    partial_key = _calibration_partial_key(mkt)
    partial = get_runtime_value(partial_key) or {}
    raw_by_temp = partial.get("by_temp") if isinstance(partial.get("by_temp"), dict) else {}
    if not raw_by_temp:
        legacy = get_runtime_value(CALIBRATION_PARTIAL_KEY) or {}
        legacy_raw = legacy.get("by_temp") if isinstance(legacy.get("by_temp"), dict) else {}
        if legacy_raw and mkt == "crypto":
            raw_by_temp = legacy_raw
            partial = legacy
        else:
            return {"status": "error", "message": "no_partial_calibration_data", "market": mkt}

    model = model or partial.get("model") or get_market_ollama_model(mkt)
    temps = [float(t) for t in raw_by_temp.keys()]
    temps.sort()
    confs = [float(x) for x in cfg["min_confidence"]]
    synthetic = list_golden_cases(market=mkt)

    payload = _score_grid_from_raw(
        raw_by_temp,
        model=model,
        temps=temps,
        confs=confs,
        synthetic=synthetic,
        market=mkt,
    )
    set_runtime_value(
        _calibration_snapshot_key(mkt),
        {**payload, "saved_at": _utc_now()},
        updated_by="api",
    )
    set_runtime_value(partial_key, {}, updated_by="api")
    if mkt == "crypto":
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
    mkt = normalize_market(market)
    cfg = _calibration_cfg()
    model = model or get_market_ollama_model(mkt)
    temps = temperatures if temperatures is not None else list(cfg["temperatures"])
    confs = (
        min_confidence_values
        if min_confidence_values is not None
        else [float(x) for x in cfg["min_confidence"]]
    )

    synthetic = list_golden_cases(market=mkt)
    historical = list_historical_cases(market=mkt)

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
        market=mkt,
    )
    set_runtime_value(
        _calibration_snapshot_key(mkt),
        {**payload, "saved_at": _utc_now()},
        updated_by="api",
    )
    if mkt == "crypto":
        set_runtime_value(CALIBRATION_SNAPSHOT_KEY, {**payload, "saved_at": _utc_now()}, updated_by="api")
    unload = _maybe_unload_ollama_after_benchmark(model)
    if unload:
        payload["ollama_unload"] = unload
    return payload


def get_calibration_snapshot(market: str | None = None) -> dict[str, Any] | None:
    mkt = normalize_market(market)
    val = get_runtime_value(_calibration_snapshot_key(mkt))
    if isinstance(val, dict):
        return val
    if mkt == "crypto":
        legacy = get_runtime_value(CALIBRATION_SNAPSHOT_KEY)
        return legacy if isinstance(legacy, dict) else None
    return None


def get_llm_settings_snapshot() -> dict[str, Any]:
    """Current production LLM params + calibration grid plan for the benchmark UI."""
    shared = load_config("guardrails").get("llm", {})
    markets: dict[str, Any] = {}
    for mkt in MARKETS:
        llm = get_market_llm_config(mkt)
        plan = get_calibration_plan(market=mkt)
        markets[mkt] = {
            "llm": {
                "temperature": llm.get("temperature"),
                "min_confidence": llm.get("min_confidence"),
                "max_tokens": llm.get("max_tokens"),
                "require_counter_thesis": llm.get("require_counter_thesis"),
                "counter_thesis_min_chars": llm.get("counter_thesis_min_chars"),
                "timeout_ms": llm.get("timeout_ms"),
            },
            "model": get_market_ollama_model(mkt),
            "prompt_version": get_market_prompt_version(mkt),
            "config_hint": market_config_apply_hint(mkt),
            "calibration": plan,
            "last_calibration": get_calibration_snapshot(mkt),
        }
    return {
        "status": "ok",
        "shared": {
            "require_counter_thesis": shared.get("require_counter_thesis"),
            "counter_thesis_min_chars": shared.get("counter_thesis_min_chars"),
            "timeout_ms": shared.get("timeout_ms"),
            "max_tokens": shared.get("max_tokens"),
            "benchmark_unload_after": shared.get("benchmark_unload_after"),
            "allowed_actions": shared.get("allowed_actions"),
        },
        "markets": markets,
    }


def _job_progress_pct(job: dict[str, Any]) -> int:
    state = job.get("state")
    if state == "done":
        return 100
    total = int(job.get("llm_calls_total") or 0)
    done = int(job.get("llm_calls_done") or 0)
    if total <= 0:
        if state == "finalize" or job.get("phase") == "finalize":
            return 95
        return 0
    pct = int(done * 100 / total)
    if job.get("phase") == "finalize":
        return min(99, max(pct, 90))
    return min(99, pct)


def _read_job(mkt: str) -> dict[str, Any]:
    raw = get_runtime_value(_calibration_job_key(mkt))
    return dict(raw) if isinstance(raw, dict) else {}


def _write_job(mkt: str, **fields: Any) -> dict[str, Any]:
    job = _read_job(mkt)
    new_state = fields.get("state", job.get("state"))
    if job.get("state") in ("cancelled", "error", "done") and new_state in ("running", "cancelling"):
        return job
    job.update(fields)
    job["market"] = mkt
    job["updated_at"] = _utc_now()
    job["progress_pct"] = _job_progress_pct(job)
    set_runtime_value(_calibration_job_key(mkt), job, updated_by="calibration_job")
    return job


def get_calibration_job_status(market: str | None = None) -> dict[str, Any]:
    mkt = normalize_market(market)
    _reconcile_stale_job(mkt)
    job = _read_job(mkt)
    if not job or job.get("state") in (None, "idle"):
        plan = get_calibration_plan(market=mkt)
        return {
            "status": "ok",
            "state": "idle",
            "market": mkt,
            "llm_calls_total": plan.get("llm_calls", 0),
            "progress_pct": 0,
            "model": get_market_ollama_model(mkt),
        }
    job["status"] = "ok"
    job["progress_pct"] = _job_progress_pct(job)
    return job


def list_calibration_jobs_status() -> dict[str, Any]:
    markets: dict[str, Any] = {}
    active_market: str | None = None
    for mkt in MARKETS:
        st = get_calibration_job_status(mkt)
        markets[mkt] = st
        if st.get("state") in ("running", "cancelling"):
            active_market = mkt
    return {"status": "ok", "markets": markets, "active_market": active_market}


def _calibration_job_worker(mkt: str, model: str | None = None) -> None:
    cancel_ev = _cancel_event(mkt)
    cancel_ev.clear()
    partial_key = _calibration_partial_key(mkt)
    try:
        plan = get_calibration_plan(market=mkt)
        temps = list(plan.get("temperatures") or [])
        fixtures = plan.get("fixtures") or {}
        case_total = int(fixtures.get("synthetic", 0)) + int(fixtures.get("historical", 0))
        llm_total = int(plan.get("llm_calls") or (len(temps) * case_total))
        calib_timeout_ms = int(_calibration_cfg().get("llm_timeout_ms", 180000))

        model = model or get_market_ollama_model(mkt)
        synthetic = list_golden_cases(market=mkt)
        historical = list_historical_cases(market=mkt)
        partial: dict[str, Any] = {"model": model, "market": mkt, "by_temp": {}}
        _clear_calibration_partial(mkt)

        _write_job(
            mkt,
            state="running",
            phase="temperature",
            started_at=_utc_now(),
            model=model,
            temperature_index=0,
            temperature_total=len(temps),
            case_index=0,
            case_total=case_total,
            llm_calls_total=llm_total,
            llm_calls_done=0,
            message="Запуск калибровки…",
            error=None,
            result=None,
        )

        calls_done = 0
        for ti, temp in enumerate(temps, 1):
            if cancel_ev.is_set():
                _abort_calibration_job(mkt)
                return

            def _on_case(cid: str, ci: int, ct: int, *, t_idx: int = ti, t_val: float = temp) -> None:
                nonlocal calls_done
                if cancel_ev.is_set():
                    return
                calls_done = (t_idx - 1) * ct + ci
                _write_job(
                    mkt,
                    state="running",
                    phase="temperature",
                    temperature_index=t_idx,
                    temperature_total=len(temps),
                    current_temperature=t_val,
                    case_index=ci,
                    case_total=ct,
                    current_case_id=cid,
                    llm_calls_done=calls_done,
                    message=f"T={t_val} · кейс {ci}/{ct} · {cid}",
                )

            runs = _run_fixtures_at_temperature(
                temperature=temp,
                model=model,
                synthetic=synthetic,
                historical=historical,
                on_case_done=_on_case,
                should_cancel=cancel_ev.is_set,
                timeout_ms=calib_timeout_ms,
            )
            if cancel_ev.is_set():
                _abort_calibration_job(mkt)
                return

            partial["by_temp"][str(temp)] = runs
            partial["updated_at"] = _utc_now()
            set_runtime_value(partial_key, partial, updated_by="calibration_job")

        if cancel_ev.is_set():
            _abort_calibration_job(mkt)
            return

        _write_job(
            mkt,
            state="running",
            phase="finalize",
            llm_calls_done=llm_total,
            message="Подсчёт сетки и рекомендации…",
        )
        if cancel_ev.is_set():
            _abort_calibration_job(mkt)
            return

        prev_snap = get_calibration_snapshot(mkt)
        result = finalize_calibration(model=model, market=mkt)
        if cancel_ev.is_set():
            if prev_snap:
                set_runtime_value(
                    _calibration_snapshot_key(mkt),
                    prev_snap,
                    updated_by="calibration_cancel_revert",
                )
            else:
                set_runtime_value(_calibration_snapshot_key(mkt), {}, updated_by="calibration_cancel")
            _clear_calibration_partial(mkt)
            _abort_calibration_job(mkt)
            return
        if result.get("status") != "ok":
            raise RuntimeError(str(result.get("message") or result.get("status")))

        _write_job(
            mkt,
            state="done",
            phase="idle",
            llm_calls_done=llm_total,
            message="Калибровка завершена",
            result=result,
            finished_at=_utc_now(),
        )
    except Exception as exc:
        if cancel_ev.is_set():
            _abort_calibration_job(mkt)
            return
        _write_job(
            mkt,
            state="error",
            phase="idle",
            error=str(exc),
            message=str(exc),
            finished_at=_utc_now(),
        )


def start_calibration_job(market: str | None = None, model: str | None = None) -> dict[str, Any]:
    """Start background calibration; HTTP returns immediately (no gateway timeout)."""
    mkt = normalize_market(market)
    model = model or get_market_ollama_model(mkt)
    current = _read_job(mkt)
    if current.get("state") in ("running", "cancelling"):
        _reconcile_stale_job(mkt)
        current = _read_job(mkt)
        if current.get("state") in ("running", "cancelling"):
            if _worker_alive(mkt):
                return {
                    "status": "already_running",
                    "market": mkt,
                    "job": get_calibration_job_status(mkt),
                }
            _reconcile_stale_job(mkt)

    blocked_by = _other_running_market(mkt)
    if blocked_by:
        return {
            "status": "blocked",
            "message": "other_market_running",
            "blocked_by": blocked_by,
            "market": mkt,
            "job": get_calibration_job_status(mkt),
        }

    _cancel_event(mkt).clear()
    _write_job(
        mkt,
        state="running",
        phase="starting",
        started_at=_utc_now(),
        model=model,
        message="Подготовка…",
        error=None,
        result=None,
    )
    thread = threading.Thread(
        target=_calibration_job_worker,
        args=(mkt, model),
        daemon=True,
        name=f"calib-{mkt}",
    )
    _worker_threads[mkt] = thread
    thread.start()
    return {"status": "started", "market": mkt, "model": model, "job": get_calibration_job_status(mkt)}


def cancel_calibration_job(market: str | None = None) -> dict[str, Any]:
    """Emergency stop: discard partial results and do not save a new snapshot."""
    mkt = normalize_market(market)
    _reconcile_stale_job(mkt)
    job = _read_job(mkt)
    state = job.get("state")
    if state not in ("running", "cancelling"):
        return {
            "status": "not_running",
            "market": mkt,
            "job": get_calibration_job_status(mkt),
        }

    _cancel_event(mkt).set()
    _clear_calibration_partial(mkt)
    _abort_calibration_job(mkt)
    return {"status": "cancelled", "market": mkt, "job": get_calibration_job_status(mkt)}
