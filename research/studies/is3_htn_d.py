"""HTN d: PRL slow33 vs lam1 on HL with the slippage model halved (L3S: live walks ~half the model), fees unchanged."""
import json
from kripto import backtest as bt, data
from kripto.research import bars_per_day
from research.studies.is3_prb import partial, summary
from research.studies.is3_prl import legs
p = data.load_panel("hl", "1d")
slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
fin, ref, _ = legs(p)
cfg = {"lam1": ref.fillna(0.0), "slow33": fin["listing_short"] + partial(fin["lowvol"] + fin["tsmom"], 0.33)}
out = {}
for m in (1.0, 0.5):
    for k, w in cfg.items():
        r = bt.run(w, p["close"], p.get("funding"), slip * m, band=0.005)
        out[f"slip{m}_{k}"] = {str(y): summary(r, f"{y}-01-01", f"{y+1}-01-01") for y in (2023, 2024, 2025, 2026)}
        print(m, k, {y: (round(x["sr"], 2), round(x["costs_ann"], 3)) for y, x in out[f"slip{m}_{k}"].items()}, flush=True)
json.dump(out, open("research/is3/htn_d.json", "w"), indent=1)
