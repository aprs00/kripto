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
    E = []
    for sym in M.COINS:                                       # per quarter, filtered at once (M.collect keeps every micro-width event: OOM)
        for y in range(int(lo[:4]), int(hi[:4])):
            for q in range(4):
                a = f"{y}-{3 * q + 1:02d}-01"
                z = f"{y}-{3 * q + 4:02d}-01" if q < 3 else f"{y + 1}-01-01"
                e, _ = M.coin_events(sym, max(lo, a), min(hi, z))
                E.append(e[(e.w > 0.001) & (e.lr >= np.log(5))].copy())
                print(sym, a, len(E[-1]), flush=True)
    E = pd.concat(E, ignore_index=True)
    # M2 does not store the bar close price: take the micro bar that closed the range bar (its t1 = the event time)
    rows = []
    for coin, g in E.groupby("coin"):
        from research.studies.is3_m6 import load as light
        b = light(f"{coin}USDT", lo, hi)                     # t1/h/l/c only
        tms = ((g.time - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta("1ms")).to_numpy(dtype=np.int64)    # unit-safe (pandas 3: us or ms)
        k = np.clip(np.searchsorted(b["t1"], tms, side="right") - 1, 0, len(b["c"]) - 1)
        assert np.all(np.abs(b["t1"][k] - tms) < 1000), "event time does not match a micro bar close"
        g = g.assign(px=b["c"][k])
        rows.append(g)
        del b
    E = pd.concat(rows)
    E["loc"] = np.where(near(E.px.to_numpy(), 0.0), "round", np.where(near(E.px.to_numpy(), 0.37), "placebo", "none"))
    E["K"] = pd.cut(E.lr, [np.log(5), np.log(10), np.log(20), np.inf], labels=["5-10", "10-20", ">=20"], right=False)
    E.to_parquet(L.ROOT / "data/is3/x1f_events.parquet")
    t = E.pivot_table(index=["K", "loc"], values=["g15", "g60", "g240", "late60"], aggfunc="mean", observed=True) * 1e4
    t["n"] = E.groupby(["K", "loc"], observed=True).size()
    print("fade returns after a trade-count jump (bp) by K x location:")
    print(t.round(1).to_string())
    e = E[(E.lr >= np.log(10)) & (E["loc"] == "round")].assign(gross=lambda z: z.g60)
    b = E[(E.lr >= np.log(10)) & (E["loc"] == "placebo")].assign(gross=lambda z: z.g60)
    L.card("x1f_vel_round", e[["time", "coin", "side", "gross"]], sample, base=b[["time", "coin", "side", "gross"]],
           note="trade-count jump >= 10x on 0.2/0.43% range bars closing within 10 bp of a round level, faded 60 min, vs placebo levels")


if __name__ == "__main__" and len(sys.argv) <= 2:
    run(sys.argv[1] if len(sys.argv) > 1 else "explore")


def dedup(sample):
    """Second pass on the stored events: M2's events cluster (up to 123 range-bar 'jumps' inside one second of ms whipsaw prints, 2022-01-05 19:45:21)
    and its g-columns start at the exact print. Keep the first event per coin per 30 min (jumps >= 10x, w 0.2/0.43%), outcome = late60 (entry 5 min
    after the event at the then-current micro close, 60 min)."""
    E = pd.read_parquet(L.ROOT / "data/is3/x1f_events.parquet")
    E = E[E.lr >= np.log(10)].sort_values("time")
    E["slot"] = E.time.dt.floor("30min")
    E = E.groupby(["coin", "slot"]).head(1)
    E = E[np.isfinite(E.late60)]
    t = E.groupby("loc").late60.agg(["mean", "median", "count"])
    print("deduplicated (1 per coin per 30 min), late60 fade (bp):\n", (t.assign(mean=t["mean"] * 1e4, median=t["median"] * 1e4)).round(1).to_string())
    print("by side:", (E.pivot_table(index="loc", columns="side", values="late60", aggfunc="mean") * 1e4).round(1).to_dict())
    e = E[E["loc"] == "round"].assign(gross=lambda z: z.late60)
    for nm, b in (("placebo", E[E["loc"] == "placebo"]), ("none", E[E["loc"] == "none"])):
        L.card(f"x1f_vel_round_dedup_vs_{nm}", e[["time", "coin", "side", "gross"]], sample, base=b.assign(gross=b.late60)[["time", "coin", "side", "gross"]],
               note="1 event per coin per 30 min, entry 5 min late, 60 min fade")


if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[2] == "dedup":
    dedup(sys.argv[1])
