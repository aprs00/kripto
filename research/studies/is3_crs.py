"""InSilico pass 3, CRS: carry's long coin-days in the top |7-d funding| decile: features vs next-7-d long P&L. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_crs a    # explore 2021-23 -> research/is3/crs_a.json
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
    c, v = p["close"], p["volume"]
    fund = p["funding"].reindex(index=c.index, columns=c.columns)
    f7 = p["funding"].rolling(7, min_periods=1).mean()
    uni = S.universe(p, 30) & f7.notna()
    pct = f7.abs().where(uni).rank(axis=1, pct=True)
    w = S.REGISTRY["carry"](p).ffill().fillna(0.0)
    sel = (w > 0) & (pct > 0.9)
    feats = {"ret7": c / c.shift(7) - 1, "off_high30": c / c.rolling(30, min_periods=10).max() - 1, "volgrowth": v.rolling(3).mean() / v.rolling(14, min_periods=5).mean(),
             "f_accel": p["funding"].rolling(3, min_periods=1).mean() / f7.replace(0, np.nan), "dv_rank": S.dollar_volume(p).rank(axis=1, pct=True)}
    btc = c["BTC"]
    fwd = (c.shift(-7) / c - 1) - (btc.shift(-7) / btc - 1).to_numpy()[:, None] - fund.shift(-1).rolling(7, min_periods=1).sum().shift(-6).fillna(0)
    rows = []
    for coin in sel.columns:
        m = sel[coin].to_numpy()
        if not m.any():
            continue
        t = c.index[m]
        d = {"time": t, "coin": coin, "fwd7": fwd[coin].reindex(t).to_numpy()}
        for k, x in feats.items():
            d[k] = x[coin].reindex(t).to_numpy()
        rows.append(pd.DataFrame(d))
    df = pd.concat(rows, ignore_index=True).dropna(subset=["fwd7"])
    ex = df[(df.time >= "2021-01-01") & (df.time < "2024-01-01")].copy()
    out = {"n": int(len(ex)), "base_mean": round(float(ex.fwd7.mean()), 4), "base_p_loss20": round(float((ex.fwd7 < -0.2).mean()), 3), "features": {}}
    print("n", len(ex), "base", out["base_mean"], out["base_p_loss20"])
    for k in feats:
        x = ex.dropna(subset=[k]).copy()
        x["q"] = x.groupby(x.time.dt.year)[k].transform(lambda s: pd.qcut(s.rank(method="first"), 5, labels=False))
        pooled = {int(q): [round(float(h.fwd7.mean()), 4), round(float((h.fwd7 < -0.2).mean()), 3), int(len(h))] for q, h in x.groupby("q")}
        by = {int(y): {int(q): round(float(h.fwd7.mean()), 4) for q, h in g.groupby("q")} for y, g in x.groupby(x.time.dt.year)}
        out["features"][k] = {"pooled": pooled, "by_year_mean": by}
        print(k, pooled, flush=True)
        for y, r in by.items():
            print("   ", y, r, flush=True)
    json.dump(out, open("research/is3/crs_a.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": run_a}[sys.argv[1]]()
