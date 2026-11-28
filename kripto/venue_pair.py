"""Two-venue paper books (backlog X2, 2026-11-12): one book holds a coin on Hyperliquid AND on Binance at the same time.

First user: `fspread_hold@pair` (funding capture: short the venue whose longs pay more funding, long the other, hold until
the spread flips). Config entries with "venue": "pair" get `shadow:<entry>` and `small:<entry>` books; incubation/active pair entries with alloc > 0
form the two-account main book `main@pair` (+ `small:main@pair`): the third alternative home for the reference $1,000, one HL and one
Binance account (design.md 2026-11-27).
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


MAIN = "main@pair"
VENUES = ("hl", "bn")
TRANSFER_RATIO = 0.70   # KS1 (design.md 2026-11-28): rebalance the two accounts to 50/50 when one is < 70 % of the other
ACCOUNT_GUARD = 0.40    # flatten + halt a pair book when one venue account is 40 % below its peak since the last transfer


def account_equity(store: P.Store, book: str, marks: dict[str, float]) -> dict[str, float]:
    """KS1: a pair book is two margin accounts (half the start capital each) that cannot net. Each account = start/2
    + its legs' trade cash flows, fees and funding + the mark value of its legs + transfers in. Sums to book_equity."""
    start = store.q("select start_equity from books where name=?", book)[0][0]
    out = {}
    for v in VENUES:
        flows = store.q("select coalesce(sum(-size*px-fee),0) from fills where book=? and coin like ?", book, f"%@{v}")[0][0]
        fund = store.q("select coalesce(sum(amount),0) from funding where book=? and coin like ?", book, f"%@{v}")[0][0]
        tr = store.q("select transfer from accounts where book=? and venue=?", book, v)
        mv = sum(sz * marks.get(c, 0.0) for c, sz in store.positions(book).items() if c.endswith(f"@{v}"))
        out[v] = start / 2 + flows + fund + mv + (tr[0][0] if tr else 0.0)
    return out


def account_step(store: P.Store, book: str, marks: dict[str, float]) -> dict:
    """Hourly, before trading: (1) if one account is < TRANSFER_RATIO of the other, move cash to 50/50 (a paper transfer: in a
    real two-account setup the owner moves it by hand, so this is optimistic about timing) and reset both peaks; (2) track
    each account's peak (checked first, see below); (3) if an account is ACCOUNT_GUARD below its peak, the book is flattened and halted (what a
    liquidation of one side would force). Returns {"accounts", "transferred", "guard"}."""
    pos = store.positions(book)
    if any(marks.get(c, 0.0) <= 0 for c in pos):           # an unpriced leg would read as a loss
        return {"accounts": None, "transferred": 0.0, "guard": False}
    acc = account_equity(store, book, marks)
    for v in VENUES:
        if not store.q("select 1 from accounts where book=? and venue=?", book, v):
            store.x("insert into accounts values(?,?,0,?)", book, v, acc[v])
    # the guard is checked BEFORE any transfer: a transfer made after an account went through its floor would not have saved it
    guard = False
    for v in VENUES:
        peak = max(store.q("select peak from accounts where book=? and venue=?", book, v)[0][0], acc[v])
        store.x("update accounts set peak=? where book=? and venue=?", peak, book, v)
        if acc[v] < peak * (1 - ACCOUNT_GUARD):
            guard = True
    lo, hi = sorted(VENUES, key=lambda v: acc[v])
    moved = 0.0
    if not guard and acc[hi] > 0 and acc[lo] < TRANSFER_RATIO * acc[hi]:
        moved = (acc[hi] - acc[lo]) / 2
        store.x("update accounts set transfer=transfer+? where book=? and venue=?", moved, book, lo)
        store.x("update accounts set transfer=transfer-? where book=? and venue=?", moved, book, hi)
        store.x("insert into transfers values(?,?,?,?,?)", P.now_iso(), book, hi, lo, moved)
        store.event("INFO", f"{book}: account transfer ${moved:.2f} {hi} -> {lo} ({acc[lo]:.2f} < {TRANSFER_RATIO:.0%} of {acc[hi]:.2f})")
        acc = account_equity(store, book, marks)
        for v in VENUES:
            store.x("update accounts set peak=? where book=? and venue=?", acc[v], book, v)
    ntr = store.q("select count(*), coalesce(sum(amount),0) from transfers where book=?", book)[0]
    store.set_meta(f"accounts:{book}", __import__("json").dumps({"ts": P.now_iso(), **{v: round(acc[v], 2) for v in VENUES},
                                                                  "transfers": ntr[0], "moved": round(ntr[1], 2)}))
    return {"accounts": acc, "transferred": moved, "guard": guard}


def whole_pairs(tgt: pd.Series, eq: float, min_notional) -> pd.Series:
    """A pair is held whole or not at all (SMP 2026-11-28): if either leg's target notional is below its venue's minimum order at
    this book's equity, both legs' targets are 0. Without this the $200 twin held one-legged positions (BN $5 minimum let the
    Binance leg through while HL's $10 blocked the hedge: small:main@pair held GRAM@bn and ZEC@bn unhedged). A 0 target closes an
    existing orphan (closing ignores the minimum)."""
    if tgt.empty:
        return tgt
    out = tgt.copy()
    by = {}
    for col in tgt.index:
        by.setdefault(leg(col)[0], []).append(col)
    for c, cols in by.items():
        if len(cols) == 2 and any(abs(float(tgt[x])) * eq < min_notional(x) for x in cols):
            out[cols] = 0.0
    return out


def main_live(store: P.Store, entries: dict) -> bool:
    """The two-account main book (design.md 2026-11-27) runs once a pair entry is incubation/active with alloc > 0, and keeps
    running (to close out / follow alloc changes) once it exists."""
    return any(sc.get("status") in ("incubation", "active") and sc.get("alloc", 0) > 0 for sc in entries.values()) \
        or bool(store.q("select 1 from books where name=?", MAIN))


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
    if any(sc.get("status") in ("incubation", "active") and sc.get("alloc", 0) > 0 for sc in entries.values()):
        live_books += [MAIN, f"small:{MAIN}"]
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
        if reason not in ("kill_switch", "retired"):
            tgt = whole_pairs(tgt, P.book_equity(store, book, marks)[0], min_notional)
        P.rebalance(None, store, book, tgt, marks, {}, reason, round_size=round_size, fill=fill,
                    min_notional=min_notional, fee_rate=lambda col: TAKER_FEE if col.endswith("@hl") else V.TAKER_FEE_BN)

    with P.trade_lock():   # every hour: account transfers/guard (KS1), kill switch + retired close-out; trades only when strat_w has the new day
        for (b, halted) in store.q("select name, halted from books"):
            if P.book_venue(b) != "pair" or halted:
                continue
            st = account_step(store, b, marks)
            if st["guard"]:
                store.event("ALERT", f"{b}: venue-account guard (one account {ACCOUNT_GUARD:.0%} below its peak: {st['accounts']}); flattening")
                reb(b, pd.Series(dtype=float), "kill_switch")
                store.x("update books set halted=1 where name=?", b)
        books = P.run_books(store, entries, risk, marks, strat_w, last_bar, MAIN if main_live(store, entries) else None, reb)
    for b in books:
        eq, gross = P.book_equity(store, b, marks)
        store.x("insert into equity values(?,?,?,?,?)", P.now_iso(), b, eq, gross, len(store.positions(b)))
    store.set_meta("pair_last_run", P.now_iso())
    if strat_w:
        store.set_meta("pair_last_bar", day)
    return {"coins": coins, "marks": marks}
