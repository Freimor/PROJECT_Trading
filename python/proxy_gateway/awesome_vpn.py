"""Fetch and parse awesome-vpn subscription sources.

Sources: https://github.com/awesome-vpn/awesome-vpn
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any
from urllib.parse import quote

import httpx
import yaml

logger = logging.getLogger(__name__)

# Official + mirrors from awesome-vpn README
SINGBOX_URLS = [
    "https://raw.githubusercontent.com/awesome-vpn/awesome-vpn/master/sing-box.json",
    "https://raw.kkgithub.com/awesome-vpn/awesome-vpn/master/sing-box.json",
    "https://ghproxy.net/https://raw.githubusercontent.com/awesome-vpn/awesome-vpn/master/sing-box.json",
]

CLASH_URLS = [
    "https://raw.githubusercontent.com/awesome-vpn/awesome-vpn/master/clash.yaml",
    "https://raw.kkgithub.com/awesome-vpn/awesome-vpn/master/clash.yaml",
    "https://ghproxy.net/https://raw.githubusercontent.com/awesome-vpn/awesome-vpn/master/clash.yaml",
]

ALL_URLS = [
    "https://raw.githubusercontent.com/awesome-vpn/awesome-vpn/master/all",
    "https://raw.kkgithub.com/awesome-vpn/awesome-vpn/master/all",
    "https://ghproxy.net/https://raw.githubusercontent.com/awesome-vpn/awesome-vpn/master/all",
]


def _fetch_first(urls: list[str], *, timeout: float = 30.0) -> str:
    errors: list[str] = []
    for url in urls:
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                resp = client.get(url)
            if resp.status_code == 200 and resp.text.strip():
                logger.info("Fetched awesome-vpn from %s", url)
                return resp.text
        except httpx.HTTPError as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("awesome-vpn fetch failed: " + "; ".join(errors[:3]))


def fetch_singbox_outbounds(*, max_nodes: int | None = None) -> list[dict[str, Any]]:
    limit = max_nodes or int(os.environ.get("TELEGRAM_AWESOME_VPN_MAX_NODES", "50"))
    raw = _fetch_first(_custom_urls("TELEGRAM_AWESOME_VPN_SINGBOX_URLS") or SINGBOX_URLS)
    data = json.loads(raw)
    outbounds = data.get("outbounds", [])
    return _filter_node_outbounds(outbounds, limit=limit)


def _custom_urls(env_name: str) -> list[str] | None:
    raw = os.environ.get(env_name, "").strip()
    if not raw:
        return None
    return [u.strip() for u in raw.split(",") if u.strip()]


def _filter_node_outbounds(outbounds: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    skip_types = {"direct", "block", "dns", "selector", "urltest", "forward"}
    nodes: list[dict[str, Any]] = []
    seen_tags: set[str] = set()
    for i, ob in enumerate(outbounds):
        if ob.get("type") in skip_types:
            continue
        if not ob.get("server"):
            continue
        tag = str(ob.get("tag") or f"node-{i}")
        if tag in seen_tags:
            tag = f"{tag}-{i}"
        ob = dict(ob)
        ob["tag"] = tag
        seen_tags.add(tag)
        nodes.append(ob)
        if len(nodes) >= limit:
            break
    return nodes


def fetch_clash_direct_proxies() -> list[str]:
    """Extract plain socks5/http proxies from clash.yaml (rare in awesome-vpn)."""
    try:
        raw = _fetch_first(_custom_urls("TELEGRAM_AWESOME_VPN_CLASH_URLS") or CLASH_URLS)
    except RuntimeError as exc:
        logger.warning("%s", exc)
        return []
    data = yaml.safe_load(raw) or {}
    urls: list[str] = []
    for proxy in data.get("proxies", []):
        url = _clash_proxy_to_url(proxy)
        if url:
            urls.append(url)
    return urls


def _clash_proxy_to_url(proxy: dict[str, Any]) -> str | None:
    ptype = proxy.get("type")
    server = proxy.get("server")
    port = proxy.get("port")
    if not server or not port:
        return None
    if ptype == "socks5":
        user, password = proxy.get("username"), proxy.get("password")
        if user and password:
            auth = f"{quote(str(user))}:{quote(str(password))}@"
            return f"socks5://{auth}{server}:{port}"
        return f"socks5://{server}:{port}"
    if ptype == "http":
        user, password = proxy.get("username"), proxy.get("password")
        if user and password:
            auth = f"{quote(str(user))}:{quote(str(password))}@"
            return f"http://{auth}{server}:{port}"
        return f"http://{server}:{port}"
    return None


def fetch_base64_share_links() -> list[str]:
    """Decode awesome-vpn `all` file — vmess/vless/ss links (for stats only)."""
    try:
        raw = _fetch_first(_custom_urls("TELEGRAM_AWESOME_VPN_ALL_URLS") or ALL_URLS)
        decoded = base64.b64decode(raw.strip(), validate=False).decode("utf-8", errors="ignore")
        return [line.strip() for line in decoded.splitlines() if line.strip()]
    except Exception as exc:
        logger.warning("awesome-vpn all decode failed: %s", exc)
        return []


def awesome_vpn_status() -> dict[str, Any]:
    gateway = os.environ.get("TELEGRAM_PROXY_GATEWAY", "").strip()
    if gateway:
        return {
            "enabled": True,
            "mode": "proxy-gateway",
            "gateway": gateway,
            "note": "sing-box urltest runs in proxy-gateway container",
        }
    status: dict[str, Any] = {"enabled": True, "sources": SINGBOX_URLS[:1]}
    try:
        nodes = fetch_singbox_outbounds(max_nodes=5)
        status["singbox_nodes_sample"] = len(nodes)
        status["fetch_ok"] = True
    except Exception as exc:
        status["fetch_ok"] = False
        status["error"] = str(exc)
    try:
        status["clash_direct_proxies"] = len(fetch_clash_direct_proxies())
    except Exception:
        status["clash_direct_proxies"] = 0
    return status
