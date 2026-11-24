"""F1 b/c: filters on the Binance books (flow, xsmom) through the F0 harness. notes.md section F1.

    systemd-run ... .venv/bin/python -m research.studies.is3_f1 explore
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from research.studies import is3_filter as F

BOOKS = {"flow": {"lookback": 3, "cap": 0.05}, "xsmom": {"lookback": 28, "every_days": 1, "cap": 0.05}}


def cascade_mask(close: pd.DataFrame, thr: float, days: int) -> pd.Series:
    med = (close / close.shift(1) - 1).median(axis=1)
    casc = med <= thr
    blocked = pd.concat([casc.shift(k) for k in range(0, days)], axis=1).fillna(False).any(axis=1)   # the cascade day's close + next days-1
    return ~blocked


def spike_high_mask(p: dict, k: float) -> pd.DataFrame:
    c, v = p["close"], p["volume"]
    hi = c >= c.rolling(20, min_periods=20).max()
    sp = v >= k * v.rolling(20, min_periods=20).median().shift(1)
    return ~(hi & sp)


def touched(w: pd.DataFrame, mask, side: int, sample: str) -> float:
    ww = F.apply(w, mask, side)
    a, b = F.cut((w.abs().sum(1)), sample), F.cut(((w - ww).abs().sum(1)), sample)
    return round(float(b.sum() / a.sum()), 4)


def explore() -> None:
    for name, prm in BOOKS.items():
        w, p, s = F.book(name, "bnall", prm)
        c = p["close"]
        for thr, days, n in ((-0.07, 2, 200), (-0.05, 2, 50), (-0.10, 2, 50), (-0.07, 1, 50), (-0.07, 3, 50)):
            m = cascade_mask(c, thr, days)
            nd = int((~m).loc[:"2023-12-31"].sum())
            F.judge(f"F1b_{name}_casc{int(-thr * 100)}_{days}d", w, p, s, m, "explore", side=-1, n_random=n,
                    note=f"block shorts {days} d from a cascade day (median coin <= {thr:.0%}); blocked days {nd}; weight touched {touched(w, m, -1, 'explore')}")
        for k, n in ((3, 200), (2, 50), (5, 50)):
            m = spike_high_mask(p, k)
            F.judge(f"F1c_{name}_spikehigh{k}x", w, p, s, m, "explore", side=1, n_random=n,
                    note=f"block longs at a 20-day high on volume >= {k}x; weight touched {touched(w, m, 1, 'explore')}")


if __name__ == "__main__":
    {"explore": explore}[sys.argv[1]]()
