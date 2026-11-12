"""Always-on watcher (owner direction 2026-11-10: "why isn't it always live?").

    python -m kripto.live          # runs forever (systemd: kripto-live.service, Restart=always)

Every TICK seconds (default 20) it fetches ALL marks of each venue with ONE public request per venue (Hyperliquid
metaAndAssetCtxs through the same >= 3 s rate-limited client class, Binance premiumIndex), re-values every open book,
tracks its true peak and enforces the drawdown kill switch right away instead of at the next hourly step. It writes a
heartbeat (`meta.live_tick`) every tick and an equity row per open book every EQUITY_EVERY seconds.

What it deliberately does NOT do: decide trades. Targets come from closed bars and are computed by the hourly step
(`kripto.paper run`), which trades minutes after a bar closes; between bar closes a strategy has no new input.
Both processes share the sqlite ledger: fills are single transactions, and anything that trades holds `paper.trade_lock`.
A kill needs CONFIRM consecutive breaching ticks and a mark for every held coin, so one bad data point cannot flatten a book.
Paper only: public market data, no keys, no orders (HARD RULE 1).
"""
from __future__ import annotations

import json
import os
import time

import pandas as pd

from . import paper as P
from .hl import HL

TICK = float(os.environ.get("KRIPTO_LIVE_TICK", "20"))
EQUITY_EVERY = 300.0
CONFIRM = 2


class Venue:
    """name ("hl" | "bn" | "pair"), marks() -> {coin: mark}, flatten(store, book, marks) closes every position of a book.
    derived=True: marks(got) builds its marks from the marks the other venues fetched this tick (no request of its own)."""

    def __init__(self, name, marks, flatten, derived=False):
        self.name, self.marks, self.flatten, self.derived = name, marks, flatten, derived


def hl_venue(hl: HL) -> Venue:
    cache: dict = {}

    def marks():
        meta, ctxs = hl.post({"type": "metaAndAssetCtxs"}, retries=2)
        return {a["name"]: float(c["markPx"]) for a, c in zip(meta["universe"], ctxs) if c.get("markPx")}

    def flatten(store, book, m):
        P.rebalance(hl, store, book, pd.Series(dtype=float), m, {}, "kill_switch",
                    fill=lambda c, d: P.simulate_fill(hl, c, d, cache))
    return Venue("hl", marks, flatten)


def bn_venue(bn) -> Venue:
    from . import venue_bn as V
    cache: dict = {}

    def marks():
        return {x["symbol"].removesuffix("USDT"): float(x["markPrice"]) for x in bn.get("/fapi/v1/premiumIndex", retries=2)
                if x["symbol"].endswith("USDT") and float(x.get("markPrice") or 0) > 0}

    def flatten(store, book, m):
        P.rebalance(None, store, book, pd.Series(dtype=float), m, {}, "kill_switch",
                    fill=lambda c, d: V.simulate_fill(bn, c, d, cache), fee_rate=V.TAKER_FEE_BN)
    return Venue("bn", marks, flatten)


def pair_venue(hl: HL, bn) -> Venue:
    """Two-venue books (venue_pair.py): legs `<COIN>@hl` / `<COIN>@bn` priced from the HL and Binance marks of this tick."""
    from . import venue_bn as V
    from .backtest import TAKER_FEE
    cache_hl: dict = {}
    cache_bn: dict = {}

    def marks(got):
        if "hl" not in got or "bn" not in got:     # one venue unreachable: no complete marks, skip this tick
            raise RuntimeError("pair needs both venues' marks")
        out = {f"{c}@hl": m for c, m in got["hl"].items()}
        for b, m in got["bn"].items():
            out[f"{b}@bn"] = m
            if b.startswith("1000"):                # HL quotes these per 1000 as k<COIN> (data.hl_to_bn)
                out[f"k{b[4:]}@bn"] = m
        return out

    def flatten(store, book, m):
        from . import data
        P.rebalance(None, store, book, pd.Series(dtype=float), m, {}, "kill_switch",
                    fill=lambda c, d: P.simulate_fill(hl, c[:-3], d, cache_hl) if c.endswith("@hl")
                    else V.simulate_fill(bn, data.hl_to_bn(c[:-3]), d, cache_bn),
                    fee_rate=lambda c: TAKER_FEE if c.endswith("@hl") else V.TAKER_FEE_BN)
    return Venue("pair", marks, flatten, derived=True)


def tick(store: P.Store, risk: dict, venues: list[Venue], state: dict, now: float | None = None) -> dict:
    """One pass over every open book. `state` carries breach counts and the last equity-row time between ticks."""
    now = time.time() if now is None else now
    out = {"ts": P.now_iso(), "open_books": 0, "worst_dd": 0.0, "nomark": 0, "killed": [], "errors": []}
    breach = state.setdefault("breach", {})
    write_eq = now - state.get("eq_ts", 0.0) >= EQUITY_EVERY
    got: dict = {}
    for v in venues:
        try:
            marks = v.marks(got) if v.derived else v.marks()
            got[v.name] = marks
        except Exception as e:   # a venue that cannot be reached is skipped this tick, never guessed
            out["errors"].append(f"{v.name}: {e!r}"[:100])
            continue
        for name, peak, halted in store.q("select name, peak, halted from books"):
            if P.book_venue(name) != v.name or halted:
                continue
            pos = store.positions(name)
            if not pos:
                continue
            if any(marks.get(c, 0.0) <= 0 for c in pos):   # no price for a held coin: equity would be wrong
                out["nomark"] += 1
                continue
            out["open_books"] += 1
            eq, gross = P.book_equity(store, name, marks)
            if eq > peak:
                peak = eq
                store.x("update books set peak=? where name=?", peak, name)
            out["worst_dd"] = round(min(out["worst_dd"], eq / peak - 1), 4)
            if eq < peak * (1 - risk["kill_drawdown"]):
                breach[name] = breach.get(name, 0) + 1
                if breach[name] >= CONFIRM:
                    with P.trade_lock():
                        if not store.q("select halted from books where name=?", name)[0][0]:
                            store.event("ALERT", f"{name}: drawdown kill-switch at equity {eq:.2f} (peak {peak:.2f}); "
                                                 f"flattening (live watcher)")
                            v.flatten(store, name, marks)
                            store.x("update books set halted=1 where name=?", name)
                            out["killed"].append(name)
                            eq, gross = P.book_equity(store, name, marks)
                    breach.pop(name, None)
            else:
                breach.pop(name, None)
            if write_eq or name in out["killed"]:
                store.x("insert into equity values(?,?,?,?,?)", out["ts"], name, eq, gross, len(store.positions(name)))
    if write_eq:
        state["eq_ts"] = now
    store.set_meta("live_tick", json.dumps(out))
    return out


def main():
    store = P.Store()
    hl = HL(min_interval=max(3.0, float(os.environ.get("KRIPTO_HL_INTERVAL", "3.0"))))
    venues = [hl_venue(hl)]
    if os.environ.get("KRIPTO_BN", "1") == "1":
        from .bn import BN
        bn = BN(min_interval=1.0)
        venues += [bn_venue(bn), pair_venue(hl, bn)]   # pair last: it reuses the marks the other two fetched
    state: dict = {}
    print(f"live watcher started: tick {TICK:.0f}s, venues {[v.name for v in venues]}", flush=True)
    last_note = ""
    while True:
        t0 = time.time()
        try:
            _, risk = P.load_cfg()               # risk limits can change without a restart
            out = tick(store, risk, venues, state)
            note = f"errors={out['errors']} nomark={out['nomark']}" if out["errors"] or out["nomark"] else ""
            if out["killed"] or note != last_note:   # log changes, not 4,000 identical lines a day
                print(f"{out['ts']} killed={out['killed']} {note or 'ok'}", flush=True)
                last_note = note
        except Exception as e:                   # the watcher must outlive any single failure
            print(f"{P.now_iso()} tick failed: {e!r}", flush=True)
        time.sleep(max(1.0, TICK - (time.time() - t0)))


if __name__ == "__main__":
    main()
