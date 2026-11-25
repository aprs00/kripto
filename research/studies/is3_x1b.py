"""X1 b: capitulation flow at a prior POC. Hours of one-voiced selling (taker delta share in the coin's bottom decile of the previous 30 days and an hour
return <= -1 sigma of the previous 30 days) whose low reaches the prior UTC day's exact POC (aggTrades 10-bp profile) from above -> long at the hour
close + 1 s, 4 h and 24 h simple returns. Placebo: the same hours at the prior POC mirrored around the prior day's close. Baseline: the same selling hours
not touching either level, matched on the hour-return decile. notes.md section X1.

    nice -n 19 .venv/bin/python -W ignore -m research.studies.is3_x1b explore
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from research.studies import is3_lib as L
from research.studies.is3_m7 import BIN, COINS, asof, load

H = 3_600_000


def hours(coin, lo, hi):
    b = load(coin, lo, hi)
    t1 = b["t1"]
    hr = t1 // H
    g = pd.DataFrame({"hr": hr, "h": b["h"], "l": b["l"], "c": b["c"], "bs": b["bs"], "ss": b["ss"]}).groupby("hr")
    a = g.agg(h=("h", "max"), l=("l", "min"), c=("c", "last"), bs=("bs", "sum"), ss=("ss", "sum"))
    a["o"] = a["c"].shift(1)
    a["ret"] = a["c"] / a["o"] - 1
    a["ds"] = (a.bs - a.ss) / (a.bs + a.ss)
    a["sig"] = a["ret"].rolling(720, min_periods=300).std().shift(1)
    a["dq10"] = a["ds"].rolling(720, min_periods=300).quantile(0.1).shift(1)
    # prior-day exact POC and close
    day = t1 // 86_400_000
    poc = {}
    cut = np.flatnonzero(np.diff(day)) + 1
    for s, e in zip(np.concatenate([[0], cut]), np.concatenate([cut, [len(day)]])):
        k = np.floor(np.log(np.sqrt(b["h"][s:e] * b["l"][s:e])) / BIN).astype(np.int64)
        V = np.bincount(k - k.min(), weights=b["bs"][s:e] + b["ss"][s:e])
        i = int(V.argmax())
        poc[int(day[s])] = (np.exp((k.min() + i) * BIN), np.exp((k.min() + i + 1) * BIN), b["c"][e - 1])
    a["day"] = (a.index * H) // 86_400_000
    a["P"] = a["day"].map(lambda d: poc.get(d - 1, (np.nan,) * 3))
    a["plo"], a["phi"], a["pc"] = (a["P"].map(lambda x: x[0]), a["P"].map(lambda x: x[1]), a["P"].map(lambda x: x[2]))
    a["mlo"], a["mhi"] = a.pc ** 2 / a.phi, a.pc ** 2 / a.plo
    sel = a[(a.ds <= a.dq10) & (a.ret <= -a.sig)].copy()
    sel["at_real"] = (sel.l <= sel.phi) & (sel.o > sel.phi)
    sel["at_mirror"] = (sel.l <= sel.mhi) & (sel.o > sel.mhi)
    out = []
    for hrv, r in sel.iterrows():
        te = (hrv + 1) * H + 1000
        p0 = asof(t1, b["c"], te)
        if te + 24 * H > t1[-1]:
            continue
        out.append({"time": pd.Timestamp(te, unit="ms", tz="UTC"), "coin": coin, "side": 1, "r4": asof(t1, b["c"], te + 4 * H) / p0 - 1,
                    "r24": asof(t1, b["c"], te + 24 * H) / p0 - 1, "ret": r.ret / r.sig, "real": bool(r.at_real), "mirror": bool(r.at_mirror)})
    return pd.DataFrame(out)


def run(sample):
    lo, hi = L.SAMPLES[sample]
    d = pd.concat([hours(c, lo, hi) for c in COINS], ignore_index=True)
    d = d[d.time < pd.Timestamp(hi, tz="UTC") - pd.Timedelta("1D")]
    d["m"] = d.groupby("coin")["ret"].transform(lambda x: pd.qcut(x, 5, labels=False)).astype(str)
    d["grp"] = np.where(d.real, "real", np.where(d.mirror, "mirror", "none"))
    print("selling hours, long next 4 h / 24 h (bp):")
    print((d.groupby("grp")[["r4", "r24"]].mean() * 1e4).round(1).assign(n=d.groupby("grp").size()).to_string())
    print("by year:", (d.pivot_table(index=d.time.dt.year, columns="grp", values="r24", aggfunc="mean") * 1e4).round(0).to_dict())
    for h in ("r4", "r24"):
        e = d[d.real].assign(gross=lambda z: z[h])
        pool = d[d.grp == "none"].assign(gross=lambda z: z[h])
        L.card(f"x1b_poc_capit_{h}", e[["time", "coin", "side", "gross"]], sample, base=L.matched(e, pool, k=5),
               note=f"one-voiced selling hour tagging the prior-day exact POC from above, long {h}, vs same hours away from levels (ret quintile)")
        m = d[d.mirror].assign(gross=lambda z: z[h])
        print(f"  {h}: mirror n {len(m)} {m.gross.mean()*1e4:+.1f} bp")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "explore")
