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




def run_b():
    """Per HL listing (first traded day >= 2023-05-15, funding exists): short's abnormal price gain vs BTC (simple, compounded per leg) and funding received, days 1..H."""
    from kripto import strategies as S
    p = data.load_panel("hl", "1d")
    c, v, f = p["close"], p["volume"], p["funding"]
    traded = (v.fillna(0) > 0) & c.notna()
    first = traded.idxmax().where(traded.any())
    dv = S.dollar_volume(p)
    rows = []
    for coin, t0 in first.dropna().items():
        if coin == "BTC" or t0 < pd.Timestamp("2023-05-15", tz="UTC"):
            continue
        i0 = c.index.get_loc(t0) + 1
        if i0 + 2 >= len(c) or not (dv[coin].iloc[i0] >= 1e6):
            continue
        for h in (14, 30, 60, 90):
            j = i0 + h
            if j >= len(c) or not np.isfinite(c[coin].iloc[j]):
                continue
            short_px = -((c[coin].iloc[j] / c[coin].iloc[i0] - 1) - (c["BTC"].iloc[j] / c["BTC"].iloc[i0] - 1))
            fr = f[coin].iloc[i0 + 1: j + 1]
            rows.append({"coin": coin, "t0": t0, "h": h, "short_px": short_px, "funding": float(fr.sum()), "f_cov": float(fr.notna().mean())})
    d = pd.DataFrame(rows)
    d = d[d.f_cov >= 0.9]
    out = {}
    for h, g in d.groupby("h"):
        out[int(h)] = {"n": int(len(g)), "px_mean": round(float(g.short_px.mean()), 4), "px_median": round(float(g.short_px.median()), 4),
                       "fund_mean": round(float(g.funding.mean()), 4), "fund_median": round(float(g.funding.median()), 4),
                       "fund_share_neg": round(float((g.funding < 0).mean()), 2), "net_mean": round(float((g.short_px + g.funding).mean()), 4),
                       "net_median": round(float((g.short_px + g.funding).median()), 4),
                       "by_year": {int(y): [int(len(x)), round(float(x.short_px.mean()), 3), round(float(x.funding.mean()), 4)] for y, x in g.groupby(g.t0.dt.year)}}
        print(h, json.dumps(out[int(h)]), flush=True)
    # incremental windows: funding per day in d1-14 vs d15-30 vs d31-60 vs d61-90
    inc = {}
    for coin, t0 in d[["coin", "t0"]].drop_duplicates().itertuples(index=False):
        i0 = c.index.get_loc(t0) + 1
        for a, b in ((1, 14), (15, 30), (31, 60), (61, 90)):
            fr = f[coin].iloc[i0 + a: i0 + b + 1]
            if len(fr) == b - a + 1 and fr.notna().mean() >= 0.9:
                inc.setdefault(f"d{a}-{b}", []).append(float(fr.mean()) * 1e4)
    out["funding_bp_per_day_by_window"] = {k: [len(x), round(float(np.mean(x)), 2), round(float(np.median(x)), 2)] for k, x in inc.items()}
    print("funding received by the short, bp/day [n, mean, median]:", out["funding_bp_per_day_by_window"], flush=True)
    json.dump({"study": "research/studies/is3_ls1.py b", **out}, open("research/is3/ls1_b.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": run_a, "b": run_b}[sys.argv[1]]()
