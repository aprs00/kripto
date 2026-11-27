"""InSilico pass 3, HLU1: block BN-only (not listed on HL that day) shorts in the Binance books (from LVH). F0 harness. NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_hlu1 a            # descriptive, hlu_explore -> research/is3/hlu1_a.json
  nice -n 19 .venv/bin/python -m research.studies.is3_hlu1 b            # F0 judge per book on hlu_explore -> research/is3/hlu1_b.json
  nice -n 19 .venv/bin/python -m research.studies.is3_hlu1 c <book>..   # ONE confirm on hlu_confirm (pre-registered HLU1c_<book>)
  nice -n 19 .venv/bin/python -m research.studies.is3_hlu1 d            # funding-extreme alternative (f7 < -0.5 ann.), hlu_explore
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data
from research.studies import is3_filter as F
from research.studies import is3_lib as L

BOOKS = {"flow": ("flow", {"lookback": 3, "cap": 0.05}), "xsmom": ("xsmom", {}),
         "blend": ("blend", {"components": {"carry_trend": {}, "carry": {}, "xsmom": {}}})}


def hl_on(bn_close):
    hl = data.load_panel("hl", "1d")["close"].notna()
    on = pd.DataFrame(False, bn_close.index, bn_close.columns)
    for col in bn_close.columns:
        hc = "k" + col[4:] if col.startswith("1000") else col
        if hc in hl.columns:
            on[col] = hl[hc].reindex(bn_close.index).fillna(False).astype(bool)
    return on


def yr_dsr(w, panel, slip, mask, side, years):
    b, f = F.run(w, panel, slip), F.run(F.apply(w, mask, side), panel, slip)
    out = {}
    for y in years:
        bb, ff = b[b.index.year == y], f[f.index.year == y]
        out[int(y)] = round(float(ff.mean() / ff.std() * np.sqrt(365) - bb.mean() / bb.std() * np.sqrt(365)), 3)
    return out


def run_a():
    lo, hi = (pd.Timestamp(x, tz="UTC") for x in L.SAMPLES["hlu_explore"])
    out = {}
    on = None
    for nm, (s, prm) in BOOKS.items():
        w, panel, slip = F.book(s, "bnall", prm)
        if on is None:
            on = hl_on(panel["close"])
        c = panel["close"]
        wl = w.ffill().fillna(0.0).shift(1).fillna(0.0)
        r = (c / c.shift(1) - 1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        f = panel["funding"].fillna(0.0)
        sel = (c.index >= lo) & (c.index < hi)
        W, R, Fd, O = wl[sel], r[sel], f[sel], on[sel]
        res = {}
        for lab, m in (("HL_listed", O), ("BN_only", ~O)):
            sm = m & (W < 0)
            ex = W.abs().where(sm, 0).sum().sum()
            res[lab] = {"short_exposure_share": round(float(ex / W.abs().where(W < 0, 0).sum().sum()), 3),
                        "price_per_unit_yr": round(float((W * R).where(sm, 0).sum().sum() / ex * 365), 3) if ex else None,
                        "funding_per_unit_yr": round(float((-W * Fd).where(sm, 0).sum().sum() / ex * 365), 3) if ex else None,
                        "by_year_pnl": {int(y): round(float(v.sum()), 4) for y, v in ((W * R - W * Fd).where(sm, 0).sum(axis=1)).groupby(W.index.year)}}
        out[nm] = res
        print(nm, json.dumps(res), flush=True)
    json.dump({"study": "research/studies/is3_hlu1.py a", **out}, open(L.OUT / "hlu1_a.json", "w"), indent=1)


def run_b(sample="hlu_explore", books=None, prefix="HLU1b", alt=False):
    out = {}
    on = None
    for nm in books or list(BOOKS):
        s, prm = BOOKS[nm]
        w, panel, slip = F.book(s, "bnall", prm)
        if alt:
            f7 = panel["funding"].rolling(7, min_periods=5).mean() * 365
            mask = ~(f7 < -0.5)
        else:
            on = hl_on(panel["close"]) if on is None else on
            mask = on
        res = F.judge(f"{prefix}_{nm}", w, panel, slip, mask, sample, side=-1, note=f"block shorts {'f7 < -0.5 ann' if alt else 'not listed on HL'} ({nm})")
        lo, hi = (pd.Timestamp(x, tz="UTC") for x in L.SAMPLES[sample])
        res["dSR_by_year"] = yr_dsr(w, panel, slip, mask, -1, range(lo.year, hi.year + (1 if hi.month > 1 or hi.day > 1 else 0)))
        print(nm, "dSR by year", res["dSR_by_year"], flush=True)
        out[nm] = res
        del w, panel, slip
    tag = prefix.lower()
    json.dump({"study": f"research/studies/is3_hlu1.py {prefix}", **out}, open(L.OUT / f"{tag}.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "a":
        run_a()
    elif a[0] == "b":
        run_b()
    elif a[0] == "c":
        run_b("hlu_confirm", a[1:], "HLU1c")
    elif a[0] == "d":
        run_b(prefix="HLU1d", alt=True)
