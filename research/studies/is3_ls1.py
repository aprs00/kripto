"""InSilico pass 3, LS1: listing_short (HL main blend leg) with the backfilled HL funding (backlog T2b a). Logged through research.evaluate (tag ls1).

  nice -n 19 .venv/bin/python -m research.studies.is3_ls1 a    # -> research/is3/ls1_a.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data, research
from kripto.strategies import REGISTRY


def sr(x):
    return float(x.mean() / x.std() * np.sqrt(365)) if x.std() > 0 else 0.0


def card(res, s):
    r = res.returns[res.gross.cumsum() > 0]
    f = res.funding.reindex(r.index).fillna(0)
    co = res.costs.reindex(r.index).fillna(0)
    out = {"sharpe": s.get("sharpe"), "start": str(r.index[0].date()), "n_days": int(len(r))}
    out["years"] = {int(y): {"sr": round(sr(x), 2), "ret": round(float(x.sum()), 4), "funding": round(float(f[x.index].sum()), 4), "costs": round(float(co[x.index].sum()), 4),
                             "price": round(float((x + co[x.index] - f[x.index]).sum()), 4)} for y, x in r.groupby(r.index.year)}
    top = r.nlargest(10)
    out["sr_wo_best10"] = round(sr(r.drop(top.index)), 2)
    out["best10_share"] = round(float(top.sum() / r.sum()), 2) if r.sum() != 0 else None
    out["sr_before_2024_07"] = round(sr(r[r.index < "2024-07-01"]), 2)
    out["sr_since_2024_07"] = round(sr(r[r.index >= "2024-07-01"]), 2)
    return out


def run_a():
    p = data.load_panel("hl", "1d")
    w = REGISTRY["listing_short"](p).ffill().fillna(0.0)
    f = p["funding"]
    short = (-w).clip(lower=0)
    cov_now = (short * f.notna()).sum(axis=1) / short.sum(axis=1)
    old = f.copy()
    old.loc[old.index < pd.Timestamp("2024-07-01", tz="UTC")] = np.nan
    cov_old = (short * old.notna()).sum(axis=1) / short.sum(axis=1)
    cov = pd.DataFrame({"now": cov_now, "old": cov_old}).dropna()
    covy = {int(y): [round(float(x.old.mean()), 3), round(float(x.now.mean()), 3)] for y, x in cov.groupby(cov.index.year)}
    tot_old = float(((short * old.notna()).sum().sum()) / short.sum().sum())
    tot_now = float(((short * f.notna()).sum().sum()) / short.sum().sum())
    print("short exposure with funding (old -> now), by year:", covy, "| total", round(tot_old, 3), "->", round(tot_now, 3), flush=True)
    res, s = research.evaluate("listing_short", p, {}, "hl", tag="ls1_full_funding")
    full = card(res, s)
    p2 = dict(p, funding=old)
    res2, s2 = research.evaluate("listing_short", p2, {}, "hl", tag="ls1_funding_masked_pre2024-07")
    masked = card(res2, s2)
    fragile = full["sr_wo_best10"] < 0.3 or full["sr_before_2024_07"] < 0
    out = {"coverage_by_year_old_now": covy, "coverage_total_old_now": [round(tot_old, 3), round(tot_now, 3)], "full": full, "masked_like_before": masked, "FRAGILE": fragile}
    print(json.dumps(out, indent=1), flush=True)
    json.dump({"study": "research/studies/is3_ls1.py a", **out}, open("research/is3/ls1_a.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": run_a}[sys.argv[1]]()
