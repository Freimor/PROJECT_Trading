"""Outbound Telegram messages via Bot API."""

from __future__ import annotations

import os
from typing import Any

import httpx

from telegram_proxy import mark_proxy_failed, select_working_proxy


def _token() -> str | None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    return token or None


def send_telegram_message(
    text: str,
    *,
    chat_id: str | None = None,
    parse_mode: str | None = None,
) -> dict[str, Any]:
    token = _token()
    if not token:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN not set"}
    cid = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not cid:
        return {"ok": False, "error": "TELEGRAM_CHAT_ID not set"}

    payload: dict[str, Any] = {"chat_id": cid, "text": text[:4096]}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    proxy = select_working_proxy(bot_token=token)
    client_kwargs: dict[str, Any] = {"timeout": 15.0}
    if proxy:
        client_kwargs["proxy"] = proxy

    try:
        with httpx.Client(**client_kwargs) as client:
            resp = client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json=payload,
            )
        data = resp.json()
        ok = bool(data.get("ok"))
        if not ok:
            mark_proxy_failed(proxy)
        return {"ok": ok, "response": data, "proxy_used": bool(proxy)}
    except httpx.HTTPError as exc:
        mark_proxy_failed(proxy)
        return {"ok": False, "error": str(exc), "proxy_used": bool(proxy)}
