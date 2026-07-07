"""HTTP client for db-api."""

from __future__ import annotations

import os
from typing import Any

import httpx


def api_base() -> str:
    return os.environ.get("DB_API_URL", "http://db-api:8000").rstrip("/")


def admin_headers() -> dict[str, str]:
    key = os.environ.get("ADMIN_API_KEY", "").strip()
    return {"X-Admin-Key": key} if key else {}


async def get_json(path: str) -> Any:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{api_base()}{path}")
        resp.raise_for_status()
        return resp.json()


async def post_json(path: str, body: dict[str, Any] | None = None) -> Any:
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{api_base()}{path}",
            json=body or {},
            headers=admin_headers(),
        )
        resp.raise_for_status()
        return resp.json()
