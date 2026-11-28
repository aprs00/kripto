"""InSilico pass 3, SMH: the HL main book (blend listing_short/lowvol/tsmom, slow_lam .33, x main_scale) at $1,000, $200 band $10 (today's small_acct), $200 hard $10 minimum.
HL 1d, taker cost model of bt.run. Constant account size. Descriptive.   PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_smh -> research/is3/smh_a.json"""
import json
import numpy as np
import pandas as pd
from kripto import backtest as bt, data, paper as P
from kripto.strategies import REGISTRY

_, risk = P.load_cfg()
SCALE = float(risk["main_scale"]["main"])
p = data.load_panel("hl", "1d")
w = REGISTRY["blend"](p, components={"listing_short": {}, "lowvol": {}, "tsmom": {}}, slow_lam=0.33).ffill().fillna(0.0) * SCALE
w = w.clip(-risk["max_asset_weight"], risk["max_asset_weight"])
slip = bt.slippage_model(p["volume"], 1)
S = slice("2021-01-01", None)


def stats(x, eq):
    res = bt.run(x, p["close"], p["funding"], slip, band=10.0 / eq)
    r = res.returns.loc[S]
    sr = lambda y: round(float(y.mean() / y.std() * np.sqrt(365)), 2) if y.std() > 0 else None
    return {"sr": sr(r), "ann%": round(float(r.mean() * 365 * 100), 1), "vol%": round(float(r.std() * np.sqrt(365) * 100), 1),
            "gross_held": round(float(res.weights.loc[S].abs().sum(axis=1).mean()), 3), "years": {int(y): sr(v) for y, v in r.groupby(r.index.year)}}


t = w.where(w.abs() * 200.0 >= 10.0, 0.0)
ga, gt = w.abs().sum(axis=1), t.abs().sum(axis=1)
sh = (gt / ga.where(ga > 0)).loc[S]
out = {"main_scale": SCALE, "usd1000": stats(w, 1000.0), "usd200_band": stats(w, 200.0), "usd200_hardmin": stats(t, 200.0),
       "deployed_share_by_year": {int(y): round(float(v.mean()), 2) for y, v in sh.groupby(sh.index.year)},
       "names_by_year_1000_vs_200": {int(y): [round(float((w.loc[S] != 0).sum(axis=1)[w.loc[S].index.year == y].mean()), 1), round(float((t.loc[S] != 0).sum(axis=1)[t.loc[S].index.year == y].mean()), 1)] for y in sorted(set(w.loc[S].index.year))},
       "last_row": {"date": str(w.index[-1]), "gross": round(float(ga.iloc[-1]), 3), "held_200": round(float(gt.iloc[-1]), 3), "btc_w": round(float(w.iloc[-1].get("BTC", 0)), 3)},
       "panel_end": str(p["close"].index[-1])}
print(json.dumps(out, indent=1)); json.dump(out, open("research/is3/smh_a.json", "w"), indent=1)
