"""InSilico pass 3, CRB: carry / carry_trend on bnall: funding received vs price P&L by |funding| decile and side. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_crb a    # -> research/is3/crb_a.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data
from kripto import strategies as S


def run_a():
    p = data.load_panel("bnall", "1d")
    c = p["close"]
    ret = (c / c.shift(1) - 1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    fund = p["funding"].reindex(index=c.index, columns=c.columns).fillna(0.0)
    f7 = p["funding"].rolling(7, min_periods=1).mean()
    uni = S.universe(p, 30) & f7.notna()
    dec = f7.abs().where(uni).rank(axis=1, pct=True)            # cross-sectional |funding| percentile in the top-30 universe, known at the close
    out = {}
    for name in ("carry", "carry_trend"):
        w = S.REGISTRY[name](p).ffill().fillna(0.0)
        wl = w.shift(1).fillna(0.0)
        dl = dec.shift(1)
        pr, fu = wl * ret, -wl * fund
        rows = {}
        for y in range(2021, 2027):
            yy = str(y)
            d = {}
            for side, sm in (("long", wl > 0), ("short", wl < 0)):
                for lab, lo, hi in (("d1-5", 0, .5), ("d6-8", .5, .8), ("d9", .8, .9), ("d10", .9, 1.01)):
                    m = (sm & (dl > lo) & (dl <= hi)).loc[yy]
                    gross = wl.abs().where(m, 0).loc[yy].sum().sum()
                    if gross < 1:
                        continue
                    a, b = pr.loc[yy].where(m, 0).sum().sum(), fu.loc[yy].where(m, 0).sum().sum()
                    d[f"{side}_{lab}"] = {"unit_days": round(float(gross), 1), "price_bp_per_unit_day": round(float(a / gross * 1e4), 1),
                                          "funding_bp_per_unit_day": round(float(b / gross * 1e4), 1), "net_bp": round(float((a + b) / gross * 1e4), 1)}
            rows[y] = d
        out[name] = rows
        print(name, json.dumps(rows), flush=True)
    json.dump(out, open("research/is3/crb_a.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": run_a}[sys.argv[1]]()
