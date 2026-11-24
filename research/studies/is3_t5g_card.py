"""T5g pre-registered form: 1-h falls >= 2 sigma on RISING open interest continue. Short (continuation) 5 min after the hour,
hold 4 h, taker. Event: side == 1 (a fall) and doi_z >= 0.59 (explore top quintile, fixed). Baseline: same coin, same z bin,
falls with -2.2 < doi_z < 0.59 (explore middle three quintiles), 3 per event.
confirmC = coins with 1-min klines outside COINS10 that have data/bn/metrics_full OI (any dates 2021-2025 it covers);
confirmT = COINS10 2024-25 once metrics_full covers it (it did not on 2026-11-24).

    nice -n 19 .venv/bin/python -m research.studies.is3_t5g_card explore | confirmC | confirmT
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

import pandas as pd

from research.studies import is3_lib as L
from research.studies import is3_t5g as G

ROOT = Path(__file__).resolve().parents[2]
NAME, THR, MID = "T5g_fall_oiup_short_4h", 0.59, (-2.2, 0.59)


def card(e: pd.DataFrame, sample: str) -> dict:
    x = e[e.side == 1].assign(m=lambda d: pd.cut(d.z, [2, 2.5, 3, 4, 1e9], labels=False, right=False))
    ev = x[x.doi_z >= THR].assign(side=-1, gross=lambda d: -d.f240)
    pool = x[(x.doi_z > MID[0]) & (x.doi_z < MID[1])].assign(side=-1, gross=lambda d: -d.f240)
    cols = ["time", "coin", "side", "gross"]
    return L.card(NAME, ev[cols], sample, L.matched(ev, pool, k=3)[cols],
                  note=f"short 4 h after a >= 2 sigma 1-h fall with OI up >= {THR} sigma; base = same-coin falls with middle OI change")


def build_other(out: Path, coins: list[str]) -> pd.DataFrame:
    parts = []
    for c in coins:
        t = pd.read_parquet(ROOT / "data/bn/metrics_full" / f"{c}USDT.parquet", columns=["t"]).t
        t = t[t < pd.Timestamp("2026-01-01", tz="UTC")]
        if len(t) < 288 * 60:
            continue
        lo = (t.min() + pd.Timedelta("31D")).strftime("%Y-%m-%d")
        hi = min(t.max(), pd.Timestamp("2026-01-01", tz="UTC")).strftime("%Y-%m-%d")
        parts.append(G.events(G.panel([c], lo, hi, "data/bn/metrics_full"), lo, hi))
    e = pd.concat(parts, ignore_index=True)
    e.to_parquet(out)
    print(len(e), e.coin.nunique())
    return e


def main(sample: str) -> None:
    if sample == "explore":
        e = pd.read_parquet(G.TAB)
    else:
        if NAME not in L.committed_prereg():
            raise SystemExit("pre-register and commit first")
        if sample == "confirmC":
            have = {os.path.basename(f)[:-12] for f in glob.glob(str(ROOT / "data/bn/klines_1m/*USDT.parquet"))}
            coins = sorted(c for c in have - set(L.COINS10) if (ROOT / "data/bn/metrics_full" / f"{c}USDT.parquet").exists())
            e = build_other(ROOT / "data/is3/t5g_confirmC.parquet", coins)
        else:
            raise SystemExit("confirmT needs COINS10 metrics for 2024-25 (not on the server yet)")
    card(e, sample)


if __name__ == "__main__":
    main(sys.argv[1])
