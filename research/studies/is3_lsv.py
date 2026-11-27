"""InSilico pass 3, LSV: listing_short's vol estimate for new coins (zero-filled pre-listing returns). Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_lsv a    # ex-ante vs realised vol (book and per name, by age), gross at the cap -> research/is3/lsv_a.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto import strategies as S
from kripto.research import bars_per_day, default_band


def book_stats(p, lo, hi, prm=None):
    prm = prm or {}
    w = S.REGISTRY["listing_short"](p, **prm)
    res = bt.run(w, p["close"], p.get("funding"), bt.slippage_model(p["volume"], 1), band=default_band())
    r = res.returns.loc[lo:hi]
    g = res.gross.loc[lo:hi]
    inv = g > 0
    r, g = r[inv], g[inv]
    rv = r.rolling(30).std() * np.sqrt(365)
    mx = prm.get("max_gross", 1.5)
    out = {"days": int(len(r)), "sr": round(float(r.mean() / r.std() * np.sqrt(365)), 2), "realised_vol": round(float(r.std() * np.sqrt(365)), 3), "target": prm.get("target_vol", 0.20),
           "rolling30_vol_median": round(float(rv.median()), 3), "rolling30_vol_p90": round(float(rv.quantile(.9)), 3),
           "gross_mean": round(float(g.mean()), 2), "share_days_at_cap": round(float((g >= mx * 0.98).mean()), 2),
           "worst10_mean": round(float(r.nsmallest(10).mean()), 4), "by_year": {int(y): {"sr": round(float(x.mean() / x.std() * np.sqrt(365)), 2), "vol": round(float(x.std() * np.sqrt(365)), 3),
                                                                                   "worst": round(float(x.min()), 4)} for y, x in r.groupby(r.index.year)}}
    return out, w, res


def per_name(p, w, lo, hi):
    """Each short coin-day: zero-filled 60-d vol estimate (what vol_target sees) vs the realised vol of the next 30 d, by age since listing."""
    c, v = p["close"], p["volume"]
    r = S.returns(p)
    est = r.fillna(0.0).rolling(60, min_periods=20).std() * np.sqrt(365)
    fut = r[::-1].rolling(30, min_periods=10).std()[::-1].shift(-1) * np.sqrt(365)
    traded = (v.fillna(0) > 0) & c.notna()
    age = traded.cummax().cumsum()
    wf = w.ffill().fillna(0.0).loc[lo:hi]
    rows = []
    for b, a_ in ((1, 7), (8, 15), (16, 30), (31, 61)):
        m = (wf < 0) & (age.loc[lo:hi] >= b) & (age.loc[lo:hi] <= a_)
        e, f_ = est.loc[lo:hi][m].stack(), fut.loc[lo:hi][m].stack()
        j = e.index.intersection(f_.index)
        j = e[j].dropna().index.intersection(f_[j].dropna().index)
        rows.append({"age": f"{b}-{a_}", "n": int(len(j)), "est_med": round(float(e[j].median()), 2), "realised_next30_med": round(float(f_[j].median()), 2),
                     "ratio_med": round(float((f_[j] / e[j].clip(lower=1e-3)).median()), 2)})
    return rows


def run_a():
    out = {}
    for ds, lo, hi in (("bnall", "2021-01-01", "2023-12-31"), ("hl", "2023-05-01", "2026-12-31")):
        p = data.load_panel(ds, "1d")
        st, w, _ = book_stats(p, lo, hi)
        st["per_name_by_age"] = per_name(p, w, lo, hi)
        out[ds] = st
        print(ds, json.dumps(st, indent=1), flush=True)
        del p, w
    json.dump(out, open("research/is3/lsv_a.json", "w"), indent=1)


def vt_floor(mode):
    """vol_target with the per-name variance fixed: 'fixed150' floors each name's vol at 150 %/yr; 'own' uses only the name's traded days (pairwise NaN-aware cov)."""
    def f(w, panel, target, lookback_days=60, max_gross=3.0):
        r0 = S.returns(panel)
        r = r0.fillna(0.0)
        lb = lookback_days
        out = w.copy()
        R, R0, Wn = r.to_numpy(), r0.to_numpy(), w.to_numpy()
        for i in range(len(w)):
            row = Wn[i]
            if not np.isfinite(row).any():
                continue
            row = np.nan_to_num(row)
            nz = np.flatnonzero(row)
            if len(nz) == 0 or i < 20:
                out.iloc[i] = 0.0 if i < 20 else row
                continue
            if mode == "own":
                sub = pd.DataFrame(R0[max(0, i - lb + 1): i + 1][:, nz])
                cov = sub.cov(min_periods=3).fillna(0.0).to_numpy() * 365
                dz = np.diag(cov) <= 0
                if dz.any():                      # < 3 traded days: fall back to the zero-filled estimate for that name
                    cz = np.cov(R[max(0, i - lb + 1): i + 1][:, nz], rowvar=False) * 365
                    cov[dz, dz] = np.atleast_2d(cz)[dz, dz]
            else:
                cov = np.atleast_2d(np.cov(R[max(0, i - lb + 1): i + 1][:, nz], rowvar=False) * 365)
                d = np.sqrt(np.maximum(np.diag(cov), 1e-12))
                fl = np.maximum(d, 1.5)
                fl[nz == list(w.columns).index("BTC")] = d[nz == list(w.columns).index("BTC")] if "BTC" in w.columns else fl[nz == -1]
                cov = cov / np.outer(d, d) * np.outer(fl, fl)
            pv = float(np.sqrt(max(row[nz] @ cov @ row[nz], 1e-12)))
            scaled = row * (target / pv)
            g = np.abs(scaled).sum()
            if g > max_gross:
                scaled *= max_gross / g
            out.iloc[i] = scaled
        return out
    return f


def run_b():
    """Pre-stated (queue LSV b; variant 'own' replaces 'median of young coins', stated before the run): PASS = realised vol closer to target AND SR not lower AND worst-day loss smaller in each explore year."""
    p = data.load_panel("bnall", "1d")
    orig = S.vol_target
    out = {}
    try:
        for lab in ("live", "fixed150", "own"):
            S.vol_target = orig if lab == "live" else vt_floor(lab)
            st, _, _ = book_stats(p, "2021-01-01", "2023-12-31")
            out[lab] = st
            print(lab, st, flush=True)
    finally:
        S.vol_target = orig
    for lab in ("fixed150", "own"):
        a, b = out[lab], out["live"]
        out[lab]["PASS"] = bool(abs(a["realised_vol"] - .2) < abs(b["realised_vol"] - .2) and a["sr"] >= b["sr"] and
                                all(a["by_year"][y]["worst"] > b["by_year"][y]["worst"] for y in b["by_year"]))
    json.dump(out, open("research/is3/lsv_b.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": run_a, "b": run_b}[sys.argv[1]]()
