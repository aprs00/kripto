"""X1 d: Sunday move + falling volume + distance from the collar (confluence of W1 a and d). From data/is3/weekend.parquet (is3_weekend build).
Event: Sunday 16-18 NY 'bait' move of >= b on falling volume (bait_v < 1) that moved price AWAY from Friday's collar (vwap 14-16 NY) and leaves
|gap| >= g -> trade toward the collar from Sunday 18:00 NY: exit at touch (t_vwap) or Monday 17:00. Placebo: the same construction from Tuesday ('pl').
Second baseline: weekend gaps of the same size without the confluence. notes.md X1.

    .venv/bin/python -W ignore -m research.studies.is3_x1d explore
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from research.studies import is3_lib as L
from research.studies.is3_lshock import sample
from research.studies.is3_weekend import OUT, ev


def run(s):
    t = sample(pd.read_parquet(OUT / "weekend.parquet"), s)
    t = t[np.isfinite(t.gap_vwap) & np.isfinite(t.bait)]
    conf = lambda u, b: u[(u.bait.abs() >= b) & (u.bait_v < 1) & (np.sign(u.bait) == -np.sign(u.gap_vwap))]
    print("touch-exit return toward the collar (bp), n; rows g, cols bait size")
    for g in (0.01, 0.02, 0.04):
        line = []
        for b in (0.005, 0.01, 0.02):
            W, P = (conf(t[(t.kind == k) & (t.gap_vwap.abs() >= g)], b) for k in ("wk", "pl"))
            rest = t[(t.kind == "wk") & (t.gap_vwap.abs() >= g)]
            line.append(f"b{b*100:g}: wk {W.t_vwap.mean()*1e4:+.0f} (n {len(W)}) pl {P.t_vwap.mean()*1e4:+.0f} (n {len(P)}) all-wk {rest.t_vwap.mean()*1e4:+.0f}")
        print(f"g {g*100:g}%: " + " | ".join(line))
    for g, b in ((0.01, 0.005), (0.02, 0.01)):
        W, P = (conf(t[(t.kind == k) & (t.gap_vwap.abs() >= g)], b) for k in ("wk", "pl"))
        L.card(f"x1d_g{g*100:g}_b{b*100:g}", ev(W, W.t_vwap, np.sign(W.gap_vwap)), s, base=ev(P, P.t_vwap, np.sign(P.gap_vwap)),
               note="Sunday bait away from the collar on falling volume, toward the collar, touch exit or Monday 17:00, vs Tuesday placebo")
        rest = t[(t.kind == "wk") & (t.gap_vwap.abs() >= g)]
        rest = rest[~rest.index.isin(W.index)]
        print(f"  vs weekend gaps without the confluence: {W.t_vwap.mean()*1e4:+.0f} vs {rest.t_vwap.mean()*1e4:+.0f} bp; by year",
              {y: round(W[W.time.dt.year == y].t_vwap.mean() * 1e4) for y in (2021, 2022, 2023)})


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "explore")
