"""InSilico pass 3, PRB: the HL main book (blend of listing_short, lowvol, tsmom; what live trades) with partial rebalancing
w_t = w_{t-1} + lam (target_t - w_{t-1}) vs lam = 1. Pre-stated in notes.md. python -m research.studies.is3_prb [a|b]"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY

COMP = {"components": {"listing_short": {}, "lowvol": {}, "tsmom": {}}}
BAND = 0.005


def partial(w: pd.DataFrame, lam: float) -> pd.DataFrame:
    T = w.fillna(0.0).to_numpy()
    out = np.zeros_like(T)
    prev = np.zeros(T.shape[1])
    for t in range(len(T)):
        prev = prev + lam * (T[t] - prev)
        out[t] = prev
    return pd.DataFrame(out, w.index, w.columns)


def summary(res, lo, hi):
    ix = (res.returns.index >= pd.Timestamp(lo, tz="UTC")) & (res.returns.index < pd.Timestamp(hi, tz="UTC"))
    r = res.returns[ix]
    o = {"sr": float(r.mean() / r.std() * np.sqrt(365)), "ann": float(r.mean() * 365), "days": int(ix.sum()),
         "worst10_mean": float(r.nsmallest(10).mean())}
    for k in ("costs", "funding", "turnover", "gross"):
        s = getattr(res, k, None)
        if isinstance(s, pd.Series):
            o[k + "_ann"] = float(s[ix].mean() * 365)
    g = r + res.costs[ix]
    o["sr_pre_cost"] = float(g.mean() / g.std() * np.sqrt(365))
    eq = (1 + r).cumprod()
    o["mdd"] = float((eq / eq.cummax() - 1).min())
    return o


if __name__ == "__main__":
    form = sys.argv[1] if len(sys.argv) > 1 else "a"
    panel = data.load_panel("hl", "1d")
    w = REGISTRY["blend"](panel, **COMP)
    slip = bt.slippage_model(panel["volume"], bars_per_day(panel["close"].index))
    lams = (1.0, 0.5, 0.33) if form == "a" else (1.0, float(sys.argv[2]))
    win = {"a": [("2023-01-01", "2024-01-01"), ("2024-01-01", "2025-01-01"), ("2023-01-01", "2025-01-01")],
           "b": [("2025-01-01", "2026-01-01"), ("2026-01-01", "2027-01-01"), ("2025-01-01", "2027-01-01")]}[form]
    out = {}
    for lam in lams:
        res = bt.run(partial(w, lam), panel["close"], panel.get("funding"), slip, band=BAND)
        out[str(lam)] = {f"{lo[:4]}-{hi[:4]}": summary(res, lo, hi) for lo, hi in win}
        print(lam, json.dumps({k: {a: round(b, 4) for a, b in v.items()} for k, v in out[str(lam)].items()}), flush=True)
    json.dump(out, open(f"research/is3/prb_{form}.json", "w"), indent=1)
