"""Hourly collector for NON-BACKFILLABLE Hyperliquid data (backlog T6a, started 2026-11-09).

Public /info only (HARD RULE 1). Runs at the end of each trader step on the same rate-limited client, so the
shared-IP budget holds (one request per >= 3 s). Per run at most ~`max_calls` extra requests:
  * discovery: `recentTrades` for the top coins -> addresses of both counterparties (weighted by notional)
  * positioning: `clearinghouseState` for the largest known accounts + a few unexplored addresses
  * L2: `l2Book` top levels for the top coins
Outputs (gitignored data/, append-only JSONL per UTC day):
  data/hl/positions/YYYY-MM-DD.jsonl   {ts, user, av, ntl, pos: [[coin, szi, entry, value, upnl, lev, liq], ...]}
  data/hl/l2/YYYY-MM-DD.jsonl          {ts, coin, bids: [[px, sz, n], ...], asks: [...]}
  data/hl/positions/addresses.json     address book {addr: {seen_ntl, first, av, last}}
A failure here must never break trading: callers wrap collect() in try/except.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import data

POS_DIR = data.DATA / "hl" / "positions"
L2_DIR = data.DATA / "hl" / "l2"
L2_LEVELS = 10
MAX_BOOK = 20000


def _day_file(d: Path, ts: float) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    return d / (time.strftime("%Y-%m-%d", time.gmtime(ts)) + ".jsonl")


def _append(path: Path, recs: list[dict]):
    if recs:
        with path.open("a") as f:
            for r in recs:
                f.write(json.dumps(r, separators=(",", ":")) + "\n")


def store_l2(book: dict, coin: str, ts: float | None = None, levels: int = L2_LEVELS, d: Path | None = None):
    """Append one L2 snapshot (also called from the fill simulator, so fills' books are kept for free)."""
    ts = ts or time.time()
    lv = book.get("levels", [[], []])
    rec = {"ts": int(ts), "coin": coin,
           "bids": [[x["px"], x["sz"], x.get("n")] for x in lv[0][:levels]],
           "asks": [[x["px"], x["sz"], x.get("n")] for x in lv[1][:levels]]}
    _append(_day_file(d or L2_DIR, ts), [rec])


def compact_state(user: str, st: dict, ts: float) -> dict:
    ms = st.get("marginSummary", {})
    pos = []
    for ap in st.get("assetPositions", []):
        p = ap.get("position", {})
        lev = (p.get("leverage") or {}).get("value")
        pos.append([p.get("coin"), p.get("szi"), p.get("entryPx"), p.get("positionValue"),
                    p.get("unrealizedPnl"), lev, p.get("liquidationPx")])
    return {"ts": int(ts), "user": user, "av": ms.get("accountValue"), "ntl": ms.get("totalNtlPos"), "pos": pos}


def pick_addresses(book: dict, n_track: int, n_explore: int) -> list[str]:
    """Largest known accounts (by last account value) + highest-notional never-snapshotted addresses."""
    known = sorted((a for a, v in book.items() if v.get("av") is not None),
                   key=lambda a: -float(book[a]["av"]))[:n_track]
    new = sorted((a for a, v in book.items() if v.get("av") is None),
                 key=lambda a: -book[a].get("seen_ntl", 0.0))[:n_explore]
    return known + new


def collect(hl, coins: list[str], n_disc: int = 6, n_l2: int = 10, n_track: int = 30, n_explore: int = 10,
            deadline_s: float = 300.0, pos_dir: Path | None = None, l2_dir: Path | None = None) -> dict:
    """One collection pass. Returns counts. `coins` = universe ordered by volume (top first)."""
    pos_dir, l2_dir = pos_dir or POS_DIR, l2_dir or L2_DIR
    t0 = time.time()
    pos_dir.mkdir(parents=True, exist_ok=True)
    ab_path = pos_dir / "addresses.json"
    book = json.loads(ab_path.read_text()) if ab_path.exists() else {}
    n = {"trades": 0, "new_addr": 0, "snaps": 0, "l2": 0, "errors": 0}

    def left():
        return time.time() - t0 < deadline_s

    for c in coins[:n_disc]:
        if not left():
            break
        try:
            for tr in hl.post({"type": "recentTrades", "coin": c}) or []:
                ntl = float(tr.get("px", 0)) * float(tr.get("sz", 0))
                for u in tr.get("users", []) or []:
                    if u not in book:
                        book[u] = {"seen_ntl": 0.0, "first": int(time.time()), "av": None, "last": None}
                        n["new_addr"] += 1
                    book[u]["seen_ntl"] = book[u].get("seen_ntl", 0.0) + ntl
                n["trades"] += 1
        except Exception:
            n["errors"] += 1

    recs = []
    for u in pick_addresses(book, n_track, n_explore):
        if not left():
            break
        try:
            ts = time.time()
            st = hl.post({"type": "clearinghouseState", "user": u})
            r = compact_state(u, st, ts)
            recs.append(r)
            book[u]["av"], book[u]["last"] = r["av"], r["ts"]
            n["snaps"] += 1
        except Exception:
            n["errors"] += 1
    _append(_day_file(pos_dir, t0), recs)

    for c in coins[:n_l2]:
        if not left():
            break
        try:
            store_l2(hl.l2_book(c), c, d=l2_dir)
            n["l2"] += 1
        except Exception:
            n["errors"] += 1

    if len(book) > MAX_BOOK:  # bound the address book: drop the smallest never-snapshotted addresses
        drop = sorted((a for a, v in book.items() if v.get("av") is None), key=lambda a: book[a].get("seen_ntl", 0.0))
        for a in drop[:len(book) - MAX_BOOK]:
            del book[a]
    tmp = ab_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(book, separators=(",", ":")))
    tmp.replace(ab_path)
    n["seconds"] = round(time.time() - t0, 1)
    return n
