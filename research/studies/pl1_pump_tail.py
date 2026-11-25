"""PL1 (2026-11-25 research): the pump-and-crash tail on the LONG side of xsmom@bn (live 11-22: IDOL, EVAA, AKE −42..−48% overnight,
−4.3% of the book). Filters through the F0 harness (research/studies/is3_filter.py): block a LONG (side=+1) on coin-days flagged below,
vs 200 random masks with the same on-share and persistence. Book = the live xsmom@bn config on bnall 1d (clean).
Pre-registered here BEFORE any explore number (journal 2026-11-25 06:40 research). Explore 2021-23 only; confirmT 2024-25 once, only for a
form that passes explore; 2026 (where the motivating losses are) stays in the vault.
  (a) conc : the 2 best daily log returns of the last 28 d >= 100% of the 28-d log return (without its two best days the coin fell)
  (b) max30: the best daily simple return of the last 28 d >= 30% (the MAX / lottery effect, Bali-Cakici-Whitelaw 2011)
  (c) thin : 30-d mean USD volume in the bottom third of the book's universe that day (small-cap pumps)
Explore pass = pct of dSR vs random >= 0.95 AND dSR > 0 AND dSR >= 0 in each of 2021, 2022, 2023 (insilico_pass3 §3 rule).
NOT tested again: blocking longs at a 20-d high on a volume spike (insilico F1c 2026-11-24: dSR −0.27..−0.72, those are the winners).
  usage: systemd-run ... .venv/bin/python -m research.studies.pl1_pump_tail explore
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from kripto.strategies import universe
from research.studies import is3_filter as F

PRM = {"lookback": 28, "every_days": 1, "cap": 0.05}


def masks(p: dict) -> dict:
    c, v = p["close"], p["volume"]
    lr = np.log(c / c.shift(1))
    tot = lr.rolling(28, min_periods=28).sum()
    a = lr.to_numpy()
    top2 = pd.DataFrame(np.nan, c.index, c.columns)
    # sum of the two largest daily log returns in the trailing 28 days (causal: includes today's close)
    arr = np.full(a.shape, np.nan)
    for i in range(27, len(a)):
        win = a[i - 27:i + 1]
        s = np.sort(np.where(np.isfinite(win), win, -np.inf), axis=0)[-2:]
        s = np.where(np.isfinite(s), s, np.nan)
        arr[i] = np.nansum(s, axis=0)
    top2 = pd.DataFrame(arr, c.index, c.columns)
    conc = (tot > 0) & (top2 >= tot)
    mx = (c / c.shift(1) - 1).rolling(28, min_periods=28).max()
    max30 = mx >= 0.30
    dv = v.rolling(30, min_periods=10).mean()                       # bnall volume = quote (USD) volume
    uni = universe(p, top_n=30)
    q = dv.where(uni).rank(axis=1, pct=True)
    thin = uni & (q <= 1 / 3)
    return {"a_conc": ~conc, "b_max30": ~max30, "c_thin": ~thin}


def per_year(w, p, s, m, side=1):
    base, filt = F.run(w, p, s), F.run(F.apply(w, m, side), p, s)
    out = {}
    for y in (2021, 2022, 2023):
        b, f = base[str(y)], filt[str(y)]
        out[y] = round(F.stats(f)["sr"] - F.stats(b)["sr"], 3)
    return out


def explore():
    w, p, s = F.book("xsmom", "bnall", PRM)
    for name, m in masks(p).items():
        ww = F.apply(w, m, 1)
        touched = float(F.cut((w - ww).abs().sum(axis=1), "explore").sum() / F.cut(w.abs().sum(axis=1), "explore").sum())
        r = F.judge(f"PL1_{name}", w, p, s, m, "explore", side=1, n_random=200, note=f"block xsmom longs; weight touched {touched:.3f}")
        py = per_year(w, p, s, m)
        ok = r["passes"] and all(v >= 0 for v in py.values())
        print(f"   per-year dSR {py} -> explore pass (pre-registered rule): {ok}")


if __name__ == "__main__":
    {"explore": explore}[sys.argv[1]]()
