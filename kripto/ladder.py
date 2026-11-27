"""Resting-ladder paper book on Binance (InSilico T1 CONFIRMED, E2 a/b passed the incubation gate on the backtest; research/is3/notes.md).

    python -m kripto.ladder              # runs forever (systemd: kripto-ladder.service, Restart=always)
    python -m kripto.ladder universe     # today's causal top-20 -> state/ladder_universe.json (run as a child, ~0.4 GB once a day)

The frozen rule, simulated against the LIVE public 1-minute klines (paper only: no keys, no orders, HARD RULE 1):
* universe: top 20 Binance USDT perps by 30-day mean daily volume up to the last day bnall holds (clean bnall, all ages,
  TRADING perps only). Recomputed once a UTC day; never while bnall is being refreshed (data.refreshing marker).
* quote: after minute m closes, bid = close[m] * (1 - 30 sigma), sigma = std of the last 1440 1-min log returns (>= 720).
  No quote when 30 sigma is deeper than the symbol's PERCENT_PRICE band (1 - multiplierDown). A quote is valid only for
  minutes that OPEN after it was computed (wall clock), so minute m+1 is never judged by it: this is the one-bar-late
  version of the backtest (is3_e2 events_late, SR 2.14), not the same-close one.
* fill: a later minute whose low is <= bid * (1 - 30 bp) fills the bid (maker, 2 bp fee, no slippage). One position per coin
  per 60 minutes. Size 5% of the book's equity, step-rounded, skipped below the symbol's min notional (the $200 twin
  therefore cannot hold BTC/ETH, as in the backtest's small_acct). All fills of one minute are taken while < 5 are open.
* exit: taker, walking the live depth (+5 bp), at the first poll >= 61 minutes after the fill minute opened (its close + 60).
Books: shadow:ladder@bn (shadow_equity) and small:ladder@bn (small_equity); while ladder@bn is incubation/active with alloc > 0
also an overlay sleeve of main_bn and small:main_bn (books(); positions tracked in the `sleeve` table so paper.rebalance leaves them alone). book_venue -> "bn", so kripto.live marks them every
20 s and enforces the kill switch, and venue_bn accrues their funding. This loop respects `halted`. Heartbeat: meta.ladder_tick.
Request budget: one klines call (limit <= 5, weight 1) per universe coin per minute through a 1.5 s client = ~30 s of each minute.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from collections import deque
from pathlib import Path

import numpy as np

from . import paper as P
from . import venue_bn as V

ENTRY = "ladder@bn"
# SIZE 0.05 -> 0.029 (2026-11-23 E2d, rule fixed before the run): -50% on every fill of the largest historical same-minute batch (17) must stay above the 25% kill.
K, THROUGH, HOLD_MIN, SIZE, SLOTS, TOPN = 30.0, 30e-4, 60, 0.029, 5, 20
MAKER_FEE_BN = 0.0002
WIN, MINP = 1440, 720
MIN_MS = 60_000
UNI_FILE = P.ROOT / "state" / "ladder_universe.json"
DELISTED_BAND = 0.15


MAIN = "main_bn"


def books(risk: dict, cfg: dict | None = None) -> dict[str, tuple[float | None, float]]:
    """book -> (cash to create it with, or None for a main book the hourly engine owns; sleeve fraction of its equity).
    The own books trade at fraction 1. When ladder@bn is incubation/active with alloc > 0 it is also an overlay sleeve of
    main_bn and small:main_bn (same account and ledger; the `sleeve` table keeps the hourly rebalance off its positions):
    orders of SIZE x alloc x the main book's whole equity (design.md 2026-11-27: the ladder is flat ~97% of the time and its
    per-order size is capped by the E2d kill-switch rule, so it shares the account's margin instead of carving out capital)."""
    out = {f"shadow:{ENTRY}": (risk.get("shadow_equity", risk["start_equity"]), 1.0),
           f"small:{ENTRY}": (risk.get("small_equity", 200.0), 1.0)}
    sc = (cfg or {}).get(ENTRY, {})
    if sc.get("status") in ("incubation", "active") and sc.get("alloc", 0) > 0:
        out[MAIN] = (None, float(sc["alloc"]))
        if risk.get("small_equity"):
            out[f"small:{MAIN}"] = (None, float(sc["alloc"]))
    return out


def sigma(closes) -> float:
    """std (ddof 1) of the last WIN 1-min log returns, NaN with fewer than MINP (as pandas rolling(1440, min_periods=720).std())."""
    c = np.asarray(closes, dtype=float)[-(WIN + 1):]
    if len(c) < MINP + 1:
        return float("nan")
    r = np.diff(np.log(c))
    return float(np.std(r, ddof=1))


def bands(info: dict) -> dict[str, float]:
    out = {}
    for s in info.get("symbols", []):
        if s.get("contractType") != "PERPETUAL" or s.get("quoteAsset") != "USDT":
            continue
        for f in s.get("filters", []):
            if f.get("filterType") == "PERCENT_PRICE":
                out[s["symbol"].removesuffix("USDT")] = 1 - float(f["multiplierDown"])
    return out


def compute_universe() -> dict:
    """Top TOPN coins by 30-day mean daily volume through the last row of bnall (live-tradable perps only)."""
    from . import data
    if (data.DATA / ".refreshing_bnall").exists():
        raise RuntimeError("bnall is being refreshed")
    v = data.load_panel("bnall", "1d")["volume"]
    v = v.loc[:, v.iloc[-1].notna() | v.iloc[-2].notna()]
    m = v.iloc[-30:].mean()[v.iloc[-30:].notna().sum() >= 20]
    info = json.loads(V.INFO_CACHE.read_text()) if V.INFO_CACHE.exists() else {"symbols": []}
    trading = {s["symbol"].removesuffix("USDT") for s in info["symbols"]
               if s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT" and s.get("status") == "TRADING"}
    m = m[[c for c in m.index if c in trading]] if trading else m
    return {"data_end": str(v.index[-1].date()), "coins": list(m.sort_values(ascending=False).index[:TOPN])}


class Ladder:
    def __init__(self, store: P.Store, bn, risk: dict, now_ms=None, cfg: dict | None = None):
        self.store, self.bn, self.risk, self.cfg = store, bn, risk, cfg or {}
        self.now_ms = now_ms or (lambda: int(time.time() * 1000))
        self.bars: dict[str, deque] = {}       # coin -> deque of (open_ms, low, close), closed minutes only
        self.quotes: dict[str, list] = {}      # coin -> [(valid_from_ms, bid)], newest last
        self.coins: list[str] = []
        self.filters: dict = {}
        self.band: dict = {}
        self.depth: dict = {}

    # ---- ledger helpers -------------------------------------------------------------------------------------------
    def entries(self, book: str) -> dict[str, tuple[int, float]]:
        """Open ladder positions of `book`: coin -> (fill minute open ms, size), from the `sleeve` table (restart-safe)."""
        return {c: (int(t0), s) for c, s, t0 in self.store.q("select coin, size, t0 from sleeve where book=? and size!=0", book)}

    def migrate(self):
        """Own books opened before the sleeve table existed: their positions are all ladder positions."""
        for b in (f"shadow:{ENTRY}", f"small:{ENTRY}"):
            if self.store.q("select 1 from sleeve where book=?", b):
                continue
            for c, s in self.store.positions(b).items():
                r = self.store.q("select reason from fills where book=? and coin=? and reason like 'ladder bid %' order by ts desc limit 1",
                                 b, c)
                self.store.x("insert or replace into sleeve values(?,?,?,?)", b, c, s, int(r[0][0].split()[-1]) if r else 0)

    def locked_until(self, coin: str) -> int:
        r = self.store.q("select reason from fills where coin=? and reason like 'ladder bid %' order by ts desc limit 1", coin)
        return int(r[0][0].split()[-1]) + HOLD_MIN * MIN_MS if r else -1

    def _fill(self, book, c, d, px, mid, fee, slip, reason, t0=None):
        """One transaction: cash, position, fill and the sleeve row (t0 = fill minute on entry, None = exit)."""
        with self.store.c:
            self.store.c.execute("update books set cash=cash-?-? where name=?", (d * px, fee, book))
            self.store.c.execute("insert into positions values(?,?,?) on conflict(book,coin) do update set size=size+excluded.size",
                                 (book, c, d))
            self.store.c.execute("insert into fills values(?,?,?,?,?,?,?,?,?)", (P.now_iso(), book, c, d, px, mid, fee, slip, reason))
            if t0 is None:
                self.store.c.execute("delete from sleeve where book=? and coin=?", (book, c))
            else:
                self.store.c.execute("insert or replace into sleeve values(?,?,?,?)", (book, c, d, t0))

    def all_marks(self, books) -> dict[str, float]:
        """Bar closes, plus Binance mark prices when a book holds coins outside the ladder universe (a main book)."""
        m = self.marks()
        if any(c not in m for b in books for c in self.store.positions(b)):
            try:
                m = {**{x["symbol"].removesuffix("USDT"): float(x["markPrice"]) for x in self.bn.premium_index()
                        if x["symbol"].endswith("USDT")}, **m}
            except Exception:
                pass
        return m

    def marks(self) -> dict[str, float]:
        return {c: b[-1][2] for c, b in self.bars.items() if b}

    # ---- market data ------------------------------------------------------------------------------------------------
    def update_bars(self, coin: str, now: int) -> list[tuple]:
        """Fetch closed 1-min bars of `coin` newer than what we hold. Returns the new ones (oldest first)."""
        b = self.bars.get(coin)
        if not b:
            limit = WIN + 2
        else:
            limit = int(min(1500, max(3, (now - b[-1][0]) // MIN_MS + 2)))
            if limit >= 1500:            # long gap: start over rather than leave a hole in sigma
                b, limit = None, WIN + 2
        rows = self.bn.klines(V.sym(coin), "1m", limit=limit)
        new = [(int(r[0]), float(r[3]), float(r[4])) for r in rows if int(r[6]) < now]   # close time passed = closed
        if not b:
            self.bars[coin] = deque(new, maxlen=WIN + 1)
            return []                    # history only: never judge fills on bars seen before any quote existed
        out = [x for x in new if x[0] > b[-1][0]]
        b.extend(out)
        return out

    # ---- one minute -------------------------------------------------------------------------------------------------
    def step(self) -> dict:
        now = self.now_ms()
        out = {"ts": P.now_iso(), "coins": len(self.coins), "quotes": 0, "fills": 0, "exits": 0, "errors": []}
        bk = books(self.risk, self.cfg)
        for b, (cash, _) in bk.items():
            if cash is not None:
                self.store.ensure_book(b, cash)
        bk = {b: frac for b, (_, frac) in bk.items() if self.store.q("select 1 from books where name=?", b)}
        for (b,) in self.store.q("select distinct book from sleeve where size!=0"):
            bk.setdefault(b, 0.0)        # a sleeve left after ladder@bn left the main book: no new fills, exits on schedule
        halted = {n for n, h in self.store.q("select name, halted from books") if h}
        self.quotes = {c: q for c, q in self.quotes.items() if c in self.coins}   # a coin that left the universe has no bid
        # 1. exits first (frees slots: the backtest frees a slot whose exit time <= the new fill's minute)
        with P.trade_lock():
            for b in bk:
                for c, (t0, s) in self.entries(b).items():
                    if b in halted or now < t0 + (HOLD_MIN + 1) * MIN_MS:
                        continue
                    try:
                        px, mid, slip = V.simulate_fill(self.bn, c, -s, self.depth)
                    except Exception as e:
                        out["errors"].append(f"exit {c}: {e!r}"[:80])
                        continue
                    self._fill(b, c, -s, px, mid, abs(s) * px * V.TAKER_FEE_BN, slip, "ladder exit")
                    out["exits"] += 1
        # 2. new closed bars, judged against quotes placed before each bar opened
        hits: dict[int, list] = {}
        for c in sorted(set(self.coins) | {c for b in bk for c in self.entries(b)}):
            try:
                new = self.update_bars(c, now)
            except Exception as e:
                out["errors"].append(f"{c}: {e!r}"[:80])
                continue
            for o, lo, _ in new:
                q = [x for x in self.quotes.get(c, []) if x[0] <= o]
                if q and lo <= q[-1][1] * (1 - THROUGH) and o > self.locked_until(c):
                    hits.setdefault(o, []).append((c, q[-1][1]))
                    break                     # one fill per coin per hour: later bars of this batch are inside the lock
        m_all = self.all_marks(bk) if hits else {}
        with P.trade_lock():
            for o in sorted(hits):
                for b, frac in bk.items():
                    if b in halted:
                        continue
                    held = self.entries(b)
                    if len(held) >= SLOTS:
                        continue
                    if not all(m_all.get(c, 0) > 0 for c in self.store.positions(b)):
                        out["errors"].append(f"{b}: no mark for a held coin, no ladder fill")
                        continue
                    eq, _ = P.book_equity(self.store, b, m_all)
                    for c, bid in hits[o]:
                        if c in held:
                            continue
                        f = self.filters.get(c, {})
                        d = V.round_step(SIZE * frac * eq / bid, f.get("step", 0.0))
                        if d <= 0 or d * bid < f.get("min_notional", 5.0):
                            continue
                        self._fill(b, c, d, bid, self.bars[c][-1][2], d * bid * MAKER_FEE_BN, 0.0, f"ladder bid {o}", t0=o)
                        out["fills"] += 1
        # 3. new quotes from the latest close, valid for minutes opening after now
        for c in self.coins:
            b = self.bars.get(c)
            if not b or b[-1][0] < now - 2 * MIN_MS - 1:      # stale: no quote rather than a quote on old data
                self.quotes.pop(c, None)
                continue
            sg = sigma([x[2] for x in b])
            if not (sg > 0) or K * sg > self.band.get(c, DELISTED_BAND):
                self.quotes.pop(c, None)
                continue
            self.quotes[c] = (self.quotes.get(c, []) + [(now, b[-1][2] * (1 - K * sg))])[-3:]
            out["quotes"] += 1
        self.depth.clear()
        if out["fills"] or out["exits"]:
            m = self.all_marks(bk)
            for b in bk:
                if all(c in m for c in self.store.positions(b)):
                    eq, gross = P.book_equity(self.store, b, m)
                    self.store.x("insert into equity values(?,?,?,?,?)", out["ts"], b, eq, gross, len(self.store.positions(b)))
        self.store.set_meta("ladder_tick", json.dumps(out))
        return out


def refresh_universe(bn) -> dict:
    """Once a UTC day, in a child process (frees the panel's RAM). Keeps yesterday's list when it cannot run."""
    old = json.loads(UNI_FILE.read_text()) if UNI_FILE.exists() else {}
    today = time.strftime("%Y-%m-%d", time.gmtime())
    if old.get("day") == today:
        return old
    V.symbol_filters(bn)                 # refreshes the exchangeInfo cache (daily)
    r = subprocess.run([sys.executable, "-m", "kripto.ladder", "universe"], cwd=P.ROOT, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        print(f"{P.now_iso()} universe refresh failed: {r.stderr.strip()[-200:]}", flush=True)
        return old
    return json.loads(UNI_FILE.read_text())


def main():
    from .bn import BN
    if len(sys.argv) > 1 and sys.argv[1] == "universe":
        u = compute_universe()
        u["day"] = time.strftime("%Y-%m-%d", time.gmtime())
        UNI_FILE.parent.mkdir(parents=True, exist_ok=True)
        UNI_FILE.write_text(json.dumps(u))
        print(json.dumps(u))
        return
    bn = BN(min_interval=float(os.environ.get("KRIPTO_LADDER_INTERVAL", "1.5")))
    store = P.Store()
    _, risk = P.load_cfg()
    L = Ladder(store, bn, risk)
    L.migrate()
    print(f"ladder started: k={K} through={THROUGH * 1e4:.0f}bp hold={HOLD_MIN}m size={SIZE} slots={SLOTS}", flush=True)
    last_note = ""
    while True:
        try:
            cfg, L.risk = P.load_cfg()
            L.cfg = cfg
            st = cfg.get(ENTRY, {}).get("status")
            if st is None:
                time.sleep(60)
                continue
            u = refresh_universe(bn) if st != "retired" else {}
            L.coins = u.get("coins", [])     # retired: no quotes, open positions still exit on schedule
            L.filters = V.symbol_filters(bn)
            L.band = bands(json.loads(V.INFO_CACHE.read_text()))
            out = L.step()
            note = f"errors={out['errors']}" if out["errors"] else ""
            if out["fills"] or out["exits"] or note != last_note:
                print(f"{out['ts']} fills={out['fills']} exits={out['exits']} quotes={out['quotes']} {note or 'ok'}", flush=True)
                last_note = note
        except Exception as e:
            print(f"{P.now_iso()} ladder step failed: {e!r}", flush=True)
        t = time.time()
        time.sleep(max(1.0, 60 - t % 60 + 3))      # next run 3 s after the next minute boundary


if __name__ == "__main__":
    main()
