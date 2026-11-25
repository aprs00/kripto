"""W3 think-through step (2026-11-25 research): is the Sunday 12->18 NY fade a MARKET effect (one bet per Sunday) or a COIN effect
(cross-sectional, market-neutral)? Exploration sample ONLY: Sundays <= 2023-12-31 (the later period is printed only when --all is
given, and was not used to choose the walk-forward form). bn100 1h, point-in-time top-100, as in w3_sunday_fade.py.
Per Sunday and coin: mv = log move 12->18 NY, m = cross-sectional median mv, e = mv - m; r = SIMPLE 24 h return after 18:00,
rm = cross-sectional mean r. Three forms, per-Sunday mean P&L of one unit, t on Sundays:
  raw     : -sign(mv) * r            for |mv| >= thr  (the replicated rule)
  excess  : -sign(e) * (r - rm)      for |e|  >= thr  (market-neutral)
  market  : -sign(m) * rm            if  |m|  >= thr  (one bet per Sunday on the equal-weight universe)
  usage: nice -n 19 .venv/bin/python -m research.studies.w3_decomp [--all]
"""
import sys

import numpy as np
import pandas as pd

from kripto import data, strategies as st


def tstat(x):
    x = pd.Series(x).dropna()
    return (x.mean() / x.std() * np.sqrt(len(x))) if len(x) > 5 and x.std() > 0 else float("nan")


def main():
    p = data.load_panel("bn100", "1h")
    c = p["close"]
    uni = st.universe(p, top_n=100, min_days=30).to_numpy()
    idx = c.index
    ny = (idx + pd.Timedelta(hours=1)).tz_convert("America/New_York")
    C = c.to_numpy()
    rows = []
    for i in np.flatnonzero((np.asarray(ny.day_of_week) == 6) & (np.asarray(ny.hour) == 18)):
        j, k = i - 6, i + 24
        if j < 0 or k >= len(idx) or idx[i] - idx[j] != pd.Timedelta(hours=6) or idx[k] - idx[i] != pd.Timedelta(hours=24):
            continue
        a, b, e_ = C[j].astype(float), C[i].astype(float), C[k].astype(float)
        mv, r = np.log(b / a), e_ / b - 1.0
        ok = uni[i] & np.isfinite(mv) & np.isfinite(r)
        if ok.sum() < 20:
            continue
        mv, r = mv[ok], r[ok]
        m, rm = np.median(mv), r.mean()
        ex = mv - m
        rows.append(dict(day=idx[i].floor("D"), n=ok.sum(), m=m, rm=rm, mv=mv, r=r, ex=ex))
    print(f"W3 decomposition | Sundays {len(rows)} | {rows[0]['day']:%Y-%m-%d} .. {rows[-1]['day']:%Y-%m-%d}")
    periods = [("explore <= 2023", lambda d: d < pd.Timestamp("2024-01-01", tz="UTC"))]
    if "--all" in sys.argv:
        periods.append((">= 2024 (seen 11-15/11-19; NOT used to choose)", lambda d: d >= pd.Timestamp("2024-01-01", tz="UTC")))
    for lab, sel in periods:
        R = [x for x in rows if sel(x["day"])]
        print(f"\n {lab}: {len(R)} Sundays")
        for thr in (0.01, 0.02):
            raw = [np.nanmean(np.where(np.abs(x["mv"]) >= thr, -np.sign(x["mv"]) * x["r"], np.nan)) if (np.abs(x["mv"]) >= thr).any() else np.nan for x in R]
            exc = [np.nanmean(np.where(np.abs(x["ex"]) >= thr, -np.sign(x["ex"]) * (x["r"] - x["rm"]), np.nan)) if (np.abs(x["ex"]) >= thr).any() else np.nan for x in R]
            mkt = [(-np.sign(x["m"]) * x["rm"]) if abs(x["m"]) >= thr else np.nan for x in R]
            # raw split: market component of the raw trade = -sign(mv) * rm, the rest is coin-specific
            rawm = [np.nanmean(np.where(np.abs(x["mv"]) >= thr, -np.sign(x["mv"]) * x["rm"], np.nan)) if (np.abs(x["mv"]) >= thr).any() else np.nan for x in R]
            for name, v in (("raw", raw), ("  of which market part", rawm), ("excess (market-neutral)", exc), ("market (one bet/Sunday)", mkt)):
                s = pd.Series(v).dropna()
                print(f"  thr {thr:.0%} {name:26s} Sundays {len(s):3d} mean {s.mean() * 1e4:+6.1f} bp median {s.median() * 1e4:+6.1f} t {tstat(s):+.2f} hit {(s > 0).mean():.0%}")
        mm = pd.Series([x["m"] for x in R])
        print(f"  |median Sunday move| >= 1% on {(mm.abs() >= 0.01).mean():.0%} of Sundays; corr(m, -rm) = {np.corrcoef(mm, [-x['rm'] for x in R])[0, 1]:+.2f}")


if __name__ == "__main__":
    main()
