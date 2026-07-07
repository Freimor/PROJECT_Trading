"""Crypto signal pipeline — dry_run / paper."""

from __future__ import annotations

from typing import Any

from binance_client import fetch_klines
from config_loader import load_config
from effective_config import get_guardrails
from event_log import log_event, log_llm_decision
from guardrails import enforce_guardrails, position_size_dry_run
from indicators.technical import compute_indicators, parse_binance_klines, rule_filter
from llm_client import validate_signal
from news_service import news_context_for_symbols
from utils import inputs_hash


def run_crypto_signal(
    *,
    symbol: str,
    env: str = "dry_run",
    workflow_name: str = "crypto-signal-dry-run",
    skip_llm: bool = False,
    equity: float = 10000.0,
) -> dict[str, Any]:
    crypto_cfg = load_config("crypto_config")
    guardrails = get_guardrails()
    testnet = crypto_cfg.get("env") == "testnet" or env == "paper"
    timeframe = crypto_cfg.get("timeframe", "4h")
    prompt_version = crypto_cfg.get("prompt_version", "crypto_validate_v1")

    raw_klines = fetch_klines(symbol, timeframe, limit=100, testnet=testnet)
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
        )
        return {"status": "skipped", "stage": "filter", "symbol": symbol, "inputs_hash": ih}

    log_event(
        market="crypto", env=env, stage="filter", symbol=symbol,
        decision="approve", workflow_name=workflow_name, inputs_hash=ih,
        payload={"rule_name": filtered.get("rule_name")},
    )

    llm_result: dict[str, Any] = {"action": "reject", "confidence": 0}
    if not skip_llm:
        news = news_context_for_symbols([symbol, symbol.replace("USDT", "")])
        llm_result = validate_signal(
            market="crypto", symbol=symbol, indicators=filtered,
            prompt_version=prompt_version, news_summary=news, timeframe=timeframe,
        )
        event_id = log_event(
            market="crypto", env=env, stage="llm", symbol=symbol,
            decision=llm_result.get("action"),
            reject_reason=llm_result.get("reject_reason"),
            workflow_name=workflow_name, inputs_hash=ih,
            prompt_version=prompt_version, model=llm_result.get("model"),
            confidence=llm_result.get("confidence"),
            latency_ms=llm_result.get("latency_ms"),
            payload={"raw": llm_result.get("raw", "")[:2000]},
        )
        log_llm_decision(
            trade_event_id=event_id, market="crypto",
            model=llm_result.get("model", "unknown"),
            prompt_version=prompt_version, inputs_hash=ih,
            raw_response=str(llm_result.get("raw", "")),
            parsed=llm_result, latency_ms=llm_result.get("latency_ms", 0),
        )
        if llm_result.get("action") != "approve":
            return {"status": "rejected", "stage": "llm", "symbol": symbol, "llm": llm_result}

    guard = enforce_guardrails(
        market="crypto", symbol=symbol, llm_decision=llm_result, env=env, guardrails=guardrails,
    )
    log_event(
        market="crypto", env=env, stage="guardrails", symbol=symbol,
        decision="approve" if guard["pass"] else "reject",
        reject_reason=guard.get("reject_reason"),
        workflow_name=workflow_name, inputs_hash=ih,
    )
    if not guard["pass"]:
        return {"status": "rejected", "stage": "guardrails", "symbol": symbol, "guard": guard}

    sizing = position_size_dry_run(
        equity=equity, entry_price=filtered["close"], guardrails=guardrails,
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
            "sizing": sizing,
        }

    return {
        "status": "ready_for_order",
        "symbol": symbol,
        "inputs_hash": ih,
        "sizing": sizing,
        "llm": llm_result,
    }
