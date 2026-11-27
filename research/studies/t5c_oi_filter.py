"""T5c: frozen OI-build long-side filter (pre-registered in research/is3/prereg.json T5c_flow / T5c_xsmom, 2026-11-27) on flow@bn and xsmom@bn,
bnall 1d, sample confirm24 only. Also the per-year dropped-vs-kept next-day mean clause.

    nice -n 19 .venv/bin/python -m research.studies.t5c_oi_filter
"""
import json

import numpy as np
import pandas as pd

from research.studies import is3_filter as F
from research.studies import is3_lib as L
from research.studies import t5b_positioning as T

BOOKS = {"flow": {"lookback": 3, "cap": 0.05}, "xsmom": {"lookback": 28, "every_days": 1, "cap": 0.05}}


def mask_for(panel: dict, start="2023-12-01", end="2026-11-22") -> pd.DataFrame:
    close = panel["close"]
    dv = panel["volume"].rolling(30, min_periods=7).mean()
    member = dv.rank(axis=1, ascending=False) <= 60
    lo, hi = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
    syms = [c + "USDT" for c in member.columns[member.loc[lo:hi].any()]]
    m = T.daily_metrics(syms, start, end)
    oi = m["oi"].reindex(index=close.index, columns=close.columns)
    with np.errstate(divide="ignore", invalid="ignore"):
        doi = np.log(oi).diff(3).replace([np.inf, -np.inf], np.nan)
    r3 = close / close.shift(3) - 1
    cand = member & (r3 > 0) & doi.notna()
    q = doi.where(cand).rank(axis=1, pct=True)
    block = cand & (q > 2 / 3)
    return ~block


def main():
    out = {}
    for b, params in BOOKS.items():
        w, panel, slip = F.book(b, "bnall", params)
        mk = mask_for(panel)
        res = F.judge(f"T5c_{b}", w, panel, slip, mk, "confirm24", side=+1)
        fwd = panel["close"].pct_change(fill_method=None).shift(-1)
        longs = (w > 0)
        yr = {}
        for y in (2024, 2025, 2026):
            sel = (w.index.year == y) & (w.index >= pd.Timestamp("2024-01-01", tz="UTC"))
            dropped = fwd[sel].where(longs[sel] & ~mk.reindex_like(w).fillna(True)[sel].astype(bool)).stack().mean()
            kept = fwd[sel].where(longs[sel] & mk.reindex_like(w).fillna(True)[sel].astype(bool)).stack().mean()
            yr[y] = {"dropped_bp": round(float(dropped) * 1e4, 1), "kept_bp": round(float(kept) * 1e4, 1)}
        res["years"] = yr
        res["year_clause"] = sum(v["dropped_bp"] < v["kept_bp"] for v in yr.values()) >= 2
        res["passes_prereg"] = bool(res["dSR"] >= 0.1 and (res["pct_dSR_vs_random"] or 0) >= 0.9 and res["year_clause"])
        print(b, yr, "passes_prereg", res["passes_prereg"], flush=True)
        out[b] = res
    (L.OUT / "T5c__confirm24_summary.json").write_text(json.dumps(out, indent=1, default=float) + "\n")


if __name__ == "__main__":
    main()
