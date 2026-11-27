"""InSilico pass 3, LSP: listing_short (defaults, band .005) as a book on bnall: by year, shorts vs BTC hedge, tail, fit with main_bn. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_lsp abc   # -> research/is3/lsp_abc.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto import strategies as S

sr = lambda x: round(float(x.mean() / x.std() * np.sqrt(365)), 2) if len(x) > 20 and x.std() > 0 else None


def run_abc():
    p = data.load_panel("bnall", "1d")
    c = p["close"]
    slip = bt.slippage_model(p["volume"], 1)
    ret = (c / c.shift(1) - 1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    fund = p["funding"].reindex(index=c.index, columns=c.columns).fillna(0.0)
    w = S.REGISTRY["listing_short"](p)
    res = bt.run(w, c, p["funding"], slip, band=0.005)
    r = res.returns.loc["2021":]
    wl = res.weights.shift(0).fillna(0.0) if hasattr(res, "weights") else w.ffill().fillna(0.0).shift(1)
    wl = res.weights.fillna(0.0)                                    # held weights during each bar
    btc = (wl["BTC"] * ret["BTC"] - wl["BTC"] * fund["BTC"]).loc["2021":]
    alts = ((wl.drop(columns=["BTC"]) * ret.drop(columns=["BTC"])) - (wl.drop(columns=["BTC"]) * fund.drop(columns=["BTC"]))).sum(axis=1).loc["2021":]
    out = {"sr_all": sr(r), "corr_btc": round(float(r.corr(ret["BTC"].loc[r.index])), 2), "by_year": {}}
    for y in sorted(set(r.index.year)):
        yy = str(y)
        out["by_year"][y] = {"sr": sr(r.loc[yy]), "net": round(float(r.loc[yy].sum()), 3), "alt_shorts": round(float(alts.loc[yy].sum()), 3), "btc_leg": round(float(btc.loc[yy].sum()), 3),
                             "costs": round(float(res.costs.loc[yy].sum()), 3), "corr_btc": round(float(r.loc[yy].corr(ret["BTC"].loc[yy])), 2),
                             "names_mean": round(float((wl.drop(columns=["BTC"]).loc[yy] < 0).sum(axis=1).mean()), 1)}
    # (b) tail
    worst = r.nsmallest(10)
    names = {}
    for d in worst.index:
        contrib = (wl.loc[d].drop("BTC") * ret.loc[d].drop("BTC"))
        names[str(d.date())] = {"ret": round(float(worst[d]), 4), "top": {k: round(float(v), 4) for k, v in contrib.nsmallest(2).items()}}
    out["worst10_days"] = names
    out["sr_wo_worst10_days"] = sr(r.drop(worst.index))
    out["sr_wo_best10_days"] = sr(r.drop(r.nlargest(10).index))
    # (c) fit with main_bn
    wf = S.REGISTRY["flow"](p, lookback=3, cap=0.05).ffill().fillna(0.0)
    wb = S.REGISTRY["blend"](p, components={"carry_trend": {}, "carry": {}, "xsmom": {}}).ffill().fillna(0.0).reindex(columns=wf.columns, fill_value=0.0)
    mix = bt.run((wf + wb) * 0.578, c, p["funding"], slip).returns.loc["2023":]
    wls = w.ffill().fillna(0.0).reindex(columns=wf.columns, fill_value=0.0)
    mix3 = bt.run((wf + wb + wls) * 0.578 * 2 / 3, c, p["funding"], slip).returns.loc["2023":]
    out["corr_with_main_bn_2023_26"] = round(float(r.loc["2023":].corr(mix)), 2)
    out["mix_vs_mix_plus_ls_sr_by_year"] = {int(y): [sr(mix[mix.index.year == y]), sr(mix3[mix3.index.year == y])] for y in sorted(set(mix.index.year))}
    out["mix_vs_mix_plus_ls_sr_all"] = [sr(mix), sr(mix3)]
    print(json.dumps(out, indent=1))
    json.dump(out, open("research/is3/lsp_abc.json", "w"), indent=1)


if __name__ == "__main__":
    {"abc": run_abc}[sys.argv[1]]()
