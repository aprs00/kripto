"""InSilico pass 3, HLF a: HL main book funding by leg and side (contributions from is3_prl.legs, held weights at the book's prior close), 2023-26."""
import json
import numpy as np, pandas as pd
from kripto import data
from research.studies.is3_prl import legs
p = data.load_panel("hl", "1d")
fin, ref, _ = legs(p)
f = p["funding"].reindex(index=ref.index, columns=ref.columns).fillna(0.0)
r = p["close"].pct_change(fill_method=None).reindex(ref.index).fillna(0.0)
out = {}
for n, w in fin.items():
    wh = w.shift(1).fillna(0.0)   # held through bar t (target at close t-1)
    for side, m in (("long", wh > 0), ("short", wh < 0)):
        for part, cols in (("BTC", ["BTC"]), ("alts", [c for c in wh.columns if c != "BTC"])):
            x = wh[cols].where(m[cols], 0.0)
            fund, price = (-x * f[cols]).sum(1), (x * r[cols]).sum(1)
            if (x.abs().sum(1) > 0).sum() == 0:
                continue
            out[f"{n}_{side}_{part}"] = {str(y): {"funding": round(float(fund[fund.index.year == y].mean() * 365), 4), "price": round(float(price[price.index.year == y].mean() * 365), 4)}
                                        for y in (2023, 2024, 2025, 2026)}
for k, v in out.items():
    print(k, {y: (x["funding"], x["price"]) for y, x in v.items()}, flush=True)
json.dump(out, open("research/is3/hlf_a.json", "w"), indent=1)
