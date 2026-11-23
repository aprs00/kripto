"""InSilico pass 3, E2 c: minute-by-minute risk of the live ladder rule (one-bar-late fills, 5%/order, < 5 open, all same-minute fills taken).

  nice -n 19 .venv/bin/python -m research.studies.is3_e2risk paths     # fill -> exit minute paths -> data/is3/e2_paths.parquet
  nice -n 19 .venv/bin/python -m research.studies.is3_e2risk report    # intraday mark, gross, outage proxy, daily loss cap, size table

Equity is simple (fractions of starting equity, no compounding), like is3_e2.daily. Marks: every open position at the minute's LOW (worst case)
and at its close; the peak is tracked on close marks (kripto.live marks last prices every 20 s, so the low mark is a bound, not what live sees).
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import metrics as mx
from research.studies import is3_e2 as E
from research.studies import is3_ladtop as T

OUT = T.OUT
HOLD, SLOTS, SIZE, COST = 60, 5, 0.05, 7e-4


def kept(t, slots=SLOTS, hold=HOLD):
    """The account's fills: same selection as is3_e2.daily."""
    until, keep = [], []
    for tm, g in t.groupby("time", sort=True):
        until = [x for x in until if x > tm]
        if len(until) < slots:
            keep.append(g)
            until += [tm + pd.Timedelta(minutes=hold)] * len(g)
    return pd.concat(keep).reset_index(drop=True)


def fills():
    t = E.fills(-30)
    lim = t.coin.map(E.bands()).fillna(0.15)
    return t[t.depth <= lim].reset_index(drop=True)


def paths():
    t = fills()
    rows = []
    for coin, g in t.groupby("coin"):
        for x in T.series(coin, E.LO, E.HI):
            for i, f in g[(g.time >= x.index[0]) & (g.time <= x.index[-1])].iterrows():
                seg = x.loc[f.time: f.time + pd.Timedelta(minutes=61)]
                if len(seg) < 62:
                    continue
                p = seg.c.iloc[61] / (1 + f.h60)                 # entry = limit; h60 (late) = c[t+61]/p - 1
                rows.append(pd.DataFrame({"fid": i, "m": np.arange(62), "time": seg.index[:62],
                                          "lo": seg.l.to_numpy()[:62] / p - 1, "cl": seg.c.to_numpy()[:62] / p - 1}))
    P = pd.concat(rows, ignore_index=True)
    P.to_parquet(OUT / "e2_paths.parquet")
    chk = P[P.m == 61].set_index("fid").cl - t.h60.reindex(P[P.m == 61].fid).to_numpy()
    print(len(t), "fills,", P.fid.nunique(), "with paths; max |exit - h60|", float(chk.abs().max()), flush=True)


def account_path(k, P, size=SIZE, h_override=None):
    """Minute equity (low and close marks) of the kept fills k; positions open at minutes 0..60, realised at 61."""
    q = P[P.fid.isin(k.fid)].merge(k[["fid", "slip"]], on="fid")
    op = q[q.m <= 60]
    net = k.set_index("fid")
    exit_ret = (h_override if h_override is not None else net.h60) - (COST + net.slip)
    ex_t = q[q.m == 61].set_index("fid").time
    real = (exit_ret.reindex(ex_t.index) * size).groupby(ex_t.to_numpy()).sum()
    mtm_lo = (op.lo * size).groupby(op.time).sum()
    mtm_cl = (op.cl * size).groupby(op.time).sum()
    gross = op.groupby("time").size() * size
    idx = mtm_lo.index.union(real.index)
    R = real.reindex(idx, fill_value=0).cumsum()
    R_before = R - real.reindex(idx, fill_value=0)              # a position realised at minute m is not also marked there
    eq_lo = 1 + R_before + mtm_lo.reindex(idx, fill_value=0)
    eq_cl = 1 + R_before + mtm_cl.reindex(idx, fill_value=0)
    eq_cl = pd.concat([eq_cl, 1 + R]).groupby(level=0).max().reindex(idx)   # after the exit the realised value counts
    peak = np.maximum.accumulate(np.maximum(eq_cl.to_numpy(), 1.0))
    dd_lo = pd.Series(eq_lo.to_numpy() - peak, idx)          # in units of STARTING equity (a fresh book meets the cascade at its peak)
    return dd_lo, gross.reindex(idx, fill_value=0), R


def booked(k, size=SIZE, cap_drop=None):
    net = (k.h60 - (COST + k.slip)) * size
    idx = pd.date_range(E.LO, E.HI, tz="UTC", inclusive="left")
    return net.groupby(k.time.dt.floor("D")).sum().reindex(idx, fill_value=0.0)


def loss_cap(t, P, cap):
    """Stop accepting fills for the rest of the UTC day once the day's P&L (realised + open at the minute low) touched -cap."""
    by = {f: g for f, g in P.groupby("fid")}
    until, acc, day, stopped = [], [], None, False
    for tm, g in t.groupby("time", sort=True):
        d = tm.floor("D")
        if d != day:
            day, stopped, today = d, False, []
        until = [x for x in until if x > tm]
        if not stopped and today:
            pnl = []
            for f in today:                     # day P&L path up to tm from accepted fills of this day
                p = by[f["fid"]]
                p = p[p.time < tm]
                v = np.where(p.m.to_numpy() == 61, f["net"], p.lo.to_numpy()) * SIZE
                pnl.append(pd.Series(v, p.time.to_numpy()))
            s = pd.concat(pnl, axis=1).sort_index()
            s = s.ffill().fillna(0).sum(axis=1)
            stopped = bool(len(s) and s.min() <= -cap)
        if stopped or len(until) >= SLOTS:
            continue
        for _, f in g.iterrows():
            today.append({"fid": f.fid, "net": f.h60 - (COST + f.slip)})
            acc.append(f)
            until.append(tm + pd.Timedelta(minutes=HOLD))
    return pd.DataFrame(acc)


def report():
    t = fills().reset_index(names="fid")
    P = pd.read_parquet(OUT / "e2_paths.parquet")
    t = t[t.fid.isin(P.fid.unique())]
    k = kept(t)
    out = {"fills": len(t), "kept": len(k)}
    r = booked(k)
    eq = 1 + r.cumsum()
    out["booked"] = {"sr": round(mx.sharpe(r, 365), 2), "worst_day": round(float(r.min()), 4), "mdd": round(float((eq / eq.cummax() - 1).min()), 4)}
    dd, gross, _ = account_path(k, P)
    worst = dd.groupby(dd.index.floor("D")).min().nsmallest(8)
    out["mark_low"] = {"mdd": round(float(dd.min()), 4), "worst_days": {str(d.date()): round(float(v), 4) for d, v in worst.items()}}
    out["gross"] = {"max": round(float(gross.max()), 2), "minutes_over_25pct": int((gross > 0.25 + 1e-9).sum()),
                    "top": {str(i): round(float(v), 2) for i, v in gross.nlargest(5).items()}}
    # outage: on days with >= 5 same-minute fills, the exits happen 3 h later (h240 + 1 min) instead of 60 min
    nmin = k.groupby("time").coin.transform("size")
    cas = k.time.dt.floor("D").isin(k.time[nmin >= 5].dt.floor("D"))
    alt = k.h60.where(~cas, k.h240)
    r2 = ((alt - (COST + k.slip)) * SIZE).groupby(k.time.dt.floor("D")).sum().reindex(r.index, fill_value=0.0)
    e2 = 1 + r2.cumsum()
    out["outage_240"] = {"cascade_days": int(k.time[nmin >= 5].dt.floor("D").nunique()), "fills_affected": int(cas.sum()),
                         "sr": round(mx.sharpe(r2, 365), 2), "worst_day": round(float(r2.min()), 4), "mdd": round(float((e2 / e2.cummax() - 1).min()), 4),
                         "cascade_day_sum_h60": round(float(((k.h60 - COST - k.slip) * SIZE)[cas].sum()), 4),
                         "cascade_day_sum_h240": round(float(((k.h240 - COST - k.slip) * SIZE)[cas].sum()), 4)}
    out["loss_cap"] = {}
    for cap in (0.02, 0.03, 0.05):
        kc = loss_cap(t, P, cap)
        rc = booked(kc)
        dc, _, _ = account_path(kc.assign(fid=kc.fid.astype(int)), P)
        ec = 1 + rc.cumsum()
        out["loss_cap"][str(cap)] = {"kept": len(kc), "sr": round(mx.sharpe(rc, 365), 2), "cagr_simple": round(float(rc.sum() / (len(rc) / 365)), 4),
                                     "booked_mdd": round(float((ec / ec.cummax() - 1).min()), 4), "mark_mdd": round(float(dc.min()), 4)}
    out["size_table"] = {}
    for s in (0.02, 0.03, 0.05, 0.08, 0.10):
        d, _, _ = account_path(k, P, size=s)
        out["size_table"][str(s)] = {"mark_mdd": round(float(d.min()), 4), "simple_ret_per_yr": round(float(booked(k, s).sum() / (len(r) / 365)), 4)}
    print(json.dumps(out, indent=1))
    (OUT / "e2c_risk.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"paths": paths, "report": report}[sys.argv[1]]()
