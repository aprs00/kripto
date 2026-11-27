"""InSilico pass 3, TFF: tsmom HL long coin-days by HL 7-d funding quintile: next-day price P&L vs funding paid. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_tff a    # hlu_explore -> research/is3/tff_a.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data
from kripto import strategies as S


def run_a():
    p = data.load_panel("hl", "1d")
    c = p["close"]
    ret = (c / c.shift(1) - 1).replace([np.inf, -np.inf], np.nan)
    fund = p["funding"].reindex(index=c.index, columns=c.columns)
    f7 = p["funding"].rolling(7, min_periods=3).mean()
    w = S.REGISTRY["tsmom"](p).ffill().fillna(0.0)
    wl = w.shift(1)
    lo, hi = "2023-04-01", "2024-12-31"
    longs = (wl > 0).loc[lo:hi]
    F = f7.shift(1).loc[lo:hi].where(longs)
    q = F.stack().rank(pct=True)
    st = pd.DataFrame({"f7": F.stack(), "w": wl.loc[lo:hi].where(longs).stack(), "r": ret.loc[lo:hi].where(longs).stack(), "f": fund.loc[lo:hi].where(longs).stack()}).dropna(subset=["f7", "w", "r"])
    st["f"] = st["f"].fillna(0.0)
    st["year"] = st.index.get_level_values(0).year
    st["q"] = st.groupby("year").f7.transform(lambda s: pd.qcut(s.rank(method="first"), 5, labels=False))
    out = {"n": int(len(st)), "by_year": {}, "thresholds_f7_q80_by_year": {}}
    for y, g in st.groupby("year"):
        out["thresholds_f7_q80_by_year"][int(y)] = round(float(g.f7.quantile(.8)), 6)
        out["by_year"][int(y)] = {int(k): {"price_bp": round(float((h.w * h.r).sum() / h.w.sum() * 1e4), 1), "funding_bp": round(float(-(h.w * h.f).sum() / h.w.sum() * 1e4), 1),
                                           "f7_ann_med": round(float(h.f7.median() * 365), 2), "n": int(len(h))} for k, h in g.groupby("q")}
        print(y, out["by_year"][int(y)], flush=True)
    out["thr_pooled_q80"] = round(float(st.f7.quantile(.8)), 6)
    json.dump(out, open("research/is3/tff_a.json", "w"), indent=1)
    print("thr", out["thr_pooled_q80"])


if __name__ == "__main__":
    {"a": run_a}[sys.argv[1]]()
