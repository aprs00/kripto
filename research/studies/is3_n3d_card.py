"""N3f pre-registered: absorption. Daily, bnall clean, coins in the point-in-time top 100: 3-day summed taker-imbalance z (60-day
stats, shift 1) <= -2 while the 3-day return >= 0 -> long at the close, hold 5 days (taker). Baseline = same coin, same trailing
14-day return decile, 3 matched days (long). explore = half-0 coins 2021-23; confirmT = half-0 coins 2024-25; confirmC = half-1 coins 2021-25.

    nice -n 19 .venv/bin/python -m research.studies.is3_n3d_card explore|confirmT|confirmC
"""
from __future__ import annotations

import sys

import pandas as pd

from kripto import data
from research.studies import is3_lib as L

NAME = "N3f_absorption_long_5d"


def main(sample: str) -> None:
    lo, hi = L.SAMPLES[sample]
    hv = 1 if sample == "confirmC" else 0
    p = data.load_panel("bnall", "1d")
    keep = [c for c in p["close"].columns if L.half(c) == hv]
    c, v, tb = (p[k][keep].loc["2020-06-01":"2026-02-01"] for k in ("close", "volume", "taker_buy"))
    top = v.rolling(30, min_periods=20).mean().shift(1).rank(axis=1, ascending=False) <= 100
    imb = 2 * tb / v - 1
    z = (imb - imb.rolling(60, min_periods=30).mean().shift(1)) / imb.rolling(60, min_periods=30).std().shift(1)
    z3, r3 = z.rolling(3).sum(), c / c.shift(3) - 1
    fr = pd.concat({"ret14": (c / c.shift(14) - 1).stack(), "f5": (c.shift(-5) / c - 1).stack(), "top": top.stack(), "ev": ((z3 <= -2) & (r3 >= 0)).stack()}, axis=1).reset_index()
    fr.columns = ["time", "coin", "ret14", "f5", "top", "ev"]
    fr = fr[(fr.time >= lo) & (fr.time < hi) & fr.top.astype(bool)].dropna(subset=["ret14", "f5"])
    fr["m"] = (fr.groupby("coin").ret14.rank(pct=True) * 9.999).astype(int)
    e, pool = fr[fr.ev.astype(bool)], fr[~fr.ev.astype(bool)]
    base = L.matched(e, pool, k=3)
    cols = ["time", "coin", "side", "gross"]
    L.card(NAME, e.assign(side=1, gross=e.f5)[cols], sample, base.assign(side=1, gross=base.f5)[cols],
           note="long 5 d after 3-day taker-imbalance z <= -2 with the 3-day return >= 0; base = same coin, same trailing 14-d return decile")


if __name__ == "__main__":
    main(sys.argv[1])
