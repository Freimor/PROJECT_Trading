"""One-off T-Invest connectivity probe (no secrets in output)."""

from __future__ import annotations

import os
import sys

import httpx

from bridges.tinvest_rest import REST_BASE_SANDBOX, TinvestRestClient, _http_proxy, _ssl_verify


def _mask(text: str, token: str) -> str:
    if token:
        return text.replace(token, "***")
    return text


def _probe_path(base: str, path: str, token: str, *, proxy: str | None, verify: bool) -> None:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    label = f"proxy={proxy or 'direct'} verify={verify}"
    try:
        with httpx.Client(timeout=30, proxy=proxy, verify=verify) as client:
            resp = client.post(f"{base}{path}", headers=headers, json={})
        print(f"  {label}: HTTP {resp.status_code} {_mask(resp.text[:240], token)}")
    except Exception as exc:
        print(f"  {label}: EXC {exc}")


def main() -> int:
    token = os.environ.get("TINKOFF_SANDBOX_TOKEN") or os.environ.get("TINKOFF_TOKEN", "")
    print(f"has_token={bool(token)} token_len={len(token)}")
    print(f"configured_proxy={_http_proxy()!r} ssl_verify={_ssl_verify()}")

    path = "/tinkoff.public.invest.api.contract.v1.SandboxService/GetSandboxAccounts"
    for verify in (True, False):
        _probe_path(REST_BASE_SANDBOX, path, token, proxy=None, verify=verify)
        _probe_path(
            REST_BASE_SANDBOX,
            path,
            token,
            proxy=os.environ.get("TELEGRAM_PROXY_GATEWAY"),
            verify=verify,
        )

    print("\nCLIENT ping (sandbox=True):")
    try:
        client = TinvestRestClient(token, sandbox=True)
        result = client.ping()
        print("  ok", result)
    except Exception as exc:
        print("  error", exc)

    return 0


if __name__ == "__main__":
    sys.exit(main())
