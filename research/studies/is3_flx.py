"""InSilico pass 3, FLX: flow@bn decay check on bnall 1d (flow lookback 3, cap .05; control: blend carry_trend/carry/xsmom). Descriptive.
  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_flx  -> research/is3/flx_ab.json"""
import json
import numpy as np
import pandas as pd
from kripto import backtest as bt, data
from kripto.strategies import REGISTRY

S = slice("2021-01-01", "2026-10-31")
p = data.load_panel("bnall", "1d")
slip = bt.slippage_model(p["volume"], 1)


def series(w):
    res = bt.run(w, p["close"], p["funding"], slip, fee=5e-4)
    return res, res.returns.loc[S]


def hac_slope(y):
    """OLS slope of y on time (years) with Newey-West (6 lags) t."""
    y = y.dropna(); x = (y.index - y.index[0]).days.to_numpy() / 365.0
    X = np.c_[np.ones(len(x)), x]; b = np.linalg.lstsq(X, y.to_numpy(), rcond=None)[0]; e = y.to_numpy() - X @ b
    L = 6; n = len(y); S0 = (X * e[:, None]).T @ (X * e[:, None])
    for l in range(1, L + 1):
        w = 1 - l / (L + 1); G = (X[l:] * e[l:, None]).T @ (X[:-l] * e[:-l, None]); S0 += w * (G + G.T)
    XtXi = np.linalg.inv(X.T @ X); V = XtXi @ S0 @ XtXi
    return float(b[1]), float(b[1] / np.sqrt(V[1, 1]))


out = {}
wf = REGISTRY["flow"](p, lookback=3, cap=0.05)
wb = REGISTRY["blend"](p, components={"carry_trend": {}, "carry": {}, "xsmom": {}})
for tag, w in (("flow", wf), ("blend", wb)):
    res, r = series(w)
    m = r.resample("ME").sum()
    roll = r.rolling(365).apply(lambda x: x.mean() / x.std() * np.sqrt(365), raw=True).resample("ME").last().loc["2022":]
    sl, t = hac_slope(m * 12)
    gross = (r + res.costs.loc[S]).groupby(r.index.year).mean() * 365
    out[tag] = {"sr_by_year": {int(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in r.groupby(r.index.year)},
                "gross_ann%_by_year": {int(y): round(float(v * 100), 1) for y, v in gross.items()},
                "cost_ann%_by_year": {int(y): round(float(v * 365 * 100), 1) for y, v in res.costs.loc[S].groupby(res.costs.loc[S].index.year).mean().items()},
                "funding_ann%_by_year": {int(y): round(float(v * 365 * 100), 1) for y, v in res.funding.loc[S].groupby(res.funding.loc[S].index.year).mean().items()},
                "monthly_ann_return_slope_per_year": round(sl, 3), "slope_hac_t": round(t, 2),
                "rolling_365d_sr_by_quarter": {str(k.date()): round(float(v), 2) for k, v in roll.resample("QE").last().items()}}
    print(tag, json.dumps(out[tag]), flush=True)
# flow's signal IC by year: rank corr of today's target weight with next day's simple return (cross-section, daily), and long vs short leg P&L
W = wf.ffill()
nxt = p["close"].pct_change(fill_method=None).shift(-1)
ic = W.rank(axis=1).corrwith(nxt.rank(axis=1), axis=1).loc[S]
out["flow_ic_by_year"] = {int(y): [round(float(x.mean()), 4), round(float(x.mean() / x.std() * np.sqrt(len(x))), 2)] for y, x in ic.groupby(ic.index.year)}
legs = {}
for side, mask in (("long", W > 0), ("short", W < 0)):
    pnl = (W.where(mask, 0.0) * nxt).sum(axis=1).loc[S]
    legs[side] = {int(y): round(float(v * 365 * 100), 1) for y, v in pnl.groupby(pnl.index.year).mean().items()}
out["flow_leg_gross_ann%_by_year"] = legs
mkt = nxt.mean(axis=1).loc[S]
out["universe_eqw_ann%_by_year"] = {int(y): round(float(v * 365 * 100), 1) for y, v in mkt.groupby(mkt.index.year).mean().items()}
out["names_held_by_year"] = {int(y): round(float(v), 1) for y, v in (W.loc[S] != 0).sum(axis=1).groupby(W.loc[S].index.year).mean().items()}
print(json.dumps({k: out[k] for k in ("flow_ic_by_year", "flow_leg_gross_ann%_by_year", "universe_eqw_ann%_by_year", "names_held_by_year")}))
json.dump(out, open("research/is3/flx_ab.json", "w"), indent=1)
