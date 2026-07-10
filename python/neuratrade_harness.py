"""NeuraTradeBench-style harness — deterministic fixtures + optional live pipeline."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from config_loader import load_config, wiki_root
from crypto_pipeline import run_crypto_signal
from db.connection import get_connection
from llm_client import list_ollama_models, validate_signal


def _cfg() -> dict[str, Any]:
    return load_config("neuratrade_config")


def _artifact_dir() -> Path:
    cfg = _cfg()
    rel = Path(str(cfg.get("artifact_dir", "data/neuratrade/reports")))
    if rel.is_absolute():
        return rel
    base = Path(__file__).resolve().parents[1]
    return base / rel


def _resolve_models(cfg: dict[str, Any]) -> list[str]:
    models = [str(m) for m in (cfg.get("models") or []) if m]
    if models:
        return models
    tag_result = list_ollama_models()
    return [m.get("name") for m in (tag_result.get("models") or [])[:3] if m.get("name")]


def _score_fixture(pass_expected: bool, result: dict[str, Any]) -> float:
    if pass_expected:
        return 1.0
    reason = str(result.get("reject_reason") or "")
    if reason in ("invalid_json", "ollama_http_error", "ollama_timeout"):
        return 0.0
    return 0.25


def _score_pipeline(status: str) -> float:
    if status in ("ready_for_order", "dry_run_complete"):
        return 1.0
    if status == "skipped":
        return 0.5
    return 0.0


def _persist_result(entry: dict[str, Any], full: dict[str, Any]) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO neuratrade_results
            (id, run_id, recorded_at, model, symbol, score, status, payload_json,
             case_id, mode, latency_ms, expected_action, actual_action, pass_expected, ablation_id)
            VALUES (?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                entry["run_id"],
                entry["model"],
                entry.get("symbol"),
                entry.get("score"),
                entry.get("status"),
                json.dumps(full, ensure_ascii=False, default=str)[:8000],
                entry.get("case_id"),
                entry.get("mode"),
                entry.get("latency_ms"),
                entry.get("expected_action"),
                entry.get("actual_action"),
                1 if entry.get("pass_expected") else 0 if entry.get("pass_expected") is not None else None,
                entry.get("ablation_id"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _run_fixtures_for_model(
    model: str,
    *,
    run_id: str,
    cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    from benchmark_service import _golden_files, _load_golden_file

    market = str((cfg.get("fixtures") or {}).get("market", "crypto"))
    ablations = cfg.get("ablations") or [{"id": "baseline"}]
    crypto_cfg = load_config("crypto_config")
    results: list[dict[str, Any]] = []

    for ablation in ablations:
        ab_id = str(ablation.get("id", "baseline"))
        clear_news = bool(ablation.get("clear_news"))

        for mkt, rel in _golden_files(market):
            if mkt != market:
                continue
            data = _load_golden_file(rel)
            pv = data.get("prompt_version") or crypto_cfg.get("prompt_version", "crypto_validate_v1")
            for case in data.get("cases") or []:
                expected = str(case.get("expected_action", "reject"))
                news = "" if clear_news else (case.get("news") or "")
                from runtime_settings import set_runtime_value

                set_runtime_value("ollama_model_override", model)
                try:
                    result = validate_signal(
                        market=mkt,
                        symbol=case.get("symbol", "BTCUSDT"),
                        indicators=case.get("indicators") or {},
                        prompt_version=pv,
                        model=model,
                        news_summary=news,
                        timeframe=case.get("timeframe", "4h"),
                    )
                finally:
                    set_runtime_value("ollama_model_override", None)

                actual = str(result.get("action", "reject"))
                passed = actual == expected
                entry = {
                    "run_id": run_id,
                    "model": model,
                    "symbol": case.get("symbol"),
                    "case_id": case.get("id"),
                    "mode": "fixtures",
                    "ablation_id": ab_id,
                    "expected_action": expected,
                    "actual_action": actual,
                    "pass_expected": passed,
                    "latency_ms": result.get("latency_ms"),
                    "status": "pass" if passed else "fail",
                    "score": _score_fixture(passed, result),
                    "confidence": result.get("confidence"),
                    "reject_reason": result.get("reject_reason"),
                }
                results.append(entry)
                _persist_result(entry, {**result, "case": case, "ablation": ablation})
    return results


def _run_pipeline_for_model(
    model: str,
    *,
    run_id: str,
    symbols: list[str],
    equity: float,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for symbol in symbols:
        from runtime_settings import set_runtime_value

        set_runtime_value("ollama_model_override", model)
        try:
            full = run_crypto_signal(
                symbol=symbol,
                env="paper",
                workflow_name="neuratrade-harness",
                skip_llm=False,
                equity=equity,
            )
        finally:
            set_runtime_value("ollama_model_override", None)

        status = str(full.get("status", ""))
        entry = {
            "run_id": run_id,
            "model": model,
            "symbol": symbol,
            "case_id": None,
            "mode": "pipeline",
            "ablation_id": None,
            "expected_action": None,
            "actual_action": None,
            "pass_expected": None,
            "latency_ms": full.get("latency_ms"),
            "status": status,
            "score": _score_pipeline(status),
        }
        results.append(entry)
        _persist_result(entry, full)
    return results


def _aggregate_run(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_model: dict[str, dict[str, Any]] = {}
    for row in results:
        model = str(row.get("model", "?"))
        bucket = by_model.setdefault(
            model,
            {
                "model": model,
                "runs": 0,
                "fixture_runs": 0,
                "fixture_pass": 0,
                "pipeline_runs": 0,
                "pipeline_pass": 0,
                "avg_score": 0.0,
                "avg_latency_ms": 0,
                "latencies": [],
                "scores": [],
            },
        )
        bucket["runs"] += 1
        bucket["scores"].append(float(row.get("score") or 0))
        if row.get("latency_ms") is not None:
            bucket["latencies"].append(int(row["latency_ms"]))
        mode = row.get("mode")
        if mode == "fixtures":
            bucket["fixture_runs"] += 1
            if row.get("pass_expected"):
                bucket["fixture_pass"] += 1
        elif mode == "pipeline":
            bucket["pipeline_runs"] += 1
            if float(row.get("score") or 0) >= 1.0:
                bucket["pipeline_pass"] += 1

    summary: list[dict[str, Any]] = []
    for model, bucket in by_model.items():
        scores = bucket.pop("scores")
        lats = bucket.pop("latencies")
        bucket["avg_score"] = round(sum(scores) / len(scores), 4) if scores else 0
        bucket["avg_latency_ms"] = int(sum(lats) / len(lats)) if lats else None
        bucket["fixture_pass_rate"] = (
            round(bucket["fixture_pass"] / bucket["fixture_runs"], 4)
            if bucket["fixture_runs"]
            else None
        )
        bucket["pipeline_pass_rate"] = (
            round(bucket["pipeline_pass"] / bucket["pipeline_runs"], 4)
            if bucket["pipeline_runs"]
            else None
        )
        summary.append(bucket)
    summary.sort(key=lambda x: (-(x.get("avg_score") or 0), -(x.get("fixture_pass_rate") or 0)))
    return {"by_model": summary}


def _export_artifact(run_id: str, report: dict[str, Any]) -> str | None:
    cfg = _cfg()
    if not cfg.get("export_artifacts", True):
        return None
    out_dir = _artifact_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{run_id}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return str(path)


def recommend_model(*, limit: int = 10) -> dict[str, Any] | None:
    """Suggest best model from recent fixture benchmarks (NeuraTradeBench-style)."""
    cfg = _cfg()
    min_rate = float(cfg.get("recommend_min_pass_rate", 0.75))
    min_runs = int(cfg.get("recommend_min_runs", 5))
    board = get_leaderboard(limit=limit)
    for row in board:
        runs = int(row.get("fixture_runs") or 0)
        rate = row.get("fixture_pass_rate")
        if runs >= min_runs and rate is not None and float(rate) >= min_rate:
            return {
                "model": row["model"],
                "fixture_pass_rate": rate,
                "avg_latency_ms": row.get("avg_latency_ms"),
                "reason": "best_fixture_pass_rate",
            }
    return None


def run_harness_cycle(*, equity: float = 10000.0, mode: str | None = None) -> dict[str, Any]:
    """Run NeuraTradeBench-style cycle: golden fixtures ± live pipeline."""
    cfg = _cfg()
    mode = (mode or cfg.get("default_mode", "fixtures")).lower()
    models = _resolve_models(cfg)
    symbols = list(cfg.get("symbols", ["BTCUSDT", "ETHUSDT"]))
    run_id = str(uuid.uuid4())
    all_results: list[dict[str, Any]] = []

    for model in models:
        if mode in ("fixtures", "both"):
            all_results.extend(_run_fixtures_for_model(model, run_id=run_id, cfg=cfg))
        if mode in ("pipeline", "both"):
            all_results.extend(
                _run_pipeline_for_model(model, run_id=run_id, symbols=symbols, equity=equity)
            )

    aggregate = _aggregate_run(all_results)
    leaderboard = get_leaderboard()
    report = {
        "status": "ok",
        "run_id": run_id,
        "mode": mode,
        "models": models,
        "results_count": len(all_results),
        "aggregate": aggregate,
        "leaderboard": leaderboard,
        "recommended_model": recommend_model(),
        "fixtures_source": str(wiki_root() / (cfg.get("fixtures") or {}).get("golden_file", "")),
        "reference": "https://github.com/sakshyambanjade/neuratrade",
    }
    artifact = _export_artifact(run_id, {**report, "results": all_results})
    if artifact:
        report["artifact_path"] = artifact
    return report


def get_leaderboard(limit: int = 10) -> list[dict[str, Any]]:
    return _leaderboard(limit)


def _leaderboard(limit: int = 10) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT model,
                   AVG(score) AS avg_score,
                   COUNT(*) AS runs,
                   SUM(CASE WHEN status IN ('ready_for_order','dry_run_complete','pass') THEN 1 ELSE 0 END) AS passes,
                   SUM(CASE WHEN mode = 'fixtures' THEN 1 ELSE 0 END) AS fixture_runs,
                   SUM(CASE WHEN mode = 'fixtures' AND pass_expected = 1 THEN 1 ELSE 0 END) AS fixture_pass,
                   AVG(CASE WHEN mode = 'fixtures' AND latency_ms IS NOT NULL THEN latency_ms END) AS avg_latency_ms,
                   AVG(CASE WHEN mode = 'pipeline' THEN score END) AS pipeline_avg_score
            FROM neuratrade_results
            WHERE recorded_at >= datetime('now', '-30 days')
            GROUP BY model
            ORDER BY avg_score DESC, fixture_pass DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            fr = int(d.get("fixture_runs") or 0)
            fp = int(d.get("fixture_pass") or 0)
            d["fixture_pass_rate"] = round(fp / fr, 4) if fr else None
            out.append(d)
        return out
    finally:
        conn.close()
