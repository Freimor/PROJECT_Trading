"""Quote stablecoin helpers for crypto workflows (USDT, USDC, …)."""

from __future__ import annotations

from typing import Any

from config_loader import load_config

ALLOWED_QUOTE_ASSETS = frozenset({"USDT", "USDC", "FDUSD", "BUSD", "TUSD", "DAI"})
RUNTIME_QUOTE_KEY = "crypto_quote_asset"


def allowed_quote_assets() -> list[str]:
    cfg = load_config("crypto_config")
    raw = cfg.get("allowed_quote_assets")
    if isinstance(raw, list) and raw:
        out = [str(a).upper() for a in raw if str(a).upper() in ALLOWED_QUOTE_ASSETS]
        if out:
            return out
    default = str(cfg.get("quote_asset", "USDT")).upper()
    return [default] if default in ALLOWED_QUOTE_ASSETS else ["USDT"]


def yaml_quote_asset() -> str:
    cfg = load_config("crypto_config")
    q = str(cfg.get("quote_asset", "USDT")).upper()
    return q if q in ALLOWED_QUOTE_ASSETS else "USDT"


def get_crypto_quote_asset() -> str:
    from runtime_settings import get_runtime_value

    stored = get_runtime_value(RUNTIME_QUOTE_KEY)
    if isinstance(stored, str):
        q = stored.upper()
        if q in ALLOWED_QUOTE_ASSETS:
            return q
    return yaml_quote_asset()


def symbol_base_asset(symbol: str, *, quote: str | None = None) -> str:
    sym = str(symbol).upper()
    q = (quote or get_crypto_quote_asset()).upper()
    if sym.endswith(q):
        return sym[: -len(q)]
    for alt in ALLOWED_QUOTE_ASSETS:
        if sym.endswith(alt):
            return sym[: -len(alt)]
    return sym.replace("USDT", "").replace("USDC", "")


def pair_with_quote(base_or_pair: str, *, quote: str | None = None) -> str:
    """Ensure trading pair suffix matches active quote asset."""
    q = (quote or get_crypto_quote_asset()).upper()
    sym = str(base_or_pair).upper()
    base = symbol_base_asset(sym, quote=q)
    return f"{base}{q}"


def wallet_quote_balance(balances: list[dict[str, Any]], *, quote: str | None = None) -> float:
    q = (quote or get_crypto_quote_asset()).upper()
    for row in balances:
        if str(row.get("asset") or "").upper() == q:
            return float(row.get("free", 0) or 0) + float(row.get("locked", 0) or 0)
    return 0.0
