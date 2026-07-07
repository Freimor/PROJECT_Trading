"""T-Invest REST client (httpx) — без официального SDK.

PyPI-пакет tinkoff-investments в карантине; используем REST-прокси API:
https://russianinvestments.github.io/investAPI/swagger-ui/
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx

REST_BASE_LIVE = "https://invest-public-api.tbank.ru/rest"
REST_BASE_SANDBOX = "https://sandbox-invest-public-api.tbank.ru/rest"

# Fallback для старых токенов/документации.
REST_BASE_LIVE_LEGACY = "https://invest-public-api.tinkoff.ru/rest"
REST_BASE_SANDBOX_LEGACY = "https://sandbox-invest-public-api.tinkoff.ru/rest"


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

    def _post(self, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = body or {}
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        last_error: Exception | None = None
        with httpx.Client(timeout=self.timeout) as client:
            for base in self._bases:
                url = f"{base}{path}"
                try:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 404 and base != self._bases[-1]:
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    if isinstance(data, dict) and {"code", "message"} <= set(data.keys()):
                        raise RuntimeError(
                            f"T-Invest API error {data.get('code')}: {data.get('message')}"
                        )
                    return data
                except Exception as exc:
                    last_error = exc
        raise RuntimeError(str(last_error or "T-Invest REST request failed"))

    def get_accounts(self) -> list[dict[str, Any]]:
        data = self._post(
            "/tinkoff.public.invest.api.contract.v1.UsersService/GetAccounts",
            {},
        )
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
        self._post(
            "/tinkoff.public.invest.api.contract.v1.SandboxService/SandboxPayIn",
            {
                "accountId": account_id,
                "amount": {"currency": "rub", "units": "1000000", "nano": 0},
            },
        )
        return account_id

    def get_account_id(self) -> str:
        if self.sandbox:
            return self.ensure_sandbox_account()
        accounts = self.get_accounts()
        if not accounts:
            raise RuntimeError("no_account")
        return str(accounts[0]["id"])

    def find_instrument(self, query: str) -> dict[str, Any] | None:
        data = self._post(
            "/tinkoff.public.invest.api.contract.v1.InstrumentsService/FindInstrument",
            {"query": query},
        )
        instruments = data.get("instruments") or []
        if not instruments:
            return None
        preferred = next(
            (i for i in instruments if str(i.get("ticker", "")).upper() == query.upper()),
            instruments[0],
        )
        return preferred

    def get_last_price(self, instrument_id: str) -> float:
        data = self._post(
            "/tinkoff.public.invest.api.contract.v1.MarketDataService/GetLastPrices",
            {"instrumentId": [instrument_id]},
        )
        prices = data.get("lastPrices") or []
        if not prices:
            return 0.0
        return quotation_to_float(prices[0].get("price"))

    def get_portfolio(self, account_id: str) -> list[dict[str, Any]]:
        data = self._post(
            "/tinkoff.public.invest.api.contract.v1.OperationsService/GetPortfolio",
            {"accountId": account_id},
        )
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
        return positions

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
