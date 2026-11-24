"""N5 e: long at a new 20-bar low made on thin volume (< 24-bar median), hold 24 bars, COINS10 1h / 4h, explore 2021-2023;
baseline = same coin, same trailing-14-bar return decile (3 matched bars). Per-year differences reported (pass3 §3 rule).

    nice -n 19 .venv/bin/python -m research.studies.is3_n5e    -> research/is3/N5e__explore.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
LO, HI = "2021-01-01", "2024-01-01"
COLS = ["time", "coin", "side", "gross"]


def main() -> dict:
    res = {}
    for tf in ("1h", "4h"):
        rows = []
        for coin in L.COINS10:
            m = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet", columns=["t", "l", "c", "qv"])
            m.index = pd.to_datetime(m.t, unit="ms", utc=True)
            m = m[(m.index >= "2020-11-01") & (m.index < "2024-02-01")]
            c = m.c.resample(tf).last().ffill(); v = m.qv.resample(tf).sum(); l = m.l.resample(tf).min()
            ev = (l < l.shift(1).rolling(20).min()) & (v < v.rolling(24).median().shift(1))
            x = pd.DataFrame({"time": c.index, "coin": coin, "ev": ev.to_numpy(), "ret14": (c / c.shift(14) - 1).to_numpy(), "f24": (c.shift(-24) / c - 1).to_numpy()})
            rows.append(x[(x.time >= LO) & (x.time < HI)].dropna())
        x = pd.concat(rows)
        x["m"] = (x.groupby("coin").ret14.rank(pct=True) * 9.999).astype(int)
        e, pool = x[x.ev.astype(bool)], x[~x.ev.astype(bool)]
        base = L.matched(e, pool, k=3)
        s = L.stats(e.assign(side=1, gross=e.f24)[COLS], base.assign(side=1, gross=base.f24)[COLS], reps=1000)
        yd = {}
        for y in (2021, 2022, 2023):
            ey, by = e[e.time.dt.year == y], base[base.time.dt.year == y]
            sy = L.stats(ey.assign(side=1, gross=ey.f24)[COLS], by.assign(side=1, gross=by.f24)[COLS], reps=300)
            yd[y] = {"n": sy["n"], "diff_bp": sy["vs_base_bp"], "p": sy["p_vs_base"]}
        res[tf] = {"n": s["n"], "mean_bp": s["mean_bp"], "matched_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"],
                   "ex_top3_bp": s["mean_ex_top3_bp"], "diff_by_year": yd}
        print(tf, res[tf])
    (ROOT / "research/is3/N5e__explore.json").write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    main()
