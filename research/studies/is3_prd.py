"""InSilico pass 3, PRD: PRL dose-response (lam grid) and leg attribution on HL. Descriptive."""
import json
import numpy as np
from kripto import backtest as bt, data
from kripto.research import bars_per_day
from research.studies.is3_prb import partial, summary
from research.studies.is3_prl import legs
p = data.load_panel("hl", "1d")
slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
fin, ref, _ = legs(p)
yrs = (2023, 2024, 2025, 2026)
out = {}
cfg = {f"lam{l}": fin["listing_short"] + partial(fin["lowvol"] + fin["tsmom"], l) for l in (1.0, .75, .5, .33, .25, .15, .1)}
cfg["tsmom_only33"] = fin["listing_short"] + fin["lowvol"] + partial(fin["tsmom"], .33)
cfg["lowvol_only33"] = fin["listing_short"] + fin["tsmom"] + partial(fin["lowvol"], .33)
for k, w in cfg.items():
    r = bt.run(w, p["close"], p.get("funding"), slip, band=0.005)
    out[k] = {str(y): summary(r, f"{y}-01-01", f"{y+1}-01-01") for y in yrs}
    print(k, {y: (round(x["sr"], 2), round(x["costs_ann"], 3), round(x["sr_pre_cost"], 2)) for y, x in out[k].items()}, flush=True)
json.dump(out, open("research/is3/prd_ab.json", "w"), indent=1)
