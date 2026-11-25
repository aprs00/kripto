"""X1 c: single-print fill + absorption. Per UTC day, 30-min TPO periods on 10-bp bins (aggTrades micro bars): single-print zone = >= 3 contiguous bins touched
by exactly one period, with bins touched by >= 2 periods both above and below (tails are not single prints). First touch within 3 days; side = approach
(from above -> long). Then the 5-min window: opposing taker delta share and 'held' (as is3_m7.touch_flow); entry touch + 5 min + 1 s, 60 min.
Compare held + top-tercile opposing delta ('absorption') with held + bottom tercile, and with the zone mirrored around the day's close. notes.md X1.

    nice -n 19 .venv/bin/python -W ignore -m research.studies.is3_x1c explore
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from research.studies import is3_lib as L
from research.studies.is3_m7 import BIN, COINS, load, touch_flow


def zones(k, per):
    """single-print zones (bin index ranges) from bin index k and 30-min period id per micro bar."""
    k0 = k.min()
    nb = k.max() - k0 + 1
    touched = np.zeros((nb, per.max() - per.min() + 1), dtype=bool)
    touched[k - k0, per - per.min()] = True
    cnt = touched.sum(1)
    multi = np.flatnonzero(cnt >= 2)
    if len(multi) < 2:
        return []
    out, run = [], []
    for i in range(multi[0], multi[-1] + 1):
        if cnt[i] == 1:
            run.append(i)
        else:
            if len(run) >= 3:
                out.append((k0 + run[0], k0 + run[-1] + 1))
            run = []
    return out


def run(sample):
    lo, hi = L.SAMPLES[sample]
    rows = []
    for coin in COINS:
        b = load(coin, lo, hi)
        t1 = b["t1"]
        day = t1 // 86_400_000
        cut = np.flatnonzero(np.diff(day)) + 1
        for s, e in zip(np.concatenate([[0], cut]), np.concatenate([cut, [len(day)]])):
            if e - s < 50 or e >= len(day):
                continue
            # each micro bar spans its own [l, h]: mark every bin it covers (bars are ~10 bp, so 1-2 bins)
            kl = np.floor(np.log(b["l"][s:e]) / BIN).astype(np.int64)
            kh = np.floor(np.log(b["h"][s:e]) / BIN).astype(np.int64)
            per = (t1[s:e] // 1_800_000).astype(np.int64)
            k = np.concatenate([kl, kh])
            pp = np.concatenate([per, per])
            C = b["c"][e - 1]
            t_end = t1[e - 1] + 3 * 86_400_000
            for (a, z) in zones(k, pp):
                zlo, zhi = np.exp(a * BIN), np.exp(z * BIN)
                if zlo <= C <= zhi:
                    continue
                side = 1 if zhi < C else -1
                for kind, (x0, x1), sd in (("real", (zlo, zhi), side), ("mirror", (C * C / zhi, C * C / zlo), -side)):
                    x = touch_flow(b, e, x0, x1, sd, t_end)
                    if x is not None:
                        rows.append({"time": pd.Timestamp(x[0], unit="ms", tz="UTC"), "coin": coin, "side": sd, "gross": x[1], "kind": kind, "opp": x[2], "held": x[3]})
        del b
    d = pd.DataFrame(rows)
    d = d[d.time < pd.Timestamp(hi, tz="UTC") - pd.Timedelta("2h")]
    d["oq"] = d.groupby("coin")["opp"].transform(lambda x: pd.qcut(x, 3, labels=False))
    print("60-min bp after the 5-min window by held x opposing-delta tercile:")
    print((d.pivot_table(index=["held", "oq"], columns="kind", values="gross", aggfunc="mean") * 1e4).round(1).to_string())
    print(d.pivot_table(index=["held", "oq"], columns="kind", values="gross", aggfunc="count").to_string())
    ab = d[(d.kind == "real") & d.held & (d.oq == 2)]
    L.card("x1c_sp_absorb", ab[["time", "coin", "side", "gross"]], sample, base=d[(d.kind == "mirror") & d.held & (d.oq == 2)][["time", "coin", "side", "gross"]],
           note="single-print zone first touch, held 5 min vs top-tercile opposing delta, vs mirrored zones under the same condition")
    L.card("x1c_sp_absorb_vs_noabs", ab[["time", "coin", "side", "gross"]], sample, base=d[(d.kind == "real") & d.held & (d.oq == 0)][["time", "coin", "side", "gross"]],
           note="same vs held with the least opposing delta")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "explore")
