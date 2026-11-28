"""HLE/HLX measure check: buy-and-hold short d2->d61 (-(P61/P1-1) + (BTC61/BTC1-1) + sum funding) vs the daily-rebalanced compounding used in hle_ab / hlx_ab."""
import json, pickle, sys
import numpy as np, pandas as pd
from kripto import data
b = pickle.load(open(sys.argv[1], "rb")); h = data.load_panel("hl", "1d")
out = {}
for nm, pan, fn in (("HLE", h, "research/is3/hle_ab.json"), ("HLX", b, "research/is3/hlx_ab.json")):
    E = pd.DataFrame(json.load(open(fn))["events"])
    c = pan["close"]; f = pan["funding"].reindex_like(c).fillna(0.0)
    res = []
    for _, e in E.iterrows():
        d0 = pd.Timestamp(e["d0"], tz="UTC"); i0 = c.index.get_loc(d0)
        a, z = c.index[i0 + 1], c.index[min(i0 + 61, len(c) - 1)]
        pa, pz = c[e["coin"]].get(a), c[e["coin"]].loc[:z].dropna().iloc[-1]
        bh = -(pz / pa - 1) + (c["BTC"][z] / c["BTC"][a] - 1) + f[e["coin"]].loc[c.index[i0 + 2]: z].sum()
        res.append(float(bh))
    E["bh"] = res
    out[nm] = {g: {"n": int(len(x)), "mean_bh": round(float(x.bh.mean()), 4), "median_bh": round(float(x.bh.median()), 4), "win_bh": round(float((x.bh > 0).mean()), 3),
                   "median_daily": round(float(x.ret.median()), 4), "by_year_median_bh": {int(y): round(float(z.bh.median()), 3) for y, z in x.groupby("year")}}
               for g, x in E.groupby("group")}
    print(nm, out[nm], flush=True)
json.dump(out, open("research/is3/hlx_bh.json", "w"), indent=1)
