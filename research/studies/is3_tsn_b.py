"""TSN b (pre-stated in notes): listing full + lowvol lam .33 + tsmom with a monthly-held signal, vs PRL slow33, HL explore 2023-24."""
import inspect, json
import numpy as np, pandas as pd
from kripto import backtest as bt, data, strategies as S
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY
from research.studies.is3_prb import partial, summary
from research.studies import is3_prl as PRL

p = data.load_panel("hl", "1d")
slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
fin, ref, _ = PRL.legs(p)
slow33 = fin["listing_short"] + partial(fin["lowvol"] + fin["tsmom"], 0.33)
orig = REGISTRY["tsmom"]


def tsmom_m(panel, target_vol=0.30):
    c = panel["close"]
    sig = S.trend_signal(panel, (7, 14, 28, 56)).groupby(c.index.to_period("M")).transform("first").where(c.notna())
    vol, mask = S.ann_vol(panel), S.universe(panel, 20)
    raw = (sig / vol).where(mask)
    raw = raw.div(raw.abs().sum(axis=1).replace(0, np.nan), axis=0)
    return S.scheduled(raw.fillna(0).where(mask.any(axis=1), np.nan), panel, 1, target_vol, 2.0, None)


REGISTRY["tsmom"] = tsmom_m
S._COMP_CACHE.clear()
finm, _, err = PRL.legs(p)
REGISTRY["tsmom"] = orig
cand = finm["listing_short"] + partial(finm["lowvol"], 0.33) + finm["tsmom"]
out = {"decomp_err": err}
for k, w in (("slow33", slow33), ("tsmom_monthly", cand)):
    r = bt.run(w, p["close"], p.get("funding"), slip, band=0.005)
    out[k] = {str(y): summary(r, f"{y}-01-01", f"{y+1}-01-01") for y in (2023, 2024)}
    print(k, {y: (round(x["sr"], 3), round(x["costs_ann"], 4), round(x["sr_pre_cost"], 3)) for y, x in out[k].items()}, flush=True)
json.dump(out, open("research/is3/tsn_b.json", "w"), indent=1)
