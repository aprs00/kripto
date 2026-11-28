"""InSilico pass 3, PDX: phase diversification of the Binance daily legs on bn100 1h -> 6 daily anchors (is3_e2b.panels). Descriptive, NOT registered.

  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_pdx ab    # -> research/is3/pdx_ab.json
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto.data import DATA
from kripto.strategies import REGISTRY
from research.studies.is3_e2b import ANCH, COMP, panels

warnings.filterwarnings("ignore")
EV = DATA.parent / "research" / "is3"
BOOKS = {"blend_nested": ("blend", COMP), "tsmom": ("tsmom", {}), "xsmom": ("xsmom", {}), "carry": ("carry", {}), "carry_trend": ("carry_trend", {})}
sr = lambda x: round(float(x.mean() / x.std() * np.sqrt(365)), 2) if len(x) > 30 and x.std() > 0 else None


def form_ab():
    P = panels()
    out = {}
    for name, (fn, kw) in BOOKS.items():
        R, C = {}, {}
        for h in ANCH:
            p = P[h]
            res = bt.run(REGISTRY[fn](p, **kw), p["close"], p["funding"], bt.slippage_model(p["volume"], 1), fee=5e-4)
            r = res.returns.loc["2021-01-01":"2026-11-01"].copy(); r.index = (r.index + pd.Timedelta(hours=24 + h)).floor("D")
            R[h] = r.groupby(level=0).sum()
            C[h] = float(res.costs.loc["2021-01-01":"2026-11-01"].mean() * 365 * 100)
        df = pd.DataFrame(R).dropna()
        df = df[df.abs().sum(axis=1) > 0]
        avg = df.mean(axis=1)
        rho = float(df.corr().where(~np.eye(len(ANCH), dtype=bool)).stack().mean())
        singles = {h: sr(df[h]) for h in ANCH}
        ms = float(np.mean([v for v in singles.values() if v is not None]))
        out[name] = {"avg6": sr(avg), "single": singles, "mean_single": round(ms, 2), "rho": round(rho, 3),
                     "predicted_avg6": round(ms * np.sqrt(6 / (1 + 5 * rho)), 2), "cost_pct_yr_single": {h: round(v, 2) for h, v in C.items()},
                     "years_avg6": {int(y): sr(x) for y, x in avg.groupby(avg.index.year)},
                     "years_00": {int(y): sr(x) for y, x in df[0].groupby(df.index.year)},
                     "years_04": {int(y): sr(x) for y, x in df[4].groupby(df.index.year)}}
        print(name, json.dumps(out[name]), flush=True)
    json.dump(out, open(EV / "pdx_ab.json", "w"), indent=1)


def hourly_returns(coins):
    from research.studies.is3_e2b import hourly
    hp = hourly(coins)                     # price at the full hour (close of the bar that ends then)
    px = pd.DataFrame(hp).sort_index()
    px = px[px.index >= "2020-12-01"].astype("float32")
    r = (px.shift(-1) / px - 1).astype("float32")       # return over [H, H+1h), labelled H
    return r.where(np.isfinite(r), 0.0)


def exact(P, fn, kw, rh, panel_of=None):
    """each anchor's book on ONE hourly grid: position held during bar [L, L+24h) = res.weights[L]; funding and costs booked at the bar end.
    Returns {h: daily P&L on 00-UTC days} for each single anchor, and their average (= the 6-sub-book portfolio, 1/6 each, no cross-book drift)."""
    out = {}
    for h in ANCH:
        p = (panel_of or P)[h]
        res = bt.run(REGISTRY[fn](p, **kw), p["close"], p["funding"], bt.slippage_model(p["volume"], 1), fee=5e-4)
        W = res.weights.reindex(columns=rh.columns).fillna(0.0)
        W = W[W.index >= "2020-12-01"]
        pos = W.reindex(rh.index, method="ffill").fillna(0.0).to_numpy(np.float32)
        pnl = pd.Series((pos * rh.to_numpy()).sum(axis=1), rh.index)
        end = res.costs.index + pd.Timedelta(hours=24)
        fc = pd.Series((res.funding.to_numpy() - res.costs.to_numpy()), end)      # funding P&L (signed) and costs, at bar end
        pnl = pnl.add(fc.groupby(level=0).sum().reindex(pnl.index, fill_value=0.0), fill_value=0.0)
        out[h] = pnl.groupby(pnl.index.floor("D")).sum().loc["2021-01-01":"2026-10-31"]
        del pos
    df = pd.DataFrame(out)
    return df


def form_x(names=("blend_nested", "tsmom", "carry")):
    P = panels()
    rh = hourly_returns(list(P[0]["close"].columns))
    out = {}
    for name in names:
        fn, kw = BOOKS[name]
        df = exact(P, fn, kw, rh)
        avg = df.mean(axis=1)
        ac = lambda x: round(float(x.autocorr(1)), 3)
        mo = lambda x: round(float(x.resample("ME").sum().mean() / x.resample("ME").sum().std() * np.sqrt(12)), 2)
        out[name] = {"avg6": sr(avg), "single": {h: sr(df[h]) for h in ANCH}, "rho": round(float(df.corr().where(~np.eye(6, dtype=bool)).stack().mean()), 3),
                     "autocorr1": {"avg6": ac(avg), "00": ac(df[0])}, "monthly_sr": {"avg6": mo(avg), **{h: mo(df[h]) for h in ANCH}},
                     "years_avg6": {int(y): sr(x) for y, x in avg.groupby(avg.index.year)}, "years_00": {int(y): sr(x) for y, x in df[0].groupby(df.index.year)}}
        print(name, json.dumps(out[name]), flush=True)
    json.dump(out, open(EV / "pdx_x.json", "w"), indent=1)


def form_xf(tag="pdx_xf"):
    """E2C c's flow@bn avg6 (approx taker split) re-measured on one hourly clock. Memory: books first, panels freed, hourly returns only for held coins."""
    import gc
    from research.studies import is3_e2c as E
    P, _ = E.panels()
    keep = {}
    for h in E.ANCH:
        p = P[h]
        res = bt.run(REGISTRY["flow"](p, **E.PARAMS), p["close"], p["funding"], bt.slippage_model(p["volume"], 1), fee=5e-4)
        W = res.weights.fillna(0.0); W = W.loc[:, W.abs().sum() > 0]
        keep[h] = (W.astype("float32"), res.funding, res.costs, res.returns)
    del P; gc.collect()
    cols = sorted(set().union(*[set(k[0].columns) for k in keep.values()]))
    rh = hourly_returns(cols)
    rh = rh[rh.index >= "2021-12-01"]
    out = {}
    for h, (W, fu, co, rr) in keep.items():
        W = W.reindex(columns=rh.columns).fillna(0.0)
        pos = W.reindex(rh.index, method="ffill").fillna(0.0).to_numpy(np.float32)
        pnl = pd.Series((pos * rh.to_numpy()).sum(axis=1), rh.index)
        fc = pd.Series(fu.to_numpy() - co.to_numpy(), co.index + pd.Timedelta(hours=24))
        pnl = pnl.add(fc.groupby(level=0).sum().reindex(pnl.index, fill_value=0.0), fill_value=0.0)
        out[h] = pnl.groupby(pnl.index.floor("D")).sum().loc["2022-01-01":"2026-10-31"]
        del pos
    df = pd.DataFrame(out); avg = df.mean(axis=1)
    mo = lambda x: round(float(x.resample("ME").sum().mean() / x.resample("ME").sum().std() * np.sqrt(12)), 2)
    res = {"avg6": sr(avg), "single": {h: sr(df[h]) for h in E.ANCH}, "rho": round(float(df.corr().where(~np.eye(6, dtype=bool)).stack().mean()), 3),
           "monthly_sr": {"avg6": mo(avg), **{h: mo(df[h]) for h in E.ANCH}},
           "years_avg6": {int(y): sr(x) for y, x in avg.groupby(avg.index.year)}, "years_00": {int(y): sr(x) for y, x in df[0].groupby(df.index.year)}}
    print(json.dumps(res), flush=True)
    json.dump(res, open(EV / f"{tag}.json", "w"), indent=1)


if __name__ == "__main__":
    {"ab": form_ab, "x": form_x, "xf": form_xf}[sys.argv[1]]()
