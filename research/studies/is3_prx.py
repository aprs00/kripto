"""InSilico pass 3, PRX: PRL's frozen rule on the same 3-leg book built on cached bnall. Descriptive replication."""
import json, pickle, sys
import numpy as np
from kripto import backtest as bt
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY
from research.studies.is3_prb import partial, summary
from research.studies.is3_prl import legs

p = pickle.load(open(sys.argv[1], "rb"))
slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
fin, ref, err = legs(p)
print("decomp err", err, flush=True)
run = lambda w: bt.run(w, p["close"], p.get("funding"), slip, band=0.005)
yrs = (2021, 2022, 2023, 2024, 2025, 2026)
out = {"decomp_err": err}
cfg = {"lam1": ref.fillna(0.0), "slow33": fin["listing_short"] + partial(fin["lowvol"] + fin["tsmom"], 0.33)}
for n in ("tsmom", "lowvol"):
    w = REGISTRY[n](p).fillna(0.0)
    cfg[f"{n}_lam1"], cfg[f"{n}_lam33"] = w, partial(w, 0.33)
for k, w in cfg.items():
    r = run(w)
    o = {str(y): summary(r, f"{y}-01-01", f"{y+1}-01-01") for y in yrs}
    o["2021-23"] = summary(r, "2021-01-01", "2024-01-01"); o["2024-26"] = summary(r, "2024-01-01", "2027-01-01")
    out[k] = o
    print(k, {y: (round(x["sr"], 2), round(x["costs_ann"], 3)) for y, x in o.items()}, flush=True)
json.dump(out, open("research/is3/prx_abc.json", "w"), indent=1)
