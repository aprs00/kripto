"""InSilico pass 3, FLQ: flow (lookback 3, cap .05) on the top-10 instead of the top-30 by volume. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_flq a     # explore 2021-23 -> research/is3/flq_a.json
  nice -n 19 .venv/bin/python -m research.studies.is3_flq b     # ONE run 2024-26 (weak confirm) -> research/is3/flq_b.json
"""
from __future__ import annotations

import json
import sys

import numpy as np

from kripto import backtest as bt
from kripto import data
from kripto import strategies as S
from kripto.research import default_band

sr = lambda x: round(float(x.mean() / x.std() * np.sqrt(365)), 2)


def run(lo, hi, tag):
    p = data.load_panel("bnall", "1d")
    slip = bt.slippage_model(p["volume"], 1)
    out = {}
    for n in (30, 10):
        r = bt.run(S.REGISTRY["flow"](p, lookback=3, cap=0.05, top_n=n), p["close"], p["funding"], slip, band=default_band())
        x = r.returns.loc[lo:hi]
        out[f"top{n}"] = {"sr": sr(x), "net_yr": round(float(x.mean() * 365), 3), "cost_yr": round(float(r.costs.loc[lo:hi].mean() * 365), 3),
                          "funding_yr": round(float(r.funding.loc[lo:hi].mean() * 365), 3), "by_year": {int(y): sr(g) for y, g in x.groupby(x.index.year)}}
    a, b = out["top10"], out["top30"]
    out["PASS"] = bool(a["sr"] > b["sr"] and sum(a["by_year"][y] > b["by_year"][y] for y in a["by_year"]) >= 2)
    print(json.dumps(out, indent=1))
    json.dump(out, open(f"research/is3/flq_{tag}.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": lambda: run("2021-01-01", "2023-12-31", "a"), "b": lambda: run("2024-01-01", "2026-12-31", "b")}[sys.argv[1]]()
