"""T-Invest REST client (httpx) — без официального SDK.

PyPI-пакет tinkoff-investments в карантине; используем REST-прокси API:
https://russianinvestments.github.io/investAPI/swagger-ui/
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any

import httpx

REST_BASE_LIVE = "https://invest-public-api.tbank.ru/rest"
REST_BASE_SANDBOX = "https://sandbox-invest-public-api.tbank.ru/rest"

# Fallback для старых токенов/документации.
REST_BASE_LIVE_LEGACY = "https://invest-public-api.tinkoff.ru/rest"
REST_BASE_SANDBOX_LEGACY = "https://sandbox-invest-public-api.tinkoff.ru/rest"

_RETRYABLE_MARKERS = ("70001", "70002", "70003", "internal error", "Internal error")


def _ssl_verify() -> bool:
    return os.environ.get("TINVEST_SSL_VERIFY", "true").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def _http_proxy() -> str | None:
    for key in ("TINVEST_HTTP_PROXY", "HTTPS_PROXY", "HTTP_PROXY"):
        value = (os.environ.get(key) or "").strip()
        if value:
            return value
    if os.environ.get("TINVEST_USE_PROXY_GATEWAY", "false").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        gateway = (os.environ.get("TELEGRAM_PROXY_GATEWAY") or "").strip()
        if gateway:
            return gateway
    return None


def _proxy_fallback_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "proxy",
            "connection refused",
            "handshake operation timed out",
            "socks",
        )
    )


def quotation_to_float(value: dict[str, Any] | None) -> float:
    if not value:
        return 0.0
    units = int(value.get("units", 0) or 0)
    nano = int(value.get("nano", 0) or 0)
    return units + nano / 1_000_000_000


class TinvestRestClient:
    def __init__(self, token: str, *, sandbox: bool = True, timeout: float = 30.0) -> None:
        self.token = token
        self.sandbox = sandbox
        self.timeout = timeout
        self._bases = (
            [REST_BASE_SANDBOX, REST_BASE_SANDBOX_LEGACY]
            if sandbox
            else [REST_BASE_LIVE, REST_BASE_LIVE_LEGACY]
        )

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.timeout,
            proxy=_http_proxy(),
            verify=_ssl_verify(),
        )

    def _post(self, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = body or {}
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        last_error: Exception | None = None
        verify_modes = [_ssl_verify()]
        if _ssl_verify():
            verify_modes.append(False)
        configured_proxy = _http_proxy()
        proxy_modes: list[str | None] = [configured_proxy] if configured_proxy else [None]
        if configured_proxy:
            proxy_modes.append(None)
        for verify in verify_modes:
            for proxy in proxy_modes:
                for attempt in range(3):
                    try:
                        with httpx.Client(
                            timeout=self.timeout, proxy=proxy, verify=verify
                        ) as client:
                            for index, base in enumerate(self._bases):
                                url = f"{base}{path}"
                                try:
                                    resp = client.post(url, headers=headers, json=payload)
                                    if resp.status_code in (404, 500, 502, 503, 504) and index < len(
                                        self._bases
                                    ) - 1:
                                        last_error = RuntimeError(
                                            f"HTTP {resp.status_code} from {base}"
                                        )
                                        continue
                                    if resp.status_code >= 400:
                                        message = resp.text[:300]
                                        try:
                                            err = resp.json()
                                            if isinstance(err, dict):
                                                if err.get("message"):
                                                    message = str(err["message"])
                                                if err.get("description"):
                                                    message = f"{message} ({err.get('description')})"
                                                elif err.get("code"):
                                                    message = f"{err.get('code')}: {message}"
                                        except Exception:
                                            pass
                                        raise RuntimeError(
                                            f"T-Invest API HTTP {resp.status_code}: {message}"
                                        )
                                    data = resp.json()
                                    if isinstance(data, dict) and {"code", "message"} <= set(
                                        data.keys()
                                    ):
                                        raise RuntimeError(
                                            f"T-Invest API error {data.get('code')}: {data.get('message')}"
                                        )
                                    return data
                                except RuntimeError as exc:
                                    last_error = exc
                                except Exception as exc:
                                    last_error = exc
                    except Exception as exc:
                        last_error = exc
                    err_text = str(last_error or "")
                    if proxy and _proxy_fallback_error(last_error or RuntimeError("")):
                        break
                    if attempt < 2 and any(
                        marker.lower() in err_text.lower() for marker in _RETRYABLE_MARKERS
                    ):
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    break
                if proxy and _proxy_fallback_error(last_error or RuntimeError("")):
                    continue
                break
            if (
                verify is True
                and last_error
                and "certificate verify failed" in str(last_error).lower()
            ):
                continue
            break
        raise RuntimeError(str(last_error or "T-Invest REST request failed"))

    def get_accounts(self) -> list[dict[str, Any]]:
        path = (
            "/tinkoff.public.invest.api.contract.v1.SandboxService/GetSandboxAccounts"
            if self.sandbox
            else "/tinkoff.public.invest.api.contract.v1.UsersService/GetAccounts"
        )
        data = self._post(path, {})
        return list(data.get("accounts") or [])

    def ensure_sandbox_account(self) -> str:
        accounts = self.get_accounts()
        if accounts:
            return str(accounts[0]["id"])
        opened = self._post(
            "/tinkoff.public.invest.api.contract.v1.SandboxService/OpenSandboxAccount",
            {},
        )
        account_id = str(opened["accountId"])
        self.sandbox_pay_in(account_id, rub_units=1_000_000)
        return account_id

    def sandbox_pay_in(self, account_id: str, *, rub_units: int = 1_000_000) -> dict[str, Any]:
        return self._post(
            "/tinkoff.public.invest.api.contract.v1.SandboxService/SandboxPayIn",
            {
                "accountId": account_id,
                "amount": {"currency": "rub", "units": str(rub_units), "nano": 0},
            },
        )

    def close_sandbox_account(self, account_id: str) -> dict[str, Any]:
        return self._post(
            "/tinkoff.public.invest.api.contract.v1.SandboxService/CloseSandboxAccount",
            {"accountId": account_id},
        )

    def get_account_id(self) -> str:
        if self.sandbox:
            return self.ensure_sandbox_account()
        accounts = self.get_accounts()
        if not accounts:
            raise RuntimeError("no_account")
        return str(accounts[0]["id"])

    def get_share_by_ticker(self, ticker: str, *, class_code: str = "TQBR") -> dict[str, Any] | None:
        """Resolve MOEX share on main board (avoids wrong FindInstrument matches)."""
        try:
            data = self._post(
                "/tinkoff.public.invest.api.contract.v1.InstrumentsService/ShareBy",
                {
                    "idType": "INSTRUMENT_ID_TYPE_TICKER",
                    "classCode": class_code,
                    "id": ticker.upper(),
                },
            )
            return data.get("instrument") or None
        except Exception:
            return None

    def find_instrument(self, query: str, *, class_code: str = "TQBR") -> dict[str, Any] | None:
        # Prefer exact TQBR share — FindInstrument often returns bonds/notes first.
        if query.isalpha() and 1 <= len(query) <= 6:
            share = self.get_share_by_ticker(query, class_code=class_code)
            if share:
                return share

        data = self._post(
            "/tinkoff.public.invest.api.contract.v1.InstrumentsService/FindInstrument",
            {"query": query},
        )
        instruments = data.get("instruments") or []
        if not instruments:
            return None

        def _score(inst: dict[str, Any]) -> tuple[int, str]:
            ticker = str(inst.get("ticker", "")).upper()
            cc = str(inst.get("classCode", ""))
            tradeable = bool(inst.get("apiTradeAvailableFlag"))
            exact = ticker == query.upper()
            tqbr = cc == class_code
            return (int(exact) * 4 + int(tqbr) * 2 + int(tradeable), ticker)

        return max(instruments, key=_score)

    def get_last_price(self, instrument_id: str) -> float:
        data = self._post(
            "/tinkoff.public.invest.api.contract.v1.MarketDataService/GetLastPrices",
            {"instrumentId": [instrument_id]},
        )
        prices = data.get("lastPrices") or []
        if not prices:
            return 0.0
        return quotation_to_float(prices[0].get("price"))

    def get_portfolio(self, account_id: str) -> dict[str, Any]:
        path = (
            "/tinkoff.public.invest.api.contract.v1.SandboxService/GetSandboxPortfolio"
            if self.sandbox
            else "/tinkoff.public.invest.api.contract.v1.OperationsService/GetPortfolio"
        )
        data = self._post(path, {"accountId": account_id})
        positions = []
        for p in data.get("positions") or []:
            positions.append(
                {
                    "figi": p.get("figi"),
                    "ticker": p.get("ticker"),
                    "quantity": quotation_to_float(p.get("quantity")),
                    "avg_price": quotation_to_float(p.get("averagePositionPrice")),
                }
            )
        return {
            "positions": positions,
            "total_amount": quotation_to_float(data.get("totalAmountPortfolio")),
        }

    def post_market_buy(
        self,
        *,
        account_id: str,
        instrument_id: str,
        lots: int,
    ) -> dict[str, Any]:
        order_path = (
            "/tinkoff.public.invest.api.contract.v1.SandboxService/PostSandboxOrder"
            if self.sandbox
            else "/tinkoff.public.invest.api.contract.v1.OrdersService/PostOrder"
        )
        return self._post(
            order_path,
            {
                "accountId": account_id,
                "instrumentId": instrument_id,
                "quantity": str(max(1, lots)),
                "direction": "ORDER_DIRECTION_BUY",
                "orderType": "ORDER_TYPE_MARKET",
                "orderId": str(uuid.uuid4()),
            },
        )

    def ping(self) -> dict[str, Any]:
        accounts = self.get_accounts()
        return {
            "status": "ok",
            "sandbox": self.sandbox,
            "accounts": len(accounts),
        }
