"""M5 a/c: range -> impulse -> range on range bars, resting bid at the old range high, queue-volume fill ladder, placebo levels. notes.md section M5.

Log-price space so the downside mirror is the same code (side -1: x -> -x, high <-> low).
Fill ladder: 'touch' (low <= level), 'q50k' / 'q250k' (pro-rata notional traded at or below the level since placement >= Q: the queue ahead of us),
'through' (low <= level - 1 bp). Exit: maker at +1w (needs a 1 bp trade-through), stop -2w taker, 60 min timeout taker. Fees: maker 2 bp, taker 5 + 1 bp.
Placebo: the same order at 0.63x / 1.37x the distance between the placement price and the level.

    .venv/bin/python -m research.studies.is3_m5 explore
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from kripto import mbars
from research.studies import is3_lib as L
from research.studies.is3_m1 import BAD, COINS, rbars

FILLS = {"touch": None, "q50k": 5e4, "q250k": 2.5e5, "q1m": 1e6, "through": "t"}
MK, TK = 2e-4, 6e-4
H_ORDER, H_POS = 2 * 3.6e6, 3.6e6


def first(mask: np.ndarray) -> int:
    return int(np.argmax(mask)) if mask.any() else -1


def trade(xh, xl, vol, t1, p0, lev, w, fill, tgt_off=None, h_order=H_ORDER, h_pos=H_POS):
    """Resting bid at log level `lev` placed after micro bar p0. Returns (fill idx, return, fee) or None."""
    end = int(np.searchsorted(t1, t1[p0] + h_order, side="right"))
    hh, ll, vv = xh[p0 + 1:end], xl[p0 + 1:end], vol[p0 + 1:end]
    if fill is None:
        k = first(ll <= lev)
    elif fill == "t":
        k = first(ll <= lev - 1e-4)
    else:
        frac = np.clip((lev - ll) / np.maximum(hh - ll, 1e-12), 0, 1)
        frac = np.where(ll <= lev, np.where(hh <= lev, 1.0, frac), 0.0)
        k = first(np.cumsum(vv * frac) >= fill)
    if k < 0:
        return None
    g = p0 + 1 + k
    stop = int(np.searchsorted(t1, t1[g] + h_pos, side="right"))
    h2, l2 = xh[g + 1:stop], xl[g + 1:stop]
    if len(h2) == 0:
        return None
    off = w if tgt_off is None else tgt_off
    tgt, sl = lev + off + 1e-4, lev - 2 * w
    it, is_ = first(h2 >= tgt), first(l2 <= sl)
    if is_ >= 0 and (it < 0 or is_ <= it):
        return g, np.exp(sl - lev) - 1, MK + TK
    if it >= 0:
        return g, np.exp(off) - 1, 2 * MK
    xc = (h2[-1] + l2[-1]) / 2                 # timeout: mid of the last micro bar (within one 10-bp step)
    return g, np.exp(xc - lev) - 1, MK + TK


def coin_events(sym: str, lo: str, hi: str, w: float, form: str = "a") -> pd.DataFrame:
    """form a: target +1w, order 2 h, position 1 h. form e: target = A (lowest low between breakout close and placement), 6 h / 6 h."""
    b = mbars.load(sym, lo, hi)
    r = rbars(b, w)
    t1 = b["t1"].astype(np.int64)
    vol = (b["buy"].sum(1) + b["sell"].sum(1)).astype(np.float64)
    bad = {pd.Timestamp(x, tz="UTC").value // 10**6 // 86_400_000 for x in BAD.get(sym, {})}
    coin = sym.replace("USDT", "")
    rows = []
    for side in (1, -1):
        xh = np.log(b["h"]) if side > 0 else -np.log(b["l"])
        xl = np.log(b["l"]) if side > 0 else -np.log(b["h"])
        rh = np.log(r["h"]) if side > 0 else -np.log(r["l"])
        rl = np.log(r["l"]) if side > 0 else -np.log(r["h"])
        rc = side * np.log(r["c"])
        busy = -1
        for i in range(10, len(rc)):
            if r["end"][i] <= busy:
                continue
            H, Lo = rh[i - 10:i].max(), rl[i - 10:i].min()
            if H - Lo > 3 * w or rc[i] <= H:
                continue
            m0 = r["end"][i] + 1
            m1 = int(np.searchsorted(t1, t1[m0 - 1] + H_ORDER, side="right"))
            a = first(xh[m0:m1] >= H + 3 * w)
            if a < 0:
                continue
            p0 = m0 + a
            if (xl[m0:p0 + 1] <= H).any() or (t1[p0] // 86_400_000) in bad:
                continue
            P = H + 3 * w
            ho, hp, toff = H_ORDER, H_POS, None
            if form == "e":
                toff = float(xl[m0:p0 + 1].min() - H)
                if toff < w:
                    continue
                ho = hp = 6 * 3.6e6
            busy = int(np.searchsorted(t1, t1[p0] + ho + hp, side="right"))
            R = H
            if form in ("bvah", "bpoc"):            # level = the 10-bar range's value-area high / POC (log space, 5-bp bins of micro-bar mids)
                s0 = int(r["end"][i - 11]) + 1 if i > 10 else 0
                s1 = int(r["end"][i - 1]) + 1
                mid = (xh[s0:s1] + xl[s0:s1]) / 2
                k = np.floor(mid / 5e-4).astype(np.int64)
                k0 = k.min()
                v = np.bincount(k - k0, weights=vol[s0:s1])
                if form == "bpoc":
                    R = (k0 + int(np.argmax(v)) + 0.5) * 5e-4
                else:
                    order = np.argsort(-v)
                    take = order[:int(np.searchsorted(np.cumsum(v[order]), 0.7 * v.sum())) + 1]   # top-volume bins to 70% (approximate VA)
                    R = (k0 + take.max() + 1) * 5e-4
                R = min(R, H)
                if P - R < 2 * w:
                    continue
            d = P - R
            for kind, lev in (("real", R), ("pl063", P - 0.63 * d), ("pl137", P - 1.37 * d)):
                for fname, f in FILLS.items():
                    out = trade(xh, xl, vol, t1, p0, lev, w, f, toff, ho, hp)
                    if out is None:
                        continue
                    g, ret, fee = out
                    rows.append({"time": pd.Timestamp(int(t1[g]), unit="ms", tz="UTC"), "coin": coin, "side": side, "w": w, "kind": kind,
                                 "fill": fname, "gross": ret, "cost": fee, "lev": float(np.exp(side * lev)), "placed": pd.Timestamp(int(t1[p0]), unit="ms", tz="UTC")})
    return pd.DataFrame(rows)


def explore(form: str = "a") -> None:
    a, b = L.SAMPLES["explore"]
    E = []
    for w in (0.002, 0.0043):
        for s in COINS:
            e = coin_events(s, a, b, w, form)
            print(s, w, "orders placed", e[(e.kind == "real") & (e.fill == "touch")].shape[0] if len(e) else 0, flush=True)
            E.append(e)
    E = pd.concat(E, ignore_index=True)
    E.to_parquet(L.ROOT / f"data/is3/m5{form}_explore.parquet")
    report(E, "explore", form)


def report(E: pd.DataFrame, sample: str, form: str = "a") -> None:
    for w in (0.002, 0.0043):
        for fname in FILLS:
            x = E[(E.w == w) & (E.fill == fname)]
            line = []
            for kind in ("real", "pl063", "pl137"):
                y = x[x.kind == kind]
                line.append(f"{kind} n{len(y)} gross {y.gross.mean() * 1e4:+.1f} net {(y.gross - y.cost).mean() * 1e4:+.1f}")
            print(f"w {w:.1%} fill {fname}: " + " | ".join(line), flush=True)
            if fname in ("q250k", "through"):
                real = x[x.kind == "real"][["time", "coin", "side", "gross", "cost"]].reset_index(drop=True)
                pl = x[x.kind != "real"][["time", "coin", "side", "gross", "cost"]].reset_index(drop=True)
                if len(real) > 20:
                    L.card(f"M5{form}_w{int(w * 1000)}_{fname}", real, sample, pl,
                           note=f"form {form}: bid old range high on {w:.1%} range bars after a 3w impulse, fill {fname}, " + ("target +1w maker, stop -2w, 60 min" if form != "e" else "target A = post-breakout low, stop -2w, 6 h") + "; base = placebo levels 0.63x/1.37x")
        y = E[(E.w == w) & (E.fill == "q250k") & (E.kind == "real")]
        if len(y):
            t = pd.to_datetime(y.time)
            print("   q250k real by year:", {int(k): round(float(v) * 1e4, 1) for k, v in (y.gross - y.cost).groupby(t.dt.year).mean().items()},
                  "by side:", {int(k): round(float(v) * 1e4, 1) for k, v in (y.gross - y.cost).groupby(y.side).mean().items()})


if __name__ == "__main__":
    {"explore": explore}[sys.argv[1]](*sys.argv[2:])
