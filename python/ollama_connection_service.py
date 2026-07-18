"""Runtime Ollama host selection — Docker container vs Windows host vs custom URL."""

from __future__ import annotations

import os
import time
from typing import Any, Literal

from runtime_settings import delete_runtime_value, get_runtime_meta, set_runtime_value

OllamaPreset = Literal["docker", "windows_host", "custom"]

RUNTIME_KEY = "ollama_connection"

PRESETS: dict[str, dict[str, str]] = {
    "docker": {
        "host": "http://ollama:11434",
        "label_ru": "Docker (trading-ollama)",
        "label_en": "Docker (trading-ollama)",
        "hint_ru": "Контейнер в docker compose. По умолчанию CPU.",
        "hint_en": "Container from docker compose. CPU by default.",
    },
    "windows_host": {
        "host": "http://host.docker.internal:11434",
        "label_ru": "Windows Ollama (GPU)",
        "label_en": "Windows Ollama (GPU)",
        "hint_ru": "Ollama.exe на хосте — часто быстрее за счёт GPU.",
        "hint_en": "Native Ollama on Windows host — often faster with GPU.",
    },
    "custom": {
        "host": "",
        "label_ru": "Свой URL",
        "label_en": "Custom URL",
        "hint_ru": "Произвольный OLLAMA_HOST (http://…:11434).",
        "hint_en": "Arbitrary OLLAMA_HOST (http://…:11434).",
    },
}


def _env_default_host() -> str:
    return os.environ.get("OLLAMA_HOST", PRESETS["docker"]["host"]).rstrip("/")


def _parse_runtime() -> dict[str, Any] | None:
    meta = get_runtime_meta(RUNTIME_KEY)
    if not meta:
        return None
    raw = meta.get("value")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            import json

            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def get_effective_ollama_host() -> str:
    """Host used by llm_client and ollama_manager."""
    rt = _parse_runtime()
    if rt:
        preset = str(rt.get("preset") or "").strip()
        if preset == "custom":
            custom = str(rt.get("custom_host") or rt.get("host") or "").strip().rstrip("/")
            if custom:
                return custom
        elif preset in PRESETS and PRESETS[preset]["host"]:
            return PRESETS[preset]["host"].rstrip("/")
        explicit = str(rt.get("host") or "").strip().rstrip("/")
        if explicit:
            return explicit
    return _env_default_host()


def _ping_host(host: str, *, timeout_sec: float = 5.0) -> dict[str, Any]:
    import httpx

    start = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            resp = client.get(f"{host.rstrip('/')}/api/tags")
        latency_ms = int((time.perf_counter() - start) * 1000)
        if resp.status_code != 200:
            return {
                "reachable": False,
                "latency_ms": latency_ms,
                "message": resp.text[:200],
            }
        models = resp.json().get("models") or []
        return {
            "reachable": True,
            "latency_ms": latency_ms,
            "models_count": len(models),
        }
    except Exception as exc:
        return {
            "reachable": False,
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "message": str(exc)[:200],
        }


def get_ollama_connection_settings(*, ping: bool = True) -> dict[str, Any]:
    rt = _parse_runtime() or {}
    preset = str(rt.get("preset") or "env")
    env_host = _env_default_host()
    effective = get_effective_ollama_host()

    if preset not in PRESETS and not rt:
        preset = _infer_preset_from_host(env_host)

    custom_host = str(rt.get("custom_host") or rt.get("host") or "").strip() or None
    meta = get_runtime_meta(RUNTIME_KEY) or {}

    out: dict[str, Any] = {
        "status": "ok",
        "preset": preset if preset in PRESETS else "custom",
        "custom_host": custom_host,
        "env_default_host": env_host,
        "effective_host": effective,
        "runtime_override": bool(rt),
        "updated_at": meta.get("updated_at"),
        "updated_by": meta.get("updated_by"),
        "presets": [
            {
                "id": pid,
                "host": pdata["host"] or None,
                "label_ru": pdata["label_ru"],
                "label_en": pdata["label_en"],
                "hint_ru": pdata["hint_ru"],
                "hint_en": pdata["hint_en"],
            }
            for pid, pdata in PRESETS.items()
        ],
    }
    if ping:
        out["ping"] = _ping_host(effective)
    return out


def _infer_preset_from_host(host: str) -> str:
    h = host.rstrip("/").lower()
    if h == PRESETS["docker"]["host"].lower():
        return "docker"
    if h == PRESETS["windows_host"]["host"].lower():
        return "windows_host"
    return "custom"


def set_ollama_connection(
    *,
    preset: str,
    custom_host: str | None = None,
    operator: str = "web:operator",
) -> dict[str, Any]:
    preset = str(preset or "").strip()
    if preset not in PRESETS:
        raise ValueError(f"invalid_ollama_preset: {preset}")

    payload: dict[str, Any] = {"preset": preset}
    if preset == "custom":
        url = str(custom_host or "").strip().rstrip("/")
        if not url.startswith("http://") and not url.startswith("https://"):
            raise ValueError("custom_host_must_be_http_url")
        payload["custom_host"] = url
        payload["host"] = url

    set_runtime_value(RUNTIME_KEY, payload, updated_by=operator)
    result = get_ollama_connection_settings(ping=True)
    try:
        from activity_feed_service import log_system_activity

        log_system_activity(
            f"Ollama host → {result['effective_host']} (preset={preset})",
            category="system",
            level="info",
            payload=payload,
        )
    except Exception:
        pass
    return result


def clear_ollama_connection(*, operator: str = "web:operator") -> dict[str, Any]:
    delete_runtime_value(RUNTIME_KEY)
    return get_ollama_connection_settings(ping=True)
