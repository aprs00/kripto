"""InSilico pass 3, TSH: the tsmom leg of the HL main book. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_tsh ab   # legs / majors vs alts / funding / net exposure vs BTC trend; crisis weeks and listing_short's worst days -> research/is3/tsh_ab.json
  nice -n 19 .venv/bin/python -m research.studies.is3_tsh c    # nested_selection expanding SR of every pool strategy at the last refits -> research/is3/tsh_c.json
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

MAJ = ["BTC", "ETH"]
sr = lambda x: round(float(x.mean() / x.std() * np.sqrt(365)), 2) if len(x) > 20 and x.std() > 0 else None


def run_ab():
    p = data.load_panel("hl", "1d")
    c = p["close"]
    ret = (c / c.shift(1) - 1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    fund = p["funding"].reindex(index=c.index, columns=c.columns).fillna(0.0)
    run = lambda w: bt.run(w, c, p["funding"], bt.slippage_model(p["volume"], 1), band=default_band())
    w = S.REGISTRY["tsmom"](p).ffill().fillna(0.0)
    wl = w.shift(1).fillna(0.0)
    rt = run(S.REGISTRY["tsmom"](p))
    lo = rt.gross[rt.gross > 0].index.min()
    lo = max(lo, pd.Timestamp("2023-03-27", tz="UTC"))
    out = {"years": {}}
    for y in range(lo.year, 2027):
        yy = str(y)
        d = {}
        for lab, m in (("long", wl > 0), ("short", wl < 0)):
            ww = wl.where(m, 0.0).loc[lo:].loc[yy]
            d[lab] = {"price": round(float((ww * ret.loc[ww.index]).sum().sum()), 4), "funding": round(float(-(ww * fund.loc[ww.index]).sum().sum()), 4)}
        ww = wl.loc[lo:].loc[yy]
        pr = (ww * ret.loc[ww.index])
        d["majors_price"] = round(float(pr[[m for m in MAJ if m in pr]].sum().sum()), 4)
        d["alts_price"] = round(float(pr.drop(columns=MAJ, errors="ignore").sum().sum()), 4)
        d["net_exposure_mean"] = round(float(ww.sum(axis=1).mean()), 2)
        d["gross_mean"] = round(float(ww.abs().sum(axis=1).mean()), 2)
        d["net"] = round(float(rt.returns.loc[lo:].loc[yy].sum()), 4)
        out["years"][y] = d
    net = wl.sum(axis=1).loc[lo:]
    btc30 = (c["BTC"] / c["BTC"].shift(30) - 1).shift(1).loc[lo:]
    out["corr_net_exposure_vs_btc30"] = round(float(net.corr(btc30)), 2)
    # P&L explained by the net exposure x the equal-weight market return (market timing) vs the rest
    mkt = ret[[x for x in c.columns]].where(wl != 0).mean(axis=1).loc[lo:]
    timing = net * mkt
    tr = rt.returns.loc[lo:]
    out["timing_share_of_gross_pnl"] = round(float(timing.sum() / (wl.loc[lo:] * ret.loc[lo:]).sum().sum()), 2)
    # (b) crisis weeks
    wk = (1 + ret["BTC"].loc[lo:]).resample("W").prod() - 1
    tw = (1 + tr).resample("W").prod() - 1
    wb = S.REGISTRY["blend"](p, components={"listing_short": {}, "lowvol": {}, "tsmom": {}})
    rb = run(wb).returns.loc[lo:]
    bw = (1 + rb).resample("W").prod() - 1
    worst, best = wk.nsmallest(20).index, wk.nlargest(20).index
    out["btc_worst20_weeks"] = {"btc": round(float(wk[worst].mean()), 4), "tsmom": round(float(tw[worst].mean()), 4), "blend": round(float(bw[worst].mean()), 4)}
    out["btc_best20_weeks"] = {"btc": round(float(wk[best].mean()), 4), "tsmom": round(float(tw[best].mean()), 4), "blend": round(float(bw[best].mean()), 4)}
    out["btc_other_weeks"] = {"tsmom": round(float(tw.drop(worst.union(best)).mean()), 4)}
    rls = run(S.REGISTRY["listing_short"](p)).returns.loc[lo:]
    rls = rls[rls != 0]
    w20 = rls.nsmallest(20).index
    out["listing_short_worst20_days"] = {"listing_short": round(float(rls[w20].mean()), 4), "tsmom": round(float(tr.reindex(w20).mean()), 4),
                                         "corr_all_days": round(float(rls.corr(tr.reindex(rls.index))), 2)}
    out["tsmom_sr_by_year"] = {int(y): sr(x) for y, x in tr.groupby(tr.index.year)}
    print(json.dumps(out, indent=1))
    json.dump(out, open("research/is3/tsh_ab.json", "w"), indent=1)


def run_c():
    p = data.load_panel("hl", "1d")
    import inspect
    src = inspect.signature(S.nested_selection)
    res = S.nested_selection(p)
    _, sel, log = res
    out = {"signature": str(src), "last_log": [[str(t.date()), ch] for t, ch in log[-3:]]}
    print(json.dumps(out, indent=1))
    json.dump(out, open("research/is3/tsh_c.json", "w"), indent=1)


if __name__ == "__main__":
    {"ab": run_ab, "c": run_c}[sys.argv[1]]()
