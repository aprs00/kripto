"""PRB stress: frozen lam .33 vs 1 on HL at band .01 (= the $10 min order at $1,000) and .05 ($200), all years. Not a choice: lam was frozen in prb_a."""
import json, numpy as np, pandas as pd
from kripto import backtest as bt, data
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY
from research.studies.is3_prb import partial, summary, COMP
h = data.load_panel("hl", "1d")
slip = bt.slippage_model(h["volume"], bars_per_day(h["close"].index))
w = REGISTRY["blend"](h, **COMP)
out = {}
for band in (0.01, 0.05):
    for lam in (1.0, 0.33):
        res = bt.run(partial(w, lam), h["close"], h.get("funding"), slip, band=band)
        out[f"band{band}_lam{lam}"] = {str(y): summary(res, f"{y}-01-01", f"{y+1}-01-01") for y in (2023, 2024, 2025, 2026)}
        print(band, lam, {k: (round(v["sr"], 2), round(v["costs_ann"], 3)) for k, v in out[f"band{band}_lam{lam}"].items()}, flush=True)
json.dump(out, open("research/is3/prb_d.json", "w"), indent=1)
