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




def run_b():
    """HL listings (first traded bar after the panel's first 30 days): which reach the $1M 7-d dollar-volume floor during days 2-61, and the beta-free short P&L (coin minus BTC) d2 -> d61 of each group."""
    p = data.load_panel("hl", "1d")
    c, v = p["close"], p["volume"]
    traded = (v.fillna(0) > 0) & c.notna()
    first = traded.idxmax()[traded.any()]
    t_cut = traded.any(axis=1).idxmax() + pd.Timedelta(days=30)
    dv = S.dollar_volume(p)
    rows = []
    for coin, t0 in first.items():
        if t0 < t_cut or coin == "BTC":
            continue
        i0 = c.index.get_loc(t0)
        if i0 + 62 >= len(c):
            continue
        win = c.index[i0 + 1: i0 + 62]
        q = bool((dv.loc[win, coin] >= 1e6).any())
        a, b = c.at[win[0], coin], c.at[win[-1], coin]
        ba, bb = c.at[win[0], "BTC"], c.at[win[-1], "BTC"]
        if not (np.isfinite(a) and np.isfinite(b)):
            continue
        rows.append({"coin": coin, "t0": str(t0.date()), "qualifies": q, "short_vs_btc": float(-(b / a - 1) + (bb / ba - 1)), "max_dv_m": float(dv.loc[win, coin].max() / 1e6)})
    df = pd.DataFrame(rows)
    out = {}
    for q, g in df.groupby("qualifies"):
        out["qualifies" if q else "below_floor"] = {"n": int(len(g)), "mean": round(float(g.short_vs_btc.mean()), 3), "median": round(float(g.short_vs_btc.median()), 3),
                                                    "win": round(float((g.short_vs_btc > 0).mean()), 2), "se": round(float(g.short_vs_btc.std() / np.sqrt(len(g))), 3),
                                                    "by_year": {int(y): [int(len(x)), round(float(x.short_vs_btc.mean()), 3)] for y, x in g.groupby(pd.to_datetime(g.t0).dt.year)}}
    out["below_floor_maxdv_median_m"] = round(float(df[~df.qualifies].max_dv_m.median()), 2) if (~df.qualifies).any() else None
    print(json.dumps(out, indent=1))
    json.dump(out, open("research/is3/hli_b.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": run_a, "b": run_b}[sys.argv[1]]()
