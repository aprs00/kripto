"""InSilico pass 3, OVL: main, main_bn, main@pair together. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_ovl ab   # -> research/is3/ovl_ab.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data
from kripto import paper as P
from research.studies.is3_ksw import book_returns

sr = lambda x: round(float(x.mean() / x.std() * np.sqrt(365)), 2)
mdd = lambda x: round(float(((1 + x).cumprod() / (1 + x).cumprod().cummax() - 1).min()), 3)


def run_ab():
    R = pd.DataFrame(book_returns()).loc["2023-05-26":"2026-10-31"].dropna()
    out = {"days": int(len(R)), "corr_all": R.corr().round(2).to_dict(), "corr_by_year": {int(y): g.corr().round(2).to_dict() for y, g in R.groupby(R.index.year)}}
    for k in R:
        w = R[k].nsmallest(20).index
        out[f"worst20_of_{k}"] = {j: round(float(R.loc[w, j].mean()), 4) for j in R}
    combos = {"main+main_bn": R[["main (HL)", "main_bn"]].mean(axis=1), "all3": R.mean(axis=1)}
    out["alone"] = {k: {"sr": sr(R[k]), "mdd": mdd(R[k])} for k in R}
    out["combined_equal_capital"] = {k: {"sr": sr(v), "mdd": mdd(v)} for k, v in combos.items()}
    # live coin overlap today: same coin, same sign, main vs main_bn
    s = P.Store()
    pos = pd.DataFrame(s.q("select book, coin, size from positions where book in ('main','main_bn') and size != 0"), columns=["book", "coin", "size"])
    a = pos[pos.book == "main"].set_index("coin")["size"]
    b = pos[pos.book == "main_bn"].set_index("coin")["size"]
    from kripto import data as D
    b.index = [c for c in b.index]
    hlnames = {D.hl_to_bn(c): c for c in a.index}
    common = [c for c in b.index if c in hlnames]
    same = [c for c in common if np.sign(a[hlnames[c]]) == np.sign(b[c])]
    out["live_overlap"] = {"main_coins": int(len(a)), "main_bn_coins": int(len(b)), "common": len(common), "same_sign": same}
    print(json.dumps(out, indent=1))
    json.dump(out, open("research/is3/ovl_ab.json", "w"), indent=1)


if __name__ == "__main__":
    {"ab": run_ab}[sys.argv[1]]()
