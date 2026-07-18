"""Chart candles — testnet quality detection and mainnet fallback."""

from __future__ import annotations

from unittest.mock import patch

from charts_service import _fetch_crypto_candles, get_chart_candles


def _flat_testnet_raw(count: int = 30, price: float = 1.6) -> list[list]:
    base_ms = 1_783_783_800_000
    return [
        [base_ms + i * 300_000, price, price, price, price, 0.0, 0, 0, 0, 0, 0, 0]
        for i in range(count)
    ]


def _varying_mainnet_raw(count: int = 30) -> list[list]:
    base_ms = 1_783_783_800_000
    rows: list[list] = []
    for i in range(count):
        close = 1.59 + (i % 7) * 0.002
        rows.append(
            [base_ms + i * 300_000, close - 0.001, close + 0.002, close - 0.003, close, 100.0, 0, 0, 0, 0, 0, 0]
        )
    return rows


@patch("charts_service.fetch_klines")
def test_fetch_crypto_candles_mainnet_fallback_when_testnet_flat(mock_fetch):
    mock_fetch.side_effect = [
        _flat_testnet_raw(),
        _varying_mainnet_raw(),
    ]
    candles, source, poor = _fetch_crypto_candles(
        symbol="TONUSDT",
        timeframe="5m",
        limit=30,
        testnet=True,
    )
    assert poor is True
    assert source == "mainnet_metrics_fallback"
    assert len(candles) == 30
    closes = {round(c["close"], 4) for c in candles}
    assert len(closes) > 2


@patch("charts_service._fetch_live_candles")
def test_get_chart_candles_reports_data_source(mock_live):
    mock_live.return_value = (
        [{"time": 1, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05, "volume": 1.0}],
        "mainnet_metrics_fallback",
        True,
    )
    resp = get_chart_candles(
        market="crypto",
        symbol="TONUSDT",
        interval="5m",
        limit=30,
        testnet=True,
        use_cache=False,
    )
    assert resp["data_source"] == "mainnet_metrics_fallback"
    assert resp["testnet_poor"] is True
