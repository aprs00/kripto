"""InSilico pass 3, T8R: market regime state -> daily returns of the live BN books (backlog T8). Descriptive + F0 filter. NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_t8r a     # forms a and b (state tables, explore 2021-23) -> data/is3/t8r_ab.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from research.studies import is3_filter as F

OUT = F.L.OUT if hasattr(F.L, "OUT") else None
BOOKS = {"flow": ("flow", {"lookback": 3, "cap": 0.05}),
         "blend": ("blend", {"components": {"carry_trend": {}, "carry": {}, "xsmom": {}}}),
         "xsmom": ("xsmom", {})}
LO, HI = pd.Timestamp("2021-01-01", tz="UTC"), pd.Timestamp("2024-01-01", tz="UTC")


def states(panel):
    c, f = panel["close"], panel["funding"]
    btc = c["BTC"]
    r = btc.pct_change(fill_method=None)
    rv = r.rolling(30, min_periods=20).std() * np.sqrt(365)
    top = panel["volume"].rolling(30, min_periods=10).mean().rank(axis=1, ascending=False) <= 100
    mf = f.where(top).rolling(7, min_periods=3).mean().mean(axis=1) * 365 * 3 if f.notna().any().any() else None
    fund = f.where(top).mean(axis=1).rolling(7, min_periods=3).mean() * 365
    ma = btc / btc.rolling(50, min_periods=40).mean() - 1
    r30 = btc.pct_change(30, fill_method=None)
    br = (c > c.rolling(20, min_periods=15).mean()).where(top & c.notna()).mean(axis=1)
    disp = c.pct_change(fill_method=None).where(top).std(axis=1).rolling(10, min_periods=5).mean()
    S = pd.DataFrame({"btc_rv30": rv, "mkt_funding7": fund, "btc_vs_ma50": ma, "btc_ret30": r30, "breadth20": br, "dispersion10": disp})
    return S.shift(1)          # known at the close BEFORE the day whose return is measured (weights at t earn t -> t+1; state from t-1 close is conservative)


def table(ret, s, q=3):
    d = pd.DataFrame({"r": ret, "s": s}).dropna()
    d = d[(d.index >= LO) & (d.index < HI)]
    d["b"] = pd.qcut(d.s, q, labels=False, duplicates="drop")
    out = {}
    for b, g in d.groupby("b"):
        sr = g.r.mean() / g.r.std() * np.sqrt(365) if g.r.std() > 0 else 0.0
        out[int(b)] = {"n": int(len(g)), "s_med": round(float(g.s.median()), 4), "mean_bp": round(float(g.r.mean()) * 1e4, 2), "median_bp": round(float(g.r.median()) * 1e4, 2),
                       "sr": round(float(sr), 2), "worst": round(float(g.r.min()), 4),
                       "sr_by_year": {int(y): round(float(x.r.mean() / x.r.std() * np.sqrt(365)), 2) if len(x) > 20 and x.r.std() > 0 else None for y, x in g.groupby(g.index.year)}}
    return out


def run_a():
    res, R = {}, {}
    panel = None
    for nm, (s, prm) in BOOKS.items():
        w, panel, slip = F.book(s, "bnall", prm)
        R[nm] = F.run(w, panel, slip)
        del w
    S = states(panel)
    for nm, r in R.items():
        res[nm] = {"sr_all": round(float(r[(r.index >= LO) & (r.index < HI)].mean() / r[(r.index >= LO) & (r.index < HI)].std() * np.sqrt(365)), 2)}
        for col in S:
            res[nm][col] = table(r, S[col])
            t = res[nm][col]
            print(f"{nm:6s} {col:13s} SR by tercile " + " | ".join(f"{b}: {v['sr']:+.2f} (med s {v['s_med']}, yrs {list(v['sr_by_year'].values())})" for b, v in t.items()), flush=True)
    (F.L.OUT / "t8r_ab.json").write_text(json.dumps(res, indent=1, default=str))
    pd.DataFrame(R).to_parquet(F.L.OUT / "t8r_books.parquet")
    S.to_parquet(F.L.OUT / "t8r_states.parquet")




def run_c():
    import json as _j
    w, panel, slip = F.book("flow", "bnall", {"lookback": 3, "cap": 0.05})
    btc = panel["close"]["BTC"]
    rv = btc.pct_change(fill_method=None).rolling(30, min_periods=20).std()
    thr = rv.rolling(365, min_periods=180).quantile(2 / 3)
    bad = (rv > thr).shift(1).fillna(False).astype(bool)
    mask = ~bad
    tf = lambda ww, m, side: F.scale(ww, m, side, k=0.5)
    out = F.judge("T8Rc_flow_halve_btc_hivol", w, panel, slip, mask, "explore", tf=tf, note="halve flow@bn when BTC 30-d vol > trailing-365 2/3 quantile")
    b = F.run(w, panel, slip)
    f = F.run(tf(w, mask, None), panel, slip)
    yrs = {}
    for y in (2021, 2022, 2023):
        bb, ff = b[b.index.year == y], f[f.index.year == y]
        yrs[y] = round(float(ff.mean() / ff.std() * np.sqrt(365) - bb.mean() / bb.std() * np.sqrt(365)), 3)
    out["dSR_by_year"] = yrs
    out["pass_prereg"] = bool(out["passes"] and all(v > 0 for v in yrs.values()))
    print("dSR by year", yrs, "PASS" if out["pass_prereg"] else "FAIL", flush=True)
    (F.L.OUT / "t8r_c.json").write_text(_j.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    {"a": run_a, "c": run_c}[sys.argv[1]]()
