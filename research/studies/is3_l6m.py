"""L6M: cc60 vs ewm20 variances in vol_target for the two shipped main books (HL main, main_bn mix). Uses is3_l6v.make_vt / track. Not registered.
PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_l6m hl|bn -> research/is3/l6m_<book>.json"""
import json, sys
import numpy as np, pandas as pd
from kripto import backtest as bt, data, strategies as S
from kripto.research import bars_per_day
from research.studies.is3_l6v import make_vt, track

book = sys.argv[1]
if book == "hl":
    p = data.load_panel("hl", "1d"); lo, hi = "2023-01-01", "2026-12-01"; fee = None
    def weights():
        return S.REGISTRY["blend"](p, components={"listing_short": {}, "lowvol": {}, "tsmom": {}}, slow_lam=0.33)
else:
    p = data.load_panel("bnall", "1d"); lo, hi = "2021-01-01", "2026-11-01"; fee = 5e-4
    cols = p["close"].columns
    def weights():
        wf = S.REGISTRY["flow"](p, lookback=3, cap=0.05).ffill().fillna(0.0).reindex(columns=cols, fill_value=0.0)
        wb = S.REGISTRY["blend"](p, components={"carry_trend": {}, "carry": {}, "xsmom": {}}).ffill().fillna(0.0).reindex(columns=cols, fill_value=0.0)
        return (wf + wb) * 0.5
c = p["close"]; r = np.log(c / c.shift(1))
slip = bt.slippage_model(p["volume"], bars_per_day(c.index))
L0, H0 = pd.Timestamp(lo, tz="UTC"), pd.Timestamp(hi, tz="UTC")
orig = S.vol_target; out = {}
for en, var in (("cc60", None), ("ewm20", (r ** 2).ewm(halflife=20, min_periods=15).mean() * 365)):
    S.vol_target = orig if var is None else make_vt(var)
    try:
        w = weights()
    finally:
        S.vol_target = orig
    kw = {"band": 0.005} if fee is None else {"fee": fee}
    res = bt.run(w, c, p.get("funding"), slip, **kw)
    ret = res.returns
    m = (ret.index >= L0) & (ret.index < H0)
    x = track(ret, 0.25, L0, H0)
    x.pop("q_vols", None)
    yrs = m.sum() / 365
    x |= {"turnover_yr": round(float(res.turnover[m].sum() / yrs), 1), "cost_pct_yr": round(float(res.costs[m].sum() / yrs * 100), 2),
          "sr_by_year": {int(y): round(float(v.mean() / v.std() * np.sqrt(365)), 2) for y, v in ret[m].groupby(ret[m].index.year)},
          "vol_by_year": {int(y): round(float(v.std() * np.sqrt(365)), 3) for y, v in ret[m].groupby(ret[m].index.year)}}
    out[en] = x
    print(book, en, json.dumps(x), flush=True)
json.dump(out, open(f"research/is3/l6m_{book}.json", "w"), indent=1)
