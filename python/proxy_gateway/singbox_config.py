"""Build sing-box config with urltest for Telegram."""

from __future__ import annotations

import json
import os
from typing import Any

from proxy_gateway.awesome_vpn import fetch_singbox_outbounds

TEST_URL = os.environ.get("TELEGRAM_PROXY_TEST_URL", "https://api.telegram.org")


def build_singbox_config(outbounds: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    nodes = outbounds if outbounds is not None else fetch_singbox_outbounds()
    if not nodes:
        raise RuntimeError("no outbounds for sing-box config")

    tags = [str(n["tag"]) for n in nodes]
    port = int(os.environ.get("PROXY_GATEWAY_PORT", "17890"))
    listen = os.environ.get("PROXY_GATEWAY_LISTEN", "0.0.0.0")

    return {
        "log": {"level": os.environ.get("SINGBOX_LOG_LEVEL", "warn")},
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": listen,
                "listen_port": port,
            }
        ],
        "outbounds": [
            *nodes,
            {"type": "direct", "tag": "direct"},
            {"type": "block", "tag": "block"},
            {
                "type": "urltest",
                "tag": "auto",
                "outbounds": tags,
                "url": TEST_URL,
                "interval": os.environ.get("SINGBOX_URLTEST_INTERVAL", "5m"),
                "tolerance": int(os.environ.get("SINGBOX_URLTEST_TOLERANCE", "100")),
            },
        ],
        "route": {"final": "auto"},
    }


def write_config(
    path: str,
    *,
    outbounds: list[dict[str, Any]] | None = None,
    config: dict[str, Any] | None = None,
) -> str:
    cfg = config or build_singbox_config(outbounds)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return path
