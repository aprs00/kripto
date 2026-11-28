"""SMV: tail of the rounded $200 book's gross and 60-d vol relative to the $1,000 book (HL and BN main mixes from is3_smd). Not registered.
PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_smv -> research/is3/smv_ab.json"""
import json
import numpy as np, pandas as pd
from research.studies import is3_smd as D

out = {}
for tag, fn in (("hl", D.hl_book), ("bn", D.bn_book)):
    D.VEN[0] = tag
    p, w, mins, S = fn()
    r0res, r0 = D.run(p, w, 1000.0, S)
    rm = pd.DataFrame(D.roundmin(w, mins), w.index, w.columns)
    rres, r = D.run(p, rm, D.EQ, S)
    g0 = r0res.weights.loc[S].abs().sum(axis=1)
    g = rres.weights.loc[S].abs().sum(axis=1)
    ratio = (g / g0).replace([np.inf, -np.inf], np.nan).dropna()
    vr = (r.rolling(60).std() / r0.rolling(60).std()).dropna()
    q = lambda s: {k: round(float(s.quantile(x)), 3) for k, x in (("p10", .1), ("p50", .5), ("p90", .9), ("p99", .99))} | {"max": round(float(s.max()), 3), "share_gt_1.25": round(float((s > 1.25).mean()), 3)}
    o = {"gross_ratio": q(ratio), "vol60_ratio": q(vr),
         "by_year": {int(y): {"gross_p90": round(float(v.quantile(.9)), 3), "gross_share_gt_1.25": round(float((v > 1.25).mean()), 3),
                              "vol60_p90": round(float(vr[vr.index.year == y].quantile(.9)), 3) if (vr.index.year == y).any() else None}
                     for y, v in ratio.groupby(ratio.index.year)}}
    # b: anatomy of excess days
    W = rm.loc[S]                     # the rounded TARGETS (held weights drift with price and the trade band)
    m = mins.reindex(W.columns).to_numpy() / D.EQ
    at_min = (np.isclose(W.abs().to_numpy(), m, rtol=1e-6) & (W.abs().to_numpy() > 0))
    n_min = pd.Series(at_min.sum(1), W.index); g_min = pd.Series((W.abs().to_numpy() * at_min).sum(1), W.index)
    names = (W != 0).sum(axis=1); univ = p["close"].loc[S].notna().sum(axis=1)
    hi = ratio[ratio > 1.25].index; lo = ratio[ratio <= 1.25].index
    o["anatomy"] = {k: {"days": int(len(ix)), "names": round(float(names.reindex(ix).mean()), 1), "at_min": round(float(n_min.reindex(ix).mean()), 1),
                        "min_share_of_gross": round(float((g_min / W.abs().sum(axis=1)).reindex(ix).mean()), 3), "universe": round(float(univ.reindex(ix).mean()), 1),
                        "sibling_gross": round(float(g0.reindex(ix).mean()), 3)} for k, ix in (("ratio_gt_1.25", hi), ("rest", lo))}
    o["vol_full"] = {"usd1000": round(float(r0.std() * np.sqrt(365)), 3), "usd200_round": round(float(r.std() * np.sqrt(365)), 3)}
    out[tag] = o
    print(tag, json.dumps(o), flush=True)
json.dump(out, open("research/is3/smv_ab.json", "w"), indent=1)
