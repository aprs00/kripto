"""T3S c: the shipped HL main blend's held positions split by the HL-BN funding spread (above / below the day's cross-sectional median), explore 2023-05..2025-03.
Next-day simple-return P&L per unit of gross, long and short separately. Not registered. -> research/is3/t3s_c.json"""
import json
import numpy as np, pandas as pd
from kripto import backtest as bt, data
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY
from research.studies import is3_t3s as T     # explore panel, spread (coins without suffix)

p = data.load_panel("hl", "1d")
w = REGISTRY["blend"](p, components={"listing_short": {}, "lowvol": {}, "tsmom": {}}, slow_lam=0.33)
res = bt.run(w, p["close"], p.get("funding"), bt.slippage_model(p["volume"], bars_per_day(p["close"].index)), band=0.005)
H = res.weights                       # held through bar t (set at t-1's close)
r = p["close"].pct_change()
sp = T.spread.reindex(index=H.index, columns=H.columns).shift(1)          # spread known when the position was set
hi = sp.gt(sp.median(axis=1), axis=0); have = sp.notna()
ix = H.index[(H.index >= pd.Timestamp(T.LO, tz="UTC")) & (H.index < pd.Timestamp(T.HI, tz="UTC"))]
out = {"lo": T.LO, "hi": T.HI, "coverage_of_gross": round(float(H.abs().where(have).sum().sum() / H.abs().sum().sum()), 3)}
for side, m in (("long", H > 0), ("short", H < 0)):
    for grp, g in (("spread_hi", hi & have), ("spread_lo", ~hi & have)):
        pnl = (H * r).where(m & g).loc[ix].sum(axis=1); gross = H.abs().where(m & g).loc[ix].sum(axis=1)
        d = (pnl / gross.replace(0, np.nan)).dropna()
        out[f"{side}_{grp}"] = {"bp_per_unit_day": round(float(d.mean() * 1e4), 2), "t_nw": round(T.nw_t(d, 3)[0], 2), "days": len(d),
                                "gross_share": round(float(gross.sum() / H.abs().loc[ix].sum().sum()), 3)}
print(json.dumps(out, indent=1)); json.dump(out, open("research/is3/t3s_c.json", "w"), indent=1)
