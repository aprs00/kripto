"""X1 f: order-velocity climax at a round number. M2's events (range bars 0.2/0.43%, trade-count ratio n_i/n_{i-1} >= 10 = 'jump', is3_m2.coin_events)
on BTC/ETH/SOL 2021-23, faded (side = against the bar), g15/g60/g240 from the bar close. Location: bar close within 10 bp of a round level
(multiples of 10^(floor(log10 p) - 1): BTC 1000s, ETH 100s, SOL 10s / 1s) vs within 10 bp of a placebo level (same grid shifted by 0.37 step)
vs neither. Dose: K = 5 / 10 / 20. notes.md X1.

    nice -n 19 .venv/bin/python -W ignore -m research.studies.is3_x1f explore
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from research.studies import is3_lib as L
from research.studies import is3_m2 as M


def near(p: np.ndarray, shift: float) -> np.ndarray:
    step = 10.0 ** (np.floor(np.log10(p)) - 1)
    x = p / step - shift
    lev = (np.round(x) + shift) * step
    return np.abs(np.log(p / lev)) < 1e-3


def run(sample):
    lo, hi = L.SAMPLES[sample]
    E, _ = M.collect(lo, hi)
    E = E[(E.w > 0.001) & (E.lr >= np.log(5))].copy()        # trade-count jumps only, his range-bar sizes
    # bar close price is not stored by M2: recover from g? no -- recompute from the micro bars at the event time
    rows = []
    for coin, g in E.groupby("coin"):
        from kripto import mbars
        b = mbars.load(f"{coin}USDT", lo, hi)
        k = np.clip(np.searchsorted(b["t1"], g.time.astype("int64") // 1000, side="right") - 1, 0, len(b["c"]) - 1)
        g = g.assign(px=b["c"][k])
        rows.append(g)
        del b
    E = pd.concat(rows)
    E["loc"] = np.where(near(E.px.to_numpy(), 0.0), "round", np.where(near(E.px.to_numpy(), 0.37), "placebo", "none"))
    E["K"] = pd.cut(E.lr, [np.log(5), np.log(10), np.log(20), np.inf], labels=["5-10", "10-20", ">=20"], right=False)
    t = E.pivot_table(index=["K", "loc"], values=["g15", "g60", "g240"], aggfunc="mean", observed=True) * 1e4
    t["n"] = E.groupby(["K", "loc"], observed=True).size()
    print("fade returns after a trade-count jump (bp) by K x location:")
    print(t.round(1).to_string())
    e = E[(E.lr >= np.log(10)) & (E["loc"] == "round")].assign(gross=lambda z: z.g60)
    b = E[(E.lr >= np.log(10)) & (E["loc"] == "placebo")].assign(gross=lambda z: z.g60)
    L.card("x1f_vel_round", e[["time", "coin", "side", "gross"]], sample, base=b[["time", "coin", "side", "gross"]],
           note="trade-count jump >= 10x on 0.2/0.43% range bars closing within 10 bp of a round level, faded 60 min, vs placebo levels")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "explore")
