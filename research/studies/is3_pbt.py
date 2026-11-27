"""InSilico pass 3, PBT: fspread_hold@pair entry timing by the HL-BN price basis. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_pbt a    # per trip: signed entry basis vs trip price P&L and basis change -> research/is3/pbt_a.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data
from kripto import strategies as S
from research.studies.is3_x1u import fsh_u


def trips(p, w):
    c = p["close"]
    hlc = [x for x in c.columns if x.endswith("@hl") and x[:-3] + "@bn" in c.columns]
    bnc = [x[:-3] + "@bn" for x in hlc]
    O = (-w[hlc].ffill().fillna(0.0) / 0.10).round().astype(int)
    b = np.log(c[hlc] / c[bnc].set_axis(hlc, axis=1))
    bmed = b.rolling(30, min_periods=10).median()
    rh = (c[hlc] / c[hlc].shift(1) - 1)
    rb = (c[bnc] / c[bnc].shift(1) - 1).set_axis(hlc, axis=1)
    rows = []
    idx = c.index
    for x in hlc:
        o = O[x].to_numpy()
        starts = np.flatnonzero((o != 0) & (np.r_[0, o[:-1]] != o))
        for i in starts:
            j = i
            while j + 1 < len(o) and o[j + 1] == o[i]:
                j += 1
            sg = o[i]
            # held from close i to close j+1 (exit trade at close j+1); price P&L of the hedged legs
            seg = slice(i + 1, min(j + 2, len(o)))
            pnl = float((-sg * rh[x].iloc[seg] + sg * rb[x].iloc[seg]).sum())
            b0 = b[x].iloc[i]
            row = {"coin": x[:-3], "t0": idx[i], "days": j - i + 1, "sign": int(sg), "b0_bp": float(b0 * 1e4), "sb_bp": float(sg * (b0 - bmed[x].iloc[i]) * 1e4),
                   "trip_price_bp": pnl * 1e4}
            for k in (1, 3, 7):
                if i + k < len(o):
                    row[f"db{k}_bp"] = float(-sg * (b[x].iloc[i + k] - b0) * 1e4)     # + = basis moved in the trade's favour
            rows.append(row)
    return pd.DataFrame(rows)


def run_a():
    p = data.load_panel("pair", "1d")
    w = fsh_u(p)
    t = trips(p, w)
    t = t[np.isfinite(t.sb_bp)]
    ex = t[(t.t0 >= "2023-05-15") & (t.t0 < "2025-01-01")].copy()
    ex["q"] = pd.qcut(ex.sb_bp, 5, labels=False, duplicates="drop")
    g = ex.groupby("q").agg(n=("sb_bp", "size"), sb_med=("sb_bp", "median"), trip_price_mean=("trip_price_bp", "mean"), trip_price_med=("trip_price_bp", "median"),
                            db1=("db1_bp", "mean"), db3=("db3_bp", "mean"), db7=("db7_bp", "mean"), days_med=("days", "median"))
    out = {"n_trips_explore": int(len(ex)), "by_quintile": g.round(2).reset_index().to_dict("records"),
           "corr_sb_trip_price": round(float(ex.sb_bp.corr(ex.trip_price_bp, method="spearman")), 3),
           "abs_sb_med": round(float(ex.sb_bp.abs().median()), 2),
           "by_year": {int(y): {"n": int(len(x)), "q4_minus_q0_trip": round(float(x[x.q == x.q.max()].trip_price_bp.mean() - x[x.q == 0].trip_price_bp.mean()), 1)}
                       for y, x in ex.groupby(ex.t0.dt.year)}}
    print(json.dumps(out, indent=1, default=str))
    json.dump(out, open("research/is3/pbt_a.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    {"a": run_a}[sys.argv[1]]()
