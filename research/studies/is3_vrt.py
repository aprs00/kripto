"""InSilico pass 3, VRT: route each leg of the HL main book to the venue with cheaper funding. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_vrt a    # funding paid always-HL vs always-BN vs routed (trailing 7-d) -> research/is3/vrt_a.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data
from kripto import strategies as S

COMPS = {"listing_short": {}, "lowvol": {}, "tsmom": {}}


def run_a():
    hl = data.load_panel("hl", "1d")
    w = S.REGISTRY["blend"](hl, components=COMPS).ffill().fillna(0.0)
    pr = data.load_panel("pair", "1d")
    fp = pr["funding"]
    both = [c for c in w.columns if f"{c}@hl" in fp.columns and f"{c}@bn" in fp.columns]
    idx = w.index.intersection(fp.index)
    idx = idx[idx >= pd.Timestamp("2023-05-15", tz="UTC")]
    wl = w.shift(1).reindex(index=idx).fillna(0.0)
    fh = fp[[f"{c}@hl" for c in both]].set_axis(both, axis=1).reindex(idx)
    fb = fp[[f"{c}@bn" for c in both]].set_axis(both, axis=1).reindex(idx)
    ok = fh.notna() & fb.notna()
    W = wl[both].where(ok, 0.0)
    cov = float(W.abs().sum(axis=1).sum() / wl.abs().sum(axis=1).sum())
    pay_hl = -(W * fh.fillna(0)).sum(axis=1)           # + = received
    pay_bn = -(W * fb.fillna(0)).sum(axis=1)
    # routed by trailing 7-d funding (known at the decision close): long -> venue with LOWER f7, short -> venue with HIGHER f7
    f7h, f7b = fh.rolling(7, min_periods=3).mean().shift(1), fb.rolling(7, min_periods=3).mean().shift(1)
    use_bn = ((W > 0) & (f7b < f7h)) | ((W < 0) & (f7b > f7h))
    routed = -(W * fh.fillna(0)).where(~use_bn, 0).sum(axis=1) - (W * fb.fillna(0)).where(use_bn, 0).sum(axis=1)
    switches = (use_bn.astype(int).diff().abs() * W.abs()).sum(axis=1)       # notional that would move venue (each = 2 extra trades)
    out = {"coverage_share_of_gross": round(cov, 3), "by_year": {}}
    for y in sorted(set(idx.year)):
        yy = str(y)
        out["by_year"][y] = {"recv_always_hl_pct": round(float(pay_hl.loc[yy].sum()) * 100, 2), "recv_always_bn_pct": round(float(pay_bn.loc[yy].sum()) * 100, 2),
                             "recv_routed_pct": round(float(routed.loc[yy].sum()) * 100, 2), "share_on_bn": round(float((W.abs().where(use_bn, 0)).loc[yy].sum().sum() / W.abs().loc[yy].sum().sum()), 2),
                             "switch_notional_x": round(float(switches.loc[yy].sum()), 1), "days": int(len(pay_hl.loc[yy]))}
    yrs = len(idx) / 365
    out["per_year_avg"] = {"always_hl": round(float(pay_hl.sum() / yrs) * 100, 2), "always_bn": round(float(pay_bn.sum() / yrs) * 100, 2), "routed": round(float(routed.sum() / yrs) * 100, 2),
                           "switch_notional_x_per_yr": round(float(switches.sum() / yrs), 1)}
    # by leg (long / short), always-HL vs always-BN
    for side, m in (("long", W > 0), ("short", W < 0)):
        out[f"{side}_recv_hl_vs_bn_pct_yr"] = [round(float(-(W.where(m, 0) * fh.fillna(0)).sum().sum() / yrs) * 100, 2),
                                               round(float(-(W.where(m, 0) * fb.fillna(0)).sum().sum() / yrs) * 100, 2)]
    print(json.dumps(out, indent=1))
    json.dump(out, open("research/is3/vrt_a.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": run_a}[sys.argv[1]]()
