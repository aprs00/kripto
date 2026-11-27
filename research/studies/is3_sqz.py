"""InSilico pass 3, SQZ: features known at the close vs the next-7-d short P&L (left tail) of new-listing shorts on bnall. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_sqz a    # explore 2021-23 -> research/is3/sqz_a.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data
from kripto import strategies as S


def frame(p):
    c, v = p["close"], p["volume"]
    fund = p["funding"].reindex(index=c.index, columns=c.columns)
    w = S.REGISTRY["listing_short"](p).ffill().fillna(0.0)
    held = (w.drop(columns=["BTC"]) < 0)
    traded = (v.fillna(0) > 0) & c.notna()
    age = traded.cummax().cumsum()
    dv = S.dollar_volume(p)
    f = {"ret7": c / c.shift(7) - 1,
         "volgrowth": v.rolling(3).mean() / v.rolling(14, min_periods=5).mean(),
         "age": age.astype(float),
         "fund7": fund.rolling(7, min_periods=1).sum(),
         "off_low": c / c.where(age >= 2).cummin() - 1,
         "dv_rank": dv.rank(axis=1, pct=True)}
    btc = c["BTC"]
    fwd = -(c.shift(-7) / c - 1) + (btc.shift(-7) / btc - 1).to_numpy()[:, None] + fund.shift(-1).rolling(7, min_periods=1).sum().shift(-6).fillna(0)
    rows = []
    for coin in held.columns:
        m = held[coin].to_numpy()
        if not m.any():
            continue
        t = c.index[m]
        d = {"time": t, "coin": coin, "fwd7": fwd[coin].reindex(t).to_numpy()}
        for k, x in f.items():
            d[k] = x[coin].reindex(t).to_numpy() if coin in x else np.nan
        rows.append(pd.DataFrame(d))
    return pd.concat(rows, ignore_index=True).dropna(subset=["fwd7"])


def run_a():
    p = data.load_panel("bnall", "1d")
    df = frame(p)
    ex = df[(df.time >= "2021-01-01") & (df.time < "2024-01-01")].copy()
    out = {"n": int(len(ex)), "base": {"mean": round(float(ex.fwd7.mean()), 4), "p_loss20": round(float((ex.fwd7 < -0.2).mean()), 3)}, "features": {}}
    for k in ("ret7", "volgrowth", "age", "fund7", "off_low", "dv_rank"):
        x = ex.dropna(subset=[k]).copy()
        x["q"] = x.groupby(x.time.dt.year)[k].transform(lambda s: pd.qcut(s.rank(method="first"), 5, labels=False))
        res = {}
        for y, g in x.groupby(x.time.dt.year):
            res[int(y)] = {int(q): [round(float(h.fwd7.mean()), 4), round(float((h.fwd7 < -0.2).mean()), 3), int(len(h))] for q, h in g.groupby("q")}
        pooled = {int(q): [round(float(h.fwd7.mean()), 4), round(float((h.fwd7 < -0.2).mean()), 3), int(len(h))] for q, h in x.groupby("q")}
        out["features"][k] = {"pooled": pooled, "by_year": res}
        print(k, "pooled [mean, P(loss>20%), n] by quintile:", pooled, flush=True)
        for y, r in res.items():
            print("   ", y, {q: v[1] for q, v in r.items()}, flush=True)
    json.dump(out, open("research/is3/sqz_a.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": run_a}[sys.argv[1]]()
