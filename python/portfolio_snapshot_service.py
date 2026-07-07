"""Exchange position snapshots and equity curve for admin charts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from binance_client import get_account_balances
from bridges.tinvest_bridge import get_portfolio_snapshot
from config_loader import load_config
from db.connection import get_connection
from db.migrate import run_migrations


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _to_unix(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def capture_exchange_position_snapshots() -> dict[str, Any]:
    """Persist per-asset rows into position_snapshots (exchange reconciliation)."""
    run_migrations()
    snap_at = _utc_now()
    inserted = 0
    conn = get_connection()
    try:
        crypto_cfg = load_config("crypto_config")
        sec_cfg = load_config("securities_config")
        testnet = crypto_cfg.get("env") == "testnet"
        sandbox = sec_cfg.get("env") == "sandbox"

        for bal in get_account_balances(testnet=testnet):
            free = float(bal.get("free", 0))
            locked = float(bal.get("locked", 0))
            qty = free + locked
            if qty <= 0:
                continue
            asset = str(bal.get("asset", ""))
            conn.execute(
                """
                INSERT INTO position_snapshots
                    (snapshot_at, market, env, symbol, quantity, avg_price, unrealized_pnl, source, raw_json)
                VALUES (?, 'crypto', 'paper', ?, ?, NULL, NULL, 'exchange', ?)
                """,
                (snap_at, asset, qty, json.dumps(bal, ensure_ascii=False)),
            )
            inserted += 1

        moex = get_portfolio_snapshot(sandbox=sandbox)
        if moex.get("status") == "ok":
            for p in moex.get("positions") or []:
                ticker = p.get("ticker") or p.get("figi") or "?"
                qty = float(p.get("quantity", 0))
                if qty == 0:
                    continue
                conn.execute(
                    """
                    INSERT INTO position_snapshots
                        (snapshot_at, market, env, symbol, quantity, avg_price, unrealized_pnl, source, raw_json)
                    VALUES (?, 'securities', 'paper', ?, ?, ?, ?, 'exchange', ?)
                    """,
                    (
                        snap_at,
                        ticker,
                        qty,
                        p.get("avg_price"),
                        p.get("unrealized_pnl"),
                        json.dumps(p, ensure_ascii=False),
                    ),
                )
                inserted += 1

        conn.commit()
        return {"status": "ok", "snapshot_at": snap_at, "rows_inserted": inserted}
    finally:
        conn.close()


def get_equity_curve(*, days: int = 30) -> dict[str, Any]:
    """Equity time series from paper_portfolio_snapshots (USDT + RUB)."""
    run_migrations()
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT captured_at, snapshot_json
            FROM paper_portfolio_snapshots
            WHERE captured_at >= datetime('now', ?)
            ORDER BY captured_at ASC
            """,
            (f"-{days} days",),
        ).fetchall()
    finally:
        conn.close()

    crypto_usdt: list[dict[str, Any]] = []
    moex_rub: list[dict[str, Any]] = []
    for row in rows:
        try:
            snap = json.loads(row["snapshot_json"] or "{}")
        except json.JSONDecodeError:
            continue
        t = _to_unix(row["captured_at"])
        if snap.get("crypto_usdt") is not None:
            crypto_usdt.append({"time": t, "value": float(snap["crypto_usdt"])})
        if snap.get("moex_rub") is not None:
            moex_rub.append({"time": t, "value": float(snap["moex_rub"])})

    return {
        "status": "ok",
        "days": days,
        "crypto_usdt": crypto_usdt,
        "moex_rub": moex_rub,
        "points": len(rows),
        "hint": (
            "Нет точек — запустите paper-сессию или POST /api/paper/snapshot"
            if not rows
            else None
        ),
    }
