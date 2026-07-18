"""Crypto scalp pipeline — 5m rules_engine; optional LLM on borderline setups."""

from __future__ import annotations

import hashlib
from typing import Any

from config_loader import load_config
from crypto_pipeline import _llm_mode, _llm_reject_reason, _synthetic_approve
from crypto_product import get_crypto_trading_product_for_trade, order_side_for_entry
from effective_config import get_config_effective, get_guardrails
from event_log import log_event, log_llm_decision
from filter_event_details import filter_log_payload
from guardrails import enforce_guardrails, position_size_dry_run
from indicators.technical import compute_indicators
from llm_client import validate_signal
from news_service import news_context_with_signals
from on_chain.metrics import apply_on_chain_gate
from retail_guard import check_retail_guard
from scalp_direction import resolve_scalp_direction
from scalp_klines import fetch_scalp_candles
from scalp_klines_feed_health import record_klines_feed_health
from signals_engine_service import consume_signals
from utils import inputs_hash


def _scalp_cfg(*, symbol: str = "", workflow_name: str = "") -> dict[str, Any]:
    from llm_assist_service import apply_instance_scalp_llm

    base = load_config("crypto_scalp_hybrid")
    return apply_instance_scalp_llm(base, symbol=symbol, workflow_name=workflow_name)


def _compute_scalp_extras(candles: list[dict[str, float]], rules: dict[str, Any]) -> dict[str, Any]:
    closes = [c["c"] for c in candles]
    volumes = [c["v"] for c in candles]
    n = int(rules.get("momentum_bars", 3))
    mom_pct = 0.0
    if len(closes) > n and closes[-n - 1]:
        mom_pct = (closes[-1] - closes[-n - 1]) / closes[-n - 1] * 100
    lookback = min(20, max(len(volumes) - 1, 1))
    avg_vol = sum(volumes[-lookback - 1 : -1]) / lookback if lookback else volumes[-1]
    vol_ratio = round(volumes[-1] / avg_vol, 4) if avg_vol else 1.0
    return {
        "momentum_pct": round(mom_pct, 4),
        "volume_ratio": vol_ratio,
        "bar_count": len(candles),
    }


def scalp_rule_filter(
    indicators: dict[str, Any],
    extras: dict[str, Any],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """Micro rules + ambiguity_score for hybrid routing."""
    rules = cfg.get("scalp_rules", {})
    checks: list[dict[str, Any]] = []
    strengths: list[float] = []

    mom_min = float(rules.get("momentum_min_pct", 0.15))
    mom = float(extras.get("momentum_pct", 0))
    mom_pass = abs(mom) >= mom_min
    mom_strength = min(1.0, abs(mom) / max(mom_min * 3, 0.01))
    checks.append(
        {
            "rule": "momentum",
            "passed": mom_pass,
            "detail": f"momentum {mom:.3f}% (need |Δ|≥{mom_min}%)",
            "strength": round(mom_strength, 3),
        }
    )
    if mom_pass:
        strengths.append(mom_strength)

    rsi = indicators.get("rsi_14")
    rsi_lo = float(rules.get("rsi_active_low", 38))
    rsi_hi = float(rules.get("rsi_active_high", 62))
    rsi_pass = rsi is not None and (rsi < rsi_lo or rsi > rsi_hi)
    rsi_strength = 0.0
    if rsi is not None:
        if rsi < rsi_lo:
            rsi_strength = min(1.0, (rsi_lo - rsi) / 15)
        elif rsi > rsi_hi:
            rsi_strength = min(1.0, (rsi - rsi_hi) / 15)
    checks.append(
        {
            "rule": "rsi_active",
            "passed": rsi_pass,
            "detail": f"RSI {rsi} outside {rsi_lo}–{rsi_hi}" if rsi is not None else "RSI n/a",
            "strength": round(rsi_strength, 3),
        }
    )
    if rsi_pass:
        strengths.append(rsi_strength)

    vol_min = float(rules.get("volume_spike_min", 1.35))
    vol_ratio = float(extras.get("volume_ratio", 1))
    vol_pass = vol_ratio >= vol_min
    vol_strength = min(1.0, (vol_ratio - 1) / max(vol_min, 0.01))
    checks.append(
        {
            "rule": "volume_spike",
            "passed": vol_pass,
            "detail": f"volume_ratio {vol_ratio} (need ≥{vol_min})",
            "strength": round(vol_strength, 3),
        }
    )
    if vol_pass:
        strengths.append(vol_strength)

    hist = indicators.get("macd_histogram")
    macd_v = indicators.get("macd")
    sig = indicators.get("macd_signal")
    macd_pass = (
        hist is not None
        and macd_v is not None
        and sig is not None
        and hist > 0
        and macd_v > sig
        and mom > 0
    )
    macd_strength = 0.4 if macd_pass else 0.0
    checks.append(
        {
            "rule": "macd_momentum_align",
            "passed": macd_pass,
            "detail": "MACD bullish aligned with positive momentum" if macd_pass else "MACD/momentum mismatch",
            "strength": macd_strength,
        }
    )
    if macd_pass:
        strengths.append(macd_strength)

    if rules.get("require_trend_align", True):
        trend = indicators.get("trend")
        trend_pass = trend == "up" and mom > 0
        trend_strength = 0.35 if trend_pass else 0.0
        checks.append(
            {
                "rule": "trend_align",
                "passed": trend_pass,
                "detail": f"trend={trend}, momentum={mom:.3f}%",
                "strength": trend_strength,
            }
        )
        if trend_pass:
            strengths.append(trend_strength)

    passed_rules = [c["rule"] for c in checks if c.get("passed")]
    min_rules = int(rules.get("min_rules_to_proceed", 2))
    proceed = len(passed_rules) >= max(1, min_rules)

    if not strengths:
        ambiguity = 1.0
    else:
        peak = max(strengths)
        ambiguity = round(max(0.0, min(1.0, 1.0 - peak)), 4)

    rule_name = "+".join(passed_rules) if passed_rules else None
    return {
        "proceed": proceed,
        "reject_reason": None if proceed else "scalp_no_rule_match",
        "rule_name": rule_name,
        "ambiguity_score": ambiguity,
        "filter_checks": checks,
        "passed_rules": passed_rules,
    }


def _scalp_llm_enabled(cfg: dict[str, Any]) -> bool:
    if cfg.get("llm_enabled") is False:
        return False
    return int(cfg.get("llm_sample_pct", 0)) > 0


def _llm_sample_selected(symbol: str, bar_ts: int, sample_pct: int) -> bool:
    if sample_pct <= 0:
        return False
    digest = hashlib.sha256(f"{symbol}:{bar_ts}".encode()).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return bucket < min(sample_pct, 100)


def _hybrid_path(
    ambiguity: float,
    *,
    clear_max: float,
    border_max: float,
    llm_sampled: bool,
    llm_enabled: bool,
) -> str:
    if ambiguity <= clear_max:
        return "script"
    if ambiguity > border_max:
        return "skip"
    return "llm" if (llm_enabled and llm_sampled) else "script"


def run_crypto_scalp_signal(
    *,
    symbol: str,
    env: str = "dry_run",
    workflow_name: str = "crypto-scalp-hybrid-dry-run",
    skip_llm: bool = False,
    equity: float = 10000.0,
) -> dict[str, Any]:
    cfg = _scalp_cfg(symbol=symbol, workflow_name=workflow_name)
    crypto_cfg = get_config_effective("crypto_config")
    product = get_crypto_trading_product_for_trade(
        cfg=crypto_cfg, symbol=symbol, workflow_name=workflow_name
    )
    guardrails = get_guardrails()
    llm_mode = _llm_mode(symbol=symbol, workflow_name=workflow_name)
    testnet = crypto_cfg.get("env") == "testnet" or env == "paper"
    timeframe = str(cfg.get("timeframe", "5m"))
    prompt_version = str(cfg.get("prompt_version", "crypto_scalp_validate_v1"))
    amb_cfg = cfg.get("ambiguity", {})
    clear_max = float(amb_cfg.get("clear_max", 0.35))
    border_max = float(amb_cfg.get("border_max", 0.72))
    sample_pct = int(cfg.get("llm_sample_pct", 0))
    llm_on = _scalp_llm_enabled(cfg) and not skip_llm and llm_mode != "disabled"

    klines = fetch_scalp_candles(
        symbol=symbol,
        timeframe=timeframe,
        limit=120,
        testnet=testnet,
        crypto_cfg=crypto_cfg,
        workflow_name=workflow_name,
        scalp_cfg=cfg,
    )
    feed_health = record_klines_feed_health(symbol, klines, cfg)
    klines_source = klines.source
    candles = klines.candles

    if feed_health.get("block_reason") or not klines.quality_ok:
        reject_reason = str(feed_health.get("block_reason") or "klines_unusable")
        quality_payload = {
            "klines_source": klines_source,
            "testnet_poor": klines.testnet_poor,
            "quality_ok": klines.quality_ok,
            "fallback_attempted": klines.fallback_attempted,
            "feed_health": feed_health,
            "filter_profile": cfg.get("filter_profile"),
            "config_version": cfg.get("version"),
            "market_type": product.get("market_type"),
            "timeframe": timeframe,
        }
        log_event(
            market="crypto",
            env=env,
            stage="filter",
            symbol=symbol,
            decision="skip",
            reject_reason=reject_reason,
            workflow_name=workflow_name,
            payload=quality_payload,
        )
        return {
            "status": "skipped",
            "stage": "filter",
            "symbol": symbol,
            "reason": reject_reason,
            "klines_source": klines_source,
            "feed_health": feed_health,
        }

    indicators = compute_indicators(candles)
    extras = _compute_scalp_extras(candles, cfg.get("scalp_rules", {}))
    merged = {**indicators, **extras}
    bar_ts = int(candles[-1]["t"]) if candles else 0

    ih = inputs_hash(
        symbol=symbol,
        timeframe=timeframe,
        indicators=merged,
        candles_ts=[c["t"] for c in candles],
    )

    log_event(
        market="crypto",
        env=env,
        stage="signal",
        symbol=symbol,
        decision="approve",
        workflow_name=workflow_name,
        inputs_hash=ih,
        payload={
            "indicators": merged,
            "timeframe": timeframe,
            "klines_source": klines_source,
            "testnet_poor": klines.testnet_poor,
            "feed_health": feed_health,
        },
    )

    filtered = scalp_rule_filter(merged, extras, cfg)
    allow_short = bool(product.get("allow_short")) and bool(product.get("is_futures"))
    direction = resolve_scalp_direction(
        merged,
        extras,
        cfg.get("scalp_rules", {}),
        allow_short=allow_short,
        bullish_filter=filtered,
    )
    llm_sampled = _llm_sample_selected(symbol, bar_ts, sample_pct) if llm_on else False
    path = _hybrid_path(
        float(filtered.get("ambiguity_score", 1)),
        clear_max=clear_max,
        border_max=border_max,
        llm_sampled=llm_sampled,
        llm_enabled=llm_on,
    )

    filter_payload = filter_log_payload(filtered)
    filter_payload.update(
        {
            "hybrid_path": path,
            "llm_enabled": llm_on,
            "llm_sample_pct": sample_pct,
            "llm_sampled": llm_sampled,
            "ambiguity_score": filtered.get("ambiguity_score"),
            "timeframe": timeframe,
            "direction": direction,
            "allow_short": allow_short,
            "market_type": product.get("market_type"),
            "filter_profile": cfg.get("filter_profile"),
            "config_version": cfg.get("version"),
            "klines_source": klines_source,
            "testnet_poor": klines.testnet_poor,
            "feed_health": feed_health,
        }
    )

    if not direction:
        log_event(
            market="crypto",
            env=env,
            stage="filter",
            symbol=symbol,
            decision="skip",
            reject_reason=filtered.get("reject_reason"),
            workflow_name=workflow_name,
            inputs_hash=ih,
            payload=filter_payload,
        )
        return {"status": "skipped", "stage": "filter", "symbol": symbol, "inputs_hash": ih}

    if path == "skip":
        log_event(
            market="crypto",
            env=env,
            stage="filter",
            symbol=symbol,
            decision="skip",
            reject_reason="scalp_ambiguity_too_high",
            workflow_name=workflow_name,
            inputs_hash=ih,
            payload=filter_payload,
        )
        return {
            "status": "skipped",
            "stage": "filter",
            "symbol": symbol,
            "reason": "ambiguity_too_high",
            "inputs_hash": ih,
        }

    log_event(
        market="crypto",
        env=env,
        stage="filter",
        symbol=symbol,
        decision="approve",
        workflow_name=workflow_name,
        inputs_hash=ih,
        payload=filter_payload,
    )

    retail_cfg = {**crypto_cfg.get("retail_guard", {}), **cfg.get("retail_guard", {})}
    if direction == "long" and retail_cfg.get("enabled", True):
        retail = check_retail_guard(indicators=merged, candles=candles)
        if not retail.get("pass"):
            log_event(
                market="crypto",
                env=env,
                stage="filter",
                symbol=symbol,
                decision="reject",
                reject_reason=retail.get("reject_reason"),
                workflow_name=workflow_name,
                inputs_hash=ih,
                payload={"retail_guard": retail, "hybrid_path": path},
            )
            return {"status": "rejected", "stage": "retail_guard", "symbol": symbol}

    on_chain = apply_on_chain_gate(
        cfg.get("on_chain"),
        side=order_side_for_entry(direction),
        default_mode="advisory",
    )
    if not on_chain.get("skipped") and not on_chain.get("pass"):
        log_event(
            market="crypto",
            env=env,
            stage="filter",
            symbol=symbol,
            decision="reject",
            reject_reason=on_chain.get("reject_reason"),
            workflow_name=workflow_name,
            inputs_hash=ih,
            payload={
                "on_chain": on_chain.get("context"),
                "on_chain_mode": on_chain.get("mode"),
                "hybrid_path": path,
            },
        )
        return {"status": "rejected", "stage": "on_chain", "symbol": symbol}

    fast_model = str(cfg.get("ollama_model_fast", "qwen2.5:3b"))
    llm_result: dict[str, Any]

    if path != "llm" or not llm_on:
        llm_result = {
            **_synthetic_approve(filtered.get("rule_name")),
            "hybrid_path": "script",
            "reasoning": f"script_path: ambiguity={filtered.get('ambiguity_score')}, rules={filtered.get('rule_name')}",
        }
        log_event(
            market="crypto",
            env=env,
            stage="llm",
            symbol=symbol,
            decision="approve",
            reject_reason=None,
            workflow_name=workflow_name,
            inputs_hash=ih,
            model="rules_engine",
            confidence=1.0,
            payload={
                "hybrid_path": "script",
                "llm_enabled": llm_on,
                "ambiguity_score": filtered.get("ambiguity_score"),
                "llm_skipped": True,
            },
        )
    else:
        news, pending_signal_ids = news_context_with_signals([symbol, symbol.replace("USDT", "")])
        user_ambiguity = str(filtered.get("ambiguity_score"))
        llm_cfg = cfg.get("llm") or {}
        llm_result = validate_signal(
            market="crypto",
            symbol=symbol,
            indicators={**merged, "ambiguity_score": filtered.get("ambiguity_score")},
            prompt_version=prompt_version,
            news_summary=f"{news}\nAmbiguity: {user_ambiguity}",
            timeframe=timeframe,
            model=fast_model,
            temperature=llm_cfg.get("temperature"),
            timeout_ms=llm_cfg.get("timeout_ms"),
            max_tokens=llm_cfg.get("max_tokens"),
        )
        event_id = log_event(
            market="crypto",
            env=env,
            stage="llm",
            symbol=symbol,
            decision=llm_result.get("action"),
            reject_reason=_llm_reject_reason(llm_result),
            workflow_name=workflow_name,
            inputs_hash=ih,
            prompt_version=prompt_version,
            model=llm_result.get("model"),
            confidence=llm_result.get("confidence"),
            latency_ms=llm_result.get("latency_ms"),
            payload={
                "hybrid_path": "llm",
                "ambiguity_score": filtered.get("ambiguity_score"),
                "llm_sampled": True,
                "raw": str(llm_result.get("raw", ""))[:2000],
            },
        )
        consume_signals(pending_signal_ids, event_id=event_id)
        log_llm_decision(
            trade_event_id=event_id,
            market="crypto",
            model=llm_result.get("model", fast_model),
            prompt_version=prompt_version,
            inputs_hash=ih,
            raw_response=str(llm_result.get("raw", "")),
            parsed=llm_result,
            latency_ms=int(llm_result.get("latency_ms") or 0),
        )
        llm_result["hybrid_path"] = "llm"
        if llm_mode == "validate_only" and llm_result.get("action") == "reject":
            return {
                "status": "rejected",
                "stage": "llm_veto",
                "symbol": symbol,
                "llm": llm_result,
                "hybrid_path": "llm",
            }

    guard = enforce_guardrails(
        market="crypto",
        symbol=symbol,
        llm_decision=llm_result,
        env=env,
        guardrails=guardrails,
        workflow_name=workflow_name,
    )
    log_event(
        market="crypto",
        env=env,
        stage="guardrails",
        symbol=symbol,
        decision="approve" if guard["pass"] else "reject",
        reject_reason=guard.get("reject_reason"),
        workflow_name=workflow_name,
        inputs_hash=ih,
        payload={
            "hybrid_path": llm_result.get("hybrid_path"),
            "llm_action": llm_result.get("action"),
            "llm_reasoning": llm_result.get("reasoning"),
        },
    )
    if not guard["pass"]:
        return {"status": "rejected", "stage": "guardrails", "symbol": symbol, "guard": guard}

    risk_scale = float(cfg.get("risk", {}).get("scale_notional_pct", 0.5))
    sizing = position_size_dry_run(
        equity=equity,
        entry_price=merged["close"],
        guardrails=guardrails,
        market="crypto",
        side=direction,
        leverage=int(product.get("leverage") or 1),
    )
    lev = int(product.get("leverage") or 1)
    sizing["quantity"] = round(float(sizing.get("quantity", 0)) * risk_scale, 8)
    sizing["notional"] = round(float(sizing.get("notional", 0)) * risk_scale, 2)
    sizing["margin_notional"] = round(float(sizing.get("margin_notional", 0)) * risk_scale, 2)
    sizing["hybrid_path"] = llm_result.get("hybrid_path")
    sizing["risk_scale"] = risk_scale

    from workflow_session_config_service import cap_sizing_to_session_capital

    sizing = cap_sizing_to_session_capital(
        sizing,
        market="crypto",
        symbol=symbol,
        workflow_name=workflow_name,
        leverage=lev,
    )

    log_event(
        market="crypto",
        env=env,
        stage="risk",
        symbol=symbol,
        decision="approve",
        workflow_name=workflow_name,
        inputs_hash=ih,
        notional=sizing.get("notional"),
        payload=sizing,
    )

    if env == "dry_run":
        log_event(
            market="crypto",
            env=env,
            stage="order",
            symbol=symbol,
            decision="skip",
            reject_reason="dry_run_mode",
            workflow_name=workflow_name,
            inputs_hash=ih,
            payload=sizing,
        )
        return {
            "status": "dry_run_complete",
            "symbol": symbol,
            "inputs_hash": ih,
            "hybrid_path": llm_result.get("hybrid_path"),
            "ambiguity_score": filtered.get("ambiguity_score"),
            "llm": llm_result,
            "sizing": sizing,
        }

    return {
        "status": "ready_for_order",
        "symbol": symbol,
        "inputs_hash": ih,
        "hybrid_path": llm_result.get("hybrid_path"),
        "direction": direction,
        "position_side": direction,
        "side": sizing.get("order_side"),
        "market_type": product.get("market_type"),
        "leverage": product.get("leverage"),
        "sizing": sizing,
        "llm": llm_result,
    }
