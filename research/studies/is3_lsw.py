"""InSilico pass 3, LSW: listing_short with raw short weights proportional to 1 / own-days realised vol (min 3 own returns, floor 100 %/yr,
cap 2x equal weight) vs equal weight and vs 200 day-wise permutations of the same relative weights across eligible names. Pre-stated in notes.md."""
from __future__ import annotations

import json
import sys
import time

import numpy as np
import pandas as pd

from kripto import strategies as S
from research.studies import is3_filter as F


def eligible(panel, skip_days=1, hold_days=60, min_dv=1e6):
    c, v = panel["close"], panel["volume"]
    traded = (v.fillna(0) > 0) & c.notna()
    started = traded.cummax()
    age = started.cumsum()
    t_cut = traded.any(axis=1).idxmax() + pd.Timedelta(days=30)
    pre = started.loc[started.index < t_cut].any()
    elig = (age > skip_days) & (age <= skip_days + hold_days) & c.notna() & (S.dollar_volume(panel) >= min_dv)
    elig = elig.loc[:, ~pre].reindex(columns=c.columns, fill_value=False)
    elig = elig & pd.DataFrame(np.broadcast_to((c.index >= t_cut)[:, None], c.shape), c.index, c.columns)
    return elig, traded


def rel_weights(panel, elig, traded, floor=1.0, cap=2.0):
    r = panel["close"].pct_change().where(traded & traded.shift(1, fill_value=False))
    n = r.notna().cumsum()
    vol = r.rolling(60, min_periods=3).std() * np.sqrt(365)   # own traded days only (NaN before listing), <= 60 d
    inv = 1.0 / vol.clip(lower=floor)
    inv = inv.where(elig)
    mean_inv = inv.mean(axis=1)
    rel = inv.div(mean_inv, axis=0)            # 1 = equal weight
    rel = rel.where(n >= 3, 1.0).where(elig)   # < 3 own returns: equal weight
    return rel.clip(upper=cap)


def book(panel, rel):
    raw = -rel.fillna(0.0)
    raw = raw.div(raw.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    raw = S.hedge_beta(raw, S.beta_to(panel))
    return S.scheduled(raw, panel, 1, 0.20, 1.5, None)


def permute(rel, rng):
    A = rel.to_numpy().copy()
    for t in range(A.shape[0]):
        j = np.where(~np.isnan(A[t]))[0]
        if len(j) > 1:
            A[t, j] = A[t, rng.permutation(j)]
    return pd.DataFrame(A, rel.index, rel.columns)


sr = lambda x: float(x.mean() / x.std() * np.sqrt(365))

if __name__ == "__main__":
    n_perm = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    w0, panel, slip = F.book("listing_short", "bnall", {})
    elig, traded = eligible(panel)
    eq = elig.astype(float).where(elig)
    w_eq = book(panel, eq)
    chk = float((w_eq.fillna(0) - w0.fillna(0)).abs().max().max())
    print("replication max |dw| vs registered listing_short:", chk, flush=True)
    rel = rel_weights(panel, elig, traded)
    w_iv = book(panel, rel)
    base, iv = F.run(w_eq, panel, slip), F.run(w_iv, panel, slip)
    out = {"replication_max_abs_dw": chk, "rel_quantiles": [float(np.nanquantile(rel.to_numpy(), q)) for q in (.05, .25, .5, .75, .95)],
           "cap_share": float((rel.to_numpy() >= 2.0 - 1e-9).sum() / np.isfinite(rel.to_numpy()).sum())}
    for nm, r in (("equal", base), ("invvol", iv)):
        e = F.cut(r, "explore")
        out[nm] = {"explore": F.stats(e), "by_year": {int(y): round(sr(e[e.index.year == y]), 3) for y in (2021, 2022, 2023)},
                   "worst10_mean": float(e.nsmallest(10).mean())}
    print(json.dumps({k: out[k] for k in ("equal", "invvol")}, default=float), flush=True)
    rng = np.random.default_rng(0)
    d0 = out["invvol"]["explore"]["sr"] - out["equal"]["explore"]["sr"]
    pd_ = []
    t0 = time.time()
    for i in range(n_perm):
        e = F.cut(F.run(book(panel, permute(rel, rng)), panel, slip), "explore")
        pd_.append(F.stats(e)["sr"] - out["equal"]["explore"]["sr"])
        if i == 0:
            print("one permutation s:", round(time.time() - t0, 1), flush=True)
    pd_ = np.array(pd_)
    out["dSR"] = d0
    out["dSR_by_year"] = {y: round(out["invvol"]["by_year"][y] - out["equal"]["by_year"][y], 3) for y in (2021, 2022, 2023)}
    out["perm_dSR_q05_q50_q95"] = [float(np.quantile(pd_, q)) for q in (.05, .5, .95)] if len(pd_) else None
    out["pct_vs_perm"] = float((pd_ < d0).mean()) if len(pd_) else None
    out["PASS"] = bool(len(pd_) and all(v > 0 for v in out["dSR_by_year"].values()) and out["pct_vs_perm"] >= 0.95)
    print(json.dumps({k: out[k] for k in ("dSR", "dSR_by_year", "perm_dSR_q05_q50_q95", "pct_vs_perm", "PASS")}, default=float), flush=True)
    json.dump(out, open("research/is3/lsw_a.json", "w"), indent=1, default=float)
