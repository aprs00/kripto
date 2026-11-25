"""X1 e: pinned oscillator + fat-node break. COINS10 2021-23, 1-min Binance klines, 10-bp daily volume profiles (is3_p1.profiles).
Day d's close crosses the 20-day composite POC (the fattest node of the previous 20 daily profiles) in direction s; confluence = daily RSI14
pinned the same way (> 70 for s = +1, < 30 for s = -1) on d and the 2 days before. Outcome: s x close(d+H)/close(d) - 1, H = 1/3/5.
Baselines: (1) node crosses without a pin; (2) crosses of the 20-day median close WITH the same pin (is the node special given the pin?). notes.md X1.

    nice -n 19 .venv/bin/python -W ignore -m research.studies.is3_x1e explore
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from research.studies import is3_lib as L
from research.studies import is3_p1 as P
from research.studies.is3_o1 import rsi


def coin_rows(coin, lo, hi):
    k = P.load(coin, "2020-11-01", "2024-01-20")
    D = P.profiles(k)
    close = k.c.resample("1D").last()
    r = rsi(close.to_frame())[close.name]
    days = sorted(d for d in D if d in close.index)
    rows = []
    for n, d in enumerate(days):
        if n < 21 or n + 5 >= len(days) or not (pd.Timestamp(lo, tz="UTC") <= d < pd.Timestamp(hi, tz="UTC") - pd.Timedelta("6D")):
            continue
        comp = {}
        for dd in days[n - 20:n]:
            off, prof = D[dd][0], D[dd][1]
            for j, vv in enumerate(prof):
                comp[off + j] = comp.get(off + j, 0.0) + vv
        node = np.exp((max(comp, key=comp.get) + 0.5) * P.BIN)
        med = float(np.median([close[dd] for dd in days[n - 20:n]]))
        prev, c = close[days[n - 1]], close[d]
        rr = [r.get(x, np.nan) for x in days[n - 2:n + 1]]
        pin = 1 if all(v > 70 for v in rr) else (-1 if all(v < 30 for v in rr) else 0)
        for kind, lev in (("node", node), ("median", med)):
            if (prev - lev) * (c - lev) < 0:
                s = 1 if c > lev else -1
                row = {"time": d, "coin": coin, "kind": kind, "side": s, "pin": pin * s}       # pin*s = +1 confluence, -1 against, 0 none
                for H in (1, 3, 5):
                    row[f"f{H}"] = s * (close[days[n + H]] / c - 1)
                rows.append(row)
    return rows


def run(sample):
    lo, hi = L.SAMPLES[sample]
    coins = L.COINS10 if sample == "explore" else None
    d = pd.DataFrame([x for c in coins for x in coin_rows(c, lo, hi)])
    t = d.pivot_table(index=["kind", "pin"], values=["f1", "f3", "f5"], aggfunc="mean") * 1e4
    t["n"] = d.groupby(["kind", "pin"]).size()
    print("side-signed return after a close through the level (bp); pin +1 = RSI pinned the same way 3 days, -1 = against, 0 none")
    print(t.round(1).to_string())
    for H in ("f3", "f5"):
        e = d[(d.kind == "node") & (d.pin == 1)].assign(gross=lambda z: z[H])
        b1 = d[(d.kind == "node") & (d.pin == 0)].assign(gross=lambda z: z[H])
        b2 = d[(d.kind == "median") & (d.pin == 1)].assign(gross=lambda z: z[H])
        L.card(f"x1e_pin_node_{H}", e[["time", "coin", "side", "gross"]], sample, base=b2[["time", "coin", "side", "gross"]],
               note=f"node cross with RSI pinned the same way vs median-close cross with the same pin; node w/o pin {b1.gross.mean()*1e4:+.0f} bp n {len(b1)}")


if __name__ == "__main__" and len(sys.argv) <= 2:
    run(sys.argv[1] if len(sys.argv) > 1 else "explore")


def pinned_days(sample):
    """Control: every day with RSI pinned (3 days) in COINS10, side = pin direction, f3 -- does the node cross add anything to the pin itself?"""
    lo, hi = L.SAMPLES[sample]
    rows = []
    for coin in L.COINS10:
        k = P.load(coin, "2020-11-01", "2024-01-20")
        close = k.c.resample("1D").last()
        r = rsi(close.to_frame())[close.name]
        up = (r > 70) & (r.shift(1) > 70) & (r.shift(2) > 70)
        dn = (r < 30) & (r.shift(1) < 30) & (r.shift(2) < 30)
        for H in (3,):
            f = close.shift(-H) / close - 1
            for d in close.index[(up | dn) & (close.index >= pd.Timestamp(lo, tz="UTC")) & (close.index < pd.Timestamp(hi, tz="UTC") - pd.Timedelta("6D"))]:
                s = 1 if up[d] else -1
                rows.append({"time": d, "coin": coin, "side": s, "gross": s * f[d], "ret14": s * (close[d] / close.shift(14)[d] - 1)})
    return pd.DataFrame(rows)


if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[2] == "control":
    p = pinned_days(sys.argv[1])
    print("all pinned days f3:", len(p), round(p.gross.mean() * 1e4, 1), "bp; by side", (p.groupby("side").gross.mean() * 1e4).round(1).to_dict())
    p["q"] = pd.qcut(p.ret14, 5, labels=False)
    print("by 14-d return quintile (same direction):", (p.groupby("q").gross.mean() * 1e4).round(0).to_dict(), (p.groupby("q").ret14.mean() * 100).round(0).to_dict())
