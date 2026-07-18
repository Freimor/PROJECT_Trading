from scalp_klines import ScalpKlinesResult, fetch_scalp_candles, klines_quality_poor


def test_klines_quality_poor_flat():
    flat = [{"c": 1.0, "h": 1.0, "l": 1.0, "v": 100.0} for _ in range(40)]
    assert klines_quality_poor(flat) is True


def test_klines_quality_poor_moving():
    moving = []
    for i in range(40):
        c = 1.0 + i * 0.01
        moving.append({"c": c, "h": c + 0.005, "l": c - 0.005, "v": 100.0 + i})
    assert klines_quality_poor(moving) is False


def test_scalp_klines_result_unusable_when_flat_after_fallback(monkeypatch):
    flat = [{"c": 1.0, "h": 1.0, "l": 1.0, "v": 100.0, "t": i} for i in range(40)]

    def fake_fetch(*args, **kwargs):
        return [[0, "1", "1", "1", "1", "1"]] * 40

    monkeypatch.setattr("scalp_klines.fetch_market_klines", lambda *a, **k: fake_fetch())
    monkeypatch.setattr(
        "scalp_klines.parse_binance_klines",
        lambda raw: flat,
    )
    monkeypatch.setattr(
        "scalp_klines.get_crypto_trading_product_for_trade",
        lambda **k: {"market_type": "usdt_futures", "is_futures": True},
    )

    result = fetch_scalp_candles(
        symbol="DUSKUSDT",
        timeframe="5m",
        limit=40,
        testnet=True,
        crypto_cfg={},
        scalp_cfg={"signal_klines_mainnet_fallback": True},
    )
    assert isinstance(result, ScalpKlinesResult)
    assert result.source == "unusable"
    assert result.quality_ok is False
    assert result.testnet_poor is True
    assert result.fallback_attempted is True
