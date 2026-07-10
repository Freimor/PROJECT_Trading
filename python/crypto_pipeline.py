"""Crypto signal pipeline — dry_run / paper."""

from __future__ import annotations

from typing import Any

from binance_client import fetch_klines
from effective_config import get_config_effective, get_guardrails
from event_log import log_event, log_llm_decision
from filter_event_details import filter_log_payload
from guardrails import enforce_guardrails, position_size_dry_run
from indicators.technical import compute_indicators, parse_binance_klines, rule_filter
from llm_client import validate_signal
from news_service import news_context_with_signals
from on_chain.metrics import on_chain_filter_for_signal
from retail_guard import check_retail_guard
from signals_engine_service import consume_signals
from swing_conservatism_service import apply_swing_conservatism_crypto


def _llm_mode() -> str:
    return str(get_guardrails().get("llm", {}).get("mode", "validate_only"))


def _llm_reject_reason(llm_result: dict[str, Any]) -> str | None:
    if llm_result.get("action") == "approve":
        return None
    return llm_result.get("reject_reason") or llm_result.get("reasoning") or None


def _synthetic_approve(rule_name: str | None) -> dict[str, Any]:
    return {
        "action": "approve",
        "confidence": 1.0,
        "reasoning": f"validate_only: rule signal {rule_name}",
        "model": "rules_engine",
        "counter_thesis": "Rules-only mode; LLM skipped or advisory.",
    }


def run_crypto_signal(
    *,
    symbol: str,
    env: str = "dry_run",
    workflow_name: str = "crypto-signal-dry-run",
    skip_llm: bool = False,
    equity: float = 10000.0,
    use_trading_agents: bool = False,
) -> dict[str, Any]:
    crypto_cfg = apply_swing_conservatism_crypto(get_config_effective("crypto_config"))
    guardrails = get_guardrails()
    llm_mode = _llm_mode()
    testnet = crypto_cfg.get("env") == "testnet" or env == "paper"
    timeframe = crypto_cfg.get("timeframe", "4h")
    prompt_version = crypto_cfg.get("prompt_version", "crypto_validate_v1")

    raw_klines = fetch_klines(symbol, timeframe, limit=250, testnet=testnet)
    candles = parse_binance_klines(raw_klines)
    indicators = compute_indicators(candles)
    ih = inputs_hash(
        symbol=symbol,
        timeframe=timeframe,
        indicators=indicators,
        candles_ts=[c["t"] for c in candles],
    )

    log_event(
        market="crypto", env=env, stage="signal", symbol=symbol,
        decision="approve", workflow_name=workflow_name,
        inputs_hash=ih, payload={"indicators": indicators},
    )

    filtered = rule_filter(indicators, crypto_cfg)
    if not filtered.get("proceed"):
        log_event(
            market="crypto", env=env, stage="filter", symbol=symbol,
            decision="skip", reject_reason=filtered.get("reject_reason"),
            workflow_name=workflow_name, inputs_hash=ih,
            payload=filter_log_payload(filtered),
        )
        return {"status": "skipped", "stage": "filter", "symbol": symbol, "inputs_hash": ih}

    log_event(
        market="crypto", env=env, stage="filter", symbol=symbol,
        decision="approve", workflow_name=workflow_name, inputs_hash=ih,
        payload=filter_log_payload(filtered),
    )

    retail = check_retail_guard(indicators=filtered, candles=candles)
    if not retail.get("pass"):
        log_event(
            market="crypto", env=env, stage="filter", symbol=symbol,
            decision="reject", reject_reason=retail.get("reject_reason"),
            workflow_name=workflow_name, inputs_hash=ih,
            payload={"retail_guard": retail},
        )
        return {"status": "rejected", "stage": "retail_guard", "symbol": symbol, "retail": retail}

    if crypto_cfg.get("on_chain", {}).get("enabled", True):
        on_chain = on_chain_filter_for_signal(side="BUY")
        if not on_chain.get("pass"):
            log_event(
                market="crypto", env=env, stage="filter", symbol=symbol,
                decision="reject", reject_reason=on_chain.get("reject_reason"),
                workflow_name=workflow_name, inputs_hash=ih,
                payload={"on_chain": on_chain.get("context")},
            )
            return {"status": "rejected", "stage": "on_chain", "symbol": symbol, "on_chain": on_chain}

    llm_result: dict[str, Any] = _synthetic_approve(filtered.get("rule_name"))
    pending_signal_ids: list[str] = []

    if llm_mode == "disabled" or skip_llm:
        llm_result = _synthetic_approve(filtered.get("rule_name"))
    elif use_trading_agents:
        from trading_agents.orchestrator import run_trading_agents
        news, pending_signal_ids = news_context_with_signals([symbol, symbol.replace("USDT", "")])
        agents = run_trading_agents(
            market="crypto", symbol=symbol, indicators=filtered, news_summary=news,
        )
        if agents.get("status") != "approved":
            return {"status": "rejected", "stage": "trading_agents", "symbol": symbol, "agents": agents}
        llm_result = agents.get("validation") or _synthetic_approve(filtered.get("rule_name"))
    else:
        news, pending_signal_ids = news_context_with_signals([symbol, symbol.replace("USDT", "")])
        llm_result = validate_signal(
            market="crypto", symbol=symbol, indicators=filtered,
            prompt_version=prompt_version, news_summary=news, timeframe=timeframe,
        )
        event_id = log_event(
            market="crypto", env=env, stage="llm", symbol=symbol,
            decision=llm_result.get("action"),
            reject_reason=_llm_reject_reason(llm_result),
            workflow_name=workflow_name, inputs_hash=ih,
            prompt_version=prompt_version, model=llm_result.get("model"),
            confidence=llm_result.get("confidence"),
            latency_ms=llm_result.get("latency_ms"),
            payload={"raw": llm_result.get("raw", "")[:2000], "llm_mode": llm_mode},
        )
        consume_signals(pending_signal_ids, event_id=event_id)
        log_llm_decision(
            trade_event_id=event_id, market="crypto",
            model=llm_result.get("model", "unknown"),
            prompt_version=prompt_version, inputs_hash=ih,
            raw_response=str(llm_result.get("raw", "")),
            parsed=llm_result, latency_ms=llm_result.get("latency_ms", 0),
        )
        if llm_mode == "validate_only" and llm_result.get("action") == "reject":
            return {"status": "rejected", "stage": "llm_veto", "symbol": symbol, "llm": llm_result}
        if llm_mode == "advisory" and llm_result.get("action") == "reject":
            llm_result = {**llm_result, "advisory_warning": True}

    guard = enforce_guardrails(
        market="crypto",
        symbol=symbol,
        llm_decision=llm_result,
        env=env,
        guardrails=guardrails,
        workflow_name=workflow_name,
    )
    log_event(
        market="crypto", env=env, stage="guardrails", symbol=symbol,
        decision="approve" if guard["pass"] else "reject",
        reject_reason=guard.get("reject_reason"),
        workflow_name=workflow_name, inputs_hash=ih,
        payload={
            "llm_action": llm_result.get("action"),
            "llm_confidence": llm_result.get("confidence"),
            "llm_reasoning": llm_result.get("reasoning"),
            "llm_reject_reason": llm_result.get("reject_reason"),
            "llm_mode": llm_mode,
        },
    )
    if not guard["pass"]:
        return {"status": "rejected", "stage": "guardrails", "symbol": symbol, "guard": guard}

    sizing = position_size_dry_run(
        equity=equity,
        entry_price=filtered["close"],
        guardrails=guardrails,
        market="crypto",
    )
    log_event(
        market="crypto", env=env, stage="risk", symbol=symbol,
        decision="approve", workflow_name=workflow_name, inputs_hash=ih,
        notional=sizing.get("notional"), payload=sizing,
    )

    if env == "dry_run":
        log_event(
            market="crypto", env=env, stage="order", symbol=symbol,
            decision="skip", reject_reason="dry_run_mode",
            workflow_name=workflow_name, inputs_hash=ih, payload=sizing,
        )
        return {
            "status": "dry_run_complete",
            "symbol": symbol,
            "inputs_hash": ih,
            "indicators": filtered,
            "llm": llm_result,
            "llm_mode": llm_mode,
            "sizing": sizing,
        }

    return {
        "status": "ready_for_order",
        "symbol": symbol,
        "inputs_hash": ih,
        "sizing": sizing,
        "llm": llm_result,
        "llm_mode": llm_mode,
    }
