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




def fsh_wait(panel, k=2, lookback=14, enter=0.1, top_n=20, max_pair=0.10, gross=2.0):
    """The live rule, plus: a new pair opens only when its signed basis (vs its 30-d median) >= 0, or after it has been a candidate for k days."""
    c, f = panel["close"], panel["funding"]
    hlc = [x for x in c.columns if x.endswith("@hl") and x[:-3] + "@bn" in c.columns]
    bnc = [x[:-3] + "@bn" for x in hlc]
    on_bn = lambda df: df[bnc].set_axis(hlc, axis=1)
    s = (f[hlc] - on_bn(f)).rolling(lookback, min_periods=lookback).mean() * 365
    b = np.log(c[hlc] / on_bn(c))
    bdev = (b - b.rolling(30, min_periods=10).median()).to_numpy()
    same = b.abs().rolling(30, min_periods=10).median() < 0.03
    dv = S.dollar_volume(panel)
    dvm = np.minimum(dv[hlc], on_bn(dv))
    elig = same & s.notna() & c[hlc].notna() & on_bn(c).notna() & (dvm > 0)
    liquid = dvm.where(elig).rank(axis=1, ascending=False) <= 2 * top_n
    can_open = elig & (dvm.where(elig).rank(axis=1, ascending=False) <= top_n)
    Sx, E, Lo, O = s.to_numpy(), (elig & liquid).to_numpy(), can_open.to_numpy(), np.zeros(len(hlc))
    wait = np.zeros(len(hlc), dtype=int)
    slots = int(round(gross / (2 * max_pair)))
    out = np.zeros((len(c), len(hlc)))
    for t in range(len(c)):
        st_ = Sx[t]
        keep = (O != 0) & E[t] & np.isfinite(st_) & (np.sign(np.nan_to_num(st_)) == O)
        O = np.where(keep, O, 0.0)
        cand_mask = (O == 0) & Lo[t] & np.isfinite(st_) & (np.abs(np.nan_to_num(st_)) > enter)
        wait = np.where(cand_mask, wait + 1, 0)
        free = slots - int((O != 0).sum())
        if free > 0:
            sg = np.sign(np.nan_to_num(st_))
            ok = cand_mask & ((sg * np.nan_to_num(bdev[t], nan=0.0) >= 0) | (wait > k))
            cand = np.flatnonzero(ok)
            cand = cand[np.argsort(-np.abs(st_[cand]))][:free]
            O[cand] = sg[cand]
            wait[cand] = 0
        out[t] = O
    leg = pd.DataFrame(-out * max_pair, c.index, hlc)
    w = pd.DataFrame(0.0, c.index, c.columns)
    w[hlc], w[bnc] = leg, -leg.to_numpy()
    return S.rebalance_rows(w.where(elig.any(axis=1), np.nan), 1)


def run_b():
    from kripto import backtest as bt
    from kripto.research import default_band
    from research.studies.is3_x1h import summary
    p = data.load_panel("pair", "1d")
    run = lambda w: bt.run(w, p["close"], p["funding"], bt.slippage_model(p["volume"], 1), band=default_band())
    out = {"live": summary(run(fsh_u(p)), "2023-05-15", "2025-01-01")}
    for k in (2, 5):
        out[f"wait{k}"] = summary(run(fsh_wait(p, k=k)), "2023-05-15", "2025-01-01")
    for k in (2, 5):
        a, l = out[f"wait{k}"], out["live"]
        out[f"wait{k}"]["PASS"] = bool(a["net_yr"] >= l["net_yr"] + 0.005 and a["sr"] >= l["sr"] and all(a["by_year"][y] > l["by_year"][y] for y in (2023, 2024)))
    print(json.dumps(out, indent=1))
    json.dump(out, open("research/is3/pbt_b.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": run_a, "b": run_b}[sys.argv[1]]()
