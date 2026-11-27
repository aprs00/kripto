"""InSilico pass 3, HLI: the HL main book (blend listing_short + lowvol + tsmom) on days listing_short holds nothing. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_hli a    # idle share by year/month, blend on idle vs active days, cash-on-idle variant -> research/is3/hli_a.json
"""
from __future__ import annotations

import inspect
import json
import sys

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto import strategies as S
from kripto.research import default_band

COMPS = {"listing_short": {}, "lowvol": {}, "tsmom": {}}
sr = lambda x: round(float(x.mean() / x.std() * np.sqrt(365)), 2) if len(x) > 20 and x.std() > 0 else None


def run_a():
    p = data.load_panel("hl", "1d")
    c = p["close"]
    run = lambda w: bt.run(w, c, p["funding"], bt.slippage_model(p["volume"], 1), band=default_band())
    wls = S.REGISTRY["listing_short"](p).ffill().fillna(0.0)
    names = (wls.drop(columns=["BTC"], errors="ignore") < 0).sum(axis=1)
    res = run(S.REGISTRY["blend"](p, components=COMPS))
    r = res.returns[res.gross > 0]
    held = names.shift(1).reindex(r.index).fillna(0)          # names held during bar t (decided at t-1)
    idle = held == 0
    out = {"idle_share_by_year": {int(y): round(float(x.mean()), 2) for y, x in idle.groupby(idle.index.year)},
           "names_dist_by_year": {int(y): {"0": round(float((x == 0).mean()), 2), "1": round(float((x == 1).mean()), 2), "2+": round(float((x >= 2).mean()), 2)} for y, x in held.groupby(held.index.year)},
           "idle_share_by_month_2026": {str(k): round(float(v), 2) for k, v in idle.loc["2026"].groupby(idle.loc["2026"].index.strftime("%Y-%m")).mean().items()},
           "blend_idle": {"days": int(idle.sum()), "sr": sr(r[idle]), "vol": round(float(r[idle].std() * np.sqrt(365)), 3), "mean_yr": round(float(r[idle].mean() * 365), 3)},
           "blend_active": {"days": int((~idle).sum()), "sr": sr(r[~idle]), "vol": round(float(r[~idle].std() * np.sqrt(365)), 3), "mean_yr": round(float(r[~idle].mean() * 365), 3)},
           "blend_idle_by_year": {int(y): sr(x) for y, x in r[idle].groupby(r[idle].index.year)}}
    # cash-on-idle: the same blend but on idle days the two remaining legs keep the scale they would have with listing_short's third in cash (x 2/3 of the rescaled weights)
    # approximation stated: scale the blend's weights by 2/3 on idle days (the vol target re-inflated the 2-leg sum to the full target)
    wb = S.REGISTRY["blend"](p, components=COMPS)
    idle_dec = (names == 0).reindex(wb.index).fillna(True)
    wc = wb.mul(np.where(idle_dec, 2 / 3, 1.0), axis=0)
    rc = run(wc)
    rc_r = rc.returns.reindex(r.index)
    out["cash_on_idle"] = {"sr_all": sr(rc_r), "sr_live": sr(r), "net_yr_all": round(float(rc_r.mean() * 365), 3), "net_yr_live": round(float(r.mean() * 365), 3),
                           "vol_all": round(float(rc_r.std() * np.sqrt(365)), 3), "vol_live": round(float(r.std() * np.sqrt(365)), 3),
                           "by_year_sr": {int(y): [sr(r[r.index.year == y]), sr(rc_r[rc_r.index.year == y])] for y in sorted(set(r.index.year))}}
    print(json.dumps(out, indent=1))
    json.dump(out, open("research/is3/hli_a.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": run_a}[sys.argv[1]]()
