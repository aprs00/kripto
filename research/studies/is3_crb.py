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




def run_b():
    p = data.load_panel("bnall", "1d")
    c = p["close"]
    ret = (c / c.shift(1) - 1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    fund = p["funding"].reindex(index=c.index, columns=c.columns).fillna(0.0)
    dv = S.dollar_volume(p)
    out = {}
    for name in ("carry", "carry_trend"):
        wl = S.REGISTRY[name](p).ffill().fillna(0.0).shift(1).fillna(0.0).loc["2025":]
        pr, fu = (wl * ret.loc[wl.index]).sum(), (-wl * fund.loc[wl.index]).sum()
        top_f = fu.sort_values(ascending=False).head(10)
        top_p = pr.sort_values().head(10)
        held = wl != 0
        adv = dv.loc[wl.index].where(held)
        r = (wl * ret.loc[wl.index]).sum(axis=1) - (wl * fund.loc[wl.index]).sum(axis=1)
        out[name] = {"funding_total": round(float(fu.sum()), 3), "top10_funding_share": round(float(top_f.sum() / fu.sum()), 2), "top10_funding": {k: round(float(v), 3) for k, v in top_f.items()},
                     "price_total": round(float(pr.sum()), 3), "top10_price_loss": {k: round(float(v), 3) for k, v in top_p.items()},
                     "held_adv_median_musd": round(float(np.nanmedian(adv.to_numpy()) / 1e6), 1), "held_adv_p10_musd": round(float(np.nanquantile(adv.to_numpy(), .1) / 1e6), 1),
                     "worst10_days": {str(k.date()): round(float(v), 4) for k, v in r.nsmallest(10).items()}}
        print(name, json.dumps(out[name]), flush=True)
    json.dump(out, open("research/is3/crb_b.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": run_a, "b": run_b}[sys.argv[1]]()
