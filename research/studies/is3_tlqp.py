"""TLQP d: tsmom top_n 10 vs 20 inside the SHIPPED HL main config (blend: listing_short, lowvol, tsmom; slow_lam .33). Not registered (descriptive precheck).
python -m research.studies.is3_tlqp -> research/is3/tlqp_d.json"""
import json
import numpy as np, pandas as pd
from kripto import backtest as bt, data
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY
from research.studies.is3_prb import summary

p = data.load_panel("hl", "1d")
slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
out = {}
for lam in (0.33, None):
    for tn in (20, 10):
        comps = {"listing_short": {}, "lowvol": {}, "tsmom": ({"top_n": tn} if tn != 20 else {})}
        w = REGISTRY["blend"](p, components=comps, slow_lam=lam)
        for cm in (1.0, 2.0):
            res = bt.run(w, p["close"], p.get("funding"), slip, band=0.005, cost_mult=cm)
            k = f"top{tn}_lam{lam}_cost{cm:g}"
            o = {}
            for y in range(2021, 2027):
                s = summary(res, f"{y}-01-01", f"{y + 1}-01-01")
                r = res.returns[res.returns.index.year == y]
                s["median_bp"] = float(r.median() * 1e4); s["mean_bp"] = float(r.mean() * 1e4)
                o[str(y)] = s
            o["2023-2026"] = summary(res, "2023-01-01", "2027-01-01")
            out[k] = o
            print(k, {a: (round(v["sr"], 2), round(v["ann"], 3), round(v.get("costs_ann", 0), 3)) for a, v in o.items()}, flush=True)
# head to head by year (cost 1): top10 - top20 at each lam
hh = {}
for lam in (0.33, None):
    a, b = out[f"top10_lam{lam}_cost1"], out[f"top20_lam{lam}_cost1"]
    hh[str(lam)] = {y: round(a[y]["sr"] - b[y]["sr"], 3) for y in a}
out["diff_sr_top10_minus_top20"] = hh
print(hh)
json.dump(out, open("research/is3/tlqp_d.json", "w"), indent=1, default=str)
