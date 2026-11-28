"""InSilico pass 3, SMR b: known answer for research.evaluate(min_weight=) = a hand truncation + bt.run (is3_smh's method) on the HL main config,
and small_minima on bnall vs is3_smq's mins. log=False: no registry lines.   PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_smr"""
import json
import numpy as np
from kripto import backtest as bt, data, research as R, venue_bn as V
from kripto.strategies import REGISTRY

params = {"components": {"listing_short": {}, "lowvol": {}, "tsmom": {}}, "slow_lam": 0.33}
p = data.load_panel("hl", "1d")
mw = R.small_minima(p["close"].columns, "hl") / 200.0
res, s = R.evaluate("blend", p, params, "hl", band=10 / 200.0, min_weight=mw, log=False)
w = REGISTRY["blend"](p, **params)
t = w.where((w.abs() * 200.0 >= 10.0) | (w == 0) | w.isna(), 0.0)
ref = bt.run(t, p["close"], p["funding"], bt.slippage_model(p["volume"], 1), band=10 / 200.0)
d = float(np.nanmax(np.abs(res.returns.to_numpy() - ref.returns.to_numpy())))
pb = data.load_panel("bnall", "1d")
mb = R.small_minima(pb["close"].columns, "bnall")
cache = {k: v["min_notional"] for k, v in V.symbol_filters(None, max_age_h=1e9).items()}
mism = int(sum(abs(mb[c] - cache.get(c, 5.0)) > 1e-9 for c in mb.index))
out = {"hl_max_abs_return_diff": d, "hl_sr_evaluate": s.get("sharpe"), "bnall_minima_mismatch_vs_cache": mism, "bnall_BTC_ETH": [float(mb.get("BTC")), float(mb.get("ETH"))],
       "bnall_share_at_5": round(float((mb == 5.0).mean()), 3)}
print(json.dumps(out, indent=1)); json.dump(out, open("research/is3/smr_b.json", "w"), indent=1)
