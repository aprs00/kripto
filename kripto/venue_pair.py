"""Two-venue paper books (backlog X2, 2026-11-12): one book holds a coin on Hyperliquid AND on Binance at the same time.

First user: `fspread_hold@pair` (funding capture: short the venue whose longs pay more funding, long the other, hold until
the spread flips). Config entries with "venue": "pair" get `shadow:<entry>` and `small:<entry>` books (no main book).
Positions are keyed `<COIN>@hl` / `<COIN>@bn` with the HL coin name on both legs (the Binance symbol is data.hl_to_bn(coin):
kPEPE -> 1000PEPE), exactly the column names of the research dataset "pair" (data.load_pair_panel), so the same strategy
function runs in research and live.

Live daily panel: closed 4h bars of both venues' live caches (HL candles_4h refreshed by the hourly HL step, Binance live_4h
refreshed by venue_bn.run) resampled to days; funding = HL prints from data/hl/funding (refreshed hourly for the live
universe and every held coin) and Binance prints from a small incremental cache of /fapi/v1/fundingRate (data/bn/live_funding).
Universe = coins in BOTH venues' live top-60 lists (+ held legs); research used every coin with funding history on both.
Rebalances once per closed UTC day. Fills: HL legs walk the HL L2 book, Binance legs the Binance depth (each with its
venue's taker fee, size step and min order). Funding accrues per leg from the same stored prints.
Paper only: public data, no keys, nothing here can place an order (HARD RULE 1).
"""
from __future__ import annotations

import os
import time

import numpy as np
import pandas as pd

from . import data
from . import paper as P
from . import venue_bn as V
from .backtest import TAKER_FEE

BN_FUND_DIR = data.DATA / "bn" / "live_funding"
HL_CANDLES = data.DATA / "hl" / "candles_4h"
HL_FUND = data.DATA / "hl" / "funding"
FUND_DAYS = 60          # Binance funding history kept for the signal (lookback 14 d + slack)
DAY_MS = 86_400_000


def leg(col: str) -> tuple[str, str]:
    """`SOL@hl` -> ("SOL", "hl")."""
    return col[:-3], col[-2:]


def bn_funding_refresh(bn, coins: list[str], now_ms: int | None = None) -> None:
    """Incremental cache of Binance funding prints per HL coin name (one request per coin once filled)."""
    V.funding_cache_refresh(bn, coins, BN_FUND_DIR, lambda c: V.sym(data.hl_to_bn(c)), now_ms, FUND_DAYS)


def _prints(path) -> pd.DataFrame:
    return pd.read_parquet(path, columns=["time", "fundingRate"]) if path.exists() else pd.DataFrame(columns=["time", "fundingRate"])


def _daily_funding(prints: pd.DataFrame) -> pd.Series:
    # same convention as the research loaders: a print at tau pays for the period ending at tau
    ts = pd.to_datetime(prints["time"].astype("int64") - 1, unit="ms", utc=True).dt.floor("1D")
    return prints.groupby(ts)["fundingRate"].sum()


def live_panel(coins: list[str], now: pd.Timestamp | None = None) -> dict:
    """Daily two-venue panel (columns `<COIN>@hl` / `<COIN>@bn`), closed days only."""
    now = now or pd.Timestamp.now("UTC")
    close, vol, fund = {}, {}, {}
    for c in coins:
        fh, fb = HL_CANDLES / f"{c}.parquet", V.LIVE_DIR / f"{data.hl_to_bn(c)}.parquet"
        if not fh.exists() or not fb.exists():
            continue
        for col, f, px, usd in ((f"{c}@hl", fh, "c", None), (f"{c}@bn", fb, "c", "qv")):
            k = pd.read_parquet(f)
            idx = pd.to_datetime(k["t"].astype("int64"), unit="ms", utc=True)
            k = k.set_index(idx)
            k = k[k.index + pd.Timedelta(hours=4) <= now]                       # closed 4h bars only
            usdv = k[usd] if usd else k["v"] * k["c"]
            day = k.index.floor("1D")
            last_bar = k.index.to_series().groupby(day).max()
            full = last_bar[last_bar == last_bar.index + pd.Timedelta(hours=20)].index   # the day's 20:00 bar is closed
            close[col] = k[px].groupby(day).last().reindex(full)
            vol[col] = usdv.groupby(day).sum().reindex(full)
        fund[f"{c}@hl"] = _daily_funding(_prints(HL_FUND / f"{c}.parquet"))
        fund[f"{c}@bn"] = _daily_funding(_prints(BN_FUND_DIR / f"{c}.parquet"))
    if not close:
        return {}
    cl = pd.DataFrame(close).sort_index()
    idx = pd.date_range(cl.index.min(), cl.index.max(), freq="1D")
    cols = list(cl.columns)
    p = {"close": cl.reindex(idx), "volume": pd.DataFrame(vol).reindex(index=idx, columns=cols)}
    p["close"] = p["close"].where(p["volume"] > 0)
    # NaN before a venue's stored prints start, so the strategy's rolling mean waits for a full window (as in research)
    p["funding"] = pd.DataFrame(fund).reindex(index=idx, columns=cols)
    return p


def accrue_funding(store: P.Store, marks: dict[str, float], nowms: int | None = None):
    """Each leg pays/receives its own venue's prints since the last accrual (stored prints, no extra requests)."""
    key = "pair_funding_accrued_ms"
    nowms = nowms or int(time.time() * 1000)
    last = int(store.get_meta(key, nowms))
    held = [r for r in store.q("select book, coin, size from positions where size!=0") if P.book_venue(r[0]) == "pair"]
    for book, col, size in held:
        c, v = leg(col)
        pr = _prints((HL_FUND if v == "hl" else BN_FUND_DIR) / f"{c}.parquet")
        pr = pr[(pr["time"] > last) & (pr["time"] <= nowms)]
        for t, rate in zip(pr["time"], pr["fundingRate"]):
            amt = -size * marks.get(col, 0.0) * float(rate)
            store.x("update books set cash=cash+? where name=?", amt, book)
            store.x("insert into funding values(?,?,?,?,?)",
                    pd.Timestamp(int(t), unit="ms", tz="UTC").isoformat(), book, col, amt, float(rate))
    store.set_meta(key, nowms)


def pair_marks(hl_marks: dict[str, float], bn_marks: dict[str, float], coins) -> dict[str, float]:
    out = {}
    for c in coins:
        if hl_marks.get(c, 0) > 0:
            out[f"{c}@hl"] = hl_marks[c]
        if bn_marks.get(data.hl_to_bn(c), 0) > 0:
            out[f"{c}@bn"] = bn_marks[data.hl_to_bn(c)]
    return out


def run(store: P.Store, cfg: dict, risk: dict, hl, bn_run: dict, hl_marks: dict, sz_dec: dict, hl_coins: list[str],
        now: pd.Timestamp | None = None):
    """One hourly step for the two-venue books. Funding is accrued every hour; trading happens once per closed day."""
    entries = {n: sc for n, sc in cfg.items() if P.venue_of(sc) == "pair"}
    bn, filters = bn_run["bn"], bn_run["filters"]
    held = {leg(c)[0] for b, c in store.q("select book, coin from positions where size!=0") if P.book_venue(b) == "pair"}
    bn_names = set(bn_run["coins"])
    coins = sorted({c for c in hl_coins if data.hl_to_bn(c) in bn_names and data.hl_to_bn(c) in filters} | held)
    marks = pair_marks(hl_marks, bn_run["marks"], coins)
    now = now or pd.Timestamp.now("UTC")
    day = str((now - pd.Timedelta(days=1)).floor("1D"))          # the latest closed day
    live_books = [f"{p}{n}" for n, sc in entries.items() if sc.get("status") != "retired" for p in ("shadow:", "small:")]
    due = any(not store.q("select 1 from rebalances where book=? and bar=?", b, day) for b in live_books)
    now_ms = int(now.timestamp() * 1000)
    bn_funding_refresh(bn, sorted(coins if due else held), now_ms)
    if store.get_meta("pair_funding_accrued_ms") is None:
        store.set_meta("pair_funding_accrued_ms", now_ms)
    accrue_funding(store, marks, now_ms)

    strat_w, last_bar = {}, day
    if due:
        panel = live_panel(coins, now)
        if panel and str(panel["close"].index[-1]) == day:
            strat_w = P.compute_targets(store, entries, panel, day)
        else:
            store.event("WARN", f"pair venue: no complete daily bar for {day} yet; retrying next hour")
    l2_hl, l2_bn = {}, {}   # order books are fetched lazily, only for legs that actually trade

    def fill(col, d):
        c, v = leg(col)
        return P.simulate_fill(hl, c, d, l2_hl) if v == "hl" else V.simulate_fill(bn, data.hl_to_bn(c), d, l2_bn)

    def round_size(col, d):
        c, v = leg(col)
        if v == "hl":
            return float(np.round(d, sz_dec.get(c, 4)))
        return V.round_step(d, filters.get(data.hl_to_bn(c), {}).get("step", 0.0))

    def min_notional(col):
        c, v = leg(col)
        return P.MIN_NOTIONAL if v == "hl" else filters.get(data.hl_to_bn(c), {}).get("min_notional", 5.0)

    def reb(book, tgt, reason):
        P.rebalance(None, store, book, tgt, marks, {}, reason, round_size=round_size, fill=fill,
                    min_notional=min_notional, fee_rate=lambda col: TAKER_FEE if col.endswith("@hl") else V.TAKER_FEE_BN)

    with P.trade_lock():   # every hour: kill switch + retired close-out; trades only when strat_w has the new day
        books = P.run_books(store, entries, risk, marks, strat_w, last_bar, None, reb)
    for b in books:
        eq, gross = P.book_equity(store, b, marks)
        store.x("insert into equity values(?,?,?,?,?)", P.now_iso(), b, eq, gross, len(store.positions(b)))
    store.set_meta("pair_last_run", P.now_iso())
    if strat_w:
        store.set_meta("pair_last_bar", day)
    return {"coins": coins, "marks": marks}
