"""InSilico pass 3, FST: Binance 8-h funding settlement, price drift into / out of 00/08/16 UTC vs the funding rate. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_fst a    # pre/post-settlement hour vs placebo, dose in |rate|, explore 2021-23 half 0 -> research/is3/fst_a.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data
from research.studies import is3_lib as L

THR = (0.0001, 0.0003, 0.0006, 0.0010)       # |previous print| buckets: 1 / 3 / 6 / 10 bp per 8 h (0.01 % = the base rate)


def settlements(panel):
    """Per coin, settlement hours S in {0, 8, 16}: rate = prints in bars S-1 or S (print-time convention puts most at S-1), previous = the one before."""
    f = panel["funding"]
    nz = f.where(f.notna() & (f != 0))
    idx = f.index
    rows = []
    hours = idx.hour
    off = ~np.isin(hours, [23, 0, 7, 8, 15, 16])
    four_h = nz[off].notna().groupby(idx[off].floor("1D")).any()    # a print at another hour that day = 4-h (or 1-h) interval: skip that coin-day
    for S in (0, 8, 16):
        pre_lab = (S - 1) % 24
        a = nz[hours == pre_lab]
        a.index = a.index + pd.Timedelta(hours=1)
        b = nz[hours == S]
        rate = a.reindex(b.index).fillna(0.0) + b.fillna(0.0)
        rate = rate.where(a.reindex(b.index).notna() | b.notna())
        rows.append(rate)
    rate = pd.concat(rows).sort_index()          # index = settlement time S
    prev = rate.shift(1)
    skip = four_h.reindex(rate.index.floor("1D")).fillna(False)
    skip.index = rate.index
    return rate, prev, skip


def events(panel, hour="pre", signal="prev", min_abs=THR[0], max_abs=None, placebo=0):
    """One event per coin-settlement with |signal| in [min_abs, max_abs): side = -sign(signal) (against the payer); gross = side * market-relative return of
    the hour ending at S ('pre', bar S-1) or starting at S ('post', bar S). placebo = shift the measured hour by that many hours (-4 = 4 h earlier)."""
    c = panel["close"]
    r = c / c.shift(1) - 1
    r = r.where(np.isfinite(r))
    mkt = r.mean(axis=1)
    rel = r.sub(mkt, axis=0)
    rate, prev, skip = settlements(panel)
    sig = prev if signal == "prev" else rate
    out = []
    lag = (-1 if hour == "pre" else 0) + placebo
    for coin in c.columns:
        s = sig[coin]
        ok = s.notna() & (s.abs() >= min_abs) & (~skip[coin].astype(bool) if coin in skip else True)
        if max_abs is not None:
            ok &= s.abs() < max_abs
        t = s.index[ok]
        bars = t + pd.Timedelta(hours=lag)
        v = rel[coin].reindex(bars).to_numpy()
        side = -np.sign(s[ok].to_numpy())
        m = np.isfinite(v)
        out.append(pd.DataFrame({"time": t[m] + pd.Timedelta(hours=lag), "coin": coin, "side": side[m].astype(int), "gross": side[m] * v[m]}))
    e = pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["time", "coin", "side", "gross"])
    return e.sort_values("time").reset_index(drop=True)


def sub(panel, lo, hi, half=0):
    cols = [c for c in panel["close"].columns if L.half(c) == half]
    return {k: v.loc[lo:hi, [c for c in cols if c in v.columns]] for k, v in panel.items()}


def run_a():
    p = data.load_panel("bn", "1h")
    p = {k: p[k] for k in ("close", "funding", "high", "low", "volume")}
    ex = sub(p, "2020-12-25", "2023-12-31 23:00")
    e0 = lambda q: events(q)
    print("null:", L.null_check(e0, ex, n=10))
    print("causal:", L.check_causal(e0, ex, "2022-06-01"))
    clip = lambda e: e[(e.time >= "2021-01-01") & (e.time < "2024-01-01")]
    out = {"cards": {}, "dose": {}}
    for hour in ("pre", "post"):
        e = clip(events(ex, hour))
        base = clip(events(ex, hour, placebo=-4))
        out["cards"][hour] = L.card(f"fst_{hour}", e, "explore", base=base, note="side = against the payer (prev print); base = same coin 4 h earlier")
        dose = {}
        for lo, hi in zip(THR, THR[1:] + (None,)):
            x = clip(events(ex, hour, min_abs=lo, max_abs=hi))
            xb = clip(events(ex, hour, min_abs=lo, max_abs=hi, placebo=-4))
            st = L.stats(x, xb, reps=500) if len(x) > 30 else {"n": len(x)}
            dose[f">={lo * 1e4:.0f}bp"] = {k: st.get(k) for k in ("n", "mean_bp", "base_bp", "vs_base_bp", "p_vs_base", "mde80_bp", "by_year", "by_side")}
            print(hour, lo, dose[f">={lo * 1e4:.0f}bp"], flush=True)
        out["dose"][hour] = dose
    # check: the realised (current) print instead of the previous one
    out["current_print_pre"] = {k: v for k, v in L.stats(clip(events(ex, "pre", signal="cur")), clip(events(ex, "pre", signal="cur", placebo=-4)), reps=500).items()
                                if k in ("n", "mean_bp", "base_bp", "vs_base_bp", "p_vs_base", "by_year")}
    print("current print:", out["current_print_pre"])
    json.dump(out, open("research/is3/fst_a.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    {"a": run_a}[sys.argv[1]]()
