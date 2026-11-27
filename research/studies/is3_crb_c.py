"""InSilico pass 3, CRB c: F0 filter. Drop coin-days in the top |7-d funding| decile of the top-30 universe from carry / carry_trend (pre-stated in notes before any CRB run);
bnall 1d explore (<= 2023) vs 200 random masks. PASS = dSR > 0 at >= 95th pct AND dSR > 0 in 2021, 2022, 2023 (checked from the saved series by the caller).

  systemd-run --user --unit is3-crbc ... -m research.studies.is3_crb_c
"""
from __future__ import annotations

import json

import numpy as np

from kripto import strategies as S
from research.studies import is3_filter as F

if __name__ == "__main__":
    out = {}
    for name in ("carry", "carry_trend"):
        w, panel, slip = F.book(name, "bnall", {})
        f7 = panel["funding"].rolling(7, min_periods=1).mean()
        uni = S.universe(panel, 30) & f7.notna()
        pct = f7.abs().where(uni).rank(axis=1, pct=True)
        mask = ~(pct > 0.9)                       # True = allowed; known at the close (weights of bar t use the mask of bar t)
        r = F.judge(f"CRBc_{name}", w, panel, slip, mask, "explore", note="drop top |7-d funding| decile of the top-30 universe")
        base = F.cut(F.run(w, panel, slip), "explore")
        filt = F.cut(F.run(F.apply(w, mask), panel, slip), "explore")
        sr = lambda x: float(x.mean() / x.std() * np.sqrt(365))
        r["dSR_by_year"] = {int(y): round(sr(filt[filt.index.year == y]) - sr(base[base.index.year == y]), 3) for y in (2021, 2022, 2023)}
        r["PASS_full_rule"] = bool(r["passes"] and all(v > 0 for v in r["dSR_by_year"].values()))
        out[name] = r
        print(name, r["dSR_by_year"], r["PASS_full_rule"], flush=True)
        del w, panel, slip
    json.dump(out, open("research/is3/crb_c.json", "w"), indent=1, default=float)
