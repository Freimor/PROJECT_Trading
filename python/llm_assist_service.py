"""Per-strategy LLM assist — runtime overrides on top of YAML + guardrails mode."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from config_loader import load_config
from runtime_settings import delete_runtime_value, get_runtime_meta, set_runtime_value

LlmAssistMode = Literal["disabled", "advisory", "validate_only"]

RUNTIME_GUARDRAILS_LLM_MODE = "guardrails_llm_mode"
RUNTIME_STRATEGY_PREFIX = "llm_assist:"

STRATEGY_DEFS: dict[str, dict[str, Any]] = {
    "crypto_scalp_hybrid": {
        "kind": "hybrid_sample",
        "label_ru": "Scalp 5m — LLM на пограничных тиках",
        "label_en": "Scalp 5m — LLM on borderline ticks",
        "hint_ru": "Чёткие сигналы — rules_engine; ambiguity в зоне border — быстрая LLM (veto).",
        "hint_en": "Clear signals use rules_engine; borderline ambiguity → fast LLM veto.",
        "config_file": "crypto_scalp_hybrid",
        "workflows": ["crypto-scalp-hybrid-paper", "crypto-scalp-hybrid-dry-run"],
    },
    "llm_swing": {
        "kind": "swing_validate",
        "label_ru": "Crypto swing 4h — LLM validate",
        "label_en": "Crypto swing 4h — LLM validate",
        "hint_ru": "После rule_filter LLM approve/reject (режим guardrails.llm.mode).",
        "hint_en": "After rule_filter LLM approve/reject (guardrails.llm.mode).",
        "config_file": "crypto_config",
        "workflows": ["crypto-signal-paper", "crypto-signal-dry-run"],
        "market": "crypto",
    },
    "securities_swing": {
        "kind": "swing_validate",
        "label_ru": "MOEX swing — LLM validate",
        "label_en": "MOEX swing — LLM validate",
        "hint_ru": "Дневной swing: LLM проверяет сигнал после фильтра.",
        "hint_en": "Daily swing: LLM validates after rule filter.",
        "config_file": "securities_config",
        "workflows": ["securities-swing-paper", "securities-swing-dry-run"],
        "market": "securities",
    },
}

LLM_MODE_OPTIONS = [
    {"id": "validate_only", "label_ru": "Validate (veto)", "label_en": "Validate (veto)"},
    {"id": "advisory", "label_ru": "Advisory (лог)", "label_en": "Advisory (log only)"},
    {"id": "disabled", "label_ru": "Выключено", "label_en": "Disabled"},
]


def _strategy_runtime_key(strategy_id: str) -> str:
    return f"{RUNTIME_STRATEGY_PREFIX}{strategy_id}"


def _read_strategy_override(strategy_id: str) -> dict[str, Any] | None:
    meta = get_runtime_meta(_strategy_runtime_key(strategy_id))
    if not meta:
        return None
    val = meta.get("value")
    return dict(val) if isinstance(val, dict) else None


def get_guardrails_llm_mode_override() -> str | None:
    meta = get_runtime_meta(RUNTIME_GUARDRAILS_LLM_MODE)
    if not meta:
        return None
    val = meta.get("value")
    if isinstance(val, dict):
        mode = val.get("mode")
        return str(mode) if mode else None
    if isinstance(val, str) and val.strip():
        return val.strip()
    return None


def get_effective_guardrails_llm_mode() -> str:
    override = get_guardrails_llm_mode_override()
    if override in ("disabled", "advisory", "validate_only"):
        return override
    return str(load_config("guardrails").get("llm", {}).get("mode", "validate_only"))


def set_guardrails_llm_mode(mode: str, *, operator: str = "web:operator") -> dict[str, Any]:
    mode = str(mode or "").strip()
    if mode not in ("disabled", "advisory", "validate_only"):
        raise ValueError(f"invalid_llm_mode: {mode}")
    set_runtime_value(RUNTIME_GUARDRAILS_LLM_MODE, {"mode": mode}, updated_by=operator)
    return get_llm_assist_settings()


def clear_guardrails_llm_mode(*, operator: str = "web:operator") -> dict[str, Any]:
    delete_runtime_value(RUNTIME_GUARDRAILS_LLM_MODE)
    return get_llm_assist_settings()


def _scalp_yaml_defaults() -> dict[str, Any]:
    cfg = load_config("crypto_scalp_hybrid")
    return {
        "enabled": bool(cfg.get("llm_enabled", False)),
        "sample_pct": int(cfg.get("llm_sample_pct", 0)),
    }


def get_scalp_llm_assist_effective(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge YAML + runtime override for crypto_scalp_hybrid."""
    base = dict(cfg or load_config("crypto_scalp_hybrid"))
    defaults = _scalp_yaml_defaults()
    override = _read_strategy_override("crypto_scalp_hybrid") or {}

    enabled = override.get("enabled") if "enabled" in override else defaults["enabled"]
    sample_pct = override.get("sample_pct") if "sample_pct" in override else defaults["sample_pct"]
    sample_pct = max(0, min(100, int(sample_pct or 0)))

    base["llm_enabled"] = bool(enabled) and sample_pct > 0
    base["llm_sample_pct"] = sample_pct if bool(enabled) else 0
    return base


def apply_scalp_llm_assist(cfg: dict[str, Any]) -> dict[str, Any]:
    merged = get_scalp_llm_assist_effective(cfg)
    out = dict(cfg)
    out["llm_enabled"] = merged.get("llm_enabled")
    out["llm_sample_pct"] = merged.get("llm_sample_pct")
    return out


def set_strategy_llm_assist(
    strategy_id: str,
    *,
    enabled: bool | None = None,
    sample_pct: int | None = None,
    operator: str = "web:operator",
) -> dict[str, Any]:
    if strategy_id not in STRATEGY_DEFS:
        raise ValueError(f"unknown_strategy: {strategy_id}")
    defn = STRATEGY_DEFS[strategy_id]
    if defn["kind"] != "hybrid_sample":
        raise ValueError(f"strategy_uses_guardrails_mode: {strategy_id}")

    existing = _read_strategy_override(strategy_id) or {}
    payload = dict(existing)
    if enabled is not None:
        payload["enabled"] = bool(enabled)
    if sample_pct is not None:
        payload["sample_pct"] = max(0, min(100, int(sample_pct)))

    set_runtime_value(_strategy_runtime_key(strategy_id), payload, updated_by=operator)
    return get_llm_assist_settings()


def clear_strategy_llm_assist(strategy_id: str, *, operator: str = "web:operator") -> dict[str, Any]:
    delete_runtime_value(_strategy_runtime_key(strategy_id))
    return get_llm_assist_settings()


def _strategy_row(strategy_id: str) -> dict[str, Any]:
    defn = STRATEGY_DEFS[strategy_id]
    kind = defn["kind"]
    override = _read_strategy_override(strategy_id)
    meta = get_runtime_meta(_strategy_runtime_key(strategy_id)) or {}

    row: dict[str, Any] = {
        "id": strategy_id,
        "kind": kind,
        "label_ru": defn["label_ru"],
        "label_en": defn["label_en"],
        "hint_ru": defn.get("hint_ru"),
        "hint_en": defn.get("hint_en"),
        "workflows": defn.get("workflows") or [],
        "runtime_override": override is not None,
        "updated_at": meta.get("updated_at"),
    }

    if kind == "hybrid_sample":
        defaults = _scalp_yaml_defaults()
        eff = get_scalp_llm_assist_effective()
        row["yaml_default"] = defaults
        row["effective"] = {
            "enabled": bool(eff.get("llm_enabled")),
            "sample_pct": int(eff.get("llm_sample_pct") or 0),
        }
        if override:
            row["override"] = override
    else:
        yaml_mode = str(load_config("guardrails").get("llm", {}).get("mode", "validate_only"))
        eff_mode = get_effective_guardrails_llm_mode()
        row["yaml_default"] = {"mode": yaml_mode}
        row["effective"] = {
            "enabled": eff_mode != "disabled",
            "mode": eff_mode,
        }
        row["uses_global_llm_mode"] = True

    return row


def get_llm_assist_settings(*, workflow: str | None = None) -> dict[str, Any]:
    from ollama_connection_service import get_ollama_connection_settings

    strategies = [_strategy_row(sid) for sid in STRATEGY_DEFS]
    if workflow:
        wf = workflow.strip().lower()
        strategies = [s for s in strategies if any(w.lower() == wf for w in s.get("workflows") or [])]

    conn = get_ollama_connection_settings(ping=False)
    return {
        "status": "ok",
        "ollama": {
            "effective_host": conn.get("effective_host"),
            "preset": conn.get("preset"),
            "reachable": (conn.get("ping") or {}).get("reachable"),
        },
        "guardrails_llm_mode": {
            "yaml_default": str(load_config("guardrails").get("llm", {}).get("mode", "validate_only")),
            "effective": get_effective_guardrails_llm_mode(),
            "runtime_override": get_guardrails_llm_mode_override() is not None,
            "options": LLM_MODE_OPTIONS,
        },
        "strategies": strategies,
    }


def strategy_id_for_workflow(workflow_name: str) -> str | None:
    wf = workflow_name.strip().lower()
    for sid, defn in STRATEGY_DEFS.items():
        for w in defn.get("workflows") or []:
            if w.lower() == wf:
                return sid
    return None


CREATE_PROFILES: dict[str, dict[str, Any]] = {
    "crypto_scalp_hybrid": {
        "kind": "hybrid_sample",
        "supports_assist": True,
        "default_enabled": False,
        "default_mode": "validate_only",
        "default_sample_pct": 15,
        "title_ru": "LLM assist для Scalp 5m",
        "title_en": "LLM assist for Scalp 5m",
        "summary_ru": (
            "Правила и индикаторы принимают большинство решений за миллисекунды. "
            "Локальная LLM (Ollama) подключается только на «пограничных» setup'ах — "
            "когда сигнал формально проходит фильтр, но неоднозначен."
        ),
        "summary_en": (
            "Rules and indicators handle most ticks instantly. Local LLM (Ollama) joins only "
            "on borderline setups — when the signal passes the filter but ambiguity is high."
        ),
        "steps_ru": [
            "Каждые 5 минут rules_engine считает momentum, RSI, volume, MACD.",
            "Чёткий сигнал → решение без LLM (быстро, предсказуемо).",
            "Пограничный сигнал (ambiguity в заданной зоне) → с заданной долей тиков LLM получает индикаторы, свечи и новости по паре.",
            "LLM отвечает approve или reject с confidence и counter-thesis — veto, не генерация BUY с нуля.",
            "Guardrails и risk по-прежнему считают размер позиции и лимиты в коде — LLM не задаёт notional.",
        ],
        "steps_en": [
            "Every 5 minutes rules_engine computes momentum, RSI, volume, MACD.",
            "Clear signal → decision without LLM (fast, predictable).",
            "Borderline signal → on a configured share of ticks LLM sees indicators, candles, and news.",
            "LLM returns approve or reject with confidence and counter-thesis — a veto, not a raw BUY.",
            "Guardrails and risk still size the position in code — LLM never sets notional.",
        ],
        "when_off_ru": "Только rules_engine + guardrails. Меньше задержек, нет зависимости от Ollama на каждом спорном тике.",
        "when_off_en": "Rules_engine + guardrails only. Lower latency, no Ollama on disputed ticks.",
        "caution_ru": "На CPU или при недоступной Ollama пограничные тики могут таймаутиться — используйте GPU-хост Ollama или уменьшите долю sample %.",
        "caution_en": "On CPU or unreachable Ollama, borderline ticks may time out — use a GPU Ollama host or lower sample %.",
    },
    "llm_swing": {
        "kind": "swing_validate",
        "supports_assist": True,
        "default_enabled": True,
        "default_mode": "validate_only",
        "default_sample_pct": 0,
        "title_ru": "LLM assist для Swing 4h",
        "title_en": "LLM assist for Swing 4h",
        "summary_ru": (
            "После rule_filter локальная LLM проверяет кандидата на вход: индикаторы, контекст свечей, "
            "релевантные новости. Это основной режим стратегии LLM Swing — assist не заменяет правила, а фильтрует их выход."
        ),
        "summary_en": (
            "After rule_filter, local LLM reviews the entry candidate: indicators, candle context, "
            "relevant news. This is the core LLM Swing mode — assist filters rule output, not replaces it."
        ),
        "steps_ru": [
            "На 4h свечах rule_filter ищет RSI/MACD/EMA setup.",
            "Кандидат → LLM validate (approve / reject) с reasoning и counter-thesis.",
            "При approve → guardrails проверяют confidence, лимиты, retail_guard → risk считает размер → ордер.",
            "При reject → сделка не отправляется, событие видно в LLM Audit и на графике (метка LLM-).",
        ],
        "steps_en": [
            "On 4h candles rule_filter finds RSI/MACD/EMA setups.",
            "Candidate → LLM validate (approve / reject) with reasoning and counter-thesis.",
            "On approve → guardrails check confidence, limits → risk sizes → order.",
            "On reject → no order; event appears in LLM Audit and chart (LLM- marker).",
        ],
        "modes_ru": {
            "validate_only": "Veto — reject LLM блокирует сделку.",
            "advisory": "Advisory — мнение LLM пишется в журнал, ордер может пройти.",
            "disabled": "Выключено — только правила, LLM не вызывается.",
        },
        "modes_en": {
            "validate_only": "Veto — LLM reject blocks the trade.",
            "advisory": "Advisory — LLM opinion is logged; order may still execute.",
            "disabled": "Disabled — rules only, no LLM calls.",
        },
        "when_off_ru": "Стратегия работает как чистый rule-based swing без второго мнения LLM.",
        "when_off_en": "Strategy runs as pure rule-based swing without LLM second opinion.",
        "caution_ru": "Запрос к Ollama на 4h — до нескольких минут; не поднимайте частоту тиков.",
        "caution_en": "Ollama call on 4h may take minutes; do not increase tick frequency.",
    },
    "deepfund_paper": {
        "kind": "swing_validate",
        "supports_assist": True,
        "default_enabled": True,
        "default_mode": "validate_only",
        "default_sample_pct": 0,
        "title_ru": "LLM assist для DeepFund paper",
        "title_en": "LLM assist for DeepFund paper",
        "summary_ru": (
            "Исследовательский рукав: те же validate-принципы, что у swing, с акцентом на честную оценку LLM "
            "на данных после training cutoff."
        ),
        "summary_en": (
            "Research sleeve: same validate pattern as swing, focused on honest LLM eval post training cutoff."
        ),
        "steps_ru": [
            "Rule filter формирует кандидата на 4h.",
            "LLM validate с полным контекстом и новостями.",
            "Результаты идут в журнал и LLM Audit для сравнения с llm_swing.",
        ],
        "steps_en": [
            "Rule filter builds a 4h candidate.",
            "LLM validate with full context and news.",
            "Results go to the journal and LLM Audit for comparison with llm_swing.",
        ],
        "modes_ru": {
            "validate_only": "Veto — стандарт для paper-оценки.",
            "advisory": "Advisory — только логирование мнения.",
            "disabled": "Без LLM — только правила.",
        },
        "modes_en": {
            "validate_only": "Veto — standard for paper eval.",
            "advisory": "Advisory — log opinion only.",
            "disabled": "No LLM — rules only.",
        },
        "when_off_ru": "DeepFund paper без LLM теряет смысл исследования — рекомендуем оставить assist включённым.",
        "when_off_en": "DeepFund paper without LLM loses research value — keep assist enabled.",
        "caution_ru": "Paper-only; не смешивайте с live без отдельной проверки.",
        "caution_en": "Paper-only; do not mix with live without separate review.",
    },
}


def get_create_profile(strategy_id: str) -> dict[str, Any]:
    profile = CREATE_PROFILES.get(strategy_id)
    if not profile:
        return {
            "status": "ok",
            "strategy_id": strategy_id,
            "supports_assist": False,
            "kind": "none",
        }
    return {"status": "ok", "strategy_id": strategy_id, **profile}


def resolve_instance_llm_settings(symbol: str, workflow_name: str) -> dict[str, Any] | None:
    """Per-automation LLM assist from session_config (running instance)."""
    try:
        from crypto_automation_instance_service import find_running_instance

        inst = find_running_instance(symbol=symbol, workflow_name=workflow_name)
    except Exception:
        inst = None
    if not inst:
        return None
    cfg = dict(inst.get("session_config") or {})
    if "llm_assist_enabled" not in cfg:
        return None
    enabled = bool(cfg.get("llm_assist_enabled"))
    mode = str(cfg.get("llm_assist_mode") or "validate_only").strip()
    if mode not in ("disabled", "advisory", "validate_only"):
        mode = "validate_only"
    sample_pct = max(0, min(100, int(cfg.get("llm_assist_sample_pct") or 0)))
    return {"enabled": enabled, "mode": mode, "sample_pct": sample_pct}


def effective_llm_mode(*, symbol: str | None = None, workflow_name: str | None = None) -> str:
    if symbol and workflow_name:
        settings = resolve_instance_llm_settings(symbol, workflow_name)
        if settings is not None:
            if not settings["enabled"]:
                return "disabled"
            mode = settings.get("mode") or "validate_only"
            if mode in ("disabled", "advisory", "validate_only"):
                return mode
    return get_effective_guardrails_llm_mode()


def apply_instance_scalp_llm(
    cfg: dict[str, Any],
    *,
    symbol: str = "",
    workflow_name: str = "",
) -> dict[str, Any]:
    out = apply_scalp_llm_assist(cfg)
    if not symbol or not workflow_name:
        return out
    settings = resolve_instance_llm_settings(symbol, workflow_name)
    if settings is None:
        return out
    if not settings["enabled"]:
        out["llm_enabled"] = False
        out["llm_sample_pct"] = 0
        return out
    pct = max(0, min(100, int(settings.get("sample_pct") or 15)))
    out["llm_enabled"] = pct > 0
    out["llm_sample_pct"] = pct
    return out


def default_llm_assist_for_strategy(strategy_id: str) -> dict[str, Any]:
    profile = CREATE_PROFILES.get(strategy_id) or {}
    if not profile.get("supports_assist"):
        return {"enabled": False, "mode": "disabled", "sample_pct": 0}
    return {
        "enabled": bool(profile.get("default_enabled", False)),
        "mode": str(profile.get("default_mode") or "validate_only"),
        "sample_pct": int(profile.get("default_sample_pct") or 0),
    }
