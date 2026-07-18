"""Pipeline context and human explanations for trade events."""

from __future__ import annotations

import json
from typing import Any

from db.connection import get_connection

STAGE_ORDER = ("signal", "filter", "llm", "guardrails", "risk", "order", "fill")

REJECT_HINTS: dict[str, str] = {
    "llm_rejected": (
        "LLM вернула action=reject без текста в reasoning — модель отклонила сделку, "
        "но не объяснила почему. Технический фильтр при этом уже прошёл."
    ),
    "llm_rejected_no_reason": (
        "LLM отклонила сделку (action=reject), но в JSON нет поля reasoning. "
        "Проверьте промпт и модель — для отказов нужно краткое объяснение."
    ),
    "ollama_timeout": "Ollama не ответила в отведённый таймаут — сделка отклонена из соображений безопасности.",
    "ollama_http_error": "Ошибка HTTP при обращении к Ollama — LLM недоступна.",
    "invalid_json": "Модель вернула ответ не в формате JSON — сделка отклонена.",
    "invalid_action": "В ответе LLM нет корректного action (approve/reject).",
    "low_confidence": "LLM одобрила сделку, но confidence ниже порога в guardrails.yaml.",
    "missing_counter_thesis": "LLM одобрила, но counter_thesis слишком короткий или пустой.",
    "scalp_no_rule_match": (
        "Scalp-фильтр: меньше min_rules_to_proceed микро-правил (momentum/RSI/volume/MACD/trend). "
        "Если klines_source=testnet и индикаторы нулевые — проверьте feed health."
    ),
    "klines_unusable": (
        "Свечи непригодны для индикаторов даже после mainnet fallback (плоские/мало баров). "
        "Сигнал не анализируется — не путать с scalp_no_rule_match."
    ),
    "testnet_feed_dead": (
        "Testnet-лента для символа давно «мёртвая» (N тиков подряд mainnet_metrics_fallback). "
        "Торговля заблокирована настройкой block_on_feed_dead."
    ),
    "scalp_no_bear_rule_match": "Scalp short-фильтр: недостаточно медвежьих правил для шорта.",
    "scalp_ambiguity_too_high": "Сигнал слишком неоднозначный (ambiguity > порога) — даже LLM-слот не вызывается.",
    "kill_switch_active": "Активен kill switch — все сделки заблокированы.",
    "max_open_positions": "Достигнут лимит открытых позиций по риск-профилю.",
    "symbol_not_whitelisted": "Символ не в allowlist workflow.",
    "outside_session": "Вне торговой сессии MOEX.",
    "dry_run_mode": "Режим dry_run — ордер намеренно не отправляется.",
    "not_paper_mode": "Рынок не в режиме paper.",
    "retail_guard:": "Retail guard (BIS): неблагоприятный контекст для розничного входа.",
}


def _hint_for_code(code: str | None) -> str | None:
    if not code:
        return None
    if code in REJECT_HINTS:
        return REJECT_HINTS[code]
    for prefix, hint in REJECT_HINTS.items():
        if prefix.endswith(":") and str(code).startswith(prefix):
            return hint
    return None


def _parse_payload(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("payload_json")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw[:500]}
    return {}


def _pipeline_for_hash(conn, inputs_hash: str | None) -> list[dict[str, Any]]:
    if not inputs_hash:
        return []
    rows = conn.execute(
        """
        SELECT id, event_at, stage, decision, reject_reason, symbol, confidence, model,
               prompt_version, latency_ms, workflow_name, payload_json
        FROM trade_events
        WHERE inputs_hash = ?
        ORDER BY event_at ASC
        """,
        (inputs_hash,),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["payload"] = _parse_payload(item)
        item.pop("payload_json", None)
        out.append(item)
    out.sort(key=lambda r: (STAGE_ORDER.index(r["stage"]) if r["stage"] in STAGE_ORDER else 99, r["event_at"]))
    return out


def _llm_audit_for_hash(conn, inputs_hash: str | None, trade_event_id: str | None) -> dict[str, Any] | None:
    if trade_event_id:
        row = conn.execute(
            """
            SELECT id, parsed_action, confidence, counter_thesis, reject_reason,
                   model, prompt_version, latency_ms, substr(raw_response, 1, 4000) AS raw_response
            FROM llm_decisions
            WHERE trade_event_id = ?
            LIMIT 1
            """,
            (trade_event_id,),
        ).fetchone()
        if row:
            return dict(row)
    if not inputs_hash:
        return None
    row = conn.execute(
        """
        SELECT id, parsed_action, confidence, counter_thesis, reject_reason,
               model, prompt_version, latency_ms, substr(raw_response, 1, 4000) AS raw_response
        FROM llm_decisions
        WHERE inputs_hash = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (inputs_hash,),
    ).fetchone()
    return dict(row) if row else None


def _find_llm_stage(pipeline: list[dict[str, Any]]) -> dict[str, Any] | None:
    for step in pipeline:
        if step.get("stage") == "llm":
            return step
    return None


def build_event_context(row: dict[str, Any]) -> dict[str, Any]:
    """Explain why an event happened — especially rejects."""
    conn = get_connection()
    try:
        inputs_hash = row.get("inputs_hash")
        pipeline = _pipeline_for_hash(conn, inputs_hash)
        llm_stage = _find_llm_stage(pipeline)
        llm_audit = _llm_audit_for_hash(conn, inputs_hash, llm_stage.get("id") if llm_stage else None)

        reject_code = row.get("reject_reason")
        hint = _hint_for_code(reject_code)
        explanation_parts: list[str] = []

        stage = str(row.get("stage") or "")
        decision = str(row.get("decision") or "")
        symbol = row.get("symbol") or "?"

        if stage == "guardrails" and decision == "reject":
            if reject_code == "llm_rejected" or (reject_code and "llm" in str(reject_code)):
                explanation_parts.append(
                    f"Сделка по {symbol} дошла до guardrails, но LLM отклонила сигнал."
                )
                if llm_stage:
                    if llm_stage.get("reject_reason"):
                        explanation_parts.append(f"Причина LLM: {llm_stage['reject_reason']}")
                    if llm_stage.get("confidence") is not None:
                        explanation_parts.append(f"Уверенность LLM: {llm_stage['confidence']}")
                elif llm_audit:
                    if llm_audit.get("reject_reason"):
                        explanation_parts.append(f"Причина LLM: {llm_audit['reject_reason']}")
                    elif llm_audit.get("counter_thesis"):
                        explanation_parts.append(f"Контр-тезис: {llm_audit['counter_thesis']}")
                else:
                    explanation_parts.append(
                        "Запись этапа llm в журнале отсутствует (возможен сбой логирования или старая версия пайплайна). "
                        "Фильтр индикаторов при этом прошёл — отказ на стороне LLM/guardrails."
                    )
            elif hint:
                explanation_parts.append(hint)
            else:
                explanation_parts.append(
                    f"Guardrails заблокировали {symbol}: {reject_code or 'лимит риска'}"
                )
        elif stage == "llm" and decision == "reject":
            reason = reject_code or (llm_audit or {}).get("reject_reason")
            if reason:
                explanation_parts.append(f"LLM отклонила {symbol}: {reason}")
            elif hint:
                explanation_parts.append(hint)
            else:
                explanation_parts.append(f"LLM отклонила сделку по {symbol} без явной причины в журнале.")
        elif stage == "filter":
            payload = _parse_payload(row)
            if payload.get("rule_name"):
                explanation_parts.append(f"Сработало правило фильтра: {payload['rule_name']}.")
            if decision in ("skip", "reject") and hint:
                explanation_parts.append(hint)
        elif hint:
            explanation_parts.append(hint)

        if not explanation_parts and reject_code:
            explanation_parts.append(f"Код отказа: {reject_code}")

        return {
            "explanation": " ".join(explanation_parts) if explanation_parts else None,
            "reject_hint": hint,
            "pipeline": pipeline,
            "llm_audit": llm_audit,
            "missing_llm_stage": bool(
                stage == "guardrails"
                and reject_code in ("llm_rejected", None)
                and not llm_stage
                and not llm_audit
            ),
        }
    finally:
        conn.close()
