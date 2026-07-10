"""Human-readable one-line summaries for trade events."""

from __future__ import annotations

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
        return f"Guardrails заблокировали действие по {symbol}: {reject or decision or 'лимит риска'}"
    if stage == "order":
        return f"Отправлен ордер {decision or ''} по {symbol} ({env})".strip()
    if stage == "fill":
        return f"Ордер исполнен по {symbol} ({decision or 'fill'})"
    if stage == "risk":
        return f"Срабатывание риск-правила по {symbol}: {reject or decision or '—'}"
    return f"{stage}/{decision} · {symbol} · {env}".strip(" ·")
