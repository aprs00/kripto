"""InSilico pass 3, FLP a/b: main_bn mixes with vs without flow on bnall 1d, vol-matched (full-sample scale; descriptive). Not registered.
  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_flp  -> research/is3/flp_ab.json"""
import json
import numpy as np
import pandas as pd
from kripto import backtest as bt, data
from kripto.strategies import REGISTRY

S = slice("2021-01-01", "2026-10-31"); VOL = 0.235
p = data.load_panel("bnall", "1d"); cols = p["close"].columns
slip = bt.slippage_model(p["volume"], 1)
wf = REGISTRY["flow"](p, lookback=3, cap=0.05).ffill().fillna(0.0).reindex(columns=cols, fill_value=0.0)
wb = REGISTRY["blend"](p, components={"carry_trend": {}, "carry": {}, "xsmom": {}}).ffill().fillna(0.0).reindex(columns=cols, fill_value=0.0)


def run(w):
    res = bt.run(w, p["close"], p["funding"], slip, fee=5e-4)
    return res, res.returns.loc[S]


def stats(r):
    sr = lambda x: round(float(x.mean() / x.std() * np.sqrt(365)), 2)
    eq = (1 + r).cumprod(); dd = float((eq / eq.cummax() - 1).min())
    return {"sr": sr(r), "ann%": round(float(r.mean() * 365 * 100), 1), "maxdd%": round(dd * 100, 1), "years": {int(y): sr(x) for y, x in r.groupby(r.index.year)},
            "sr_2025_26": sr(r.loc["2025":])}


out = {}
for tag, w in (("i_half_flow", .5 * wf + .5 * wb), ("ii_blend_only", wb), ("iii_quarter_flow", .25 * wf + .75 * wb)):
    _, r0 = run(w)
    k = VOL / float(r0.std() * np.sqrt(365))
    res, r = run(w * k)
    out[tag] = {"scale": round(k, 3), **stats(r)}
    print(tag, json.dumps(out[tag]), flush=True)
rf, rfl = run(wf); rb, rbl = run(wb)
out["corr_flow_blend_by_year"] = {int(y): round(float(rfl[rfl.index.year == y].corr(rbl[rbl.index.year == y])), 2) for y in sorted(set(rfl.index.year))}
# b: funding overlap: per-coin funding P&L of each book (weights held x funding), 2025-26
fu = p["funding"].reindex(rf.weights.index).fillna(0.0)
ff = (-(rf.weights * fu)).loc["2025":"2026-10"].sum(); fb = (-(rb.weights * fu)).loc["2025":"2026-10"].sum()
both = pd.concat([ff, fb], axis=1, keys=["flow", "blend"]).fillna(0.0)
both = both[(both.abs() > 1e-6).any(axis=1)]
same_sign = float(((both.flow * both.blend) > 0)[both.flow.abs() > 0].mean())
out["funding_2025_26"] = {"flow_total": round(float(ff.sum()), 3), "blend_total": round(float(fb.sum()), 3), "corr_per_coin": round(float(both.flow.corr(both.blend)), 2),
                          "share_of_flow_funding_coins_where_blend_same_sign": round(same_sign, 2),
                          "flow_funding_top10_coins": ff.sort_values(ascending=False).head(10).round(4).to_dict()}
print(json.dumps({k: out[k] for k in ("corr_flow_blend_by_year", "funding_2025_26")}))
json.dump(out, open("research/is3/flp_ab.json", "w"), indent=1)
