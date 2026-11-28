"""InSilico pass 3, TLX: TLQ's liquidity-tier diagnosis on cached bnall standalone tsmom; frozen top_n 10 vs 20.
python -m research.studies.is3_tlx data/is3/fc1c_bnall_1d.pkl"""
import json, pickle, sys
import numpy as np, pandas as pd
from kripto import backtest as bt, strategies as S
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY
from research.studies.is3_prb import summary

p = pickle.load(open(sys.argv[1], "rb"))
bpd = bars_per_day(p["close"].index)
slip = bt.slippage_model(p["volume"], bpd)
yrs = range(2020, 2027)
out = {"a": {}, "b": {}}
w = S._ffill_targets(REGISTRY["tsmom"](p)).fillna(0.0)
cols = w.columns
r = p["close"].pct_change(fill_method=None).fillna(0.0)
f = p["funding"].reindex(index=w.index, columns=cols).fillna(0.0)
sl = slip.reindex(index=w.index, columns=cols).fillna(25e-4)
dv = p["volume"].rolling(30, min_periods=7).mean()
rank = dv.where(S.universe(p, 20)).rank(axis=1, ascending=False)
tier = pd.DataFrame(np.select([rank <= 7, rank <= 14, rank <= 20], [1, 2, 3], 0), index=rank.index, columns=cols)
wh, th = w.shift(1).fillna(0.0), tier.shift(1).fillna(0)
tr = (w - wh).abs()
price, fund, cost = wh * r, -wh * f, tr * (bt.TAKER_FEE + sl)
for k in (1, 2, 3):
    o = {}
    for y in yrs:
        ix = w.index.year == y
        mh, mt = (th == k).loc[ix], (tier == k).loc[ix]
        g = float(wh.abs().loc[ix].where(mh, 0).sum(1).mean())
        pr, fu, co = (float(x.loc[ix].where(m, 0).sum(1).mean() * 365) for x, m in ((price, mh), (fund, mh), (cost, mt)))
        o[str(y)] = {"gross_exp": round(g, 3), "price": round(pr, 4), "funding": round(fu, 4), "cost": round(co, 4), "net": round(pr + fu - co, 4),
                     "price_per_gross": round(pr / g, 3) if g > 0 else None}
    out["a"][f"tier{k}"] = o
    print(f"tier{k}", {y: (v["price_per_gross"], v["price"], v["cost"], v["net"]) for y, v in o.items()}, flush=True)
for tn in (20, 10):
    wt = S._ffill_targets(REGISTRY["tsmom"](p, top_n=tn)).fillna(0.0)
    res = bt.run(wt, p["close"], p.get("funding"), slip, band=0.005)
    out["b"][f"top{tn}"] = {str(y): summary(res, f"{y}-01-01", f"{y+1}-01-01") for y in yrs}
    print(f"top{tn}", {y: (round(v["sr"], 2), round(v["costs_ann"], 3), round(v["turnover_ann"], 0)) for y, v in out["b"][f"top{tn}"].items()}, flush=True)
json.dump(out, open("research/is3/tlx_ab.json", "w"), indent=1, default=str)
