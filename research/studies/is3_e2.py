"""InSilico pass 3, E2 a: walk-forward of the resting ladder (T1, frozen mechanics) over k x hold x slots, causal top-20 Binance universe.

  .venv/bin/python -m research.studies.is3_e2 build <k>      # fills for k sigma, 2021-01..2026-10 -> data/is3/e2_k<k>.parquet (k=30 reuses ladtop_x/c/v)
  .venv/bin/python -m research.studies.is3_e2 wf             # walk-forward (18 configs), registered as one walk_forward line

Mechanics as is3_ladtop.events: bid k*sigma (24-h std of 1-min log returns) below the previous close, fill if the low is 30 bp through, exit at market
`hold` minutes later, one position per coin per hour. Account: 5% per order, all same-minute fills taken while fewer than `slots` are open.
Audit rules (research/is3/T1i_audit.md): fills deeper than the coin's PERCENT_PRICE band are dropped.
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from kripto import data, research
from kripto import events as ev
from kripto import metrics as mx
from research.studies import is3_ladtop as T

OUT = T.OUT
LO, HI = pd.Timestamp("2021-01-01", tz="UTC"), pd.Timestamp("2026-11-01", tz="UTC")
KS, HOLDS, SLOTS, SIZE = (20, 30, 40), (15, 60, 240), (5, 10), 0.05


def one_k(a):
    coin, lo, hi, days, k = a
    out = []
    for x in T.series(coin, lo, hi):
        e = T.events(*(x[f].to_numpy() for f in ("c", "h", "l", "qv")), x.index, k=k)
        if len(e):
            e["slip"] = ev.slip_per_day(x["qv"].to_frame(coin))[coin].reindex(e.time.dt.floor("D")).to_numpy()
            out.append(e)
    if not out:
        return pd.DataFrame()
    e = pd.concat(out).assign(coin=coin, day=lambda d: d.time.dt.floor("D")).merge(days, on="day")
    return e[(e.time >= lo) & (e.time < hi)].drop(columns="t")


def build(k, workers=2):
    k = int(k)
    u = pd.read_parquet(OUT / "top_universe.parquet")
    u = u[(u.day >= LO) & (u.day < HI)]
    jobs = [(c, LO, HI, g[["day", "rank", "age"]], k) for c, g in u.groupby("coin")]
    with ProcessPoolExecutor(workers) as ex:
        t = pd.concat([x for x in ex.map(one_k, jobs) if len(x)]).sort_values(["time", "coin"]).reset_index(drop=True)
    t.to_parquet(OUT / f"e2_k{k}.parquet")
    print(k, len(t), "fills", t.coin.nunique(), "coins", t.time.min(), t.time.max(), flush=True)


def fills(k) -> pd.DataFrame:
    if k == 30:
        t = pd.concat([pd.read_parquet(OUT / f"ladtop_{s}.parquet") for s in "xcv"])
    else:
        t = pd.read_parquet(OUT / f"e2_k{k}.parquet")
    return t[(t.time >= LO) & (t.time < HI)].sort_values(["time", "coin"]).reset_index(drop=True)


def bands() -> dict:
    """multiplierDown of PERCENT_PRICE per base coin (how far below mark a bid may rest)."""
    d = json.load(open(data.DATA / "bn" / "live_exchange_info.json"))
    out = {}
    for s in d["symbols"]:
        if s.get("quoteAsset") != "USDT" or s.get("contractType") != "PERPETUAL":
            continue
        for f in s["filters"]:
            if f["filterType"] == "PERCENT_PRICE":
                out[s["symbol"][:-4]] = 1 - float(f["multiplierDown"])
    return out


def daily(t, hold, slots, cost=1.0, drop=()):
    """Daily account returns (P&L booked on the fill day), as is3_ladtop.account but 5% per order and a cost multiplier."""
    t = t[~t.coin.isin(drop)]
    until, keep = [], []
    for tm, g in t.groupby("time", sort=True):
        until = [x for x in until if x > tm]
        if len(until) < slots:
            keep.append(g)
            until += [tm + pd.Timedelta(minutes=hold)] * len(g)
    g = pd.concat(keep)
    net = g[f"h{hold}"] - cost * (7e-4 + g.slip)
    idx = pd.date_range(LO, HI, tz="UTC", inclusive="left")
    return (net * SIZE).groupby(g.time.dt.floor("D")).sum().reindex(idx, fill_value=0.0), len(g)


def wf(train_days=240, test_days=60):
    bd = bands()
    configs = [{"k": k, "hold": h, "slots": s} for k in KS for h in HOLDS for s in SLOTS]
    F = {}
    for k in KS:
        t = fills(k)
        lim = t.coin.map(bd).fillna(0.15)
        n0 = len(t)
        F[k] = t[t.depth <= lim]
        print(f"k{k}: {n0} fills, {n0 - len(F[k])} beyond the PERCENT_PRICE band dropped", flush=True)
    R, sums, n = {}, [], {}
    for i, p in enumerate(configs):
        R[i], n[i] = daily(F[p["k"]], p["hold"], p["slots"])
        sums.append({"i": i, **p, "n": n[i], "sharpe": round(mx.sharpe(R[i], 365), 2), "cagr": round(float((1 + R[i]).prod() ** (365 / len(R[i])) - 1), 4)})
    R = pd.DataFrame(R)
    folds, oos, avg, start = [], [], [], LO + pd.Timedelta(days=train_days)
    while start < HI:
        end = start + pd.Timedelta(days=test_days)
        ins = R[R.index < start]
        score = ins.mean() / ins.std() * np.sqrt(365)
        b = int(score.idxmax())
        seg = R.loc[(R.index >= start) & (R.index < end), b]
        oos.append(seg)
        avg.append(R.loc[(R.index >= start) & (R.index < end)].mean(axis=1))
        folds.append({"from": str(start.date()), **configs[b], "is_sr": round(float(score[b]), 2), "oos_sr": round(mx.sharpe(seg, 365), 2)})
        start = end
    o, a = pd.concat(oos), pd.concat(avg)
    last = folds[-1]
    stress = {}
    for lab, kw in (("cost2x", {"cost": 2.0}), ("small200", {"drop": ("BTC", "ETH")}), ("small200_cost2x", {"cost": 2.0, "drop": ("BTC", "ETH")})):
        stress[lab] = []
        for f in folds:                                    # the same causal choices, re-priced
            r, _ = daily(F[f["k"]], f["hold"], f["slots"], **kw)
            fr = pd.Timestamp(f["from"], tz="UTC")
            stress[lab].append(r[(r.index >= fr) & (r.index < fr + pd.Timedelta(days=test_days))])
        stress[lab] = round(mx.sharpe(pd.concat(stress[lab]), 365), 2)
    eq = (1 + o).cumprod()
    out = {"strategy": "ladder", "dataset": "bntop20_1m", "n_configs": len(configs),
           "grid_median_sharpe": float(pd.DataFrame(sums).sharpe.median()), "grid_frac_positive": float((pd.DataFrame(sums).sharpe > 0).mean()),
           "oos": mx.summary(o, n_trials=research.n_trials("walk_forward") + 1), "oos_grid_avg": round(mx.sharpe(a, 365), 3),
           "oos_by_year": {str(y): round(float(x.sum()), 4) for y, x in o.groupby(o.index.year)},
           "oos_mdd": round(float((eq / eq.cummax() - 1).min()), 4), "oos_worst_day": round(float(o.min()), 4),
           "stress_sr": stress, "chosen_today": last, "size_per_order": SIZE, "band_rule": "PERCENT_PRICE multiplierDown, delisted 0.15",
           "note": "InSilico E2a; fills from research/studies/is3_e2.py; P&L booked on fill day; 2026 = vault year (spent for T1k30 h60)"}
    research.log_trial({"kind": "walk_forward", **out})
    res = {**out, "folds": folds, "grid": sorted(sums, key=lambda d: -d["sharpe"])}
    (OUT / "e2_wf.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k != "folds"}, indent=1, default=str))
    print("\n".join(f"{f['from']} k{f['k']} h{f['hold']} s{f['slots']} is {f['is_sr']} oos {f['oos_sr']}" for f in folds))


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build(*sys.argv[2:])
    elif sys.argv[1] == "wf":
        wf()
