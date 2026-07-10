"""Investment strategy catalog and runtime selection per market."""

from __future__ import annotations

from typing import Any, Literal

from config_loader import load_config
from effective_config import get_config_effective
from runtime_settings import get_runtime_value, set_runtime_value

Market = Literal["crypto", "securities"]


def _workflow_for_mode(config_name: str, *, dry_run: str, paper: str) -> str:
    mode = get_config_effective(config_name).get("mode", "dry_run")
    return paper if str(mode) != "dry_run" else dry_run


def _runtime_key(market: str) -> str:
    return f"strategy_{market}"


def symbols_for_workflow(workflow: str) -> list[str]:
    try:
        from workflow_universe_service import enabled_symbols_for_workflow

        enabled = enabled_symbols_for_workflow(workflow)
        if enabled:
            return enabled
    except Exception:
        pass
    return []


def _symbols_label(symbols: list[str], *, market: str, max_show: int = 6) -> str:
    if not symbols:
        return "—"
    if market == "crypto":
        labels = [str(s).replace("USDT", "") for s in symbols[:max_show]]
    else:
        labels = [str(s) for s in symbols[:max_show]]
    text = ", ".join(labels)
    if len(symbols) > max_show:
        text += f" (+{len(symbols) - max_show})"
    return text


def _crypto_strategy_description(pairs: list[str]) -> tuple[str, str]:
    label = _symbols_label(pairs, market="crypto")
    ru = (
        f"Ищет возможности на активных USDT-парах: {label}. "
        "Список пар настраивается в «Котировки workflow»."
    )
    en = (
        f"Looks for setups on active USDT pairs: {label}. "
        "Edit the pair list in «Workflow quotes»."
    )
    return ru, en


def _securities_strategy_description(universe: list[str]) -> tuple[str, str]:
    label = _symbols_label(universe, market="securities")
    ru = (
        f"Торговля акциями из активного списка ({label}): фильтр по индикаторам, затем LLM. "
        "Список тикеров — в «Котировки workflow». Сделки в часы сессии MOEX."
    )
    en = (
        f"Trades stocks from the active watchlist ({label}): indicator filter, then LLM. "
        "Tickers are managed in «Workflow quotes». MOEX session hours only."
    )
    return ru, en


def get_active_strategy_id(market: str) -> str:
    runtime = get_runtime_value(_runtime_key(market))
    if runtime:
        return str(runtime)
    if market == "securities":
        yaml_mode = str(load_config("securities_config").get("active_mode", "swing_signals"))
        if yaml_mode in ("swing_signals", "index_dca", "factor_sleeve", "bond_ladder"):
            return yaml_mode
        return "swing_signals"
    if market == "crypto":
        return str(load_config("crypto_config").get("active_strategy", "llm_swing"))
    return ""


def _securities_catalog() -> dict[str, dict[str, Any]]:
    sec = get_config_effective("securities_config")
    swing = sec.get("swing_signals", {})
    dca = sec.get("index_dca", {})
    factor_cfg = load_config("factor_sleeve")
    bond_cfg = load_config("bond_ladder")

    swing_wf = _workflow_for_mode(
        "securities_config",
        dry_run="securities-swing-dry-run",
        paper="securities-swing-paper",
    )
    universe = symbols_for_workflow(swing_wf) or list(swing.get("universe", ["SBER", "GAZP", "LKOH"]))
    desc_ru, desc_en = _securities_strategy_description(universe)
    factor_universe = list(factor_cfg.get("universe", universe))
    bond_tickers = [str(r.get("ticker")) for r in bond_cfg.get("rungs", []) if r.get("ticker")]

    return {
        "swing_signals": {
            "id": "swing_signals",
            "label": "Swing + LLM",
            "description": desc_ru,
            "description_en": desc_en,
            "rationale_ru": (
                "Базовая LLM-стратегия для акций MOEX: индикаторы отсекают шум, модель проверяет контекст. "
                "Подходит для paper/live-теста validate-only режима."
            ),
            "rationale_en": (
                "Core MOEX LLM swing: indicators filter noise, model validates context. "
                "Best for paper/live validate-only testing."
            ),
            "paper_ref": "https://arxiv.org/abs/2505.07078",
            "workflow": swing_wf,
            "symbols": universe,
            "chart_default": universe[0] if universe else "SBER",
            "chart_interval": "1d",
            "uses_llm": True,
            "kind": "trading",
            "chart_overlays": {
                "price": ["ema50", "ema200"],
                "panels": [
                    {"id": "rsi", "series": ["rsi_14"], "levels": ["rsi_oversold", "rsi_overbought"]},
                    {"id": "macd", "series": ["macd", "macd_signal"], "histogram": "macd_histogram"},
                ],
            },
        },
        "index_dca": {
            "id": "index_dca",
            "label": "Индекс DCA (TMOS)",
            "description": (
                f"Ежемесячная покупка {dca.get('ticker', 'TMOS')} на фиксированную сумму без LLM. "
                "Пассивное накопление, минимум операций."
            ),
            "description_en": (
                f"Monthly {dca.get('ticker', 'TMOS')} purchase for a fixed RUB amount — no LLM. "
                "Passive accumulation with minimal turnover."
            ),
            "rationale_ru": (
                "Из исследований пассивного инвестирования (mega-firms, индексные притоки): "
                "для долгого горизонта DCA в широкий индекс часто устойчивее активного тайминга. "
                "LLM здесь не нужна — меньше точек отказа и нагрузки на Ollama."
            ),
            "rationale_en": (
                "From passive investing research: DCA into a broad index is often more robust than active timing. "
                "No LLM — fewer failure modes and no Ollama load."
            ),
            "paper_ref": "https://www.fmg.ac.uk/sites/default/files/2024-04/DP868-revised.pdf",
            "workflow": "securities-dca-sandbox",
            "symbols": [str(dca.get("ticker", "TMOS"))],
            "chart_default": str(dca.get("ticker", "TMOS")),
            "chart_interval": "1d",
            "uses_llm": False,
            "kind": "allocation",
        },
        "factor_sleeve": {
            "id": "factor_sleeve",
            "label": "Factor sleeve (momentum)",
            "description": (
                f"Отдельный рукав: momentum по {len(factor_universe)} тикерам MOEX, "
                f"ребаланс top-{factor_cfg.get('top_n', 3)} без LLM."
            ),
            "description_en": (
                f"Separate sleeve: momentum across {len(factor_universe)} MOEX tickers, "
                f"rebalance to top-{factor_cfg.get('top_n', 3)} — no LLM."
            ),
            "rationale_ru": (
                "По работам о факторной предсказуемости на MOEX: momentum/value работают на горизонте недель/месяцев, "
                "а не на intraday swing. Отдельный flow не смешивает факторную логику с LLM-swing и снижает overfitting."
            ),
            "rationale_en": (
                "MOEX factor research: momentum works on weeks/months, not intraday swing. "
                "Separate flow avoids mixing factor logic with LLM swing."
            ),
            "paper_ref": "https://doi.org/10.17323/j.jcfr.2073-0438.19.2.2025.67-81",
            "workflow": "securities-factor-sleeve",
            "symbols": factor_universe,
            "chart_default": factor_universe[0] if factor_universe else "SBER",
            "chart_interval": "1d",
            "uses_llm": False,
            "kind": "allocation",
        },
        "bond_ladder": {
            "id": "bond_ladder",
            "label": "Bond ladder (ОФЗ)",
            "description": (
                "Мониторинг лестницы ОФЗ: дюрация, дрейф и чувствительность к шоку ключевой ставки. "
                "Не торгует по LLM — только алерты и план ребаланса."
            ),
            "description_en": (
                "OFZ bond ladder monitor: duration, drift, and key-rate shock sensitivity. "
                "No LLM trading — alerts and rebalance plan only."
            ),
            "rationale_ru": (
                "Ivashchenko & Kosowski (2024): ёмкость облигационных стратегий ограничена; "
                "рознице важнее контроль дюрации и ребаланс по ступеням, чем «умный» тайминг. "
                "Flow отделён от акций и крипто."
            ),
            "rationale_en": (
                "Bond strategy capacity is limited; retail should control duration and ladder rungs, not LLM timing."
            ),
            "paper_ref": "https://doi.org/10.1080/0015198X.2024.2360390",
            "workflow": "bond-ladder-flow",
            "symbols": bond_tickers or ["SU26238RMFS4"],
            "chart_default": bond_tickers[0] if bond_tickers else "SU26238RMFS4",
            "chart_interval": "1d",
            "uses_llm": False,
            "kind": "fixed_income",
        },
    }


def _crypto_catalog() -> dict[str, dict[str, Any]]:
    crypto = get_config_effective("crypto_config")
    deep_cfg = load_config("deepfund_config")
    wf = _workflow_for_mode(
        "crypto_config",
        dry_run="crypto-signal-dry-run",
        paper="crypto-signal-paper",
    )
    pairs = symbols_for_workflow(wf) or list(crypto.get("pairs", ["BTCUSDT", "ETHUSDT"]))
    desc_ru, desc_en = _crypto_strategy_description(pairs)
    deep_pairs = list(deep_cfg.get("symbols", pairs))
    scalp_cfg = load_config("crypto_scalp_hybrid")
    scalp_pairs = list(scalp_cfg.get("pairs", pairs))
    scalp_wf = str(scalp_cfg.get("paper", {}).get("workflow_name", "crypto-scalp-hybrid-paper"))
    scalp_symbols = symbols_for_workflow(scalp_wf) or scalp_pairs
    return {
        "llm_swing": {
            "id": "llm_swing",
            "label": "LLM swing (4h)",
            "description": desc_ru,
            "description_en": desc_en,
            "rationale_ru": (
                "Основной crypto-flow: правила генерируют кандидата, LLM только validate-only (FINSABER/DeepFund). "
                "Интервал 4h — компромисс между шумом и нагрузкой на Ollama (~3 мин на запрос)."
            ),
            "rationale_en": (
                "Main crypto flow: rules propose, LLM validate-only. 4h interval balances noise vs Ollama load."
            ),
            "paper_ref": "https://arxiv.org/abs/2505.07078",
            "workflow": _workflow_for_mode(
                "crypto_config",
                dry_run="crypto-signal-dry-run",
                paper="crypto-signal-paper",
            ),
            "symbols": pairs,
            "chart_default": pairs[0] if pairs else "BTCUSDT",
            "chart_interval": crypto.get("timeframe", "4h"),
            "uses_llm": True,
            "kind": "trading",
            "chart_overlays": {
                "price": ["ema50", "ema200"],
                "panels": [
                    {"id": "rsi", "series": ["rsi_14"], "levels": ["rsi_oversold", "rsi_overbought"]},
                    {"id": "macd", "series": ["macd", "macd_signal"], "histogram": "macd_histogram"},
                ],
            },
        },
        "deepfund_paper": {
            "id": "deepfund_paper",
            "label": "DeepFund paper",
            "description": (
                f"Параллельный paper-тест на {', '.join(deep_pairs)} с данными после cutoff "
                f"{deep_cfg.get('training_cutoff_date', '2024-09-01')} — честная оценка LLM."
            ),
            "description_en": (
                f"Parallel paper test on {', '.join(deep_pairs)} with post-cutoff data "
                f"{deep_cfg.get('training_cutoff_date', '2024-09-01')} — honest LLM eval."
            ),
            "rationale_ru": (
                "По DeepFund (2025): live-paper на данных после обучения модели отделяет «подгонку под историю» "
                "от реальной полезности LLM. Не заменяет llm_swing — дополняет как исследовательский рукав."
            ),
            "rationale_en": (
                "DeepFund pattern: post-training-cutoff paper isolates real LLM value from backtest overfit."
            ),
            "paper_ref": "https://arxiv.org/abs/2505.11065",
            "workflow": "deepfund-live-paper",
            "symbols": deep_pairs,
            "chart_default": deep_pairs[0] if deep_pairs else "BTCUSDT",
            "chart_interval": crypto.get("timeframe", "4h"),
            "uses_llm": True,
            "kind": "research",
        },
        "crypto_scalp_hybrid": {
            "id": "crypto_scalp_hybrid",
            "label": "Scalp hybrid 5m",
            "description": (
                f"5m скальп: ~80% сделок по скрипту, ~{scalp_cfg.get('llm_sample_pct', 20)}% пограничных — "
                f"быстрая LLM ({scalp_cfg.get('ollama_model_fast', 'qwen3.5:4b')}). Пары: "
                f"{_symbols_label(scalp_symbols, market='crypto')}."
            ),
            "description_en": (
                f"5m scalp: ~80% script trades, ~{scalp_cfg.get('llm_sample_pct', 20)}% borderline via fast LLM "
                f"({scalp_cfg.get('ollama_model_fast', 'qwen3.5:4b')})."
            ),
            "rationale_ru": (
                "LLM на каждом 5m тике не тянет железо (~3 мин на 9B). Гибрид: чёткие импульсы — rules_engine, "
                "сомнительные (ambiguity 0.35–0.72) — только в 20% слотов qwen3.5:4b (think=false). validate_only + retail_guard."
            ),
            "rationale_en": (
                "LLM every 5m bar is too slow on 9B. Hybrid routes clear impulses to script; borderline cases hit fast LLM in 20% slots."
            ),
            "paper_ref": "https://arxiv.org/abs/2505.07078",
            "workflow": scalp_wf,
            "symbols": scalp_symbols,
            "chart_default": scalp_symbols[0] if scalp_symbols else "BTCUSDT",
            "chart_interval": str(scalp_cfg.get("timeframe", "5m")),
            "uses_llm": True,
            "kind": "trading",
            "chart_overlays": {
                "price": ["ema50"],
                "panels": [
                    {"id": "rsi", "series": ["rsi_14"], "levels": ["rsi_oversold", "rsi_overbought"]},
                    {"id": "macd", "series": ["macd_histogram"], "histogram": "macd_histogram"},
                ],
            },
        },
    }


def get_strategy_catalog(market: str) -> dict[str, Any]:
    if market == "securities":
        strategies = _securities_catalog()
    elif market == "crypto":
        strategies = _crypto_catalog()
    else:
        raise ValueError(f"unknown market: {market}")

    active = get_active_strategy_id(market)
    if active not in strategies:
        active = next(iter(strategies))

    return {
        "market": market,
        "active": active,
        "strategies": list(strategies.values()),
    }


def get_strategy_state(market: str) -> dict[str, Any]:
    catalog = get_strategy_catalog(market)
    active_id = catalog["active"]
    strategies = {s["id"]: s for s in catalog["strategies"]}
    active = strategies.get(active_id, catalog["strategies"][0])
    return {
        "market": market,
        "active": active_id,
        "strategy": active,
        "strategies": catalog["strategies"],
    }


def set_active_strategy(
    market: str,
    strategy_id: str,
    *,
    operator: str = "web",
) -> dict[str, Any]:
    catalog = get_strategy_catalog(market)
    valid = {s["id"] for s in catalog["strategies"]}
    if strategy_id not in valid:
        raise ValueError(f"unknown strategy: {strategy_id}")

    set_runtime_value(_runtime_key(market), strategy_id, updated_by=operator)

    try:
        from activity_feed_service import log_system_activity

        label = next(s["label"] for s in catalog["strategies"] if s["id"] == strategy_id)
        log_system_activity(
            f"Стратегия {market}: {label}",
            category=market,
            level="info",
        )
    except Exception:
        pass

    try:
        from automation_control_service import sync_market_workflows

        sync = sync_market_workflows(market)
        state = get_strategy_state(market)
        state["workflow_sync"] = {
            "primary_workflow": sync.get("primary_workflow"),
            "workflows": sync.get("workflows", []),
            "active_workflows": sync.get("active_workflows", []),
        }
        return state
    except Exception:
        pass

    return get_strategy_state(market)


def symbols_for_market(market: str) -> list[str]:
    state = get_strategy_state(market)
    wf = str(state.get("strategy", {}).get("workflow", ""))
    if wf:
        enabled = symbols_for_workflow(wf)
        if enabled:
            return enabled
    return list(state["strategy"].get("symbols", []))
