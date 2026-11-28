"""InSilico pass 3, T5D: OI built against a 3-day FALL as a short-side filter (bnall 1d, point-in-time top 60, metrics_full OI). Descriptive, NOT registered.

  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_t5x a [start end]   # -> research/is3/t5x_a_<start>.json

Losers = r3 = close/close.shift(3) - 1 < 0 among members (top 60 by 30-d mean dollar volume). doi = log OI change over 3 days (daily OI = last 5-min row of each UTC day,
t5b_positioning.daily_metrics). Outcome for a SHORT opened at the close of day t: -(r_{t+1} - mean_universe r_{t+1}) + funding_{t+1} (shorts receive positive funding).
Day-level: per day the mean outcome per doi tercile/quintile among that day's losers; t from day series; spread top - bottom per day.
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
import pandas as pd

from kripto import data
from research.studies import t5b_positioning as T

warnings.filterwarnings("ignore")
EV = data.DATA.parent / "research" / "is3"


def build(start, end):
    p = data.load_panel("bnall", "1d")
    c = p["close"]
    dv = p["volume"].rolling(30, min_periods=7).mean()
    member = (dv.rank(axis=1, ascending=False) <= 60) & c.notna()
    lo, hi = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
    syms = [x + "USDT" for x in member.columns[member.loc[lo:hi].any()]]
    m = T.daily_metrics(syms, start, end)
    oi = m["oi"].reindex(index=c.index, columns=c.columns)
    with np.errstate(divide="ignore", invalid="ignore"):
        doi = np.log(oi).diff(3).replace([np.inf, -np.inf], np.nan)
    r3 = c / c.shift(3) - 1
    r1 = (c.shift(-1) / c - 1).where(member)
    mkt = r1.mean(axis=1)
    fund = p["funding"].reindex(index=c.index, columns=c.columns).shift(-1).fillna(0.0)
    short_pnl = -(r1.sub(mkt, axis=0)) + fund
    cand = member & (r3 < 0) & doi.notna() & short_pnl.notna()
    win = (c.index >= lo) & (c.index <= hi)
    return doi.where(cand).loc[win], short_pnl.where(cand).loc[win], r3.where(cand).loc[win]


def by_bucket(doi, y, k):
    q = doi.rank(axis=1, pct=True)
    b = np.ceil(q * k).clip(1, k)
    rows = {}
    for j in range(1, k + 1):
        rows[j] = y.where(b == j).mean(axis=1)
    return pd.DataFrame(rows).dropna(how="all")


def tstat(x):
    x = x.dropna()
    return round(float(x.mean() / (x.std() / np.sqrt(len(x)))), 2) if len(x) > 10 and x.std() > 0 else None


def form_a(start="2021-12-05", end="2022-12-31"):
    doi, y, r3 = build(start, end)
    out = {"window": [start, end], "days": int(doi.notna().any(axis=1).sum()), "cand_per_day": round(float(doi.notna().sum(axis=1).mean()), 1)}
    for k in (3, 5):
        D = by_bucket(doi, y, k)
        sp = (D[k] - D[1])
        out[f"q{k}"] = {"mean_bp": {j: round(float(D[j].mean() * 1e4), 1) for j in D}, "median_bp": {j: round(float(D[j].median() * 1e4), 1) for j in D},
                        "top_minus_bottom_bp": round(float(sp.mean() * 1e4), 1), "t": tstat(sp),
                        "by_half": {h: round(float(sp[(sp.index.month <= 6) == (h == "H1")].mean() * 1e4), 1) for h in ("H1", "H2")}}
    # null check: shuffle doi across candidates within each day (keeps the day's composition, breaks the OI link); 200 copies
    rng = np.random.default_rng(7)
    D3 = by_bucket(doi, y, 3); real = float((D3[3] - D3[1]).mean())
    A = doi.to_numpy(); sims = []
    for _ in range(200):
        B = A.copy()
        for i in range(len(B)):
            ok = np.isfinite(B[i])
            B[i, ok] = rng.permutation(B[i, ok])
        Ds = by_bucket(pd.DataFrame(B, doi.index, doi.columns), y, 3)
        sims.append(float((Ds[3] - Ds[1]).mean()))
    sims = np.array(sims)
    out["null_shuffle"] = {"mean_bp": round(float(sims.mean() * 1e4), 2), "sd_bp": round(float(sims.std() * 1e4), 2), "real_pct": round(float((sims < real).mean()), 3)}
    # control: is it just the size of the fall? top-minus-bottom doi tercile within r3 terciles
    qr = np.ceil(r3.rank(axis=1, pct=True) * 3).clip(1, 3)
    out["within_r3_tercile_t3_minus_t1_bp"] = {}
    for j in (1, 2, 3):
        Dj = by_bucket(doi.where(qr == j), y.where(qr == j), 3)
        out["within_r3_tercile_t3_minus_t1_bp"][j] = round(float((Dj[3] - Dj[1]).mean() * 1e4), 1)
    tag = start[:7]
    print(json.dumps(out, indent=1)); json.dump(out, open(EV / f"t5x_a_{tag}.json", "w"), indent=1)


def form_d():
    from kripto.strategies import REGISTRY
    p = data.load_panel("bnall", "1d")
    c = p["close"]
    lo, hi = pd.Timestamp("2021-12-05", tz="UTC"), pd.Timestamp("2026-11-20", tz="UTC")
    books = {"flow": REGISTRY["flow"](p, lookback=3, cap=0.05), "xsmom": REGISTRY["xsmom"](p, lookback=28, every_days=1, cap=0.05)}
    held = {k: (w.ffill().fillna(0.0) < -1e-6) for k, w in books.items()}
    syms = sorted({x + "USDT" for h in held.values() for x in h.columns[h.loc[lo:hi].any()]})
    oi = T.daily_metrics(syms, str(lo.date()), str(hi.date()))["oi"].reindex(index=c.index, columns=c.columns)
    with np.errstate(divide="ignore", invalid="ignore"):
        doi = np.log(oi).diff(3).replace([np.inf, -np.inf], np.nan)
    dv = p["volume"].rolling(30, min_periods=7).mean()
    member = (dv.rank(axis=1, ascending=False) <= 100) & c.notna()
    r1 = (c.shift(-1) / c - 1).where(member); mkt = r1.mean(axis=1)
    fund = p["funding"].reindex(index=c.index, columns=c.columns).shift(-1).fillna(0.0)
    y = -(r1.sub(mkt, axis=0)) + fund
    out = {}
    for k, h in held.items():
        cand = h & doi.notna() & y.notna()
        D = by_bucket(doi.where(cand).loc[lo:hi], y.where(cand).loc[lo:hi], 3)
        sp = D[3] - D[1]
        out[k] = {"shorts_per_day": round(float(cand.loc[lo:hi].sum(axis=1).mean()), 1),
                  "by_year": {int(yy): {"t1_bp": round(float(D.loc[D.index.year == yy, 1].mean() * 1e4), 1), "t3_bp": round(float(D.loc[D.index.year == yy, 3].mean() * 1e4), 1),
                                        "spread_bp": round(float(sp[sp.index.year == yy].mean() * 1e4), 1), "t": tstat(sp[sp.index.year == yy])} for yy in range(2022, 2027)}}
        print(k, json.dumps(out[k]), flush=True)
    json.dump(out, open(EV / "t5x_d.json", "w"), indent=1)


if __name__ == "__main__":
    a = sys.argv[2:]
    {"a": form_a, "d": form_d}[sys.argv[1]](*a)
