"""InSilico third pass, item T1: resting bids (and offers) k sigma away from the last close, re-quoted every minute.

  nice -n 19 .venv/bin/python -m research.studies.is3_ladder build [workers]    # fills of all coins -> data/is3/ladder.parquet
  nice -n 19 .venv/bin/python -m research.studies.is3_ladder checks
  nice -n 19 .venv/bin/python -m research.studies.is3_ladder explore

A fill: during minute t the low trades at least THROUGH bp beyond limit = close[t-1] * (1 - k * sig[t-1]), sig = trailing-24h std
of 1-min log returns, known at t-1. The entry price is the limit (no improvement). After the fill, exits are measured from minute
t+1 on (minute t's path after the fill is unknown, so nothing good may happen in it): holds of 5/15/60/240 min as taker, and the
author's two levels as resting offers. One open position per coin. Entry maker 2 bp; taker exit 5 bp + modelled slippage.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from kripto import data
from kripto import events as ev
from research.studies import is3_lib as L
from research.studies.is3_lshock import coins, path, sample

OUT = data.DATA / "is3"
KS, HOLDS = (6, 8, 10, 12, 15, 20, 30), (1, 5, 15, 60, 240)


def fills(c, h, l, v, idx, through=10e-4, sides=(1, -1), ks=KS) -> pd.DataFrame:
    r = np.diff(np.log(c), prepend=np.nan)
    sig = pd.Series(r).rolling(1440, min_periods=720).std().to_numpy()
    vb = pd.Series(v).rolling(1440, min_periods=720).mean().to_numpy()
    hi10, lo10 = pd.Series(h).rolling(10).max().to_numpy(), pd.Series(l).rolling(10).min().to_numpy()
    r60 = pd.Series(np.log(c)).diff(60).to_numpy()
    T, rows = len(c), []
    cp, sp = np.roll(c, 1), np.roll(sig, 1)
    for side in sides:
        for k in ks:
            lim = cp * (1 - side * k * sp)
            hit = (l <= lim * (1 - through)) if side > 0 else (h >= lim * (1 + through))
            last = -1
            for t in np.flatnonzero(hit & (sp > 0)):
                if t < 12 or t <= last or t + 241 >= T:
                    continue
                p, O = lim[t], (hi10[t - 1] if side > 0 else lo10[t - 1])
                row = {"time": idx[t], "side": side, "k": k, "sig": sp[t], "depth": k * sp[t], "r60": side * r60[t - 1], "vm": v[t] / vb[t - 1],
                       "through": side * (p - (l[t] if side > 0 else h[t])) / p, "close_vs": side * (c[t] / p - 1)}
                for hh in HOLDS:
                    row[f"h{hh}"] = side * (c[t + hh] / p - 1)
                # author's exits as resting offers from t+1, no stop for 240 min, then out at the close; entry price = the limit, not the close
                mid, g, rem = p + 0.5 * (O - p), 0.0, 1.0
                for tp, f in ((mid, 0.5), (O, 0.5)):
                    w = h[t + 1:t + 241] if side > 0 else l[t + 1:t + 241]
                    ok = (w >= tp * 1.0001) if side > 0 else (w <= tp * 0.9999)
                    g += f * side * ((tp if ok.any() else c[t + 240]) / p - 1)
                row["x240"] = g
                w = slice(t + 1, t + 61)
                row["mae60"] = (l[w].min() / p - 1) if side > 0 else (p / h[w].max() - 1)
                rows.append(row)
                last = t + 60
    return pd.DataFrame(rows)


def one(coin):
    P = data.load_bn_minute_panel([coin])
    idx = P["close"].index
    t = fills(*(P[k][coin].to_numpy(dtype=np.float64) for k in ("close", "high", "low", "volume")), idx)
    t["slip"] = ev.slip_per_day(P["volume"])[coin].reindex(t["time"].dt.floor("D")).to_numpy()
    t["coin"] = coin
    print(coin, len(t), flush=True)
    return t


def build(workers=3):
    with ProcessPoolExecutor(workers) as ex:
        t = pd.concat(ex.map(one, coins())).sort_values(["time", "coin"]).reset_index(drop=True)
    # breadth known BEFORE the fill: other coins with a k>=6 fill in the 30 minutes up to the previous minute
    for side in (1, -1):
        a = t[(t.side == side) & (t.k == 6)]
        tm, cn = a["time"].to_numpy(), a["coin"].to_numpy()
        m = t.side == side
        hi = np.searchsorted(tm, t.loc[m, "time"].to_numpy(), side="left")
        lo = np.searchsorted(tm, (t.loc[m, "time"] - pd.Timedelta("30min")).to_numpy(), side="left")
        t.loc[m, "breadth"] = [len(set(cn[i:j])) for i, j in zip(lo, hi)]
    t.to_parquet(OUT / "ladder.parquet")
    print(len(t), t.groupby(["side", "k"]).size().to_dict())


def rows(t, col, maker_exit=False):
    c = 4e-4 if maker_exit else 7e-4 + t.slip
    return t.assign(gross=t[col], cost=c)[t[col].notna()]


def explore(s="explore", prefix="T1"):
    t = sample(pd.read_parquet(OUT / "ladder.parquet"), s)
    for side, nm in ((1, "bid"), (-1, "offer")):
        print(f"== a: {nm}s k sigma away, exit after 1/5/15/60/240 min (gross bp, net of maker entry + taker exit)")
        for k in KS:
            q = t[(t.side == side) & (t.k == k)]
            if len(q) < 10:
                continue
            r = {h: L.stats(rows(q, f"h{h}"), reps=400) for h in HOLDS}
            print(f"  k={k:2d} n={len(q):6d} days={r[60]['days']} depth {q.depth.median() * 1e4:.0f} bp, mae60 {q.mae60.mean() * 1e4:+.0f} |",
                  " | ".join(f"h{h} {x['mean_bp']:+.0f} net {x['net_bp']['own_cost']:+.0f} (p {x['p']:.2f}, ex3 {x['mean_ex_top3_bp']:+.0f})" for h, x in r.items()))
        for k in (8, 12, 20):
            q = t[(t.side == side) & (t.k == k)]
            if len(q) >= 30:
                L.card(f"{prefix}a_{nm}_k{k}", rows(q, "h60"), s, note="hold 60")
                L.card(f"{prefix}b_{nm}_k{k}", rows(q, "x240", True), s, note="author levels as resting offers, 240 min cap")
        print("== c: by breadth before the fill")
        for k in (8, 12):
            q = t[(t.side == side) & (t.k == k)]
            for lo, hi in ((0, 0), (1, 4), (5, 19), (20, 99)):
                g = q[(q.breadth >= lo) & (q.breadth <= hi)]
                if len(g) >= 20:
                    L.card(f"{prefix}c_{nm}_k{k}_b{lo}", rows(g, "h60"), s, note=f"breadth {lo}-{hi}")


def checks():
    P = data.load_bn_minute_panel(["BTC", "DOGE", "AVAX"])
    P = {k: x[(x.index >= "2021-03-01") & (x.index < "2021-09-01")].astype("float64") for k, x in P.items()}

    def fn(p):
        out = [fills(*(p[f][k].to_numpy(dtype=float) for f in ("close", "high", "low", "volume")), p["close"].index, sides=(1,), ks=(8,)).assign(coin=k) for k in p["close"]]
        return pd.concat(out).assign(gross=lambda d: d.h60)
    L.null_check(fn, P, n=20)
    L.check_causal(fn, P, "2021-06-15")


if __name__ == "__main__":
    {"build": lambda: build(int(sys.argv[2]) if len(sys.argv) > 2 else 3), "checks": checks, "explore": explore}[sys.argv[1]]()
