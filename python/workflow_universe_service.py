"""Per-workflow tradable asset lists (watchlist + enabled flags)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal

from config_loader import load_config
from effective_config import get_config_effective
from runtime_settings import get_runtime_value, set_runtime_value

Market = Literal["crypto", "securities"]
Source = Literal["yaml", "manual", "llm"]

WORKFLOW_REGISTRY: dict[str, dict[str, Any]] = {
    "crypto-signal-dry-run": {"market": "crypto", "label": "Крипто: сигналы (без сделок)"},
    "crypto-signal-paper": {"market": "crypto", "label": "Крипто: автоторговля (демо)"},
    "crypto-scalp-hybrid-dry-run": {"market": "crypto", "label": "Крипто: scalp hybrid (сигналы)"},
    "crypto-scalp-hybrid-paper": {"market": "crypto", "label": "Крипто: scalp hybrid (paper)"},
    "crypto-monitor-testnet": {"market": "crypto", "label": "Крипто: мониторинг демо-счёта"},
    "securities-swing-dry-run": {"market": "securities", "label": "MOEX: сигналы swing (без сделок)"},
    "securities-swing-paper": {"market": "securities", "label": "MOEX: swing (paper)"},
    "securities-dca-sandbox": {"market": "securities", "label": "MOEX: DCA (sandbox)"},
    "deepfund-live-paper": {"market": "crypto", "label": "DeepFund: live-paper (post-cutoff)"},
    "securities-factor-sleeve": {"market": "securities", "label": "MOEX: factor sleeve (weekly)"},
    "bond-ladder-flow": {"market": "securities", "label": "MOEX: bond ladder monitor"},
    "neuratrade-harness": {"market": "crypto", "label": "NeuraTrade: Ollama harness"},
    "regulatory-monitor": {"market": "shared", "label": "ESRB/FSB/CBR regulatory scan"},
    "papers-monitor-weekly": {"market": "shared", "label": "Research papers discovery"},
}

# Dry-run and paper variants share the same tradable universe for one strategy.
_UNIVERSE_SIBLING_WORKFLOWS: dict[str, list[str]] = {
    "crypto-signal-dry-run": ["crypto-signal-paper"],
    "crypto-signal-paper": ["crypto-signal-dry-run"],
    "crypto-scalp-hybrid-dry-run": ["crypto-scalp-hybrid-paper"],
    "crypto-scalp-hybrid-paper": ["crypto-scalp-hybrid-dry-run"],
    "securities-swing-dry-run": ["securities-swing-paper"],
    "securities-swing-paper": ["securities-swing-dry-run"],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _runtime_key(workflow: str) -> str:
    return f"workflow_universe:{workflow}"


def workflow_market(workflow: str) -> str:
    meta = WORKFLOW_REGISTRY.get(workflow)
    if not meta:
        raise ValueError(f"unknown_workflow: {workflow}")
    return str(meta["market"])


def _yaml_defaults(workflow: str) -> list[dict[str, Any]]:
    market = workflow_market(workflow)
    if market == "shared":
        return []
    items: list[dict[str, Any]] = []
    if market == "crypto":
        if workflow.startswith("crypto-scalp-hybrid"):
            pairs = list(load_config("crypto_scalp_hybrid").get("pairs", ["BTCUSDT", "ETHUSDT"]))
        else:
            pairs = list(get_config_effective("crypto_config").get("pairs", ["BTCUSDT", "ETHUSDT"]))
        for sym in pairs:
            items.append(
                {
                    "symbol": str(sym).upper(),
                    "enabled": True,
                    "source": "yaml",
                    "added_at": None,
                }
            )
    elif workflow == "securities-dca-sandbox":
        ticker = str(
            get_config_effective("securities_config").get("index_dca", {}).get("ticker", "TMOS")
        ).upper()
        items.append({"symbol": ticker, "enabled": True, "source": "yaml", "added_at": None})
    else:
        universe = list(
            get_config_effective("securities_config")
            .get("swing_signals", {})
            .get("universe", ["SBER", "GAZP", "LKOH"])
        )
        for sym in universe:
            items.append(
                {
                    "symbol": str(sym).upper(),
                    "enabled": True,
                    "source": "yaml",
                    "added_at": None,
                }
            )
    return items


def _normalize_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for raw in items:
        symbol = str(raw.get("symbol", "")).strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        out.append(
            {
                "symbol": symbol,
                "enabled": bool(raw.get("enabled", True)),
                "source": str(raw.get("source") or "manual"),
                "added_at": raw.get("added_at"),
            }
        )
    return out


def get_workflow_universe(workflow: str) -> dict[str, Any]:
    workflow_market(workflow)
    stored = get_runtime_value(_runtime_key(workflow))
    if isinstance(stored, dict) and isinstance(stored.get("items"), list):
        items = _normalize_items(stored["items"])
        runtime_override = True
    else:
        items = _yaml_defaults(workflow)
        runtime_override = False

    enabled = [i["symbol"] for i in items if i.get("enabled")]
    return {
        "workflow": workflow,
        "market": workflow_market(workflow),
        "runtime_override": runtime_override,
        "items": items,
        "enabled_symbols": enabled,
        "updated_at": (stored or {}).get("updated_at") if isinstance(stored, dict) else None,
    }


def enabled_symbols_for_workflow(workflow: str) -> list[str]:
    return list(get_workflow_universe(workflow).get("enabled_symbols", []))


def all_enabled_symbols() -> list[str]:
    symbols: set[str] = set()
    for workflow in WORKFLOW_REGISTRY:
        symbols.update(enabled_symbols_for_workflow(workflow))
    return sorted(symbols)


def _mirror_universe_siblings(
    workflow: str,
    items: list[dict[str, Any]],
    *,
    operator: str,
) -> None:
    siblings = _UNIVERSE_SIBLING_WORKFLOWS.get(workflow, [])
    if not siblings:
        return
    now = _utc_now()
    for sibling in siblings:
        payload = {
            "workflow": sibling,
            "market": workflow_market(sibling),
            "items": items,
            "updated_at": now,
            "updated_by": operator,
            "mirrored_from": workflow,
        }
        set_runtime_value(_runtime_key(sibling), payload, updated_by=operator)


def save_workflow_universe(
    workflow: str,
    items: list[dict[str, Any]],
    *,
    operator: str = "web",
) -> dict[str, Any]:
    workflow_market(workflow)
    normalized = _normalize_items(items)
    payload = {
        "workflow": workflow,
        "market": workflow_market(workflow),
        "items": normalized,
        "updated_at": _utc_now(),
        "updated_by": operator,
    }
    set_runtime_value(_runtime_key(workflow), payload, updated_by=operator)
    _mirror_universe_siblings(workflow, normalized, operator=operator)
    _log_activity(workflow, f"Universe обновлён ({len(normalized)} активов)", operator)
    return get_workflow_universe(workflow)


def add_symbols_to_workflow(
    workflow: str,
    symbols: list[str],
    *,
    source: Source = "manual",
    enabled: bool = True,
    operator: str = "web",
) -> dict[str, Any]:
    state = get_workflow_universe(workflow)
    by_symbol = {i["symbol"]: dict(i) for i in state["items"]}
    now = _utc_now()
    for raw in symbols:
        sym = str(raw).strip().upper()
        if not sym:
            continue
        if sym in by_symbol:
            by_symbol[sym]["enabled"] = enabled or by_symbol[sym].get("enabled", True)
            continue
        by_symbol[sym] = {
            "symbol": sym,
            "enabled": enabled,
            "source": source,
            "added_at": now,
        }
    return save_workflow_universe(workflow, list(by_symbol.values()), operator=operator)


def set_symbol_enabled(
    workflow: str,
    symbol: str,
    enabled: bool,
    *,
    operator: str = "web",
) -> dict[str, Any]:
    state = get_workflow_universe(workflow)
    sym = symbol.strip().upper()
    found = False
    items: list[dict[str, Any]] = []
    for item in state["items"]:
        row = dict(item)
        if row["symbol"] == sym:
            row["enabled"] = enabled
            found = True
        items.append(row)
    if not found:
        raise ValueError(f"symbol_not_in_universe: {sym}")
    return save_workflow_universe(workflow, items, operator=operator)


def remove_symbol_from_workflow(
    workflow: str,
    symbol: str,
    *,
    operator: str = "web",
) -> dict[str, Any]:
    sym = symbol.strip().upper()
    state = get_workflow_universe(workflow)
    items = [i for i in state["items"] if i["symbol"] != sym]
    if len(items) == len(state["items"]):
        raise ValueError(f"symbol_not_in_universe: {sym}")
    return save_workflow_universe(workflow, items, operator=operator)


def apply_llm_universe_suggestion(
    workflow: str,
    symbols: list[str],
    *,
    mode: Literal["replace", "merge"] = "merge",
    disable_others: bool = False,
    operator: str = "web",
) -> dict[str, Any]:
    suggested = [str(s).strip().upper() for s in symbols if str(s).strip()]
    suggested_set = set(suggested)
    now = _utc_now()

    if mode == "replace":
        items = [
            {"symbol": sym, "enabled": True, "source": "llm", "added_at": now}
            for sym in suggested
        ]
        return save_workflow_universe(workflow, items, operator=operator)

    state = get_workflow_universe(workflow)
    by_symbol = {i["symbol"]: dict(i) for i in state["items"]}
    for sym in suggested:
        if sym in by_symbol:
            by_symbol[sym]["enabled"] = True
            by_symbol[sym]["source"] = "llm"
        else:
            by_symbol[sym] = {"symbol": sym, "enabled": True, "source": "llm", "added_at": now}

    if disable_others:
        for sym, row in by_symbol.items():
            if sym not in suggested_set:
                row["enabled"] = False

    return save_workflow_universe(workflow, list(by_symbol.values()), operator=operator)


def reset_workflow_universe(workflow: str, *, operator: str = "web") -> dict[str, Any]:
    from runtime_settings import delete_runtime_value

    delete_runtime_value(_runtime_key(workflow))
    _log_activity(workflow, "Universe сброшен к YAML", operator)
    return get_workflow_universe(workflow)


def _log_activity(workflow: str, message: str, operator: str) -> None:
    try:
        from activity_feed_service import log_system_activity

        market = workflow_market(workflow)
        log_system_activity(
            f"{workflow}: {message}",
            category=market,
            level="info",
            payload={"workflow": workflow, "operator": operator},
        )
    except Exception:
        pass


def _fallback_universe_suggestion(
    workflow: str,
    *,
    hint: str | None = None,
    max_symbols: int = 8,
    llm_error: str | None = None,
) -> dict[str, Any]:
    """Catalog/YAML list when local LLM is slow or unavailable."""
    from asset_catalog_service import search_assets

    market = workflow_market(workflow)
    symbols: list[str] = []
    if hint and hint.strip():
        hits = search_assets(market, hint.strip(), limit=max_symbols)
        symbols = [str(h["symbol"]).upper() for h in hits if h.get("symbol")]

    if not symbols:
        symbols = [d["symbol"] for d in _yaml_defaults(workflow)]

    if market == "crypto" and len(symbols) < max_symbols:
        from asset_catalog_service import _crypto_catalog

        for sym in _crypto_catalog():
            if sym not in symbols:
                symbols.append(sym)
            if len(symbols) >= max_symbols:
                break

    symbols = symbols[:max_symbols]
    reason = "Базовый список из каталога и YAML"
    if llm_error:
        reason = f"{reason} (LLM: {llm_error})"
    return {
        "status": "ok",
        "symbols": symbols,
        "rationale": reason,
        "fallback": True,
        "model": None,
        "llm_error": llm_error,
    }


def suggest_universe_with_llm(
    workflow: str,
    *,
    hint: str | None = None,
    max_symbols: int = 8,
) -> dict[str, Any]:
    """Ask local LLM for a symbol list; returns parsed symbols + raw response."""
    import time

    import httpx

    from config_loader import load_prompt_body
    from llm_client import list_ollama_models, ollama_host
    from market_llm_config import get_market_ollama_model

    market = workflow_market(workflow)
    model = get_market_ollama_model(market)
    # Short JSON list — do not inherit signal-validation token budget (4096+).
    timeout_sec = 90.0
    num_predict = 256

    ollama_ping = list_ollama_models()
    if ollama_ping.get("status") != "ok":
        return {
            "status": "error",
            "message": f"ollama_unavailable: {ollama_ping.get('message', 'no response')}",
            "model": model,
        }
    available = {m.get("name", "") for m in ollama_ping.get("models", [])}
    if model not in available and f"{model}:latest" not in available:
        names = ", ".join(sorted(available)[:6]) or "—"
        return {
            "status": "error",
            "message": f"ollama_model_missing: {model} (available: {names})",
            "model": model,
        }

    current = get_workflow_universe(workflow)
    enabled = current.get("enabled_symbols") or []
    catalog_hint = (
        "Crypto USDT pairs (examples): BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT."
        if market == "crypto"
        else "MOEX tickers (examples): SBER, GAZP, LKOH, GMKN, YNDX, TMOS."
    )

    system_raw = load_prompt_body("universe_suggest_v1.md")
    if system_raw.startswith("---"):
        parts = system_raw.split("---", 2)
        system_prompt = parts[2].strip() if len(parts) >= 3 else system_raw
    else:
        system_prompt = system_raw

    user_content = (
        f"Market: {market}\n"
        f"Workflow: {workflow}\n"
        f"Max symbols: {max_symbols}\n"
        f"Current enabled: {', '.join(enabled) or '(none)'}\n"
        f"{catalog_hint}\n"
        "Reply with compact JSON only (no reasoning text).\n"
    )
    if hint:
        user_content += f"Operator hint: {hint.strip()}\n"

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "format": "json",
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.2,
            "num_predict": num_predict,
        },
    }

    start = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            resp = client.post(f"{ollama_host()}/api/chat", json=payload)
    except httpx.TimeoutException:
        return {
            "status": "error",
            "message": (
                f"ollama_timeout: модель {model} не ответила за {int(timeout_sec)} с. "
                "Проверьте Ollama и попробуйте короче подсказку."
            ),
            "model": model,
            "latency_ms": int((time.perf_counter() - start) * 1000),
        }
    except httpx.RequestError as exc:
        return {
            "status": "error",
            "message": f"ollama_connection_error: {exc}",
            "model": model,
            "latency_ms": int((time.perf_counter() - start) * 1000),
        }

    latency_ms = int((time.perf_counter() - start) * 1000)
    if resp.status_code != 200:
        return {
            "status": "error",
            "message": f"ollama_http_{resp.status_code}: {resp.text[:300]}",
            "model": model,
            "latency_ms": latency_ms,
        }

    content = ""
    try:
        content = resp.json().get("message", {}).get("content", "")
        parsed = _parse_universe_llm_json(content)
    except Exception as exc:
        return {
            "status": "error",
            "message": f"llm_parse_error: {exc}",
            "raw": content[:500],
            "model": model,
            "latency_ms": latency_ms,
        }

    symbols_raw = parsed.get("symbols") or parsed.get("pairs") or parsed.get("tickers") or []
    symbols = [str(s).strip().upper() for s in symbols_raw if str(s).strip()][:max_symbols]
    if not symbols:
        return {
            "status": "error",
            "message": "llm_empty_symbols: модель вернула пустой список",
            "raw": parsed,
            "model": model,
            "latency_ms": latency_ms,
        }
    return {
        "status": "ok",
        "model": model,
        "symbols": symbols,
        "rationale": parsed.get("rationale") or parsed.get("summary") or "",
        "raw": parsed,
        "latency_ms": latency_ms,
    }


def _parse_universe_llm_json(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    if not text:
        raise ValueError("empty_response")
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        parsed = json.loads(text[start : end + 1])
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("invalid_json")
