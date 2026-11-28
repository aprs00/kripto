"""InSilico pass 3, CPB: per-coin band .02 (update to target only when |target - held| > .02) on flow@bn / blend_bn, cached bnall. python -m research.studies.is3_cpb a|b <pickle> [books]"""
import json, pickle, sys
import numpy as np, pandas as pd
from kripto import backtest as bt
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY
from research.studies.is3_prb import summary
from research.studies.is3_tsb import banded

BOOKS = {"flow_bn": lambda p: REGISTRY["flow"](p, lookback=3, cap=0.05),
         "blend_bn": lambda p: REGISTRY["blend"](p, components={"carry_trend": {}, "carry": {}, "xsmom": {}})}

if __name__ == "__main__":
    form, pk = sys.argv[1], sys.argv[2]
    names = sys.argv[3].split(",") if len(sys.argv) > 3 else list(BOOKS)
    p = pickle.load(open(pk, "rb"))
    slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
    yrs = (2021, 2022, 2023) if form == "a" else (2024, 2025, 2026)
    out = {}
    for nm in names:
        w0 = BOOKS[nm](p).fillna(0.0)
        for k, w in (("base", w0), ("band02", banded(w0, 0.02))):
            r = bt.run(w, p["close"], p.get("funding"), slip, band=0.005)
            o = {str(y): summary(r, f"{y}-01-01", f"{y+1}-01-01") for y in yrs}
            o["all"] = summary(r, f"{yrs[0]}-01-01", f"{yrs[-1]+1}-01-01")
            tr = r.weights.diff().abs().to_numpy().ravel(); tr = tr[tr > 1e-9]
            o["share_trades_below_5usd_at_1000"] = float((tr * 1000 < 5).mean())
            out[f"{nm}_{k}"] = o
            print(nm, k, {y: (round(x["sr"], 3), round(x["costs_ann"], 4), round(x["sr_pre_cost"], 3)) for y, x in o.items() if isinstance(x, dict)}, round(o["share_trades_below_5usd_at_1000"], 3), flush=True)
    json.dump(out, open(f"research/is3/cpb_{form}.json", "w"), indent=1)
