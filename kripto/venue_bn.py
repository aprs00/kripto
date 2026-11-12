"""Binance USDT-M perps paper venue (owner direction 2026-11-09; design.md changelog, backlog B1).

Same accounting as the HL engine in paper.py. Differences: data and marks come from Binance PUBLIC endpoints
(kripto/bn.py, no keys, cannot trade), fills walk the live Binance depth (top 20 levels) + 5 bp taker fee,
sizes are rounded to the symbol's step size, and the min order is the symbol's MIN_NOTIONAL (mostly $5).
Books: `main_bn` (config/risk.json start_equity) and `shadow:<entry>@bn` for config entries with "venue": "bn".
Live panel = 4h klines (closed bars only) incl. taker buy quote volume (`taker_buy`), so `flow` can run live.
Funding is accrued from /fapi/v1/fundingRate (usually 8-hourly). The panel's `funding` is NaN (no strategy that
trades on Binance uses it yet), so a funding-based strategy needs that added first.
"""
from __future__ import annotations

import json
import math
import os
import time

import numpy as np
import pandas as pd

from . import data
from .bn import BN
from . import paper as P

TAKER_FEE_BN = 0.0005
LIVE_DIR = data.DATA / "bn" / "live_4h"
INFO_CACHE = data.DATA / "bn" / "live_exchange_info.json"
UNIVERSE = int(os.environ.get("KRIPTO_BN_UNIVERSE", "60"))
BAR_MS = 4 * 3600 * 1000


def sym(coin: str) -> str:
    return coin + "USDT"


def symbol_filters(bn: BN, max_age_h: float = 24) -> dict[str, dict]:
    """coin -> {step, min_notional} for TRADING USDT perpetuals. exchangeInfo is cached on disk for a day."""
    info = None
    if INFO_CACHE.exists() and time.time() - INFO_CACHE.stat().st_mtime < max_age_h * 3600:
        info = json.loads(INFO_CACHE.read_text())
    if info is None:
        info = bn.exchange_info()
        INFO_CACHE.parent.mkdir(parents=True, exist_ok=True)
        INFO_CACHE.write_text(json.dumps(info))
    out = {}
    for x in info["symbols"]:
        if x.get("contractType") != "PERPETUAL" or x.get("quoteAsset") != "USDT" or x.get("status") != "TRADING":
            continue
        f = {g["filterType"]: g for g in x["filters"]}
        step = float((f.get("MARKET_LOT_SIZE") or f["LOT_SIZE"])["stepSize"])
        out[x["symbol"].removesuffix("USDT")] = {"step": step, "min_notional": float(f["MIN_NOTIONAL"]["notional"])}
    return out


def round_step(d: float, step: float) -> float:
    """Round a size toward zero to the exchange step (never trade more than asked)."""
    if step <= 0:
        return d
    n = math.floor(abs(d) / step + 1e-9)
    return math.copysign(round(n * step, 12), d)


def refresh(bn: BN, filters: dict, held: set[str], history_days: int = P.HISTORY_DAYS) -> list[str]:
    """Top-UNIVERSE coins by 24h quote volume (+ anything held); incremental 4h kline cache on disk."""
    tick = [t for t in bn.ticker_24h() if t["symbol"].removesuffix("USDT") in filters and t["symbol"].endswith("USDT")]
    tick.sort(key=lambda t: float(t["quoteVolume"]), reverse=True)
    coins = [t["symbol"].removesuffix("USDT") for t in tick[:UNIVERSE]]
    if "BTC" not in coins:
        coins.append("BTC")  # beta reference for the hedged strategies
    coins = list(dict.fromkeys(coins + sorted(c for c in held if c in filters)))
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    floor_ms = int((pd.Timestamp.now("UTC") - pd.Timedelta(days=history_days + 10)).timestamp() * 1000)
    for c in coins:
        f = LIVE_DIR / f"{c}.parquet"
        have = pd.read_parquet(f) if f.exists() else None
        start = int(have["t"].max()) if have is not None and len(have) else floor_ms  # refetch the last (forming) bar
        # small pages once cached: klines weight is set by `limit` (<100 → 1, >1000 → 10); page forward if behind
        limit = 99 if have is not None and len(have) else 1500
        rows = []
        while True:
            page = bn.klines(sym(c), "4h", start_ms=start, limit=limit)
            rows += page
            if len(page) < limit:
                break
            start = int(page[-1][0]) + 1
        if not rows:
            continue
        k = pd.DataFrame([r[:11] for r in rows],
                         columns=["t", "o", "h", "l", "c", "v", "T", "qv", "n", "tbv", "tbqv"])
        k = k[["t", "o", "h", "l", "c", "qv", "tbqv"]].astype(float)
        k["t"] = k["t"].astype("int64")
        d = pd.concat(([have] if have is not None else []) + [k])
        d = d.drop_duplicates("t", keep="last").sort_values("t")
        d = d[d["t"] >= floor_ms].reset_index(drop=True)
        tmp = f.with_suffix(".tmp")
        d.to_parquet(tmp)
        tmp.replace(f)
    return coins


def live_panel(coins: list[str], now: pd.Timestamp | None = None) -> dict:
    now = now or pd.Timestamp.now("UTC")
    cols = {"close": "c", "high": "h", "low": "l", "volume": "qv", "taker_buy": "tbqv"}
    frames = {k: {} for k in cols}
    for c in coins:
        f = LIVE_DIR / f"{c}.parquet"
        if not f.exists():
            continue
        df = pd.read_parquet(f)
        df.index = pd.to_datetime(df["t"], unit="ms", utc=True)
        for k, col in cols.items():
            frames[k][c] = df[col]
    p = {k: pd.DataFrame(v).sort_index() for k, v in frames.items()}
    idx = pd.date_range(p["close"].index.min(), p["close"].index.max(), freq="4h")
    p = {k: v.reindex(idx) for k, v in p.items()}
    p["close"] = p["close"].where(p["volume"] > 0)
    p["funding"] = pd.DataFrame(np.nan, idx, p["close"].columns)
    closed = idx + pd.Timedelta(hours=4) <= now  # bar t is closed only once t + 4h <= now
    cutoff = now - pd.Timedelta(days=P.HISTORY_DAYS)
    return {k: v.loc[closed & (v.index >= cutoff)] for k, v in p.items()}


def simulate_fill(bn: BN, coin: str, size: float, cache: dict | None = None) -> tuple[float, float, float]:
    """Walk the live Binance book (top 20). Returns (avg_px, mid, slippage_bps). size>0 buy.
    `cache`: one dict per run; books trading the same coin within P.L2_TTL share one depth snapshot."""
    hit = cache.get(coin) if cache is not None else None
    if hit and time.time() - hit[0] < P.L2_TTL:
        book = hit[1]
    else:
        book = bn.depth(sym(coin), 20)
        if cache is not None:
            cache[coin] = (time.time(), book)
    bids = [(float(p), float(q)) for p, q in book["bids"]]
    asks = [(float(p), float(q)) for p, q in book["asks"]]
    mid = (bids[0][0] + asks[0][0]) / 2
    levels = asks if size > 0 else bids
    remaining, cost = abs(size), 0.0
    for px, q in levels:
        take = min(remaining, q)
        cost += take * px
        remaining -= take
        if remaining <= 1e-12:
            break
    if remaining > 1e-12:  # deeper than the visible book: punish with 2% beyond the last level
        cost += remaining * levels[-1][0] * (1.02 if size > 0 else 0.98)
    px = cost / abs(size)
    return px, mid, (px / mid - 1) * 1e4 * (1 if size > 0 else -1)


def accrue_funding(bn: BN, store: P.Store, marks: dict[str, float]):
    key = "bn_funding_accrued_ms"
    nowms = int(time.time() * 1000)
    last = int(store.get_meta(key, nowms))
    held = [r for r in store.q("select book, coin, size from positions where size!=0") if P.book_venue(r[0]) == "bn"]
    rates = {c: [(int(r["fundingTime"]), float(r["fundingRate"]), float(r.get("markPrice") or 0) or marks.get(c, 0.0))
                 for r in bn.funding_rate(sym(c), last + 1, nowms)]
             for c in sorted({c for _, c, _ in held})}
    for book, c, size in held:
        for t, rate, mk in rates.get(c, []):
            amt = -size * mk * rate
            store.x("update books set cash=cash+? where name=?", amt, book)
            store.x("insert into funding values(?,?,?,?,?)",
                    pd.Timestamp(t, unit="ms", tz="UTC").isoformat(), book, c, amt, rate)
    store.set_meta(key, nowms)


def run(store: P.Store, cfg: dict, risk: dict, bn: BN | None = None) -> dict:
    """One hourly step for every Binance config entry (venue "bn") plus the `main_bn` book. Returns the run's client,
    coins, marks and symbol filters (the two-venue pair books reuse them instead of asking again)."""
    bn = bn or BN(min_interval=float(os.environ.get("KRIPTO_BN_INTERVAL", "1.0")))
    entries = {n: sc for n, sc in cfg.items() if P.venue_of(sc) == "bn"}
    filters = symbol_filters(bn)
    coins = refresh(bn, filters, P.held_coins(store, "bn"))
    marks = {x["symbol"].removesuffix("USDT"): float(x["markPrice"]) for x in bn.premium_index()
             if x["symbol"].endswith("USDT") and x["symbol"].removesuffix("USDT") in filters}
    if store.get_meta("bn_funding_accrued_ms") is None:
        store.set_meta("bn_funding_accrued_ms", int(time.time() * 1000))
    accrue_funding(bn, store, marks)

    panel = live_panel(coins)
    last_bar = str(panel["close"].index[-1])
    strat_w = P.compute_targets(store, entries, panel, last_bar)

    depth = {}   # depth snapshots of this run, shared by all books trading the same coin

    def reb(book, tgt, reason):
        P.rebalance(None, store, book, tgt, marks, {}, reason,
                    round_size=lambda c, d: round_step(d, filters.get(c, {}).get("step", 0.0)),
                    fill=lambda c, d: simulate_fill(bn, c, d, depth),
                    min_notional=lambda c: filters.get(c, {}).get("min_notional", 5.0),
                    fee_rate=TAKER_FEE_BN)

    with P.trade_lock():
        books = P.run_books(store, entries, risk, marks, strat_w, last_bar, "main_bn", reb)
    for b in books:
        eq, gross = P.book_equity(store, b, marks)
        store.x("insert into equity values(?,?,?,?,?)", P.now_iso(), b, eq, gross, len(store.positions(b)))
    store.set_meta("bn_last_run", P.now_iso())
    store.set_meta("bn_last_bar", last_bar)
    return {"bn": bn, "coins": coins, "marks": marks, "filters": filters}
