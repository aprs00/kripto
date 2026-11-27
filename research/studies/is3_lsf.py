"""InSilico pass 3, LSF: listing_short's squeezed tail. Descriptive state -> distribution + F0 filter. NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_lsf a     # bnall 1d 2021-23 only (HL kept for the held-out form c) -> research/is3/lsf_a.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data
from kripto import strategies as S
from research.studies import is3_lib as L


def short_days(p, skip_days=1, hold_days=60, min_dv=1e6):
    """Coin-days the listing_short book holds (same eligibility as kripto.strategies.listing_short)."""
    c, v = p["close"], p["volume"]
    traded = (v.fillna(0) > 0) & c.notna()
    started = traded.cummax()
    age = started.cumsum()
    any_t = traded.any(axis=1)
    t_cut = any_t.idxmax() + pd.Timedelta(days=30)
    pre = started.loc[started.index < t_cut].any()
    elig = (age > skip_days) & (age <= skip_days + hold_days) & c.notna() & (S.dollar_volume(p) >= min_dv)
    elig = elig.loc[:, ~pre].reindex(columns=c.columns, fill_value=False)
    elig = elig & pd.DataFrame(np.broadcast_to((c.index >= t_cut)[:, None], c.shape), c.index, c.columns)
    return elig, age


def events(p, lo, hi, H=7):
    c, f = p["close"], p["funding"].fillna(0.0)
    elig, age = short_days(p)
    r = c / c.shift(1) - 1
    ab = r.sub(r["BTC"], axis=0)
    fwd_px = -(c.shift(-H) / c - 1).sub(c["BTC"].shift(-H) / c["BTC"] - 1, axis=0)    # short's abnormal P&L over the next H days
    fwd_f = f[::-1].rolling(H, min_periods=H).sum()[::-1].shift(-1)                  # funding received by the short over t+1..t+H (positive rate: longs pay)
    f3 = f.rolling(3, min_periods=3).sum()                                           # received by a short over the last 3 days (known at t)
    px3 = (c / c.shift(3) - 1).sub(c["BTC"] / c["BTC"].shift(3) - 1, axis=0)
    st = pd.DataFrame({"f3": f3.where(elig).stack(), "px3": px3.where(elig).stack(), "age": age.where(elig).stack(),
                       "px": fwd_px.where(elig).stack(), "fund": fwd_f.where(elig).stack()}).dropna()
    st.index.names = ["time", "coin"]
    st = st.reset_index()
    st = st[(st.time >= lo) & (st.time < hi)]
    st["gross"] = st.px + st.fund
    st["side"] = -1
    return st


def run_a():
    p = data.load_panel("bnall", "1d")
    lo, hi = (pd.Timestamp(x, tz="UTC") for x in L.SAMPLES["explore"])
    out = {}
    for H in (7, 30):
        e = events(p, lo, hi, H)
        e["q"] = pd.qcut(e.f3, 5, labels=False, duplicates="drop")
        tab = e.groupby("q").agg(n=("gross", "size"), f3_bp=("f3", lambda x: x.median() * 1e4), px_bp=("px", lambda x: x.mean() * 1e4),
                                 fund_bp=("fund", lambda x: x.mean() * 1e4), net_bp=("gross", lambda x: x.mean() * 1e4), net_med_bp=("gross", lambda x: x.median() * 1e4))
        yrs = e.groupby([e.time.dt.year, "q"]).gross.mean().unstack().mul(1e4).round(0)
        print(f"\nH={H}d, {len(e)} short coin-days, {e.coin.nunique()} coins; by trailing-3d funding quintile (0 = short PAID most):\n{tab.round(1).to_string()}\nnet by year:\n{yrs.to_string()}", flush=True)
        # within past-3d price move terciles (squeeze control)
        e["pt"] = pd.qcut(e.px3, 3, labels=False)
        ctl = e.groupby(["pt", "q"]).gross.mean().unstack().mul(1e4).round(0)
        print("net by px3 tercile (0 = coin FELL most vs BTC) x funding quintile:\n" + ctl.to_string(), flush=True)
        lowq = e[e.q == 0]
        rest = e[e.q > 0]
        c = L.card(f"LSF_a_low_funding_H{H}", lowq.assign(gross=-lowq.gross), "explore", base=rest.assign(gross=-rest.gross),
                   note="EXIT value: minus the short's next-H P&L in the lowest trailing-funding quintile vs the rest")
        out[f"H{H}"] = {"table": tab.round(2).to_dict("index"), "by_year": yrs.to_dict("index"), "px3_ctl": ctl.to_dict("index"),
                        "card": {k: c.get(k) for k in ("n", "mean_bp", "median_bp", "base_bp", "vs_base_bp", "p_vs_base", "mde80_bp", "by_year")}}
    json.dump({"study": "research/studies/is3_lsf.py a", **out}, open(L.OUT / "lsf_a.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    {"a": run_a}[sys.argv[1]]()
