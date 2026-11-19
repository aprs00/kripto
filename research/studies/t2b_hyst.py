"""T2b(e) listing_short liquidity hysteresis (2026-11-19). Fixed configs, evaluate lines tagged t2be (not a walk-forward).

  nice -n 19 .venv/bin/python -m research.studies.t2b_hyst explore     # bnall, events/returns up to 2023-06-30 only
  nice -n 19 .venv/bin/python -m research.studies.t2b_hyst confirm     # bnall 2023-07-01 on + HL in full (run only after the rule is written)

Variants (enter_mult, stay_mult) x min_dv 1M: A base (1, 1), B hysteresis (1, 0.5), C entry floor (2, 1), D hold-through (1, 0).
Churn = re-entries: a coin's short switched on again after the liquidity rule switched it off inside its holding window.
The backtest charges 21 bp at dv $1M; live XTEN paid 60 bp in, 22 out, so threshold churn is UNDER-charged here.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from kripto import data, metrics as mx, research as R, strategies as st

SPLIT = "2023-07-01"
BASE = {"skip_days": 1, "hold_days": 60, "min_dv": 1e6}
VARIANTS = {"A base": (1.0, 1.0), "B hyst 0.5": (1.0, 0.5), "C enter 2x": (2.0, 1.0), "D hold-through": (1.0, 0.0)}


def churn(panel, lo, hi):
    """Entries per event coin from the raw (pre-hedge) eligibility pattern of each variant, events starting in [lo, hi)."""
    out = {}
    for name, (em, sm) in VARIANTS.items():
        w = st.REGISTRY["listing_short"](panel, **BASE, enter_mult=em, stay_mult=sm, beta_neutral=False)
        on = (w.fillna(0) < 0)
        first = on.idxmax().where(on.any())
        keep = [c for c in on.columns if pd.notna(first[c]) and (lo is None or first[c] >= pd.Timestamp(lo, tz="UTC"))
                and (hi is None or first[c] < pd.Timestamp(hi, tz="UTC"))]
        o = on[keep]
        entries = (o & ~o.shift(1, fill_value=False)).sum()
        out[name] = (len(keep), float((entries >= 2).mean()) if len(keep) else np.nan, float(entries.mean()) if len(keep) else np.nan,
                     float(o.sum().mean()) if len(keep) else np.nan)
    return out


def perf(panel, ds, lo, hi):
    for name, (em, sm) in VARIANTS.items():
        res, _ = R.evaluate("listing_short", panel, {**BASE, "enter_mult": em, "stay_mult": sm}, ds, tag="t2be")
        sel = pd.Series(True, res.returns.index)
        if lo:
            sel &= res.returns.index >= lo
        if hi:
            sel &= res.returns.index < hi
        first = res.gross[res.gross > 0].index.min()
        sel &= res.returns.index >= first
        r = res.returns[sel]
        ppy = mx.periods_per_year(r.index)
        yrs = len(r) / ppy
        sr = r.mean() / r.std() * np.sqrt(ppy)
        eq = (1 + r).cumprod()
        print(f"   {name:16s} SR {sr:+.2f}  ret/yr {r.mean() * ppy:+.1%}  cost/yr {res.costs[sel].sum() / yrs:.2%}  "
              f"turn/yr {res.turnover[sel].sum() / yrs:5.1f}  fund/yr {res.funding[sel].sum() / yrs:+.2%}  mdd {(eq / eq.cummax() - 1).min():.1%}")


def main(mode):
    if mode == "explore":
        samples = [("bnall", "1d", None, SPLIT)]
    else:
        samples = [("bnall", "1d", SPLIT, None), ("hl", "1d", None, None)]
    for ds, iv, lo, hi in samples:
        p = data.load_panel(ds, iv)
        print(f"== {ds} {iv} {lo or 'start'} .. {hi or 'end'}")
        for name, (n, share2, ent, days) in churn(p, lo, hi).items():
            print(f"   {name:16s} events {n:4d}  share with >=2 entries {share2:.1%}  entries/event {ent:.2f}  short days/event {days:.1f}")
        perf(p, f"{ds}_{iv}", lo, hi)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "explore")
