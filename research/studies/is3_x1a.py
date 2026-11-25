"""X1 a: the confirmed resting-ladder fill (T1k30, one bar late) at a prior-day / weekly low vs elsewhere. notes.md section X1.

    nice -n 19 .venv/bin/python -W ignore -m research.studies.is3_x1a explore
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from research.studies import is3_lib as L
from research.studies import is3_ladtop as T


def features(sample):
    lo, hi = (pd.Timestamp(x, tz="UTC") for x in L.SAMPLES[sample])
    f = pd.read_parquet(L.ROOT / "data/is3/e2_k-30.parquet")
    f = f[(f.time >= lo) & (f.time < hi - pd.Timedelta("1D"))].copy()
    rows = []
    for coin, g in f.groupby("coin"):
        parts = T.series(coin, lo - pd.Timedelta("10D"), hi)
        if not parts:
            continue
        x = pd.concat(parts)
        x = x[~x.index.duplicated()]
        dl = x["l"].resample("1D").min()
        pdl = dl.shift(1)
        pwl = dl.rolling(7).min().shift(1)
        for _, r in g.iterrows():
            t = r.time
            cp = x["c"].asof(t - pd.Timedelta("2min"))
            p = cp * (1 - r.depth)
            d = t.floor("D")
            rows.append({"time": t, "coin": coin, "depth": r.depth, "h60": r.h60, "h240": r.h240, "h15": r.h15,
                         "xd": np.log(p / pdl.get(d, np.nan)), "xw": np.log(p / pwl.get(d, np.nan)),
                         "today_low_before": np.log(p / x["l"][d:t - pd.Timedelta("1min")].min()) if t > d + pd.Timedelta("1min") else np.nan})
    return pd.DataFrame(rows)


def run(sample):
    d = features(sample).dropna(subset=["xd", "xw"])
    d["side"] = 1
    d["dq"] = pd.qcut(d.depth, 5, labels=False).astype(str)
    bins = [-np.inf, -0.02, 0, 0.02, np.inf]
    lab = ["thru>2%", "thru0-2%", "above0-2%", "above>2%"]
    for col in ("xd", "xw"):
        d[col + "b"] = pd.cut(d[col], bins, labels=lab)
        t = d.groupby(col + "b", observed=True).agg(n=("h60", "size"), h15=("h15", "mean"), h60=("h60", "mean"), h240=("h240", "mean"), depth=("depth", "mean"))
        print(f"\n{col} (fill price vs prior {'day' if col == 'xd' else '7-day'} low), bp:")
        print((t.assign(h15=t.h15 * 1e4, h60=t.h60 * 1e4, h240=t.h240 * 1e4, depth=t.depth * 1e4)).round(0).to_string())
    print("\nfresh low of today before the fill (fill below every earlier price today) share:", round(float((d.today_low_before < 0).mean()), 2))
    for col, name in (("xd", "x1a_pdl"), ("xw", "x1a_pwl")):
        at = d[d[col] <= 0.0]
        rest = d[d[col] > 0.0].assign(m=lambda z: z.dq)
        e = at.assign(gross=at.h60, m=at.dq)
        base = L.matched(e, rest.assign(gross=rest.h60), k=3)
        L.card(name, e[["time", "coin", "side", "gross"]], sample, base=base, note=f"T1k30 late fills at/through the prior {'day' if col == 'xd' else 'week'} low vs other fills matched on depth quintile, h60")
        print("  by year at / rest:", {y: (round(at[at.time.dt.year == y].h60.mean() * 1e4), round(rest[rest.time.dt.year == y].h60.mean() * 1e4)) for y in (2021, 2022, 2023)})


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "explore")
