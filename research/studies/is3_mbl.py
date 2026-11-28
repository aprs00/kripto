"""InSilico pass 3, MBL c: main_bn's first 19 live days (-9.13 %) among the backtest's 19-day windows of its mix (.5 flow + .5 blend_nested@bn components, LSP's
main_bn scaling (wf + wb) * 0.578), bnall 1d, taker 5 bp. Descriptive.   PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_mbl -> research/is3/mbl_c.json"""
import json
import numpy as np
from kripto import backtest as bt, data
from kripto.strategies import REGISTRY

LIVE, LIVE_VOL, N = -0.0913, 0.276, 19
p = data.load_panel("bnall", "1d")
wf = REGISTRY["flow"](p, lookback=3, cap=0.05).ffill().fillna(0.0)
wb = REGISTRY["blend"](p, components={"carry_trend": {}, "carry": {}, "xsmom": {}}).ffill().fillna(0.0).reindex(columns=wf.columns, fill_value=0.0)
r = bt.run((wf + wb) * 0.578, p["close"], p["funding"], bt.slippage_model(p["volume"], 1), fee=5e-4).returns.loc["2021-01-01":"2026-10-31"]
vol = float(r.std() * np.sqrt(365))
out = {"bt_ann_pct": round(float(r.mean() * 365 * 100), 1), "bt_vol_pct": round(vol * 100, 1), "bt_sr": round(float(r.mean() / r.std() * np.sqrt(365)), 2)}
for tag, x in (("raw", r), ("vol_matched", r * LIVE_VOL / vol)):
    w = (1 + x).rolling(N).apply(np.prod, raw=True).dropna() - 1
    out[tag] = {"pct_rank_of_live": round(float((w < LIVE).mean()), 3), "median_19d_pct": round(float(w.median() * 100), 2), "p5_19d_pct": round(float(w.quantile(.05) * 100), 2),
                "by_year_share_le_live": {int(y): round(float((g <= LIVE).mean()), 3) for y, g in w.groupby(w.index.year)}}
print(json.dumps(out, indent=1)); json.dump(out, open("research/is3/mbl_c.json", "w"), indent=1)
