"""InSilico pass 3, BNH: HL main book (blend of listing_short, lowvol, tsmom) dependence on its lowvol leg. Descriptive.

  nice -n 19 .venv/bin/python -m research.studies.is3_bnh a    # full vs leave-one-out (research.evaluate, tag bnh), by year; attribution with the blend's scale -> research/is3/bnh_a.json
  nice -n 19 .venv/bin/python -m research.studies.is3_bnh b    # lowvol legs (long/short), price vs funding, by year, top-5 coin share -> research/is3/bnh_b.json
  nice -n 19 .venv/bin/python -m research.studies.is3_bnh c    # nested selection without 2025 (panel cut 2024-12-31) and the choice log -> research/is3/bnh_c.json
"""
from __future__ import annotations

import inspect
import json
import sys

import numpy as np
import pandas as pd

from kripto import data, research
from kripto import strategies as S

COMPS = {"listing_short": {}, "lowvol": {}, "tsmom": {}}
sr = lambda x: float(x.mean() / x.std() * np.sqrt(365)) if len(x) > 20 and x.std() > 0 else float("nan")


def invested(res):
    return res.returns[res.returns.index >= res.gross[res.gross > 0].index.min()]


def byyear(r):
    return {int(y): {"sr": round(sr(x), 2), "ret": round(float(x.sum()), 4)} for y, x in r.groupby(r.index.year)}


def run_a():
    p = data.load_panel("hl", "1d")
    out = {}
    runs = {"full": COMPS, **{f"no_{k}": {n: v for n, v in COMPS.items() if n != k} for k in COMPS}}
    for lab, comps in runs.items():
        res, s = research.evaluate("blend", p, {"components": comps}, "hl", tag="bnh")
        r = invested(res)
        top = r.nlargest(10)
        out[lab] = {"sharpe": round(s["sharpe"], 2), "start": str(r.index[0].date()), "years": byyear(r), "sr_wo_best10": round(sr(r.drop(top.index)), 2)}
        if lab == "full":
            full_r, full_top = r, top
    # attribution: blend weights = k_t * sum_i(w_i * unit/tv_i) / n; component part i = k_t * w_i * unit/tv_i / n
    c = p["close"]
    ret = (c / c.shift(1) - 1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    fund = p["funding"].reindex(index=c.index, columns=c.columns).fillna(0.0)
    parts = {}
    for n, prm in COMPS.items():
        tv = inspect.signature(S.REGISTRY[n]).parameters["target_vol"].default
        parts[n] = S._ffill_targets(S.REGISTRY[n](p, **prm)).reindex(columns=c.columns, fill_value=0.0).fillna(0.0) * (0.20 / tv) / len(COMPS)
    raw = sum(parts.values())
    wb = S.REGISTRY["blend"](p, components=COMPS).ffill().fillna(0.0).reindex(columns=c.columns, fill_value=0.0)
    k = (wb.abs().sum(axis=1) / raw.abs().sum(axis=1).replace(0, np.nan)).fillna(0.0)
    contrib = {}
    for n, w in parts.items():
        wl = w.mul(k, axis=0).shift(1).fillna(0.0)
        contrib[n] = ((wl * ret).sum(axis=1) - (wl * fund).sum(axis=1)).reindex(full_r.index)
    tot = sum(contrib.values())
    out["attribution_check_corr_vs_blend_gross"] = round(float(tot.corr(full_r)), 3)
    out["attribution_by_year"] = {int(y): {n: round(float(contrib[n][g.index].sum()), 4) for n in COMPS} for y, g in full_r.groupby(full_r.index.year)}
    out["attribution_total"] = {n: round(float(contrib[n].sum()), 4) for n in COMPS}
    out["lowvol_share_of_best10_days"] = round(float(contrib["lowvol"][full_top.index].sum() / tot[full_top.index].sum()), 2)
    out["best10_days"] = [str(d.date()) for d in full_top.index]
    print(json.dumps(out, indent=1))
    json.dump(out, open("research/is3/bnh_a.json", "w"), indent=1)


def run_b():
    p = data.load_panel("hl", "1d")
    c = p["close"]
    ret = (c / c.shift(1) - 1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    fund = p["funding"].reindex(index=c.index, columns=c.columns).fillna(0.0)
    w = S.REGISTRY["lowvol"](p).ffill().fillna(0.0).reindex(columns=c.columns, fill_value=0.0)
    wl = w.shift(1).fillna(0.0)
    start = w.abs().sum(axis=1).gt(0).idxmax()
    out = {"start": str(start.date()), "years": {}}
    for side, m in (("long", wl > 0), ("short", wl < 0)):
        ww = wl.where(m, 0.0)
        pr, fu = (ww * ret).loc[start:], -(ww * fund).loc[start:]
        for y in sorted(set(pr.index.year)):
            yy = str(y)
            d = out["years"].setdefault(y, {})
            d[side] = {"price": round(float(pr.loc[yy].sum().sum()), 4), "funding": round(float(fu.loc[yy].sum().sum()), 4),
                       "gross_mean": round(float(ww.loc[yy].abs().sum(axis=1).mean()), 2)}
            if side == "short":
                pass
    tot = ((wl * ret) - (wl * fund)).loc[start:]
    for y in sorted(set(tot.index.year)):
        coin = tot.loc[str(y)].sum()
        top5 = coin.sort_values(ascending=False).head(5)
        out["years"][y]["total"] = round(float(coin.sum()), 4)
        out["years"][y]["top5"] = {k_: round(float(v), 4) for k_, v in top5.items()}
        out["years"][y]["top5_share"] = round(float(top5.sum() / coin.sum()), 2) if coin.sum() > 0 else None
        out["years"][y]["bottom3"] = {k_: round(float(v), 4) for k_, v in coin.sort_values().head(3).items()}
    print(json.dumps(out, indent=1))
    json.dump(out, open("research/is3/bnh_b.json", "w"), indent=1)


def run_c():
    p = data.load_panel("hl", "1d")
    out = {}
    _, _, log = S.nested_selection(p)
    out["full_log"] = [[str(t.date()), ch] for t, ch in log]
    cut = {k: v.loc[:"2024-12-31"] for k, v in p.items() if isinstance(v, pd.DataFrame)}
    _, _, log2 = S.nested_selection(cut)
    out["cut_2024_log_tail"] = [[str(t.date()), ch] for t, ch in log2[-4:]]
    print(json.dumps(out, indent=1, default=str))
    json.dump(out, open("research/is3/bnh_c.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    {"a": run_a, "b": run_b, "c": run_c}[sys.argv[1]]()
