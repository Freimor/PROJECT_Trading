"""Tests for klines feed health counters and alerts."""

from __future__ import annotations

from scalp_klines import ScalpKlinesResult
from scalp_klines_feed_health import record_klines_feed_health


def test_feed_health_increments_fallback_streak(monkeypatch):
    store: dict = {}

    def fake_get(key):
        return store.get(key)

    def fake_set(key, val, updated_by=""):
        store[key] = val

    monkeypatch.setattr("runtime_settings.get_runtime_value", fake_get)
    monkeypatch.setattr("runtime_settings.set_runtime_value", fake_set)
    monkeypatch.setattr(
        "scalp_klines_feed_health._emit_feed_dead_alert",
        lambda *a, **k: False,
    )

    cfg = {
        "klines_quality": {
            "feed_dead_alert_ticks": 3,
            "block_signals_on_unusable": True,
            "block_on_feed_dead": False,
        }
    }
    result = ScalpKlinesResult(
        candles=[{"c": 1.0, "h": 1.01, "l": 0.99, "v": 1.0, "t": 1}],
        source="mainnet_metrics_fallback",
        testnet_poor=True,
        quality_ok=True,
        fallback_attempted=True,
    )

    h1 = record_klines_feed_health("DUSKUSDT", result, cfg)
    h2 = record_klines_feed_health("DUSKUSDT", result, cfg)
    h3 = record_klines_feed_health("DUSKUSDT", result, cfg)

    assert h1["consecutive_mainnet_fallback"] == 1
    assert h3["consecutive_mainnet_fallback"] == 3
    assert h3["feed_dead"] is True
    assert h3["block_reason"] is None


def test_feed_health_blocks_unusable(monkeypatch):
    store: dict = {}

    monkeypatch.setattr("runtime_settings.get_runtime_value", lambda k: store.get(k))
    monkeypatch.setattr(
        "runtime_settings.set_runtime_value",
        lambda k, v, updated_by="": store.update({k: v}),
    )
    monkeypatch.setattr(
        "scalp_klines_feed_health._emit_feed_dead_alert",
        lambda *a, **k: False,
    )

    cfg = {"klines_quality": {"block_signals_on_unusable": True}}
    result = ScalpKlinesResult(
        candles=[],
        source="unusable",
        testnet_poor=True,
        quality_ok=False,
        fallback_attempted=True,
    )
    health = record_klines_feed_health("DUSKUSDT", result, cfg)
    assert health["block_reason"] == "klines_unusable"
