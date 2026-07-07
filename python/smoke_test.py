"""Smoke tests — run inside db-api container: python smoke_test.py"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("WIKI_CONFIG_PATH", "/data/trading_wiki")
os.environ.setdefault("TRADING_DB_PATH", "/data/trading.db")

# Allow local run from python/
sys.path.insert(0, os.path.dirname(__file__))


def main() -> None:
    from db.init_db import init_database
    from crypto_pipeline import run_crypto_signal
    from securities_pipeline import run_securities_dca_dry_run, run_securities_swing_dry_run
    from news_service import seed_sources, ingest_all
    from backtest.metrics import dry_run_funnel

    init_database()
    seed_sources()
    print("1. DB init OK")

    r = run_crypto_signal(symbol="BTCUSDT", skip_llm=True)
    assert r["status"] in ("dry_run_complete", "skipped", "rejected"), r
    print(f"2. Crypto pipeline OK: {r['status']}")

    dca = run_securities_dca_dry_run()
    assert dca["status"] == "dry_run_complete"
    print("3. Securities DCA OK")

    swing = run_securities_swing_dry_run(ticker="SBER", skip_llm=True)
    assert swing["status"] in ("dry_run_complete", "skipped", "rejected"), swing
    print(f"4. Securities swing OK: {swing['status']}")

    news = ingest_all()
    print(f"5. News ingest OK: inserted={news.get('inserted', 0)}")

    funnel = dry_run_funnel()
    print(f"6. Backtest funnel OK: {funnel.get('funnel', {}).keys()}")

    from bridges.tinvest_bridge import check_tinvest_connection

    tinvest = check_tinvest_connection(sandbox=True)
    if tinvest.get("status") == "skipped":
        print("7. T-Invest skipped (no sandbox token)")
    else:
        assert tinvest.get("status") == "ok", tinvest
        print(f"7. T-Invest sandbox OK: accounts={tinvest.get('accounts')}")

    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    main()
