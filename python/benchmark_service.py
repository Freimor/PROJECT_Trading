"""LLM benchmark — sampling, outcome labeling, replay, scoring."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import yaml

from binance_client import _credentials
from config_loader import load_config, wiki_root
from db.connection import get_connection
from db.migrate import run_migrations
from evaluation.replay import champion_challenger_report, replay_by_inputs_hash
from llm_client import validate_signal
from runtime_settings import get_runtime_value, set_runtime_value


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _benchmark_cfg() -> dict[str, Any]:
    try:
        return load_config("benchmark_config")
    except FileNotFoundError:
        return {
            "crypto": {"timeframe": "4h", "horizon_bars": 6, "good_return_pct": 1.0, "bad_return_pct": -1.0},
            "securities": {
                "moex_interval": 24,
                "horizon_bars": 5,
                "good_return_pct": 2.0,
                "bad_return_pct": -2.0,
            },
            "sampling": {"max_cases_per_run": 80, "min_age_hours": 30},
        }


def _load_golden_file(rel_path: str) -> dict[str, Any]:
    path = wiki_root() / rel_path
    if not path.exists():
        return {"cases": []}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def sample_benchmark_cases(*, days: int = 30, market: str | None = None) -> dict[str, Any]:
    """Pull LLM decision cases from trade log into benchmark_cases."""
    run_migrations()
    cfg = _benchmark_cfg()
    max_cases = int(cfg.get("sampling", {}).get("max_cases_per_run", 80))
    conn = get_connection()
    inserted = 0
    try:
        q = """
            SELECT l.inputs_hash, l.market, l.created_at, l.parsed_action,
                   l.model, l.prompt_version, l.confidence
            FROM llm_decisions l
            WHERE l.created_at >= datetime('now', ?)
        """
        params: list[Any] = [f"-{days} days"]
        if market:
            q += " AND l.market = ?"
            params.append(market)
        q += " ORDER BY l.created_at DESC LIMIT ?"
        params.append(max_cases * 2)
        rows = list(conn.execute(q, params).fetchall())

        if not rows:
            q2 = """
                SELECT inputs_hash, market, event_at AS created_at, decision AS parsed_action,
                       model, prompt_version, confidence
                FROM trade_events
                WHERE stage = 'llm' AND event_at >= datetime('now', ?)
            """
            params2: list[Any] = [f"-{days} days"]
            if market:
                q2 += " AND market = ?"
                params2.append(market)
            q2 += " ORDER BY event_at DESC LIMIT ?"
            params2.append(max_cases * 2)
            rows = list(conn.execute(q2, params2).fetchall())

        seen: set[str] = set()
        for row in rows:
            ih = row["inputs_hash"]
            if ih in seen:
                continue
            seen.add(ih)

            sig = conn.execute(
                """
                SELECT symbol, payload_json FROM trade_events
                WHERE inputs_hash = ? AND stage = 'signal'
                ORDER BY event_at DESC LIMIT 1
                """,
                (ih,),
            ).fetchone()
            if not sig:
                continue
            payload = json.loads(sig["payload_json"] or "{}")
            indicators = payload.get("indicators") or {}
            symbol = sig["symbol"] or ""

            exists = conn.execute(
                "SELECT 1 FROM benchmark_cases WHERE inputs_hash = ?", (ih,)
            ).fetchone()
            if exists:
                continue

            conn.execute(
                """
                INSERT INTO benchmark_cases
                    (inputs_hash, market, symbol, decision_at, indicators_json,
                     original_action, original_model, prompt_version, confidence, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'live')
                """,
                (
                    ih,
                    row["market"],
                    symbol,
                    row["created_at"],
                    json.dumps(indicators, ensure_ascii=False),
                    row["parsed_action"],
                    row["model"],
                    row["prompt_version"],
                    row["confidence"],
                ),
            )
            inserted += 1
            if inserted >= max_cases:
                break
        conn.commit()
        total = conn.execute("SELECT COUNT(*) AS c FROM benchmark_cases").fetchone()["c"]
        return {"status": "ok", "inserted": inserted, "total_cases": total}
    finally:
        conn.close()


def _forward_return_crypto(
    symbol: str,
    decision_at: str,
    entry_price: float,
    *,
    timeframe: str,
    horizon_bars: int,
) -> float | None:
    if entry_price <= 0:
        return None
    try:
        dt = _parse_dt(decision_at)
        start_ms = int(dt.timestamp() * 1000)
        _, _, base = _credentials(True)
        url = f"{base}/api/v3/klines"
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                url,
                params={
                    "symbol": symbol,
                    "interval": timeframe,
                    "startTime": start_ms,
                    "limit": horizon_bars + 2,
                },
            )
            resp.raise_for_status()
            klines = resp.json()
        if len(klines) <= horizon_bars:
            return None
        exit_close = float(klines[horizon_bars][4])
        return round((exit_close - entry_price) / entry_price * 100, 4)
    except Exception:
        return None


def _forward_return_securities(
    ticker: str,
    decision_at: str,
    entry_price: float,
    *,
    horizon_bars: int,
    interval: int = 24,
) -> float | None:
    if entry_price <= 0:
        return None
    try:
        candles = _fetch_moex_candles(ticker, interval=interval)
        if len(candles) < horizon_bars + 2:
            return None
        dt = _parse_dt(decision_at).date()
        idx = None
        for i, c in enumerate(candles):
            begin = str(c.get("t", ""))[:10]
            try:
                cdate = datetime.strptime(begin, "%Y-%m-%d").date()
            except ValueError:
                continue
            if cdate <= dt:
                idx = i
        if idx is None or idx + horizon_bars >= len(candles):
            return None
        exit_close = float(candles[idx + horizon_bars]["c"])
        return round((exit_close - entry_price) / entry_price * 100, 4)
    except Exception:
        return None


def _classify_label(
    action: str,
    forward_return_pct: float | None,
    *,
    good_pct: float,
    bad_pct: float,
) -> str:
    if forward_return_pct is None:
        return "pending"
    if action == "approve":
        if forward_return_pct >= good_pct:
            return "good"
        if forward_return_pct <= bad_pct:
            return "bad"
        return "neutral"
    if forward_return_pct >= good_pct:
        return "missed_opportunity"
    if forward_return_pct <= bad_pct:
        return "good_reject"
    return "neutral_reject"


def label_outcomes(*, market: str | None = None, limit: int = 100) -> dict[str, Any]:
    """Compute forward returns and auto-labels for benchmark cases."""
    run_migrations()
    cfg = _benchmark_cfg()
    min_age_h = int(cfg.get("sampling", {}).get("min_age_hours", 30))
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=min_age_h)).isoformat()
    conn = get_connection()
    labeled = 0
    pending = 0
    try:
        q = """
            SELECT * FROM benchmark_cases
            WHERE decision_at <= ?
        """
        params: list[Any] = [cutoff]
        if market:
            q += " AND market = ?"
            params.append(market)
        q += " ORDER BY decision_at DESC LIMIT ?"
        params.append(limit)
        cases = conn.execute(q, params).fetchall()

        for case in cases:
            mkt = case["market"]
            indicators = json.loads(case["indicators_json"] or "{}")
            entry = float(indicators.get("close") or 0)
            mcfg = cfg.get("crypto" if mkt == "crypto" else "securities", {})
            horizon = int(mcfg.get("horizon_bars", 5))
            good_pct = float(mcfg.get("good_return_pct", 1.0))
            bad_pct = float(mcfg.get("bad_return_pct", -1.0))

            if mkt == "crypto":
                crypto_cfg = load_config("crypto_config")
                tf = mcfg.get("timeframe") or crypto_cfg.get("timeframe", "4h")
                fwd = _forward_return_crypto(
                    case["symbol"],
                    case["decision_at"],
                    entry,
                    timeframe=tf,
                    horizon_bars=horizon,
                )
            else:
                fwd = _forward_return_securities(
                    case["symbol"],
                    case["decision_at"],
                    entry,
                    horizon_bars=horizon,
                    interval=int(mcfg.get("moex_interval", 24)),
                )

            label = _classify_label(
                case["original_action"] or "reject",
                fwd,
                good_pct=good_pct,
                bad_pct=bad_pct,
            )
            if label == "pending":
                pending += 1
                continue

            label_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT OR REPLACE INTO benchmark_labels
                    (id, inputs_hash, horizon_bars, forward_return_pct, label, labeled_at)
                VALUES (
                    COALESCE((SELECT id FROM benchmark_labels WHERE inputs_hash = ?), ?),
                    ?, ?, ?, ?, ?
                )
                """,
                (
                    case["inputs_hash"],
                    label_id,
                    case["inputs_hash"],
                    horizon,
                    fwd,
                    label,
                    _utc_now(),
                ),
            )
            labeled += 1
        conn.commit()
        return {"status": "ok", "labeled": labeled, "pending": pending, "processed": len(cases)}
    finally:
        conn.close()


def run_benchmark_replay(
    *,
    model: str | None = None,
    prompt_version: str | None = None,
    market: str | None = None,
    limit: int = 30,
    label: str = "replay",
) -> dict[str, Any]:
    """Replay LLM on stored benchmark cases."""
    run_migrations()
    run_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO benchmark_runs
                (id, started_at, label, model, prompt_version, cases_count, status)
            VALUES (?, ?, ?, ?, ?, 0, 'running')
            """,
            (run_id, _utc_now(), label, model, prompt_version),
        )
        conn.commit()

        q = "SELECT * FROM benchmark_cases"
        params: list[Any] = []
        if market:
            q += " WHERE market = ?"
            params.append(market)
        q += " ORDER BY decision_at DESC LIMIT ?"
        params.append(limit)
        cases = conn.execute(q, params).fetchall()
        results: list[dict[str, Any]] = []

        for case in cases:
            replay = replay_by_inputs_hash(
                case["inputs_hash"],
                model=model,
                prompt_version=prompt_version or case["prompt_version"],
            )
            if replay.get("status") != "ok":
                continue
            new_action = replay.get("replay", {}).get("action")
            conf = replay.get("replay", {}).get("confidence")
            lat = replay.get("replay", {}).get("latency_ms")
            changed = bool(replay.get("changed"))
            conn.execute(
                """
                INSERT INTO benchmark_results
                    (id, run_id, inputs_hash, action, confidence, latency_ms, changed_from_original)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    run_id,
                    case["inputs_hash"],
                    new_action,
                    conf,
                    lat,
                    1 if changed else 0,
                ),
            )
            results.append(
                {
                    "inputs_hash": case["inputs_hash"][:12],
                    "symbol": case["symbol"],
                    "action": new_action,
                    "changed": changed,
                }
            )

        conn.execute(
            "UPDATE benchmark_runs SET cases_count = ?, status = 'ok', ended_at = ? WHERE id = ?",
            (len(results), _utc_now(), run_id),
        )
        conn.commit()
        return {
            "status": "ok",
            "run_id": run_id,
            "model": model,
            "prompt_version": prompt_version,
            "cases_replayed": len(results),
            "results_preview": results[:10],
        }
    except Exception as exc:
        conn.execute(
            "UPDATE benchmark_runs SET status = 'error', ended_at = ? WHERE id = ?",
            (_utc_now(), run_id),
        )
        conn.commit()
        return {"status": "error", "run_id": run_id, "message": str(exc)}
    finally:
        conn.close()


SNAPSHOT_KEY = "benchmark_last_snapshot"


def save_benchmark_snapshot(payload: dict[str, Any], *, operator: str = "api") -> dict[str, Any]:
    data = {**payload, "saved_at": _utc_now()}
    set_runtime_value(SNAPSHOT_KEY, data, updated_by=operator)
    return data


def get_benchmark_snapshot() -> dict[str, Any] | None:
    val = get_runtime_value(SNAPSHOT_KEY)
    return val if isinstance(val, dict) else None


def _golden_files(market: str | None = None) -> list[tuple[str, str]]:
    cfg = _benchmark_cfg()
    golden_cfg = cfg.get("golden", {})
    files: list[tuple[str, str]] = []
    if market in (None, "crypto"):
        files.append(("crypto", golden_cfg.get("crypto_file", "benchmark/crypto_golden_v1.yaml")))
    if market in (None, "securities"):
        files.append(("securities", golden_cfg.get("securities_file", "benchmark/moex_golden_v1.yaml")))
    return files


def list_golden_cases(*, market: str | None = None) -> list[dict[str, Any]]:
    crypto_cfg = load_config("crypto_config")
    sec_cfg = load_config("securities_config")
    out: list[dict[str, Any]] = []
    for mkt, rel in _golden_files(market):
        data = _load_golden_file(rel)
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
                    "expected_action": case.get("expected_action"),
                    "prompt_version": pv,
                }
            )
    return out


def run_one_golden_case(
    *,
    case_id: str,
    market: str,
    model: str | None = None,
) -> dict[str, Any]:
    crypto_cfg = load_config("crypto_config")
    sec_cfg = load_config("securities_config")
    default_model = model or crypto_cfg.get("ollama_model", "qwen3.5:9b")

    for mkt, rel in _golden_files(market):
        if mkt != market:
            continue
        data = _load_golden_file(rel)
        pv = data.get("prompt_version") or (
            crypto_cfg.get("prompt_version")
            if mkt == "crypto"
            else sec_cfg.get("swing_signals", {}).get("prompt_version", "securities_validate_v1")
        )
        for case in data.get("cases") or []:
            if case.get("id") != case_id:
                continue
            expected = case.get("expected_action", "reject")
            result = validate_signal(
                market=mkt,
                symbol=case.get("symbol", "BTCUSDT"),
                indicators=case.get("indicators") or {},
                prompt_version=pv,
                model=model or default_model,
                news_summary=case.get("news") or "",
                timeframe=case.get("timeframe", "4h"),
            )
            actual = result.get("action")
            return {
                "status": "ok",
                "id": case_id,
                "market": mkt,
                "symbol": case.get("symbol"),
                "expected": expected,
                "actual": actual,
                "pass": actual == expected,
                "confidence": result.get("confidence"),
                "latency_ms": result.get("latency_ms"),
            }
    return {"status": "error", "message": "golden_case_not_found", "id": case_id}


def aggregate_golden_results(details: list[dict[str, Any]], *, model: str) -> dict[str, Any]:
    passed = sum(1 for d in details if d.get("pass"))
    total = len(details)
    return {
        "status": "ok",
        "model": model,
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if total else 0,
        "details": details,
    }


def run_golden_benchmark(
    *,
    model: str | None = None,
    market: str | None = None,
) -> dict[str, Any]:
    """Regression test against frozen golden cases in wiki/benchmark/."""
    files = _golden_files(market)

    crypto_cfg = load_config("crypto_config")
    sec_cfg = load_config("securities_config")
    default_model = model or crypto_cfg.get("ollama_model", "qwen3.5:9b")

    all_results: list[dict[str, Any]] = []
    passed = 0
    total = 0

    for mkt, rel in files:
        data = _load_golden_file(rel)
        pv = data.get("prompt_version") or (
            crypto_cfg.get("prompt_version")
            if mkt == "crypto"
            else sec_cfg.get("swing_signals", {}).get("prompt_version", "securities_validate_v1")
        )
        for case in data.get("cases") or []:
            total += 1
            expected = case.get("expected_action", "reject")
            result = validate_signal(
                market=mkt,
                symbol=case.get("symbol", "BTCUSDT"),
                indicators=case.get("indicators") or {},
                prompt_version=pv,
                model=model or default_model,
                news_summary=case.get("news") or "",
                timeframe=case.get("timeframe", "4h"),
            )
            actual = result.get("action")
            ok = actual == expected
            if ok:
                passed += 1
            all_results.append(
                {
                    "id": case.get("id"),
                    "market": mkt,
                    "symbol": case.get("symbol"),
                    "expected": expected,
                    "actual": actual,
                    "confidence": result.get("confidence"),
                    "latency_ms": result.get("latency_ms"),
                    "pass": ok,
                }
            )

    result = {
        "status": "ok",
        "model": model or default_model,
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if total else 0,
        "details": all_results,
    }
    save_benchmark_snapshot({"golden": result, "kind": "golden"})
    return result


def _score_labels(rows: list[dict[str, Any]]) -> dict[str, Any]:
    approves = [r for r in rows if r.get("original_action") == "approve"]
    rejects = [r for r in rows if r.get("original_action") == "reject"]

    good_app = sum(1 for r in approves if r.get("label") == "good")
    bad_app = sum(1 for r in approves if r.get("label") == "bad")
    missed = sum(1 for r in rejects if r.get("label") == "missed_opportunity")
    good_rej = sum(1 for r in rejects if r.get("label") == "good_reject")

    labeled_approves = good_app + bad_app
    precision = round(good_app / labeled_approves, 4) if labeled_approves else None
    opportunities = good_app + missed
    recall = round(good_app / opportunities, 4) if opportunities else None

    sim_pnl = 0.0
    sim_count = 0
    for r in approves:
        ret = r.get("forward_return_pct")
        if ret is not None:
            sim_pnl += float(ret)
            sim_count += 1

    return {
        "cases_labeled": len(rows),
        "approve_count": len(approves),
        "reject_count": len(rejects),
        "precision_approve": precision,
        "recall": recall,
        "good_approves": good_app,
        "bad_approves": bad_app,
        "missed_opportunities": missed,
        "good_rejects": good_rej,
        "simulated_pnl_approve_pct": round(sim_pnl, 4),
        "avg_return_per_approve_pct": round(sim_pnl / sim_count, 4) if sim_count else None,
    }


def benchmark_report(*, days: int = 30, market: str | None = None) -> dict[str, Any]:
    """Full benchmark report: operational + outcome metrics."""
    run_migrations()
    sample_benchmark_cases(days=days, market=market)
    label_outcomes(market=market, limit=200)

    from evaluation.replay import evaluation_metrics

    conn = get_connection()
    try:
        q = """
            SELECT c.*, l.forward_return_pct, l.label, l.horizon_bars
            FROM benchmark_cases c
            LEFT JOIN benchmark_labels l ON l.inputs_hash = c.inputs_hash
            WHERE c.decision_at >= datetime('now', ?)
        """
        params: list[Any] = [f"-{days} days"]
        if market:
            q += " AND c.market = ?"
            params.append(market)
        rows = [dict(r) for r in conn.execute(q, params).fetchall()]
        labeled = [r for r in rows if r.get("label") and r.get("label") != "pending"]

        by_market: dict[str, Any] = {}
        for mkt in ("crypto", "securities"):
            if market and market != mkt:
                continue
            subset = [r for r in labeled if r.get("market") == mkt]
            if subset:
                by_market[mkt] = {
                    "outcome": _score_labels(subset),
                    "operational": evaluation_metrics(market=mkt, days=days),
                }

        recent_runs = conn.execute(
            """
            SELECT id, label, model, prompt_version, cases_count, status, started_at
            FROM benchmark_runs ORDER BY started_at DESC LIMIT 5
            """
        ).fetchall()

        return {
            "status": "ok",
            "days": days,
            "total_cases": len(rows),
            "labeled_cases": len(labeled),
            "by_market": by_market,
            "operational_all": evaluation_metrics(market=market, days=days),
            "recent_runs": [dict(r) for r in recent_runs],
            "config": _benchmark_cfg(),
            "last_snapshot": get_benchmark_snapshot(),
        }
    finally:
        conn.close()


def run_full_benchmark(
    *,
    days: int = 30,
    market: str | None = None,
    model: str | None = None,
    challenger_model: str | None = None,
    skip_golden: bool = False,
) -> dict[str, Any]:
    """End-to-end: sample → label → report → optional replay + golden."""
    report = benchmark_report(days=days, market=market)
    golden = None if skip_golden else run_golden_benchmark(model=model, market=market)

    replay = None
    champion_cmp = None
    if model:
        replay = run_benchmark_replay(model=model, market=market, limit=30, label="full-benchmark")

    if model and challenger_model:
        conn = get_connection()
        try:
            hashes = [
                r["inputs_hash"]
                for r in conn.execute(
                    "SELECT inputs_hash FROM benchmark_cases ORDER BY decision_at DESC LIMIT 20"
                ).fetchall()
            ]
        finally:
            conn.close()
        if hashes:
            crypto_cfg = load_config("crypto_config")
            champion_cmp = champion_challenger_report(
                inputs_hashes=hashes,
                champion_model=model,
                challenger_model=challenger_model,
                prompt_version=crypto_cfg.get("prompt_version", "crypto_validate_v1"),
            )

    payload = {
        "status": "ok",
        "report": report,
        "golden": golden,
        "replay": replay,
        "champion_challenger": champion_cmp,
    }
    save_benchmark_snapshot(
        {
            "kind": "full",
            "report": report,
            "golden": golden,
        },
        operator="api",
    )
    return payload
