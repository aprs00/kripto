"""O1 pre-registered forms.
O1d_reset50_long_4h: 4h RSI14 falls through 50 having been > 70 within the previous 20 bars -> long 6 bars (24 h), taker; baseline = same
  coin, same decile of the trailing 14-bar return, 3 matched bars (long). explore COINS10 2021-23; confirmT COINS10 2024-25;
  confirmC the other coins with 1-min klines 2021-25.
O1e_ladder_rsi50: the ladder's one-bar-late fills (T1k30, data/is3/e2_k-30.parquet), h60, when the coin's daily RSI14 at the
  previous close is >= 50, vs fills with RSI < 50 (baseline). explore 2021-23; confirmT 2024-25 fills (same file; the split is new).

    nice -n 19 .venv/bin/python -m research.studies.is3_o1_card <form> explore|confirmT|confirmC
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from kripto import data
from research.studies import is3_lib as L
from research.studies import is3_o1 as O

ROOT = Path(__file__).resolve().parents[2]
COLS = ["time", "coin", "side", "gross"]


def panel4h(coins, lo, hi):
    cols = {}
    for coin in coins:
        k = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet", columns=["t", "c"])
        k.index = pd.to_datetime(k.t, unit="ms", utc=True)
        cols[coin] = k.c[(k.index >= pd.Timestamp(lo, tz="UTC") - pd.Timedelta("60D")) & (k.index < pd.Timestamp(hi, tz="UTC") + pd.Timedelta("10D"))].resample("4h").last()
    return pd.DataFrame(cols)


def reset50(sample):
    lo, hi = L.SAMPLES[sample]
    if sample == "confirmC":
        have = {os.path.basename(f)[:-12] for f in glob.glob(str(ROOT / "data/bn/klines_1m/*USDT.parquet"))}
        coins = sorted(have - set(L.COINS10))
    else:
        coins = L.COINS10
    O.LO, O.HI = lo, hi
    parts = []
    for i in range(0, len(coins), 10):
        c = panel4h(coins[i:i + 10], lo, hi)
        lf = O.long_frame(c)
        lf = lf[(lf.time >= lo) & (lf.time < hi)].dropna(subset=["ret14", "rsi", "f6"])
        lf["m"] = (lf.groupby("coin").ret14.rank(pct=True) * 9.999).astype(int)
        ev = O.events(c, "4h")
        ev = ev[ev.form == "d_to_mean_short"].merge(lf, on=["time", "coin"], how="inner")
        key = set(zip(ev.time, ev.coin))
        pool = lf[[(t, k) not in key for t, k in zip(lf.time, lf.coin)]]
        base = L.matched(ev, pool, k=3)
        parts.append((ev.assign(side=1, gross=ev.f6)[COLS], base.assign(side=1, gross=base.f6)[COLS]))
    e = pd.concat([p[0] for p in parts]); b = pd.concat([p[1] for p in parts])
    L.card("O1d_reset50_long_4h", e, sample, b, note="long 24 h after 4h RSI14 falls through 50 from > 70 (within 20 bars); base = same coin, same trailing 14-bar return decile")


def ladder(sample):
    lo, hi = L.SAMPLES[sample]
    f = pd.read_parquet(ROOT / "data/is3/e2_k-30.parquet")
    f = f[(f.time >= lo) & (f.time < hi)]
    r1 = O.rsi(data.load_panel("bnall", "1d")["close"]).shift(1)
    f["rsi_d"] = [r1[cn].get(dy, np.nan) if cn in r1.columns else np.nan for cn, dy in zip(f.coin, f.day)]
    f = f.dropna(subset=["rsi_d"])
    ev, base = f[f.rsi_d >= 50], f[f.rsi_d < 50]
    L.card("O1e_ladder_rsi50", ev.assign(side=1, gross=ev.h60)[COLS], sample, base.assign(side=1, gross=base.h60)[COLS],
           note="ladder fills (T1k30 one bar late) h60 when the coin's prior-day daily RSI14 >= 50; base = fills with RSI < 50")


if __name__ == "__main__":
    {"reset50": reset50, "ladder": ladder}[sys.argv[1]](sys.argv[2])
