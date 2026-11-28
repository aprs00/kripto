"""PRL stress on the frozen slow33 rule (no choice): band .01 ($1,000 min order), band .05 ($200), 2x costs at band .005; all HL years; causality check."""
import json, numpy as np, pandas as pd
from kripto import backtest as bt, data
from kripto.research import bars_per_day
from research.studies.is3_prb import partial, summary
from research.studies.is3_prl import legs
p = data.load_panel("hl", "1d")
slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
fin, ref, _ = legs(p)
books = {"lam1": ref.fillna(0.0), "slow33": fin["listing_short"] + partial(fin["lowvol"] + fin["tsmom"], 0.33)}
# causality: truncating the panel at a date must not change earlier slow33 weights
cut = pd.Timestamp("2025-06-01", tz="UTC")
pc = {k: (v.loc[:cut] if hasattr(v, "loc") else v) for k, v in p.items()}
fc, _, _ = legs(pc)
w2 = fc["listing_short"] + partial(fc["lowvol"] + fc["tsmom"], 0.33)
caus = float((w2 - books["slow33"].loc[:cut]).abs().max().max())
print("causality max |dw| (truncated panel):", caus, flush=True)
out = {"causality_err": caus}
for lab, band, cm in (("band.01", 0.01, 1.0), ("band.05", 0.05, 1.0), ("2xcost", 0.005, 2.0)):
    for k, w in books.items():
        r = bt.run(w, p["close"], p.get("funding"), slip, band=band, cost_mult=cm)
        out[f"{lab}_{k}"] = {y: summary(r, f"{y}-01-01", f"{y+1}-01-01") for y in (2023, 2024, 2025, 2026)}
        print(lab, k, {y: round(v["sr"], 2) for y, v in out[f"{lab}_{k}"].items()}, flush=True)
json.dump(out, open("research/is3/prl_s.json", "w"), indent=1)
