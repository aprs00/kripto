"""InSilico pass 3, CRS b: F0 on carry (bnall): block top-|funding|-decile longs whose funding is fading (f3/f7 < .443). Pre-stated in notes. Unit is3-crsb."""
from __future__ import annotations

import json

import numpy as np

from kripto import strategies as S
from research.studies import is3_filter as F

if __name__ == "__main__":
    w, panel, slip = F.book("carry", "bnall", {})
    f7 = panel["funding"].rolling(7, min_periods=1).mean()
    uni = S.universe(panel, 30) & f7.notna()
    pct = f7.abs().where(uni).rank(axis=1, pct=True)
    fa = panel["funding"].rolling(3, min_periods=1).mean() / f7.replace(0, np.nan)
    mask = ~((pct > 0.9) & (fa < 0.443))
    r = F.judge("CRSb", w, panel, slip, mask, "explore", side=1, note="block top-decile carry longs with fading funding (f3/f7 < .443)")
    base = F.cut(F.run(w, panel, slip), "explore")
    filt = F.cut(F.run(F.apply(w, mask, 1), panel, slip), "explore")
    sr = lambda x: float(x.mean() / x.std() * np.sqrt(365))
    r["dSR_by_year"] = {int(y): round(sr(filt[filt.index.year == y]) - sr(base[base.index.year == y]), 3) for y in (2021, 2022, 2023)}
    r["PASS_full_rule"] = bool(r["passes"] and all(x > 0 for x in r["dSR_by_year"].values()))
    print(r["dSR_by_year"], r["PASS_full_rule"], flush=True)
    json.dump(r, open("research/is3/crs_b.json", "w"), indent=1, default=float)
