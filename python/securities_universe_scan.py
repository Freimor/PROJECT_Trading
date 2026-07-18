"""MOEX ISS universe pre-scan for securities swing — liquidity + daily swing score."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from concurrent.futures import ThreadPoolExecutor, as_completed

from config_loader import load_config
from effective_config import get_config_effective
from indicators.technical import compute_indicators
from market_data import fetch_moex_candles_as_of

logger = logging.getLogger(__name__)

SCAN_PROGRESS_KEY = "securities_universe_scan_progress"
DEFAULT_SCAN_CONTEXT = "moex-create"
TQBR_ISS_URL = (
    "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json"
)
_EQUITY_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9]{1,4}(P|-RX)?$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _scan_cfg(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    from securities_universe_scan_settings_service import get_merged_scan_config

    cfg = dict(get_merged_scan_config())
    if overrides:
        cfg.update(overrides)
    return cfg


def _last_scan_key(scan_context: str) -> str:
    return f"securities_universe_last_scan:{scan_context.strip() or DEFAULT_SCAN_CONTEXT}"


def _store_last_scan(scan_context: str, payload: dict[str, Any]) -> None:
    from runtime_settings import set_runtime_value

    set_runtime_value(_last_scan_key(scan_context), payload, updated_by="scan")


def get_last_scan(scan_context: str = DEFAULT_SCAN_CONTEXT) -> dict[str, Any] | None:
    from runtime_settings import get_runtime_value

    raw = get_runtime_value(_last_scan_key(scan_context))
    return raw if isinstance(raw, dict) else None


def _set_scan_progress(*, scan_context: str, total: int, done: int = 0, current: str | None = None) -> None:
    from runtime_settings import set_runtime_value

    set_runtime_value(
        SCAN_PROGRESS_KEY,
        {
            "in_progress": True,
            "scan_context": scan_context,
            "total": total,
            "done": done,
            "current_ticker": current,
            "started_at": _utc_now(),
        },
        updated_by="scan",
    )


def _clear_scan_progress() -> None:
    from runtime_settings import delete_runtime_value

    delete_runtime_value(SCAN_PROGRESS_KEY)


def get_scan_progress() -> dict[str, Any]:
    from runtime_settings import get_runtime_value

    raw = get_runtime_value(SCAN_PROGRESS_KEY)
    if not isinstance(raw, dict) or not raw.get("in_progress"):
        return {"in_progress": False}
    return {
        "in_progress": True,
        "scan_context": raw.get("scan_context"),
        "total": int(raw.get("total") or 0),
        "done": int(raw.get("done") or 0),
        "current_ticker": raw.get("current_ticker"),
        "started_at": raw.get("started_at"),
    }


_FUND_NAME_MARKERS = ("ПИФ", "БПИФ", "ETF", "ФОНД", "FUND", "ОБЛИГ", "BOND")


def _is_equity_row(row: dict[str, Any], *, whitelist: set[str] | None = None) -> bool:
    sym = str(row.get("symbol") or "").upper().strip()
    if not sym or sym.startswith("RU"):
        return False
    if whitelist and sym in whitelist:
        return True
    if not _EQUITY_TICKER_RE.match(sym):
        return False
    shortname = str(row.get("shortname") or "").upper()
    if any(marker in shortname for marker in _FUND_NAME_MARKERS):
        return False
    return True


def fetch_tqbr_liquidity_rows(*, board: str = "TQBR") -> list[dict[str, Any]]:
    url = TQBR_ISS_URL.replace("/boards/TQBR/", f"/boards/{board.upper()}/")
    with httpx.Client(timeout=45) as client:
        resp = client.get(
            url,
            params={
                "iss.meta": "off",
                "securities.columns": "SECID,SHORTNAME",
                "marketdata.columns": "SECID,VALTODAY,NUMTRADES,LAST",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    sec_rows = (data.get("securities") or {}).get("data") or []
    md_rows = (data.get("marketdata") or {}).get("data") or []
    md_cols = (data.get("marketdata") or {}).get("columns") or []
    md_idx = {name: i for i, name in enumerate(md_cols)}

    market: dict[str, dict[str, Any]] = {}
    for row in md_rows:
        if not row:
            continue
        secid = str(row[md_idx.get("SECID", 0)] or "").upper()
        if not secid:
            continue
        market[secid] = {
            "valtoday": float(row[md_idx.get("VALTODAY", 1)] or 0),
            "numtrades": int(row[md_idx.get("NUMTRADES", 2)] or 0),
            "last": row[md_idx.get("LAST", 3)],
        }

    out: list[dict[str, Any]] = []
    for row in sec_rows:
        secid = str(row[0] or "").upper().strip()
        if not secid:
            continue
        md = market.get(secid, {})
        out.append(
            {
                "symbol": secid,
                "shortname": row[1] if len(row) > 1 else None,
                "valtoday": float(md.get("valtoday") or 0),
                "numtrades": int(md.get("numtrades") or 0),
                "last": md.get("last"),
            }
        )
    return out


def _whitelist(cfg: dict[str, Any]) -> set[str]:
    sec = get_config_effective("securities_config")
    items = sec.get("swing_signals", {}).get("universe") or []
    extra = cfg.get("candidates") or []
    return {str(s).upper().strip() for s in [*items, *extra] if str(s).strip()}


def get_scan_candidate_info() -> dict[str, Any]:
    cfg = _scan_cfg()
    rows = fetch_tqbr_liquidity_rows()
    wl = _whitelist(cfg)
    min_val = float(cfg.get("min_valtoday_mln", 50)) * 1_000_000
    min_trades = int(cfg.get("min_numtrades", 100))
    equities_only = bool(cfg.get("equities_only", True))
    use_whitelist = bool(cfg.get("use_whitelist", False))

    filtered = []
    for row in rows:
        sym = row["symbol"]
        if equities_only and not _is_equity_row(row, whitelist=wl):
            continue
        if use_whitelist and sym not in wl:
            continue
        if row["valtoday"] < min_val or row["numtrades"] < min_trades:
            continue
        filtered.append(row)

    return {
        "tickers_count": len(filtered),
        "board": "TQBR",
        "source": "moex_iss",
        "equities_only": equities_only,
        "use_whitelist": use_whitelist,
        "whitelist_count": len(wl),
        "min_valtoday_mln": float(cfg.get("min_valtoday_mln", 50)),
        "min_numtrades": min_trades,
        "max_scan_tickers": int(cfg.get("max_scan_tickers", 30)),
    }


def _volume_ratio(candles: list[dict[str, float]], lookback: int = 20) -> float:
    if len(candles) < lookback + 1:
        return 0.0
    recent = candles[-1].get("v") or 0
    avg = sum(c.get("v") or 0 for c in candles[-lookback - 1 : -1]) / lookback
    if avg <= 0:
        return 0.0
    return float(recent) / float(avg)


def _momentum_pct(candles: list[dict[str, float]], bars: int = 5) -> float:
    if len(candles) < bars + 1:
        return 0.0
    start = float(candles[-bars - 1].get("c") or 0)
    end = float(candles[-1].get("c") or 0)
    if start <= 0:
        return 0.0
    return ((end - start) / start) * 100.0


def _atr_pct(candles: list[dict[str, float]], period: int = 14) -> float | None:
    if len(candles) < period + 2:
        return None
    trs: list[float] = []
    for i in range(-period, 0):
        h = float(candles[i].get("h") or 0)
        l = float(candles[i].get("l") or 0)
        pc = float(candles[i - 1].get("c") or 0)
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    atr = sum(trs) / len(trs) if trs else 0
    last = float(candles[-1].get("c") or 0)
    if last <= 0:
        return None
    return (atr / last) * 100.0


def score_swing_ticker(
    symbol: str,
    *,
    cfg: dict[str, Any],
    candles: list[dict[str, float]] | None = None,
    valtoday: float = 0,
    numtrades: int = 0,
    valtoday_max: float = 1,
) -> dict[str, Any]:
    sym = str(symbol).upper()
    if candles is None:
        as_of = _utc_now()
        candles = fetch_moex_candles_as_of(sym, interval=24, as_of=as_of, limit=int(cfg.get("klines_limit", 60)))

    if len(candles) < 30:
        return {
            "symbol": sym,
            "eligible": False,
            "score": 0.0,
            "reject_reason": "insufficient_bars",
            "metrics": {"valtoday": valtoday, "numtrades": numtrades},
        }

    indicators = compute_indicators(candles)
    atr = _atr_pct(candles)
    vol_ratio = _volume_ratio(candles)
    mom = _momentum_pct(candles, bars=int(cfg.get("momentum_bars", 5)))
    rsi = indicators.get("rsi_14")

    liq_score = min(1.0, valtoday / max(valtoday_max, 1)) if valtoday_max > 0 else 0.5
    trades_score = min(1.0, numtrades / max(int(cfg.get("min_numtrades", 100)) * 5, 1))

    vol_min = float(cfg.get("volume_ratio_min", 0.25))
    vol_s = min(1.0, vol_ratio / max(vol_min, 0.01))
    if vol_ratio < vol_min * 0.5:
        vol_s *= 0.35

    mom_min = float(cfg.get("momentum_min_pct", 0.5))
    mom_s = min(1.0, abs(mom) / max(mom_min * 2, 0.01))

    rsi_s = 0.55
    if rsi is not None:
        lo = float(cfg.get("rsi_active_low", 35))
        hi = float(cfg.get("rsi_active_high", 65))
        if lo <= rsi <= hi:
            rsi_s = 0.85
        elif rsi < 30 or rsi > 70:
            rsi_s = 0.95
        else:
            rsi_s = 0.6

    atr_s = 0.5
    if atr is not None:
        atr_s = min(1.0, max(0.2, atr / 3.0))

    w_liq = float(cfg.get("weight_liquidity", 0.35))
    w_vol = float(cfg.get("weight_volume", 0.25))
    w_mom = float(cfg.get("weight_momentum", 0.2))
    w_rsi = float(cfg.get("weight_rsi", 0.1))
    w_atr = float(cfg.get("weight_atr", 0.1))
    score = round(
        w_liq * liq_score
        + w_vol * vol_s
        + w_mom * mom_s
        + w_rsi * rsi_s
        + w_atr * atr_s
        + 0.05 * trades_score,
        4,
    )

    min_score = float(cfg.get("min_score", 0.35))
    eligible = score >= min_score
    reject_reason: str | None = None
    if not eligible:
        if vol_ratio < vol_min * 0.5:
            reject_reason = "volume_too_low"
        else:
            reject_reason = "score_low"
    return {
        "symbol": sym,
        "eligible": eligible,
        "score": score,
        "reject_reason": reject_reason,
        "metrics": {
            "valtoday": valtoday,
            "numtrades": numtrades,
            "volume_ratio": round(vol_ratio, 3),
            "atr_pct": round(atr, 3) if atr is not None else None,
            "momentum_pct": round(mom, 3),
            "rsi_14": rsi,
            "liquidity_score": round(liq_score, 3),
        },
    }


def scan_securities_universe(
    scan_context: str = DEFAULT_SCAN_CONTEXT,
    *,
    top_n: int | None = None,
    config_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = _scan_cfg(config_overrides)
    if top_n is not None:
        cfg["top_n"] = top_n
    if not cfg.get("enabled", True):
        return {"status": "skipped", "reason": "universe_scan_disabled"}

    ctx = str(scan_context or DEFAULT_SCAN_CONTEXT).strip() or DEFAULT_SCAN_CONTEXT
    min_val = float(cfg.get("min_valtoday_mln", 50)) * 1_000_000
    min_trades = int(cfg.get("min_numtrades", 100))
    max_scan = int(cfg.get("max_scan_tickers", 30))
    wl = _whitelist(cfg)
    equities_only = bool(cfg.get("equities_only", True))
    use_whitelist = bool(cfg.get("use_whitelist", False))

    try:
        rows = fetch_tqbr_liquidity_rows()
    except Exception as exc:
        logger.exception("moex_iss_fetch_failed")
        return {"status": "error", "reason": "iss_fetch_failed", "message": str(exc)[:200]}

    liquid: list[dict[str, Any]] = []
    for row in rows:
        sym = row["symbol"]
        if equities_only and not _is_equity_row(row, whitelist=wl):
            continue
        if use_whitelist and sym not in wl:
            continue
        if row["valtoday"] < min_val or row["numtrades"] < min_trades:
            continue
        liquid.append(row)

    liquid.sort(key=lambda r: float(r.get("valtoday") or 0), reverse=True)
    to_score = liquid[:max_scan]
    valtoday_max = float(to_score[0]["valtoday"]) if to_score else 1.0

    ranked: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    _set_scan_progress(scan_context=ctx, total=len(to_score))
    try:
        workers = min(6, max(1, len(to_score)))

        def _score_row(row: dict[str, Any]) -> dict[str, Any]:
            sym = row["symbol"]
            return score_swing_ticker(
                sym,
                cfg=cfg,
                valtoday=float(row.get("valtoday") or 0),
                numtrades=int(row.get("numtrades") or 0),
                valtoday_max=valtoday_max,
            )

        if workers <= 1 or len(to_score) <= 1:
            for idx, row in enumerate(to_score):
                sym = row["symbol"]
                _set_scan_progress(scan_context=ctx, total=len(to_score), done=idx, current=sym)
                try:
                    ranked.append(_score_row(row))
                except Exception as exc:
                    logger.warning("moex_scan_ticker_failed symbol=%s err=%s", sym, exc)
                    errors.append({"symbol": sym, "error": str(exc)[:200]})
                _set_scan_progress(scan_context=ctx, total=len(to_score), done=idx + 1, current=sym)
        else:
            done = 0
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_score_row, row): row for row in to_score}
                for fut in as_completed(futures):
                    row = futures[fut]
                    sym = row["symbol"]
                    try:
                        ranked.append(fut.result())
                    except Exception as exc:
                        logger.warning("moex_scan_ticker_failed symbol=%s err=%s", sym, exc)
                        errors.append({"symbol": sym, "error": str(exc)[:200]})
                    done += 1
                    _set_scan_progress(scan_context=ctx, total=len(to_score), done=done, current=sym)
    finally:
        _clear_scan_progress()

    ranked.sort(key=lambda r: float(r.get("score") or 0), reverse=True)
    top = int(cfg.get("top_n", 5))
    selected = [r for r in ranked if r.get("eligible")][:top]

    result = {
        "status": "ok",
        "scan_context": ctx,
        "scanned_at": _utc_now(),
        "source": "moex_iss",
        "board": "TQBR",
        "liquidity_pool_count": len(liquid),
        "scored_count": len(ranked),
        "ranked": ranked,
        "selected": selected,
        "selected_symbols": [r["symbol"] for r in selected],
        "errors": errors,
        "config": {
            "top_n": top,
            "min_score": cfg.get("min_score"),
            "min_valtoday_mln": cfg.get("min_valtoday_mln"),
        },
    }
    _store_last_scan(ctx, result)
    return result
