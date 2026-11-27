"""InSilico pass 3, LSB: Binance perp listings, short-vs-BTC d2 -> d61 (price and funding), by year, HL-listed vs BN-only. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_lsb ab   # -> research/is3/lsb_ab.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data
from kripto import strategies as S


def run_ab():
    p = data.load_panel("bnall", "1d")
    c, v = p["close"], p["volume"]
    fund = p["funding"].reindex(index=c.index, columns=c.columns)
    traded = (v.fillna(0) > 0) & c.notna()
    first = traded.idxmax()[traded.any()]
    t_cut = traded.any(axis=1).idxmax() + pd.Timedelta(days=30)
    dv = S.dollar_volume(p)
    hl = data.load_panel("hl", "1d")["close"]
    hl_on = {data.hl_to_bn(x): hl[x] for x in hl.columns}
    rows = []
    for coin, t0 in first.items():
        if t0 < t_cut or coin == "BTC":
            continue
        i0 = c.index.get_loc(t0)
        if i0 + 62 >= len(c):
            continue
        win = c.index[i0 + 1: i0 + 62]
        if not (dv.loc[win, coin] >= 1e6).any():
            continue
        a, b = c.at[win[0], coin], c.at[win[-1], coin]
        if not (np.isfinite(a) and np.isfinite(b)) or a <= 0:
            continue
        ba, bb = c.at[win[0], "BTC"], c.at[win[-1], "BTC"]
        fsum = float(fund.loc[win[1:], coin].fillna(0).sum())            # shorts RECEIVE positive funding
        h = hl_on.get(coin)
        on_hl = bool(h is not None and np.isfinite(h.get(win[0], np.nan)))
        rows.append({"coin": coin, "t0": t0, "price": float(-(b / a - 1) + (bb / ba - 1)), "funding": fsum, "on_hl": on_hl,
                     "dv0_m": float(dv.loc[win[:7], coin].max() / 1e6)})
    df = pd.DataFrame(rows)
    df["total"] = df.price + df.funding
    df["year"] = df.t0.dt.year
    df["month"] = df.t0.dt.to_period("M")

    def summ(g):
        mm = g.groupby("month").total.mean()
        return {"n": int(len(g)), "mean": round(float(g.total.mean()), 3), "median": round(float(g.total.median()), 3), "win": round(float((g.total > 0).mean()), 2),
                "price_mean": round(float(g.price.mean()), 3), "funding_mean": round(float(g.funding.mean()), 3),
                "t_month_clustered": round(float(mm.mean() / (mm.std() / np.sqrt(len(mm)))), 2) if len(mm) > 3 else None}
    out = {"by_year": {int(y): summ(g) for y, g in df.groupby("year")},
           "by_year_on_hl": {int(y): {str(k): summ(x) for k, x in g.groupby("on_hl")} for y, g in df.groupby("year")},
           "per_month_count": {int(y): round(float(len(g) / g.month.nunique()), 1) for y, g in df.groupby("year")}}
    df["terc"] = df.groupby("year").dv0_m.transform(lambda s: pd.qcut(s, 3, labels=False, duplicates="drop"))
    out["by_year_dv_tercile"] = {int(y): {int(k): summ(x)["mean"] for k, x in g.groupby("terc")} for y, g in df.groupby("year")}
    print(json.dumps(out, indent=1, default=str))
    json.dump(out, open("research/is3/lsb_ab.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    {"ab": run_ab}[sys.argv[1]]()
