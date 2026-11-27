"""InSilico pass 3, T9B: alpha-decay curve of the live main books' target changes (library N8). Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_t9b a      # curves per strategy -> data/is3/t9b_a.json (forms a and b: by year, delay cost)

Decision time D = 4h bar open + 4h (the bar's close); target change dw(D) = w[t] - w[t-1] on the 4h grid (traded at D in bt.run).
Signed return of the change over h hours: sum_i dw_i (P_i(D+h) / P_i(D) - 1), P from 1h closes (1h bar opening at D+h-1h). Per unit turnover = / sum |dw|.
Delay cost of k hours = the curve at +k h (what a fill k hours late gives up, before costs).
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data
from kripto.strategies import REGISTRY

OUT = data.DATA / "is3"
HS = (0, 1, 2, 4, 8, 12, 24, 48)
BOOKS = {  # name: (dataset, strategy, params)
    "blend_hl": ("hl", "blend", {"components": {"listing_short": {}, "lowvol": {}, "tsmom": {}}}),
    "tsmom_hl": ("hl", "tsmom", {}),
    "listing_short_hl": ("hl", "listing_short", {}),
    "lowvol_hl": ("hl", "lowvol", {}),
    "blend_bn": ("bn", "blend", {"components": {"carry_trend": {}, "carry": {}, "xsmom": {}}}),
    "tsmom_bn": ("bn", "tsmom", {}),
    "xsmom_bn": ("bn", "xsmom", {}),
    "carry_bn": ("bn", "carry", {}),
    "carry_trend_bn": ("bn", "carry_trend", {}),
    "blend_bnlive": ("bnlive", "blend", {"components": {"carry_trend": {}, "carry": {}, "xsmom": {}}}),
    "flow_bnlive": ("bnlive", "flow", {"lookback": 3, "cap": 0.05}),
}


def close_1h(ds):
    return data.load_panel(ds, "1h")["close"]


def curve(w, c4, c1, reps=1000, seed=7, start=None):
    dw = w.ffill().fillna(0.0).diff().fillna(0.0)          # NaN = hold the last target (bt.run ffills); fillna(0) made fake changes
    dw = dw[dw.abs().sum(axis=1) > 1e-9]
    if start is not None:
        dw = dw[dw.index + pd.Timedelta(hours=4) >= start]
    D = dw.index + pd.Timedelta(hours=4)
    c1 = c1.reindex(columns=dw.columns)
    P = {h: c1.reindex(D + pd.Timedelta(hours=h) - pd.Timedelta(hours=1)).to_numpy() for h in HS}
    P0 = P[0]
    A = dw.to_numpy()
    turn = np.abs(A).sum(axis=1)
    rows = {}
    for h in HS:
        r = np.where(np.isfinite(P[h] / P0), P[h] / P0 - 1, 0.0)
        rows[h] = (A * r).sum(axis=1)
    # known answer: +4h on the 1h grid equals the 4h panel's next-bar return for the same dw
    nxt = (c4.shift(-1) / c4 - 1).reindex(index=dw.index, columns=dw.columns).to_numpy()
    k4 = np.nansum(A * np.where(np.isfinite(nxt), nxt, 0.0), axis=1)
    agree = float(np.corrcoef(k4, rows[4])[0, 1])
    df = pd.DataFrame({f"h{h}": rows[h] for h in HS}, index=D).assign(turn=turn)
    rng = np.random.default_rng(seed)
    days = df.index.floor("D")
    g = df.groupby(days).sum()
    out = {"n_changes": int(len(df)), "turn_per_yr": round(float(turn.sum() / ((D[-1] - D[0]).days / 365)), 1), "check_4h_corr": round(agree, 4),
           "hour_of_change": {int(k): int(v) for k, v in pd.Series(D.hour).value_counts().sort_index().items()}}
    est, ci = {}, {}
    G = g.to_numpy()
    T = g["turn"].to_numpy()
    for j, h in enumerate(HS):
        x = G[:, j]
        est[h] = float(x.sum() / T.sum() * 1e4)
        b = []
        for _ in range(reps):
            i = rng.integers(0, len(g), len(g))
            b.append(x[i].sum() / T[i].sum() * 1e4)
        ci[h] = [round(float(np.quantile(b, 0.025)), 2), round(float(np.quantile(b, 0.975)), 2)]
    out["bp_per_turn"] = {h: round(v, 2) for h, v in est.items()}
    out["ci95"] = ci
    yrs = {}
    for y, gy in g.groupby(g.index.year):
        yrs[int(y)] = {h: round(float(gy[f"h{h}"].sum() / gy["turn"].sum() * 1e4), 2) for h in (1, 4, 24, 48)}
    out["by_year"] = yrs
    return out


def live_bn_panel():
    """The live Binance 4h inputs (data/bn/live_4h, with taker_buy) without the live cutoff, and 1h closes of the same coins from bn100."""
    from kripto import paper as P
    from kripto import venue_bn as V
    P.HISTORY_DAYS = 100000
    coins = sorted(f.stem for f in V.LIVE_DIR.glob("*.parquet"))
    p4 = V.live_panel(coins)
    c1 = data.load_bn_panel("1h", [c + "USDT" for c in coins], kdir=data.BN100_DIR, fdir=data.DATA / "bn" / "funding_all", lean=True)["close"]
    return p4, c1


def run_a():
    res = {}
    for ds in ("hl", "bn", "bnlive"):
        if ds == "bnlive":
            p4, c1 = live_bn_panel()
        else:
            p4 = data.load_panel(ds, "4h")
            c1 = close_1h(ds)
        start = c1.index[0] + pd.Timedelta(days=2)
        for nm, (d, s, prm) in BOOKS.items():
            if d != ds:
                continue
            w = REGISTRY[s](p4, **prm)
            res[nm] = curve(w, p4["close"], c1, start=start)
            r = res[nm]
            print(f"{nm:18s} n {r['n_changes']:5d} turn/yr {r['turn_per_yr']:6.1f} chk {r['check_4h_corr']} | bp/turn " +
                  " ".join(f"+{h}h {v:+.1f}" for h, v in r["bp_per_turn"].items()) + f" | ci +1h {r['ci95'][1]} +24h {r['ci95'][24]}", flush=True)
            print(f"   by year (+1/+4/+24/+48): {r['by_year']}  hours {r['hour_of_change']}", flush=True)
        del p4, c1
    (OUT / "t9b_a.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    {"a": run_a}[sys.argv[1]]()
