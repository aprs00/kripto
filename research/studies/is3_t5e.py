"""T5e: up-spikes continue. Long at the close one bar after a 1-min UP move >= 8 x 24-h sigma that is NOT alone (at least one
other coin of the build universe moved >= 3 sigma up in the same minute), exit at market 60 min later (taker).
Baseline = same-coin up moves of 3-5 sigma (any breadth), same 60-min long, 3 per event (is3_lib.matched).
Explore = data/is3/t5a.parquet (COINS10 2021-23). Confirm samples are built here, once each, after the committed prereg:
  confirmT = COINS10 2024-2025, confirmC = the other 73 lshock coins 2021-2025 (breadth counted among those 73).

    nice -n 19 .venv/bin/python -m research.studies.is3_t5e explore | confirmT | confirmC
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from research.studies import is3_lib as L
from research.studies import is3_t5a as A

ROOT = Path(__file__).resolve().parents[2]
NAME, ZMIN, BMIN = "T5e_upspike_z8_b2_h60", 8.0, 2


def card(e: pd.DataFrame, sample: str) -> dict:
    ev = e[(e.dirq == 1) & (e.z >= ZMIN) & (e.breadth >= BMIN)].assign(side=1, gross=lambda d: -d.f60, m=0)
    pool = e[(e.dirq == 1) & (e.z >= 3) & (e.z < 5)].assign(side=1, gross=lambda d: -d.f60, m=0)
    cols = ["time", "coin", "side", "gross"]
    return L.card(NAME, ev[cols], sample, L.matched(ev, pool, k=3)[cols],
                  note=f"long 60 min after a >= {ZMIN:g} sigma up minute with breadth >= {BMIN}; base = same-coin 3-5 sigma up moves")


def main(sample: str) -> None:
    if sample == "explore":
        e = pd.read_parquet(A.TAB)
    else:
        if NAME not in L.committed_prereg():
            raise SystemExit("pre-register and commit first")
        if sample == "confirmT":
            e = A.build(L.COINS10, "2024-01-01", "2026-01-01", ROOT / "data/is3/t5a_confirmT.parquet")
        else:
            coins = sorted(set(pd.read_parquet(ROOT / "data/is3/lshock.parquet", columns=["coin"]).coin) - set(L.COINS10))
            e = A.build(coins, "2021-01-01", "2026-01-01", ROOT / "data/is3/t5a_confirmC.parquet")
    card(e, sample)


if __name__ == "__main__":
    main(sys.argv[1])
