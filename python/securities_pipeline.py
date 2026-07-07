"""Securities pipelines — DCA and swing dry_run."""

from __future__ import annotations

from typing import Any

import httpx

from config_loader import load_config
from event_log import log_event, log_llm_decision
from guardrails import enforce_guardrails
from indicators.technical import compute_indicators, rule_filter
from llm_client import validate_signal
from news_service import news_context_for_symbols
from utils import inputs_hash


def _fetch_moex_candles(secid: str, interval: int = 24) -> list[dict[str, float]]:
    url = (
        f"https://iss.moex.com/iss/engines/stock/markets/shares/"
        f"boards/TQBR/securities/{secid}/candles.json"
    )
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, params={"interval": interval, "limit": 100})
        resp.raise_for_status()
        data = resp.json()
    cols = data["candles"]["columns"]
    rows = data["candles"]["data"]
    candles = []
    for row in rows:
        rec = dict(zip(cols, row))
        candles.append({
            "t": rec.get("begin", 0),
            "o": float(rec.get("open", 0)),
            "h": float(rec.get("high", 0)),
            "l": float(rec.get("low", 0)),
            "c": float(rec.get("close", 0)),
            "v": float(rec.get("volume", 0)),
        })
    return candles


def run_securities_swing_dry_run(
    *,
    ticker: str,
    env: str = "dry_run",
    workflow_name: str = "securities-swing-dry-run",
    skip_llm: bool = False,
) -> dict[str, Any]:
    sec_cfg = load_config("securities_config")
    guardrails = load_config("guardrails")
    swing = sec_cfg.get("swing_signals", {})
    prompt_version = swing.get("prompt_version", "securities_validate_v1")

    candles = _fetch_moex_candles(ticker)
    if len(candles) < 30:
        return {"status": "error", "message": "insufficient_candles", "ticker": ticker}

    indicators = compute_indicators(candles)
    ih = inputs_hash(
        symbol=ticker, timeframe="1d", indicators=indicators,
        candles_ts=[int(str(c["t"])[:10].replace("-", "")) if isinstance(c["t"], str) else c["t"] for c in candles],
    )

    log_event(
        market="securities", env=env, stage="signal", symbol=ticker,
        workflow_name=workflow_name, inputs_hash=ih, currency="RUB",
        payload={"indicators": indicators},
    )

    filtered = rule_filter(indicators, {"rule_filter": {"rsi_oversold": 40, "rsi_overbought": 60}})
    if not filtered.get("proceed"):
        log_event(
            market="securities", env=env, stage="filter", symbol=ticker,
            decision="skip", reject_reason="no_rule_match",
            workflow_name=workflow_name, inputs_hash=ih, currency="RUB",
        )
        return {"status": "skipped", "stage": "filter", "ticker": ticker}

    llm_result: dict[str, Any] = {"action": "reject"}
    if not skip_llm:
        news = news_context_for_symbols([ticker, "MOEX"])
        llm_result = validate_signal(
            market="securities", symbol=ticker, indicators=filtered,
            prompt_version=prompt_version, news_summary=news, timeframe="1d",
        )
        log_event(
            market="securities", env=env, stage="llm", symbol=ticker,
            decision=llm_result.get("action"),
            workflow_name=workflow_name, inputs_hash=ih, currency="RUB",
            model=llm_result.get("model"), confidence=llm_result.get("confidence"),
        )
        log_llm_decision(
            trade_event_id=None,
            market="securities",
            model=llm_result.get("model", "unknown"),
            prompt_version=prompt_version,
            inputs_hash=ih,
            raw_response=str(llm_result.get("raw", "")),
            parsed=llm_result,
            latency_ms=int(llm_result.get("latency_ms") or 0),
        )

    guard = enforce_guardrails(
        market="securities", symbol=ticker, llm_decision=llm_result, env=env, guardrails=guardrails,
    )
    log_event(
        market="securities", env=env, stage="guardrails", symbol=ticker,
        decision="approve" if guard["pass"] else "reject",
        reject_reason=guard.get("reject_reason"),
        workflow_name=workflow_name, inputs_hash=ih, currency="RUB",
    )

    return {
        "status": "dry_run_complete" if guard["pass"] else "rejected",
        "ticker": ticker,
        "inputs_hash": ih,
        "indicators": filtered,
        "llm": llm_result,
        "guard": guard,
    }


def run_securities_dca_dry_run(
    *,
    env: str = "dry_run",
    workflow_name: str = "securities-dca-sandbox",
) -> dict[str, Any]:
    sec_cfg = load_config("securities_config")
    dca = sec_cfg.get("index_dca", sec_cfg.get("dca", {}))
    ticker = dca.get("ticker", "TMOS")
    amount_rub = dca.get("amount_rub", 10000)

    log_event(
        market="securities", env=env, stage="signal", symbol=ticker,
        decision="approve", workflow_name=workflow_name, currency="RUB",
        notional=amount_rub,
        payload={"mode": "index_dca", "amount_rub": amount_rub, "order_type": dca.get("order_type", "MARKET")},
    )

    if env == "dry_run":
        log_event(
            market="securities", env=env, stage="order", symbol=ticker,
            decision="skip", reject_reason="dry_run_mode",
            workflow_name=workflow_name, currency="RUB", notional=amount_rub,
            payload={"tax_stub": {"type": "purchase", "amount_rub": amount_rub, "ticker": ticker}},
        )
        return {
            "status": "dry_run_complete",
            "ticker": ticker,
            "amount_rub": amount_rub,
            "tax_stub": {"type": "purchase", "amount_rub": amount_rub, "ticker": ticker},
        }

    return {"status": "ready_for_order", "ticker": ticker, "amount_rub": amount_rub}
