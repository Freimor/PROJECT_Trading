"""Hashing utilities for replay and audit."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_hex(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def inputs_hash(*, symbol: str, timeframe: str, indicators: dict, candles_ts: list[int]) -> str:
    return sha256_hex({
        "symbol": symbol,
        "timeframe": timeframe,
        "indicators": indicators,
        "candles_ts": candles_ts[-20:],
    })
