"""InSilico pass 3, TSN: HL tsmom turnover decomposition (a) and T1c reconciliation (d). Descriptive."""
import json
import numpy as np, pandas as pd
from kripto import backtest as bt, data, strategies as S
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY
from research.studies.is3_prb import partial, summary

p = data.load_panel("hl", "1d")
slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
c = p["close"]
month = c.index.to_period("M")
mfreeze = lambda df: df.groupby(month).transform("first")


def tsm(sig=None, vol=None, mask=None):
    vol = S.ann_vol(p) if vol is None else vol
    mask = S.universe(p, 20) if mask is None else mask
    sig = S.trend_signal(p, (7, 14, 28, 56)) if sig is None else sig
    raw = (sig / vol).where(mask)
    raw = raw.div(raw.abs().sum(axis=1).replace(0, np.nan), axis=0)
    return S.scheduled(raw.fillna(0).where(mask.any(axis=1), np.nan), p, 1, 0.30, 2.0, None)


base = REGISTRY["tsmom"](p)
chk = float((tsm().fillna(0) - base.fillna(0)).abs().max().max())
print("replication", chk, flush=True)
mask = S.universe(p, 20).astype(bool)
cfg = {"base": base, "sig_monthly": tsm(sig=mfreeze(S.trend_signal(p, (7, 14, 28, 56))).where(c.notna())),
       "vol_monthly": tsm(vol=mfreeze(S.ann_vol(p))), "universe_monthly": tsm(mask=mfreeze(mask.astype(float)).fillna(0).astype(bool) & c.notna()),
       "ema3_T1c": REGISTRY["tsmom"](p, smooth_days=3.0), "partial_lam.21": partial(base, 1 - 2 ** (-1 / 3))}
out = {"replication": chk}
for k, w in cfg.items():
    r = bt.run(w, c, p.get("funding"), slip, band=0.005)
    out[k] = {str(y): summary(r, f"{y}-01-01", f"{y+1}-01-01") for y in (2023, 2024, 2025, 2026)}
    out[k]["all"] = summary(r, "2023-01-01", "2027-01-01")
    print(k, {y: (round(x["sr"], 2), round(x["turnover_ann"], 1), round(x["sr_pre_cost"], 2)) for y, x in out[k].items()}, flush=True)
json.dump(out, open("research/is3/tsn_ad.json", "w"), indent=1)
