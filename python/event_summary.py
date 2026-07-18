"""Human-readable one-line summaries for trade events."""

from __future__ import annotations

import json
from typing import Any

from filter_event_details import summarize_filter_event


def summarize_trade_event(row: dict[str, Any]) -> str:
    stage = str(row.get("stage") or "")
    decision = str(row.get("decision") or "")
    symbol = row.get("symbol") or "?"
    market = row.get("market") or ""
    env = row.get("env") or ""
    confidence = row.get("confidence")
    reject = row.get("reject_reason")

    if stage == "signal":
        return f"Технический сигнал по {symbol} ({market}, {env}): {decision or 'ожидание'}"
    if stage == "filter":
        return summarize_filter_event(row, compact=False)
    if stage == "llm":
        if decision == "approve":
            conf = f", уверенность {confidence:.0%}" if confidence is not None else ""
            return f"LLM одобрила сделку по {symbol}{conf}"
        if decision == "reject":
            reason = f": {reject}" if reject else ""
            return f"LLM отклонила сделку по {symbol}{reason}"
        return f"LLM оценка по {symbol}: {decision or '—'}"
    if stage == "guardrails":
        if decision == "approve":
            return f"Guardrails пропустили сделку по {symbol}"
        return f"Guardrails заблокировали действие по {symbol}: {reject or decision or 'лимит риска'}"
    if stage == "order":
        side = ""
        raw = row.get("payload_json") or row.get("payload")
        payload: dict[str, Any] = {}
        if isinstance(raw, dict):
            payload = raw
        elif isinstance(raw, str):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {}
        s = str(payload.get("side") or "").upper()
        if s == "BUY":
            side = "покупка"
        elif s == "SELL":
            side = "продажа"
        from automation_equity_service import resolve_order_notional

        notional = resolve_order_notional(row, payload)
        amount_s = ""
        if notional and notional > 0:
            cur = row.get("currency") or ("USDT" if market == "crypto" else "RUB")
            unit = "₽" if str(cur).upper() in ("RUB", "RUR") else str(cur)
            amt = f"{notional:,.2f}".replace(",", " ").rstrip("0").rstrip(".")
            amount_s = f" на {amt} {unit}"
        if payload.get("exit_reason"):
            return f"Продажа{amount_s or ''} ({payload.get('exit_reason')}) по {symbol} ({env})".strip()
        if side == "продажа":
            return f"Продажа{amount_s} по {symbol} ({env})".strip()
        if side == "покупка":
            return f"Покупка{amount_s} по {symbol} ({env})".strip()
        if side:
            return f"Ордер {side.upper()}{amount_s} по {symbol} ({env})".strip()
        return f"Ордер {decision or ''} по {symbol} ({env})".strip()
    if stage == "fill":
        from automation_equity_service import resolve_order_notional

        raw = row.get("payload_json") or row.get("payload")
        payload: dict[str, Any] = {}
        if isinstance(raw, dict):
            payload = raw
        elif isinstance(raw, str):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {}
        notional = resolve_order_notional(row, payload)
        if notional and notional > 0:
            return f"Исполнение по {symbol}: {notional:.2f} USDT"
        return f"Ордер исполнен по {symbol} ({decision or 'fill'})"
    if stage == "risk":
        if decision == "approve":
            notional = None
            raw = row.get("payload_json") or row.get("payload")
            if isinstance(raw, dict):
                notional = raw.get("notional")
            elif isinstance(raw, str):
                try:
                    notional = json.loads(raw).get("notional")
                except json.JSONDecodeError:
                    pass
            if notional is not None:
                return f"Рассчитан размер позиции по {symbol}: ~{notional} USDT"
            return f"Риск-модуль одобрил размер позиции по {symbol}"
        return f"Риск-модуль по {symbol}: {reject or decision or '—'}"
    return f"{stage}/{decision} · {symbol} · {env}".strip(" ·")
