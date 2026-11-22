"""Move bars ("rotations"): bars that close when price has travelled a fixed distance, whatever the time (InSilico tg:103-107).

Built in two steps from Binance aggTrades. scripts/mbars_build.py reduces each day to MICRO bars (a bar closes on the first
trade >= 10 bp from its open) with the taker flow in 12 size bins (tsize.EDGES) and the number of trades. Range bars of any
larger width, order velocity (trades per bar, trades per second) and volume / delta at price come from the micro bars, so the
raw trades (about 100 GB) are read once. Micro bars restart at 00:00 UTC (`full`=False marks the cut bar of the day).
Storage: data/bn/mbars/<SYMBOL>/<date>.npz. Arrays: t0, t1 (ms), o, h, l, c, n, buy (N, 12), sell (N, 12), full.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .tsize import EDGES, NBINS

STEP = 1e-3
DIR = Path(__file__).resolve().parent.parent / "data" / "bn" / "mbars"


def micro(price: np.ndarray, qty: np.ndarray, t_ms: np.ndarray, buyer_is_maker: np.ndarray, step: float = STEP) -> dict:
    """One day's trades (time order) -> micro bars. The trade that completes a bar belongs to it; its price opens the next."""
    p = np.asarray(price, dtype=np.float64)
    N = len(p)
    ends, start, o = [], 0, p[0] if N else np.nan
    while start < N:
        up, dn, w, a, hit = o * (1 + step), o / (1 + step), 512, start, -1
        while a < N:                               # doubling windows: the first trade outside (dn, up)
            x = p[a:a + w]
            m = (x >= up) | (x <= dn)
            j = int(m.argmax())
            if m[j]:
                hit = a + j
                break
            a, w = a + w, min(w * 2, 1 << 18)
        if hit < 0:
            break
        ends.append(hit)
        start, o = hit + 1, p[hit]
    full = np.ones(len(ends), dtype=bool)
    if start < N:                                  # the day's unfinished bar
        ends.append(N - 1)
        full = np.append(full, False)
    ends = np.asarray(ends, dtype=np.int64)
    K = len(ends)
    st = np.concatenate([[0], ends[:-1] + 1]).astype(np.int64)
    n = ends - st + 1
    bar = np.repeat(np.arange(K), n)
    ntl = p * np.asarray(qty, dtype=np.float64)
    key = bar * NBINS + np.searchsorted(EDGES, ntl, side="right")
    sellside = np.asarray(buyer_is_maker, dtype=bool)
    agg = lambda m: np.bincount(key[m], weights=ntl[m], minlength=K * NBINS).reshape(K, NBINS).astype(np.float32)
    opens = np.concatenate([[p[0]], p[ends[:-1]]])
    hi, lo = np.maximum.reduceat(p, st), np.minimum.reduceat(p, st)
    return {"t0": np.asarray(t_ms)[st].astype(np.int64), "t1": np.asarray(t_ms)[ends].astype(np.int64), "o": opens,
            "h": np.maximum(hi, opens), "l": np.minimum(lo, opens), "c": p[ends], "n": n.astype(np.int32),
            "buy": agg(~sellside), "sell": agg(sellside), "full": full}


def range_bars(b: dict, width: float) -> dict:
    """Range bars: consecutive micro bars until high / low - 1 >= width. Open = previous close."""
    h, l = b["h"], b["l"]
    ends, i0, H, L = [], 0, -np.inf, np.inf
    for i in range(len(h)):
        H, L = max(H, h[i]), min(L, l[i])
        if H / L - 1 >= width:
            ends.append(i)
            H, L = -np.inf, np.inf
    full = np.ones(len(ends), dtype=bool)
    if len(h) and (not ends or ends[-1] < len(h) - 1):
        ends.append(len(h) - 1)
        full = np.append(full, False)
    ends = np.asarray(ends, dtype=np.int64)
    st = np.concatenate([[0], ends[:-1] + 1]).astype(np.int64)
    return {"t0": b["t0"][st], "t1": b["t1"][ends], "o": b["o"][st], "h": np.maximum.reduceat(h, st), "l": np.minimum.reduceat(l, st),
            "c": b["c"][ends], "n": np.add.reduceat(b["n"], st), "buy": np.add.reduceat(b["buy"], st, axis=0),
            "sell": np.add.reduceat(b["sell"], st, axis=0), "full": full}


def vap(b: dict, bin_bp: float = 10.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(lower bin edges in log price, volume, delta) at price: each micro bar's flow sits at its mid price (within one step)."""
    k = np.floor(np.log(np.sqrt(b["h"] * b["l"])) / (bin_bp / 1e4)).astype(np.int64)
    lo, size = k.min(), k.max() - k.min() + 1
    bs, ss = b["buy"].sum(1, dtype=np.float64), b["sell"].sum(1, dtype=np.float64)
    B, S = np.bincount(k - lo, weights=bs, minlength=size), np.bincount(k - lo, weights=ss, minlength=size)
    return (lo + np.arange(size)) * bin_bp / 1e4, B + S, B - S


def load(symbol: str, start: str, end: str) -> dict:
    """Micro bars of all stored days in [start, end), concatenated in time order."""
    fs = [f for f in sorted((DIR / symbol).glob("????-??-??.npz")) if start <= f.stem < end]
    parts = [np.load(f) for f in fs]
    if not parts:
        raise FileNotFoundError(f"no micro bars for {symbol} {start}..{end} in {DIR}")
    return {k: np.concatenate([z[k] for z in parts]) for k in parts[0].files}
