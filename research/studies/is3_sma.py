"""InSilico pass 3, SMA b: known answer research.evaluate(round_min=) == hand round-to-min + bt.run on the HL main config (log=False). 
  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_sma -> research/is3/sma_b.json"""
import json
import numpy as np
from kripto import backtest as bt, data, research as R
from kripto.strategies import REGISTRY
from research.studies.is3_smd import roundmin, EQ
import pandas as pd

params = {"components": {"listing_short": {}, "lowvol": {}, "tsmom": {}}, "slow_lam": 0.33}
p = data.load_panel("hl", "1d")
mins = R.small_minima(p["close"].columns, "hl")
res, s = R.evaluate("blend", p, params, "hl", band=10 / 200.0, round_min=mins / 200.0, log=False)
w = REGISTRY["blend"](p, **params)
hand = pd.DataFrame(roundmin(w.fillna(0.0), mins), w.index, w.columns).where(w.notna())
ref = bt.run(hand, p["close"], p["funding"], bt.slippage_model(p["volume"], 1), band=10 / 200.0)
out = {"max_abs_return_diff": float(np.nanmax(np.abs(res.returns.to_numpy() - ref.returns.to_numpy()))), "sr_evaluate": s.get("sharpe"), "eq": EQ}
print(json.dumps(out)); json.dump(out, open("research/is3/sma_b.json", "w"), indent=1)
