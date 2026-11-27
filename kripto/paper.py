"""Paper-trading engine for Hyperliquid perps. Run once per hour (systemd timer):

    python -m kripto.paper run          # update data, accrue funding, rebalance due books, mark equity
    python -m kripto.paper status       # human/agent readable summary

Accounting: each book holds USD cash and signed coin sizes. Buying size q at price p: cash -= q*p.
Equity = cash + sum(q * mark). (Equivalent to perp PnL accounting.) Funding: cash -= q * mark * rate.
Fills: simulated taker orders that walk the LIVE L2 book (top 20 levels) + taker fee.
NOTHING here can place a real order: there are no keys and no exchange endpoint other than public /info.
Venues: HL here; Binance USDT-M perps in venue_bn.py (books named `main_bn` / `shadow:<entry>@bn`).
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import collect, data
from .backtest import TAKER_FEE
from .hl import HL
from .strategies import REGISTRY

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "state" / "paper.db"
CFG = ROOT / "config" / "strategies.json"
RISK = ROOT / "config" / "risk.json"
LIVE_INTERVAL = "4h"
LIVE_UNIVERSE = int(os.environ.get("KRIPTO_LIVE_UNIVERSE", "60"))  # top coins by volume kept fresh (+ anything held)
MIN_NOTIONAL = 10.0        # HL minimum order value
HISTORY_DAYS = 220

SCHEMA = """
create table if not exists books(name text primary key, cash real, start_equity real, peak real,
    halted integer default 0, created text);
create table if not exists positions(book text, coin text, size real, primary key(book, coin));
create table if not exists fills(ts text, book text, coin text, size real, px real, mid real, fee real,
    slip_bps real, reason text);
create table if not exists equity(ts text, book text, equity real, gross real, n_pos integer);
create table if not exists funding(ts text, book text, coin text, amount real, rate real);
create table if not exists events(ts text, level text, msg text);
create table if not exists meta(k text primary key, v text);
create table if not exists rebalances(book text, bar text, primary key(book, bar));
create table if not exists targets(strategy text primary key, bar text, weights text);
create table if not exists universe(venue text, bar text, coins text, primary key(venue, bar));
create table if not exists sleeve(book text, coin text, size real, t0 integer, primary key(book, coin));
"""


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Store:
    def __init__(self, path: Path = DB):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.c = sqlite3.connect(path)
        self.c.executescript(SCHEMA)

    def q(self, sql, *a):
        return self.c.execute(sql, a).fetchall()

    def x(self, sql, *a):
        self.c.execute(sql, a)
        self.c.commit()

    def event(self, level, msg):
        print(f"[{level}] {msg}", flush=True)
        self.x("insert into events values(?,?,?)", now_iso(), level, msg)

    def get_meta(self, k, default=None):
        r = self.q("select v from meta where k=?", k)
        return r[0][0] if r else default

    def set_meta(self, k, v):
        self.x("insert or replace into meta values(?,?)", k, str(v))

    def ensure_book(self, name, cash):
        if not self.q("select 1 from books where name=?", name):
            self.x("insert into books values(?,?,?,?,0,?)", name, cash, cash, cash, now_iso())
            self.event("INFO", f"created book {name} with ${cash:.2f}")

    def resize_untouched(self, name, cash):
        """A book that has never traded takes the configured starting equity (the main books moved from $200 to
        $1,000 on 2026-11-10). A book with any fill or position keeps its history and size."""
        row = self.q("select cash, start_equity from books where name=?", name)
        if not row or abs(row[0][1] - cash) < 1e-9 or abs(row[0][0] - row[0][1]) > 1e-9:
            return
        if self.q("select 1 from fills where book=? limit 1", name) or self.positions(name):
            return
        self.x("update books set cash=?, start_equity=?, peak=? where name=?", cash, cash, cash, name)
        self.x("delete from equity where book=?", name)  # flat rows at the old size would read as a fake jump
        self.event("INFO", f"resized untouched book {name} to ${cash:.2f}")

    def positions(self, book) -> dict[str, float]:
        return {c: s for c, s in self.q("select coin,size from positions where book=? and size!=0", book)}

    def cash(self, book) -> float:
        return self.q("select cash from books where name=?", book)[0][0]


@contextlib.contextmanager
def trade_lock():
    """Held by whatever is trading books (the hourly step, the live watcher's kill switch): one at a time across processes."""
    DB.parent.mkdir(parents=True, exist_ok=True)
    with open(DB.parent / "trade.lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def load_cfg():
    return json.loads(CFG.read_text()), json.loads(RISK.read_text())


def venue_of(sc: dict) -> str:
    """Venue a config entry trades: "hl" (default) or "bn". Binance entries are named `<strategy>@bn`."""
    return sc.get("venue", "hl")


def book_venue(book: str) -> str:
    """hl, bn or pair. Binance books: main_bn, shadow:<entry>@bn and their small-account twins small:main_bn, small:<entry>@bn.
    Two-venue books (venue_pair.py): shadow:<entry>@pair / small:<entry>@pair, positions keyed `<COIN>@hl` / `<COIN>@bn`."""
    if book.endswith("@pair"):
        return "pair"
    return "bn" if book.endswith("_bn") or book.endswith("@bn") else "hl"


def strategy_fn(name: str, sc: dict):
    """Config entry -> registered strategy function (`strategy` field lets one strategy run on several venues)."""
    return REGISTRY.get(sc.get("strategy", name))


def held_coins(store: Store, venue: str) -> set[str]:
    """Coins (venue names) held by any book on `venue`, including the `venue` legs of two-venue (pair) books, so each
    venue's data refresh keeps every held coin fresh."""
    out = set()
    for b, c in store.q("select book, coin from positions where size!=0"):
        if book_venue(b) == venue:
            out.add(c)
        elif book_venue(b) == "pair" and c.endswith("@" + venue):
            out.add(data.hl_to_bn(c[:-3]) if venue == "bn" else c[:-3])
    return out


# --------------------------------------------------------------------------- market data
def refresh_data(hl: HL, store: Store) -> list[str]:
    uni = data.hl_universe(hl)
    uni = uni[~uni["isDelisted"]]
    coins = list(uni["name"][:LIVE_UNIVERSE])
    held = held_coins(store, "hl")
    coins = list(dict.fromkeys(coins + sorted(held)))
    data.hl_update_candles(coins, LIVE_INTERVAL, hl, log=lambda m: None)
    # context snapshot (funding/OI/premium) -> research dataset for HL-specific hypotheses
    snap = uni.assign(ts=pd.Timestamp.now("UTC").floor("min"))
    keep = [c for c in ["ts", "name", "funding", "premium", "openInterest", "oraclePx", "markPx", "midPx",
                        "dayNtlVlm", "maxLeverage"] if c in snap.columns]
    d = data.DATA / "hl" / "ctx"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{pd.Timestamp.now('UTC'):%Y-%m}.parquet"
    snap = snap[keep].astype({k: str for k in keep if k not in ("ts", "dayNtlVlm")})
    (pd.concat([pd.read_parquet(p), snap]) if p.exists() else snap).to_parquet(p)
    return coins


def refresh_funding(hl: HL, coins: list[str]):
    """Stored HL funding history (pair books, research). Runs AFTER the HL trades (2026-11-25): one request per coin took ~3.5 min
    before the fills, and live HL fills ~11 min after the bar close drifted ≈ +10 bp against us (assumptions row 20). No live HL
    signal reads this hour's funding."""
    since = (pd.Timestamp.now("UTC") - pd.Timedelta(days=30)).strftime("%Y-%m-%d")  # live needs little; deep backfill is done offline
    data.hl_update_funding(coins, since, hl, log=lambda m: None)


def live_panel(coins: list[str]) -> dict:
    p = data.load_hl_panel(LIVE_INTERVAL, coins)
    cutoff = pd.Timestamp.now("UTC") - pd.Timedelta(days=HISTORY_DAYS)
    bar = pd.Timedelta(hours=4)
    # drop the still-forming candle: bar t is closed only once t + bar <= now
    closed = p["close"].index + bar <= pd.Timestamp.now("UTC")
    return {k: v.loc[closed & (v.index >= cutoff)] for k, v in p.items()}


# --------------------------------------------------------------------------- execution sim
L2_TTL = 180.0   # seconds a fetched order book may be reused by the other books trading the same coin in this run


def simulate_fill(hl: HL, coin: str, size: float, cache: dict | None = None) -> tuple[float, float, float]:
    """Walk the live book. Returns (avg_px, mid, slippage_bps). size>0 buy.
    `cache` ({coin: (time, book)}, one per run): books that trade the same coin within L2_TTL share one snapshot, so
    adding books (e.g. the $200 twins) does not add API calls."""
    hit = cache.get(coin) if cache is not None else None
    if hit and time.time() - hit[0] < L2_TTL:
        book = hit[1]
    else:
        book = hl.l2_book(coin)
        if cache is not None:
            cache[coin] = (time.time(), book)
        try:  # keep the book we already paid a request for (non-backfillable L2 data, T6a)
            collect.store_l2(book, coin)
        except Exception:
            pass
    bids, asks = book["levels"][0], book["levels"][1]
    mid = (float(bids[0]["px"]) + float(asks[0]["px"])) / 2
    levels = asks if size > 0 else bids
    remaining, cost = abs(size), 0.0
    for lv in levels:
        take = min(remaining, float(lv["sz"]))
        cost += take * float(lv["px"])
        remaining -= take
        if remaining <= 1e-12:
            break
    if remaining > 1e-12:  # deeper than visible book: punish with 2% beyond last level
        last = float(levels[-1]["px"])
        cost += remaining * last * (1.02 if size > 0 else 0.98)
    px = cost / abs(size)
    slip = (px / mid - 1) * 1e4 * (1 if size > 0 else -1)
    return px, mid, slip


# --------------------------------------------------------------------------- core steps
def hl_held(store: Store) -> list[tuple]:
    return [tuple(r) for r in store.q("select book, coin, size from positions where size!=0") if book_venue(r[0]) == "hl"]


def accrue_funding(hl: HL, store: Store, marks: dict[str, float], held: list[tuple] | None = None, nowms: int | None = None):
    """Funding since the last accrual on `held` (book, coin, size): the positions held over that period. run_once snapshots
    them BEFORE trading and accrues after the trades (so the API calls do not delay the fills); default = current positions."""
    last = int(store.get_meta("funding_accrued_ms", int(time.time() * 1000)))
    nowms = int(time.time() * 1000) if nowms is None else nowms
    held = hl_held(store) if held is None else held
    coins = sorted({c for _, c, _ in held})
    rates = {}
    for c in coins:
        rows = hl.funding_history(c, last + 1, nowms)
        rates[c] = [(r["time"], float(r["fundingRate"])) for r in rows]
    for book, c, size in held:
        for t, rate in rates.get(c, []):
            amt = -size * marks.get(c, 0.0) * rate
            store.x("update books set cash=cash+? where name=?", amt, book)
            store.x("insert into funding values(?,?,?,?,?)",
                    pd.Timestamp(t, unit="ms", tz="UTC").isoformat(), book, c, amt, rate)
    store.set_meta("funding_accrued_ms", nowms)


def sleeve(store: Store, book: str) -> dict[str, float]:
    """coin -> size an overlay sleeve (the ladder) holds inside `book`; the rest of the position belongs to the book's rebalance."""
    return {c: s for c, s in store.q("select coin, size from sleeve where book=? and size!=0", book)}


def book_equity(store: Store, book: str, marks: dict[str, float]) -> tuple[float, float]:
    pos = store.positions(book)
    eq = store.cash(book) + sum(s * marks.get(c, 0.0) for c, s in pos.items())
    gross = sum(abs(s) * marks.get(c, 0.0) for c, s in pos.items())
    return eq, gross


def apply_risk(w: pd.Series, risk: dict) -> pd.Series:
    w = w.fillna(0.0).clip(-risk["max_asset_weight"], risk["max_asset_weight"])
    g = w.abs().sum()
    if g > risk["max_gross"]:
        w = w * risk["max_gross"] / g
    return w


def rebalance(hl: HL, store: Store, book: str, target_w: pd.Series, marks: dict[str, float],
              meta_sz: dict[str, int], reason: str, *, round_size=None, fill=None,
              min_notional=None, fee_rate=TAKER_FEE):
    """Trade `book` to target weights. HL defaults; another venue passes round_size(coin, d), fill(coin, d) and
    min_notional(coin). `fee_rate` is a number or fee_rate(coin) (two-venue books pay each leg its venue's fee)."""
    round_size = round_size or (lambda c, d: float(np.round(d, meta_sz.get(c, 4))))
    fill = fill or (lambda c, d: simulate_fill(hl, c, d))
    min_notional = min_notional or (lambda c: MIN_NOTIONAL)
    eq, _ = book_equity(store, book, marks)
    pos = store.positions(book)
    # Overlay sleeves (kripto/ladder.py trading inside a main book, same account): the part of a position the sleeve owns is
    # not this rebalance's to net. A kill switch or retirement closes everything, sleeve included, and drops the sleeve rows.
    sl = sleeve(store, book)
    if reason in ("kill_switch", "retired"):
        if sl:
            store.x("delete from sleeve where book=?", book)
    else:
        pos = {c: s - sl.get(c, 0.0) for c, s in pos.items()}
    coins = sorted(set(pos) | set(target_w[target_w != 0].index))
    for c in coins:
        if c not in marks:
            continue
        tgt_sz = float(target_w.get(c, 0.0)) * eq / marks[c]
        d = tgt_sz - pos.get(c, 0.0)
        d = round_size(c, d)
        closing = abs(tgt_sz) < 1e-12 and abs(pos.get(c, 0.0)) > 1e-12
        if closing:
            d = -pos.get(c, 0.0)
        if d == 0 or (abs(d) * marks[c] < min_notional(c) and not closing):
            continue
        px, mid, slip = fill(c, d)
        fee = abs(d) * px * (fee_rate(c) if callable(fee_rate) else fee_rate)
        with store.c:   # ONE transaction per fill: the live watcher must never see cash moved without the position
            store.c.execute("update books set cash=cash-?-? where name=?", (d * px, fee, book))
            store.c.execute("insert into positions values(?,?,?) on conflict(book,coin) do update set "
                            "size=size+excluded.size", (book, c, d))
            store.c.execute("insert into fills values(?,?,?,?,?,?,?,?,?)",
                            (now_iso(), book, c, d, px, mid, fee, slip, reason))


def record_universe(store: Store, venue: str, panel: dict, last_bar: str):
    """The coins the strategies saw at this bar (first run of the bar wins), so scripts/live_vs_backtest.py can replay
    with the point-in-time universe: Binance's top-volume universe drifts, and a replay on today's list holds coins
    (e.g. AGT after its pump) that live could not have held then."""
    store.x("insert or ignore into universe values(?,?,?)", venue, last_bar, json.dumps(sorted(panel["close"].columns)))


def compute_targets(store: Store, entries: dict, panel: dict, last_bar: str) -> dict[str, pd.Series]:
    """Latest target weights per non-retired config entry (saved in `targets` for the main-book blend)."""
    strat_w: dict[str, pd.Series] = {}
    for name, sc in entries.items():
        fn = strategy_fn(name, sc)
        if sc.get("status") == "retired" or fn is None:
            continue
        try:
            w = fn(panel, **sc.get("params", {}))
            row = w.iloc[-1]
            if row.notna().any():
                row = row.fillna(0.0)
                strat_w[name] = row
                store.x("insert or replace into targets values(?,?,?)", name, last_bar,
                        json.dumps({k: float(v) for k, v in row.items() if v != 0}))
        except Exception as e:  # a broken strategy must not take the engine down
            store.event("ERROR", f"strategy {name} failed: {e!r}")
    return strat_w


def run_books(store: Store, entries: dict, risk: dict, marks: dict[str, float], strat_w: dict[str, pd.Series],
              last_bar: str, main: str, reb) -> list[str]:
    """Kill switch, then rebalance each due book of one venue. `reb(book, target_weights, reason)` trades.
    main = allocation-weighted blend of that venue's incubation/active entries' latest targets.
    Three sizes of the same targets: `shadow:<entry>` (shadow_equity: measures the signal, min order barely binds),
    `main` (start_equity: the account the owner could fund) and, when risk.json has `small_equity`, the twins
    `small:<entry>` and `small:<main>`: the same thing in a small account, where the min order decides what can be held."""
    small = risk.get("small_equity")
    kinds = [("shadow:", risk.get("shadow_equity", risk["start_equity"]))] + ([("small:", small)] if small else [])
    for n, sc in entries.items():   # a retired entry's books are closed out once, not left holding stale positions
        if sc.get("status") != "retired":
            continue
        for prefix, _ in kinds:
            book = f"{prefix}{n}"
            if store.positions(book):
                reb(book, pd.Series(dtype=float), "retired")
                store.event("INFO", f"{book}: entry retired, positions closed")
            last = store.q("select n_pos from equity where book=? order by ts desc limit 1", book)
            npos = len(store.positions(book))
            if last and last[0][0] != npos:   # final equity row, so `status` shows the closed book and not its last live one
                eq, gross = book_equity(store, book, marks)
                store.x("insert into equity values(?,?,?,?,?)", now_iso(), book, eq, gross, npos)
    books, sizes = {}, {}
    for n, sc in entries.items():
        if sc.get("status") != "retired":
            for prefix, size in kinds:
                books[f"{prefix}{n}"], sizes[f"{prefix}{n}"] = (n,), size
    if main:   # two-venue books have no main book (main=None)
        books[main], sizes[main] = None, risk["start_equity"]
    if main and small:
        books[f"small:{main}"], sizes[f"small:{main}"] = None, small
    for b in books:
        store.ensure_book(b, sizes[b])
        store.resize_untouched(b, sizes[b])

    for book, spec in books.items():
        sig_key = f"{book}_alloc_sig"   # "main_alloc_sig" / "main_bn_alloc_sig" as before; one per allocation book
        halted = store.q("select halted from books where name=?", book)[0][0]
        eq, _ = book_equity(store, book, marks)
        priced = all(marks.get(c, 0.0) > 0 for c in store.positions(book))   # a held coin without a mark would be valued at 0
        peak = max(store.q("select peak from books where name=?", book)[0][0], eq) if priced else \
            store.q("select peak from books where name=?", book)[0][0]
        store.x("update books set peak=? where name=?", peak, book)
        if not halted and priced and eq < peak * (1 - risk["kill_drawdown"]):
            store.event("ALERT", f"{book}: drawdown kill-switch at equity {eq:.2f} (peak {peak:.2f}); flattening")
            reb(book, pd.Series(dtype=float), "kill_switch")
            store.x("update books set halted=1 where name=?", book)
            continue
        if halted:
            continue
        if store.q("select 1 from rebalances where book=? and bar=?", book, last_bar):
            continue
        if spec is None:
            live = {n: sc for n, sc in entries.items()
                    if sc.get("status") in ("incubation", "active") and sc.get("alloc", 0) > 0}
            saved = {n: pd.Series(json.loads(w)) for n, _, w in store.q("select * from targets")}
            parts = [(sc["alloc"], saved[n]) for n, sc in live.items() if n in saved]
            tgt = pd.concat([a * w for a, w in parts], axis=1).fillna(0.0).sum(axis=1) if parts else pd.Series(dtype=float)
            # AL2b (design.md 2026-11-26): one monthly multiplier per main book (scripts.main_scale), so the mix of separately
            # vol-targeted books runs at the steady-mode vol; the small twin uses its big sibling's number. Absent = 1.
            scale = float(risk.get("main_scale", {}).get(book.removeprefix("small:"), 1.0))
            tgt = tgt * scale
            alloc_sig = json.dumps({**{n: sc["alloc"] for n, sc in live.items()}, **({"_scale": scale} if scale != 1.0 else {})},
                                   sort_keys=True)
            changed = alloc_sig != store.get_meta(sig_key)
            fresh = any(n in strat_w for n in live)
            due = fresh or changed or (not parts and bool(store.positions(book)))
            store.set_meta(sig_key, alloc_sig)
        else:
            n = spec[0]
            if n not in strat_w:
                continue
            tgt, due = strat_w[n], True
        if due:
            reb(book, apply_risk(tgt, risk), f"bar {last_bar}")
            store.x("insert or ignore into rebalances values(?,?)", book, last_bar)
    return list(books)


def run_once():
    cfg, risk = load_cfg()
    store, hl = Store(), HL(min_interval=float(os.environ.get("KRIPTO_HL_INTERVAL", "3.0")))
    coins = refresh_data(hl, store)
    ctx = {r["name"]: r for r in hl.meta_and_ctxs()}
    marks = {c: float(r["markPx"]) for c, r in ctx.items() if r.get("markPx")}
    sz_dec = {c: int(r["szDecimals"]) for c, r in ctx.items()}
    if store.get_meta("funding_accrued_ms") is None:
        store.set_meta("funding_accrued_ms", int(time.time() * 1000))
    held_before, t_before = hl_held(store), int(time.time() * 1000)   # funding is accrued after the trades, on these

    panel = live_panel(coins)
    last_bar = str(panel["close"].index[-1])
    entries = {n: sc for n, sc in cfg.items() if venue_of(sc) == "hl"}
    record_universe(store, "hl", panel, last_bar)
    strat_w = compute_targets(store, entries, panel, last_bar)
    l2 = {}   # order books fetched in this run, shared by all books trading the same coin (see simulate_fill)
    reb = lambda book, tgt, reason: rebalance(hl, store, book, tgt, marks, sz_dec, reason,
                                              fill=lambda c, d: simulate_fill(hl, c, d, l2))
    with trade_lock():
        books = run_books(store, entries, risk, marks, strat_w, last_bar, "main", reb)
    store.set_meta("hl_trades_done", now_iso())   # fill-delay audit: trades finished, before funding/BN/pair/collector
    try:
        accrue_funding(hl, store, marks, held_before, t_before)
    except Exception as e:   # retried next run: funding_accrued_ms only moves on success
        store.event("ERROR", f"hl funding accrual failed: {e!r}")
    for b in books:
        eq, gross = book_equity(store, b, marks)
        store.x("insert into equity values(?,?,?,?,?)", now_iso(), b, eq, gross, len(store.positions(b)))
    store.set_meta("last_run", now_iso())
    store.set_meta("last_bar", last_bar)
    if os.environ.get("KRIPTO_BN", "1") == "1" and any(venue_of(sc) == "bn" for sc in cfg.values()):
        try:  # Binance paper venue; a failure here must never break HL trading
            from . import venue_bn
            bn_run = venue_bn.run(store, cfg, risk)
        except Exception as e:
            bn_run = None
            store.event("ERROR", f"binance venue failed: {e!r}")
    try:   # after both venues' trades, before the pair books (their HL legs accrue from these stored prints)
        refresh_funding(hl, coins)
    except Exception as e:
        store.event("WARN", f"hl funding refresh failed: {e!r}")
    if os.environ.get("KRIPTO_BN", "1") == "1" and any(venue_of(sc) == "bn" for sc in cfg.values()):
        if bn_run and any(venue_of(sc) == "pair" for sc in cfg.values()):
            try:  # two-venue books (X2); needs both venues' marks, never breaks either venue's own books
                from . import venue_pair
                venue_pair.run(store, cfg, risk, hl, bn_run, marks, sz_dec, coins)
            except Exception as e:
                store.event("ERROR", f"pair venue failed: {e!r}")
    if os.environ.get("KRIPTO_COLLECT", "1") == "1":  # T6a: non-backfillable HL data; never breaks trading
        try:
            n = collect.collect(hl, coins)
            store.set_meta("collect_last", json.dumps({"ts": now_iso(), **n}))
            if n.get("errors"):
                store.event("WARN", f"collector: {n}")
        except Exception as e:
            store.event("WARN", f"collector failed: {e!r}")


def collect_status(store: Store) -> str:
    """Non-backfillable data health (T6a): last collector pass + days held per dataset. A gap here is data lost forever."""
    last = store.get_meta("collect_last") or "never"
    hl = data.DATA / "hl"
    ctx_days = 0
    for f in sorted((hl / "ctx").glob("*.parquet")):
        try:
            ctx_days += pd.read_parquet(f, columns=["ts"])["ts"].astype(str).str[:10].nunique()
        except Exception:
            pass
    pos_days = len(list((hl / "positions").glob("*.jsonl")))
    l2_days = len(list((hl / "l2").glob("*.jsonl")))
    flow_days = len(list((hl / "flow").glob("*.parquet"))) + len(list((hl / "flow").glob("*.jsonl")))
    return (f"collector: last={last} | days held: ctx={ctx_days} positions={pos_days} l2={l2_days} flow={flow_days}\n"
            f"flow (websocket): {store.get_meta('flow_tick') or 'never'}\n"
            f"bn liquidations (websocket, since 2026-11-17): {store.get_meta('liq_tick') or 'never'}")


def status() -> str:
    store = Store()
    lines = [f"last_run={store.get_meta('last_run')} last_bar={store.get_meta('last_bar')} "
             f"bn_last_bar={store.get_meta('bn_last_bar')}",
             f"live watcher: {store.get_meta('live_tick') or 'never ran'}"]
    for name, start, halted in store.q("select name,start_equity,halted from books order by name"):
        r = store.q("select ts,equity,gross,n_pos from equity where book=? order by ts desc limit 1", name)
        if not r:
            continue
        ts, eq, gross, n = r[0]
        first = store.q("select ts from equity where book=? order by ts limit 1", name)[0][0]
        fund = store.q("select coalesce(sum(amount),0) from funding where book=?", name)[0][0]
        fees = store.q("select coalesce(sum(fee),0), count(*) from fills where book=?", name)[0]
        reb = store.q("select max(bar) from rebalances where book=?", name)[0][0]
        lines.append(f"{name:28s} eq=${eq:8.2f} ret={eq/start-1:+7.2%} gross={gross/eq if eq else 0:4.2f}x "
                     f"pos={n:2d} fees=${fees[0]:.2f} ({fees[1]} fills) funding=${fund:+.2f} "
                     f"lastreb={reb[:16] if reb else 'never'} {'HALTED ' if halted else ''}since {first[:10]}")
    lines.append(collect_status(store))
    ev = store.q("select ts,level,msg from events where level!='INFO' order by ts desc limit 10")
    if ev:
        lines.append("recent warnings/errors:")
        lines += [f"  {t} {l} {m}" for t, l, m in ev]
    return "\n".join(lines)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "run":
        try:
            run_once()
        except Exception as e:
            Store().event("ERROR", f"run failed: {e!r}")
            raise
        print(status())
    elif cmd == "status":
        print(status())
