"""InSilico pass 3, FLD: is flow@bn's taker-imbalance signal still there? Rank IC by year, tercile, lag; leg price P&L. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_fld ab   # -> research/is3/fld_ab.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data
from kripto import strategies as S


def ic_series(score, fwd):
    s, f = score.rank(axis=1), fwd.rank(axis=1)
    ok = score.notna() & fwd.notna()
    s, f = s.where(ok), f.where(ok)
    sd, fd = s.sub(s.mean(axis=1), axis=0), f.sub(f.mean(axis=1), axis=0)
    return (sd * fd).sum(axis=1) / np.sqrt((sd ** 2).sum(axis=1) * (fd ** 2).sum(axis=1))


def tstat(x):
    x = x.dropna()
    # weekly blocks to respect overlap / clustering
    wk = x.groupby(x.index.to_period("W")).mean()
    return round(float(wk.mean() / (wk.std() / np.sqrt(len(wk)))), 2) if len(wk) > 5 else None


def run_ab():
    p = data.load_panel("bnall", "1d")
    c, v, tb = p["close"], p["volume"], p["taker_buy"]
    n = 3
    imb = (2 * tb - v).rolling(n, min_periods=n).sum() / v.rolling(n, min_periods=n).sum()
    uni = S.universe(p, 30) & imb.notna()
    score = imb.where(uni)
    r = (c / c.shift(1) - 1).replace([np.inf, -np.inf], np.nan)
    rel = r.sub(r.where(uni.shift(1)).mean(axis=1), axis=0)
    dv = S.dollar_volume(p).where(uni)
    terc = dv.rank(axis=1, pct=True)
    out = {"ic_by_year": {}, "ic_by_lag_year": {}, "ic_tercile_year": {}}
    fwd1 = rel.shift(-1)
    ic1 = ic_series(score, fwd1)
    fwd3 = (1 + rel).shift(-1).rolling(3).apply(np.prod, raw=True).shift(-2) - 1
    ic3 = ic_series(score, fwd3)
    for y in range(2021, 2027):
        yy = str(y)
        out["ic_by_year"][y] = {"ic1": round(float(ic1.loc[yy].mean()), 4), "t1": tstat(ic1.loc[yy]), "ic3": round(float(ic3.loc[yy].mean()), 4), "t3": tstat(ic3.loc[yy])}
        out["ic_by_lag_year"][y] = {}
        for lag in range(0, 6):
            icl = ic_series(score, rel.shift(-lag)) if lag else ic_series(score, rel)   # lag 0 = same-day (formation day's last return: not tradable, shows co-movement)
            out["ic_by_lag_year"][y][lag] = round(float(icl.loc[yy].mean()), 4)
        out["ic_tercile_year"][y] = {}
        for lab, lo, hi in (("thin", 0, 1 / 3), ("mid", 1 / 3, 2 / 3), ("liquid", 2 / 3, 1.01)):
            m = (terc > lo) & (terc <= hi)
            icx = ic_series(score.where(m), fwd1.where(m))
            out["ic_tercile_year"][y][lab] = {"ic1": round(float(icx.loc[yy].mean()), 4), "t": tstat(icx.loc[yy])}
    # leg price P&L of the live book (unit weights), by year
    w = S.REGISTRY["flow"](p, lookback=3, cap=0.05).ffill().fillna(0.0)
    wl = w.shift(1).fillna(0.0)
    rr = r.fillna(0.0)
    out["legs_price_by_year"] = {int(y): {"long": round(float((wl.where(wl > 0, 0) * rr).loc[str(y)].sum().sum()), 4),
                                          "short": round(float((wl.where(wl < 0, 0) * rr).loc[str(y)].sum().sum()), 4)} for y in range(2021, 2027)}
    print(json.dumps(out, indent=1))
    json.dump(out, open("research/is3/fld_ab.json", "w"), indent=1)


if __name__ == "__main__":
    {"ab": run_ab}[sys.argv[1]]()
