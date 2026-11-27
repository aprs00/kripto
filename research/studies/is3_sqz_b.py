"""InSilico pass 3, SQZ b: F0 on the bnall listing_short book: block shorts whose price is >= 43.3 % above the post-listing low (pre-stated in notes). Unit is3-sqzb."""
from __future__ import annotations

import json

import numpy as np

from kripto import strategies as S
from research.studies import is3_filter as F

if __name__ == "__main__":
    w, panel, slip = F.book("listing_short", "bnall", {})
    c, v = panel["close"], panel["volume"]
    traded = (v.fillna(0) > 0) & c.notna()
    age = traded.cummax().cumsum()
    off_low = c / c.where(age >= 2).cummin() - 1
    mask = ~(off_low >= 0.433)
    mask["BTC"] = True
    r = F.judge("SQZb", w, panel, slip, mask, "explore", side=-1, note="block shorts >= 43.3 % above the post-listing low")
    base = F.cut(F.run(w, panel, slip), "explore")
    filt = F.cut(F.run(F.apply(w, mask, -1), panel, slip), "explore")
    sr = lambda x: float(x.mean() / x.std() * np.sqrt(365))
    r["dSR_by_year"] = {int(y): round(sr(filt[filt.index.year == y]) - sr(base[base.index.year == y]), 3) for y in (2021, 2022, 2023)}
    r["PASS_full_rule"] = bool(r["passes"] and all(x > 0 for x in r["dSR_by_year"].values()))
    print(r["dSR_by_year"], r["PASS_full_rule"], flush=True)
    json.dump(r, open("research/is3/sqz_b.json", "w"), indent=1, default=float)
