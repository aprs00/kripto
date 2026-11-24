"""N5e pre-registered: 4h bars, long at the close of a bar that makes a new 20-bar low on thin volume (< the 24-bar median), hold
24 bars (4 days), taker; baseline = same coin, same trailing-14-bar return decile, 3 matched bars. explore COINS10 2021-23,
confirmT COINS10 2024-25, confirmC the other coins with 1-min klines 2021-25.

    nice -n 19 .venv/bin/python -m research.studies.is3_n5e_card explore|confirmT|confirmC
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

import pandas as pd

from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
NAME = "N5e_thin_low_long_4h"
COLS = ["time", "coin", "side", "gross"]


def main(sample: str) -> None:
    lo, hi = L.SAMPLES[sample]
    if sample == "confirmC":
        coins = sorted({os.path.basename(f)[:-12] for f in glob.glob(str(ROOT / "data/bn/klines_1m/*USDT.parquet"))} - set(L.COINS10))
    else:
        coins = L.COINS10
    rows = []
    for coin in coins:
        m = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet", columns=["t", "l", "c", "qv"])
        m.index = pd.to_datetime(m.t, unit="ms", utc=True)
        m = m[(m.index >= pd.Timestamp(lo, tz="UTC") - pd.Timedelta("20D")) & (m.index < pd.Timestamp(hi, tz="UTC") + pd.Timedelta("6D"))]
        if len(m) < 10000:
            continue
        c = m.c.resample("4h").last().ffill(); v = m.qv.resample("4h").sum(); l = m.l.resample("4h").min()
        ev = (l < l.shift(1).rolling(20).min()) & (v < v.rolling(24).median().shift(1))
        x = pd.DataFrame({"time": c.index, "coin": coin, "ev": ev.to_numpy(), "ret14": (c / c.shift(14) - 1).to_numpy(), "f24": (c.shift(-24) / c - 1).to_numpy()})
        rows.append(x[(x.time >= lo) & (x.time < hi)].dropna())
    x = pd.concat(rows)
    x["m"] = (x.groupby("coin").ret14.rank(pct=True) * 9.999).astype(int)
    e, pool = x[x.ev.astype(bool)], x[~x.ev.astype(bool)]
    base = L.matched(e, pool, k=3)
    L.card(NAME, e.assign(side=1, gross=e.f24)[COLS], sample, base.assign(side=1, gross=base.f24)[COLS],
           note="long 4 days after a 4h new 20-bar low on thin volume; base = same coin, same trailing 14-bar return decile")


if __name__ == "__main__":
    main(sys.argv[1])
