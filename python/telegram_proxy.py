"""Telegram proxy selection with health probing."""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org"
_lock = threading.Lock()
_active_proxy: str | None = None
_active_checked_at: float = 0.0
_failed_proxies: dict[str, float] = {}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _probe_timeout() -> float:
    try:
        return float(os.environ.get("TELEGRAM_PROXY_PROBE_TIMEOUT_SEC", "8"))
    except ValueError:
        return 8.0


def _reprobe_interval() -> float:
    try:
        return float(os.environ.get("TELEGRAM_PROXY_REPROBE_SEC", "300"))
    except ValueError:
        return 300.0


def _failed_ttl() -> float:
    try:
        return float(os.environ.get("TELEGRAM_PROXY_FAILED_TTL_SEC", "120"))
    except ValueError:
        return 120.0


def _awesome_vpn_enabled() -> bool:
    return _env_bool("TELEGRAM_AWESOME_VPN_ENABLED", True)


def _gateway_proxy_url() -> str | None:
    if not _awesome_vpn_enabled():
        return None
    return os.environ.get(
        "TELEGRAM_PROXY_GATEWAY",
        "socks5://proxy-gateway:17890",
    ).strip() or None


def _load_awesome_vpn_direct_proxies() -> list[str]:
    if not _awesome_vpn_enabled() or _gateway_proxy_url():
        return []
    try:
        from proxy_gateway.awesome_vpn import fetch_clash_direct_proxies

        return fetch_clash_direct_proxies()
    except Exception as exc:
        logger.warning("awesome-vpn clash direct proxies: %s", exc)
        return []


def normalize_proxy_url(raw: str) -> str | None:
    value = raw.strip()
    if not value or value.startswith("#"):
        return None
    if "://" in value:
        return value
    # host:port:user:pass
    parts = value.split(":")
    if len(parts) == 2:
        return f"socks5://{parts[0]}:{parts[1]}"
    if len(parts) == 4:
        host, port, user, password = parts
        auth = f"{quote(user)}:{quote(password)}@"
        return f"socks5://{auth}{host}:{port}"
    return None


def _split_proxy_blob(blob: str) -> list[str]:
    items: list[str] = []
    for chunk in re.split(r"[\n,;]+", blob):
        normalized = normalize_proxy_url(chunk)
        if normalized:
            items.append(normalized)
    return items


def load_proxy_candidates() -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def add_many(urls: list[str]) -> None:
        for url in urls:
            if url not in seen:
                seen.add(url)
                ordered.append(url)

    single = os.environ.get("TELEGRAM_PROXY", "").strip()
    if single:
        normalized = normalize_proxy_url(single)
        if normalized:
            add_many([normalized])

    list_raw = os.environ.get("TELEGRAM_PROXY_LIST", "").strip()
    if list_raw:
        add_many(_split_proxy_blob(list_raw))

    file_path = os.environ.get("TELEGRAM_PROXY_FILE", "").strip()
    if file_path and os.path.isfile(file_path):
        try:
            content = open(file_path, encoding="utf-8").read()
            add_many(_split_proxy_blob(content))
        except OSError as exc:
            logger.warning("Cannot read TELEGRAM_PROXY_FILE %s: %s", file_path, exc)

    fetch_url = os.environ.get("TELEGRAM_PROXY_FETCH_URL", "").strip()
    if fetch_url:
        try:
            with httpx.Client(timeout=_probe_timeout()) as client:
                resp = client.get(fetch_url)
            if resp.status_code == 200:
                add_many(_split_proxy_blob(resp.text))
        except httpx.HTTPError as exc:
            logger.warning("Cannot fetch TELEGRAM_PROXY_FETCH_URL: %s", exc)

    add_many(_load_awesome_vpn_direct_proxies())

    gateway = _gateway_proxy_url()
    if gateway:
        add_many([gateway])

    return ordered


def _probe_timeout_for(proxy_url: str | None = None) -> float:
    base = _probe_timeout()
    gateway = _gateway_proxy_url()
    if gateway and proxy_url == gateway:
        try:
            return max(base, float(os.environ.get("TELEGRAM_GATEWAY_PROBE_TIMEOUT_SEC", "60")))
        except ValueError:
            return max(base, 60.0)
    return base


def probe_proxy(proxy_url: str | None, *, bot_token: str | None = None) -> bool:
    if not proxy_url:
        return probe_direct(bot_token=bot_token)

    timeout = _probe_timeout_for(proxy_url)
    test_url = _TELEGRAM_API
    if bot_token:
        test_url = f"{_TELEGRAM_API}/bot{bot_token}/getMe"

    try:
        with httpx.Client(proxy=proxy_url, timeout=timeout, follow_redirects=True) as client:
            resp = client.get(test_url)
        if bot_token:
            if resp.status_code != 200:
                return False
            data = resp.json()
            return bool(data.get("ok"))
        return resp.status_code < 500
    except httpx.HTTPError:
        return False


def probe_direct(*, bot_token: str | None = None) -> bool:
    timeout = _probe_timeout()
    test_url = f"{_TELEGRAM_API}/bot{bot_token}/getMe" if bot_token else _TELEGRAM_API
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(test_url)
        if bot_token:
            return resp.status_code == 200 and bool(resp.json().get("ok"))
        return resp.status_code < 500
    except httpx.HTTPError:
        return False


def _is_failed_recently(proxy_url: str) -> bool:
    failed_at = _failed_proxies.get(proxy_url)
    if failed_at is None:
        return False
    if time.time() - failed_at > _failed_ttl():
        _failed_proxies.pop(proxy_url, None)
        return False
    return True


def select_working_proxy(*, force: bool = False, bot_token: str | None = None) -> str | None:
    global _active_proxy, _active_checked_at

    with _lock:
        if (
            not force
            and _active_proxy
            and time.time() - _active_checked_at < _reprobe_interval()
            and not _is_failed_recently(_active_proxy)
        ):
            return _active_proxy

    candidates = load_proxy_candidates()
    skip_probe = _env_bool("TELEGRAM_PROXY_SKIP_PROBE", False)

    if not candidates:
        if probe_direct(bot_token=bot_token):
            with _lock:
                _active_proxy = None
                _active_checked_at = time.time()
            logger.info("Telegram: direct connection works, no proxy")
            return None
        logger.error("Telegram: no proxy candidates and direct connection failed")
        return None

    for proxy in candidates:
        if _is_failed_recently(proxy):
            continue
        if skip_probe or probe_proxy(proxy, bot_token=bot_token):
            with _lock:
                _active_proxy = proxy
                _active_checked_at = time.time()
            logger.info("Telegram: using proxy %s", _mask_proxy(proxy))
            return proxy
        logger.warning("Telegram: proxy failed probe: %s", _mask_proxy(proxy))
        _failed_proxies[proxy] = time.time()

    # Gateway may still be starting — retry with longer timeout once
    gateway = _gateway_proxy_url()
    if gateway and gateway in candidates and not skip_probe:
        logger.info("Telegram: retrying gateway proxy with extended timeout")
        if probe_proxy(gateway, bot_token=bot_token):
            with _lock:
                _active_proxy = gateway
                _active_checked_at = time.time()
            return gateway

    logger.error("Telegram: no working proxy found among %d candidates", len(candidates))
    return None


def get_active_proxy() -> str | None:
    with _lock:
        return _active_proxy


def mark_proxy_failed(proxy_url: str | None = None) -> None:
    global _active_proxy, _active_checked_at
    with _lock:
        target = proxy_url or _active_proxy
        if target:
            _failed_proxies[target] = time.time()
            logger.warning("Telegram: marked proxy failed %s", _mask_proxy(target))
        _active_proxy = None
        _active_checked_at = 0.0


def proxy_status(*, bot_token: str | None = None) -> dict[str, Any]:
    candidates = load_proxy_candidates()
    active = get_active_proxy()
    result: dict[str, Any] = {
        "active_proxy": _mask_proxy(active) if active else None,
        "candidates": [_mask_proxy(p) for p in candidates],
        "candidate_count": len(candidates),
        "direct_ok": probe_direct(bot_token=bot_token) if not candidates else None,
        "active_ok": probe_proxy(active, bot_token=bot_token) if active else None,
        "failed_recently": [_mask_proxy(p) for p, ts in _failed_proxies.items() if time.time() - ts <= _failed_ttl()],
        "awesome_vpn_enabled": _awesome_vpn_enabled(),
        "gateway_proxy": _mask_proxy(_gateway_proxy_url()) if _awesome_vpn_enabled() else None,
    }
    if _awesome_vpn_enabled():
        try:
            from proxy_gateway.awesome_vpn import awesome_vpn_status

            result["awesome_vpn"] = awesome_vpn_status()
            if gateway := _gateway_proxy_url():
                result["awesome_vpn"]["gateway_probe_ok"] = probe_proxy(gateway, bot_token=bot_token)
        except Exception as exc:
            result["awesome_vpn"] = {"fetch_ok": False, "error": str(exc)}
    return result


def _mask_proxy(proxy_url: str | None) -> str | None:
    if not proxy_url:
        return None
    return re.sub(r":([^:@/]+)@", ":***@", proxy_url)


def httpx_client_kwargs() -> dict[str, Any]:
    proxy = select_working_proxy()
    if proxy:
        return {"proxy": proxy}
    return {}
