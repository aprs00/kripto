"""InSilico pass 3, XST: xsmom vs tsmom as blend_nested@bn's 3rd component on bnall. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_xst ab   # -> research/is3/xst_ab.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto import strategies as S
from kripto.research import default_band

sr = lambda x: round(float(x.mean() / x.std() * np.sqrt(365)), 2)
mdd = lambda x: round(float(((1 + x).cumprod() / (1 + x).cumprod().cummax() - 1).min()), 3)


def run_ab():
    p = data.load_panel("bnall", "1d")
    c = p["close"]
    slip = bt.slippage_model(p["volume"], 1)
    run = lambda w: bt.run(w, c, p["funding"], slip, band=default_band()).returns.loc["2021":]
    R = {k: run(S.REGISTRY[k](p)) for k in ("xsmom", "tsmom", "carry", "carry_trend")}
    B = {x: run(S.REGISTRY["blend"](p, components={"carry_trend": {}, "carry": {}, x: {}})) for x in ("xsmom", "tsmom")}
    carry = (R["carry"] + R["carry_trend"]) / 2
    wk = (1 + c["BTC"].pct_change().loc["2021":]).resample("W").prod() - 1
    W = {k: (1 + v).resample("W").prod() - 1 for k, v in R.items()}
    worst, best = wk.nsmallest(20).index, wk.nlargest(20).index
    cw = carry.nsmallest(20).index
    out = {"btc_worst20_weeks": {k: round(float(W[k][worst].mean()), 4) for k in ("xsmom", "tsmom")},
           "btc_best20_weeks": {k: round(float(W[k][best].mean()), 4) for k in ("xsmom", "tsmom")},
           "carry_worst20_days": {"carry": round(float(carry[cw].mean()), 4), **{k: round(float(R[k][cw].mean()), 4) for k in ("xsmom", "tsmom")}},
           "corr_with_carry_by_year": {int(y): {k: round(float(R[k][R[k].index.year == y].corr(carry[carry.index.year == y])), 2) for k in ("xsmom", "tsmom")} for y in range(2021, 2027)},
           "blend_by_year": {int(y): {x: {"sr": sr(B[x][B[x].index.year == y]), "mdd": mdd(B[x][B[x].index.year == y]),
                                          "worst_month": round(float(B[x][B[x].index.year == y].resample("ME").sum().min()), 3)} for x in B} for y in range(2023, 2027)},
           "blend_2023_26": {x: {"sr": sr(B[x].loc["2023":]), "mdd": mdd(B[x].loc["2023":])} for x in B}}
    print(json.dumps(out, indent=1))
    json.dump(out, open("research/is3/xst_ab.json", "w"), indent=1)


if __name__ == "__main__":
    {"ab": run_ab}[sys.argv[1]]()
