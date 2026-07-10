"""T-Invest API bridge — HTTP wrapper for n8n (REST via httpx)."""

from __future__ import annotations

import os
from typing import Any

import httpx

from bridges.tinvest_rest import TinvestRestClient


def _token(sandbox: bool) -> str:
    if sandbox:
        return os.environ.get("TINKOFF_SANDBOX_TOKEN", "").strip()
    return os.environ.get("TINKOFF_TOKEN", "").strip()


def _token_error(sandbox: bool) -> dict[str, Any] | None:
    if sandbox:
        if os.environ.get("TINKOFF_SANDBOX_TOKEN", "").strip():
            return None
        if os.environ.get("TINKOFF_TOKEN", "").strip():
            return {
                "status": "error",
                "reject_reason": "missing_sandbox_token",
                "message": (
                    "Для sandbox нужен отдельный TINKOFF_SANDBOX_TOKEN. "
                    "TINKOFF_TOKEN (live) не подходит для песочницы — выпустите sandbox-токен "
                    "в кабинете T-Bank Invest → Настройки → API."
                ),
            }
        return {
            "status": "error",
            "reject_reason": "missing_tinkoff_token",
            "message": "Задайте TINKOFF_SANDBOX_TOKEN в .env",
        }
    if not os.environ.get("TINKOFF_TOKEN", "").strip():
        return {
            "status": "error",
            "reject_reason": "missing_tinkoff_token",
            "message": "Задайте TINKOFF_TOKEN в .env",
        }
    return None


def _client(sandbox: bool) -> TinvestRestClient | None:
    if _token_error(sandbox):
        return None
    token = _token(sandbox)
    if not token:
        return None
    return TinvestRestClient(token, sandbox=sandbox)


def _moex_last_price(ticker: str) -> float:
    """Fallback when T-Invest sandbox returns empty last price.

    Uses MOEX ISS marketdata; if empty, falls back to the latest candle close.
    """
    url = (
        f"https://iss.moex.com/iss/engines/stock/markets/shares/"
        f"boards/TQBR/securities/{ticker.upper()}/marketdata.json"
    )
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, params={"iss.only": "marketdata"})
            resp.raise_for_status()
            data = resp.json()
        cols = data["marketdata"]["columns"]
        rows = data["marketdata"]["data"]
        if not rows:
            raise RuntimeError("empty_marketdata")
        row = dict(zip(cols, rows[0]))
        for key in ("LAST", "LCURRENTPRICE", "WAPRICE", "CLOSEPRICE"):
            val = row.get(key)
            if val is not None and float(val) > 0:
                return float(val)
    except Exception:
        # Candles fallback: use latest close as an approximate last price.
        try:
            candles_url = (
                f"https://iss.moex.com/iss/engines/stock/markets/shares/"
                f"boards/TQBR/securities/{ticker.upper()}/candles.json"
            )
            with httpx.Client(timeout=20) as client:
                resp = client.get(candles_url, params={"interval": 10, "from": "latest", "iss.only": "candles"})
                resp.raise_for_status()
                data = resp.json()
            cols = data["candles"]["columns"]
            rows = data["candles"]["data"]
            if not rows:
                return 0.0
            last = dict(zip(cols, rows[-1]))
            close = last.get("close")
            return float(close) if close is not None and float(close) > 0 else 0.0
        except Exception:
            return 0.0


def _probe_live_api() -> bool:
    """Read-only check: live T-Invest API reachable (helps distinguish sandbox outage)."""
    live_token = os.environ.get("TINKOFF_TOKEN", "").strip()
    if not live_token:
        return False
    url = (
        "https://invest-public-api.tinkoff.ru/rest"
        "/tinkoff.public.invest.api.contract.v1.UsersService/GetAccounts"
    )
    try:
        with httpx.Client(timeout=15, verify=False) as client:
            resp = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {live_token}",
                    "Content-Type": "application/json",
                },
                json={},
            )
        return resp.status_code == 200
    except Exception:
        return False


def _sandbox_outage_hint() -> str | None:
    if not _probe_live_api():
        return None
    return (
        "Боевой T-Invest API отвечает, а песочница — нет. "
        "Похоже на сбой sandbox на стороне T-Bank (ошибка 70001), а не на проблему в проекте. "
        "Попробуйте позже или перевыпустите sandbox-токен в кабинете T-Bank Invest."
    )


def _humanize_tinvest_error(message: str, *, sandbox: bool) -> str:
    text = message or "unknown error"
    lower = text.lower()
    if "certificate verify failed" in lower or "ssl" in lower:
        return (
            f"{text}. Проверьте TINVEST_SSL_VERIFY или прокси (TINVEST_HTTP_PROXY). "
            "Для Docker попробуйте TINVEST_USE_PROXY_GATEWAY=true."
        )
    if "70001" in text or "internal error" in lower:
        if sandbox:
            outage = _sandbox_outage_hint()
            if outage:
                return f"{text}. {outage}"
        hint = (
            "Проверьте TINKOFF_SANDBOX_TOKEN (отдельный sandbox-токен в кабинете T-Bank). "
            if sandbox
            else "Проверьте TINKOFF_TOKEN и права на торговлю. "
        )
        return f"{text}. {hint}Если ошибка повторяется — это может быть сбой на стороне T-Bank."
    if "unauthenticated" in lower or "40003" in text:
        return f"{text}. Выпустите новый токен в личном кабинете T-Bank Invest."
    return text


def post_dca_order(
    *,
    ticker: str,
    amount_rub: float,
    sandbox: bool = True,
    dry_run: bool = True,
) -> dict[str, Any]:
    if dry_run:
        return {
            "status": "dry_run",
            "ticker": ticker,
            "amount_rub": amount_rub,
            "sandbox": sandbox,
            "message": "Order not sent — dry_run=True",
        }

    client = _client(sandbox)
    token_err = _token_error(sandbox)
    if token_err:
        return {**token_err, "sandbox": sandbox}
    if client is None:
        return {
            "status": "error",
            "reject_reason": "missing_tinkoff_token",
            "message": "Задайте TINKOFF_SANDBOX_TOKEN в .env",
            "sandbox": sandbox,
        }

    try:
        instrument = client.find_instrument(ticker)
        if not instrument:
            return {"status": "error", "reject_reason": "instrument_not_found", "ticker": ticker}

        figi = str(instrument.get("figi", ""))
        if not figi:
            return {"status": "error", "reject_reason": "instrument_not_found", "ticker": ticker}

        account_id = client.get_account_id()
        price = client.get_last_price(figi)
        price_source = "tinkoff"
        if price <= 0:
            price = _moex_last_price(ticker)
            price_source = "moex_iss"
        if price <= 0:
            return {
                "status": "error",
                "reject_reason": "no_price",
                "message": "Не удалось получить цену: tinkoff_last_price=0 и moex_iss_fallback=0",
                "ticker": ticker,
                "figi": figi,
            }

        lot_size = max(1, int(instrument.get("lot") or 1))
        lots = max(1, int(amount_rub / (price * lot_size)))
        order = client.post_market_buy(
            account_id=account_id,
            instrument_id=figi,
            lots=lots,
        )
        return {
            "status": "submitted",
            "order_id": order.get("orderId") or order.get("order_id"),
            "ticker": ticker,
            "figi": figi,
            "lots": lots,
            "lot_size": lot_size,
            "price": price,
            "price_source": price_source,
            "sandbox": sandbox,
        }
    except Exception as exc:
        return {
            "status": "error",
            "reject_reason": "tinkoff_api_error",
            "message": _humanize_tinvest_error(str(exc), sandbox=sandbox),
        }


def get_portfolio_snapshot(sandbox: bool = True) -> dict[str, Any]:
    client = _client(sandbox)
    token_err = _token_error(sandbox)
    if token_err:
        return {**token_err, "sandbox": sandbox}
    if client is None:
        return {"status": "error", "reject_reason": "missing_tinkoff_token"}

    try:
        account_id = client.get_account_id()
        portfolio = client.get_portfolio(account_id)
        return {
            "status": "ok",
            "account_id": account_id,
            "positions": portfolio.get("positions", []),
            "total_amount": portfolio.get("total_amount", 0.0),
            "sandbox": sandbox,
        }
    except Exception as exc:
        return {
            "status": "error",
            "reject_reason": "tinkoff_api_error",
            "message": _humanize_tinvest_error(str(exc), sandbox=sandbox),
        }


def get_tinvest_sandbox_bundle(sandbox: bool = True) -> tuple[dict[str, Any], dict[str, Any]]:
    """Single T-Invest session: connection probe + portfolio (avoids duplicate GetAccounts)."""
    token_err = _token_error(sandbox)
    if token_err:
        err = {**token_err, "sandbox": sandbox}
        return err, dict(err)
    client = _client(sandbox)
    if client is None:
        missing = {
            "status": "skipped",
            "reject_reason": "missing_tinkoff_token",
            "sandbox": sandbox,
        }
        return missing, {"status": "error", "reject_reason": "missing_tinkoff_token"}

    try:
        account_id = client.get_account_id()
        portfolio_data = client.get_portfolio(account_id)
        connection = {
            "status": "ok",
            "sandbox": sandbox,
            "accounts": 1,
            "account_id": account_id,
        }
        portfolio = {
            "status": "ok",
            "account_id": account_id,
            "positions": portfolio_data.get("positions", []),
            "total_amount": portfolio_data.get("total_amount", 0.0),
            "sandbox": sandbox,
        }
        return connection, portfolio
    except Exception as exc:
        msg = _humanize_tinvest_error(str(exc), sandbox=sandbox)
        return (
            {
                "status": "error",
                "reject_reason": "tinkoff_api_error",
                "message": msg,
                "sandbox": sandbox,
            },
            {
                "status": "error",
                "reject_reason": "tinkoff_api_error",
                "message": msg,
                "sandbox": sandbox,
            },
        )


def check_tinvest_connection(sandbox: bool = True) -> dict[str, Any]:
    """Lightweight connectivity probe for smoke tests and admin status."""
    token_err = _token_error(sandbox)
    if token_err:
        return {**token_err, "sandbox": sandbox}
    client = _client(sandbox)
    if client is None:
        return {
            "status": "skipped",
            "reject_reason": "missing_tinkoff_token",
            "sandbox": sandbox,
        }
    try:
        result = client.ping()
        return {**result, "status": "ok"}
    except Exception as exc:
        return {
            "status": "error",
            "reject_reason": "tinkoff_api_error",
            "message": _humanize_tinvest_error(str(exc), sandbox=sandbox),
            "sandbox": sandbox,
        }
