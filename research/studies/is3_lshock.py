"""InSilico third pass, item L1: the liquidation fade forms that were planned and never run (research/is3/notes.md).

  nice -n 19 .venv/bin/python -m research.studies.is3_lshock build [workers]     # trigger table, all 83 coins -> data/is3/lshock.parquet
  nice -n 19 .venv/bin/python -m research.studies.is3_lshock checks              # null data + causality
  nice -n 19 .venv/bin/python -m research.studies.is3_lshock explore

Trigger = a "climax" minute: log return <= -z_min x trailing-24h sigma on >= 5 x trailing-24h mean volume. Two kinds of rows:
kind "rev": the author's entry (first up minute that takes back the climax body on less volume), reversal 1..5 minutes after the
climax; kind "any": the close of the minute after the climax whatever happened (the matched baseline: it fell as much, no pattern).
Every row stores the author's-exit P&L for entries 0 / 1 / 2 / 5 minutes late, plain holds, adverse excursion and the BTC hedge.
All returns simple, in the direction of a LONG (mirror triggers side = -1 are stored for the short side too).
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from kripto import data
from kripto import events as ev
from research.studies import is3_lib as L

OUT = data.DATA / "is3"
LAGS, HOLDS = (0, 1, 2, 5), (5, 15, 60, 240)
ZMIN, M = 4.0, 5.0


def path(h, l, c, te, side, targets, stop, hold, skip=0):
    """P&L of one trade entered at c[te]: half/half limit targets (trade-through 1 bp), stop as market order, time exit.
    skip = minutes after the entry in which targets cannot fill (pessimistic fills); the stop always can."""
    pe, rem, g = c[te], 1.0, 0.0
    if side * (pe - stop) <= 0 or te + hold >= len(c):
        return np.nan
    tg = [list(x) for x in targets]
    for j in range(te + 1, te + hold + 1):
        if side * (l[j] if side > 0 else h[j]) <= side * stop:
            px = min(stop, c[j - 1]) if side > 0 else max(stop, c[j - 1])
            return g + rem * side * (px / pe - 1)
        if j - te > skip:
            for x in tg:
                if x[1] > 0 and (h[j] >= x[0] * 1.0001 if side > 0 else l[j] <= x[0] * 0.9999):
                    if side * (x[0] - pe) > 0:
                        g += x[1] * side * (x[0] / pe - 1)
                    else:                                   # late entry already beyond the target: leave at this close
                        g += x[1] * side * (c[j] / pe - 1)
                    rem, x[1] = rem - x[1], 0.0
            if rem <= 1e-9:
                return g
    return g + rem * side * (c[te + hold] / pe - 1)


def triggers(c, h, l, v, idx, btc=None, sides=(1, -1), zmin=ZMIN) -> pd.DataFrame:
    """c, h, l, v: float64 arrays of one coin's gap-free minutes."""
    r = np.diff(np.log(c), prepend=np.nan)
    sig = pd.Series(r).rolling(1440, min_periods=720).std().shift(1).to_numpy()
    vb = pd.Series(v).rolling(1440, min_periods=720).mean().shift(1).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        zz, vm = r / sig, v / vb
    rows, T = [], len(c)
    org_hi, org_lo = pd.Series(h).rolling(10).max().to_numpy(), pd.Series(l).rolling(10).min().to_numpy()
    for side in sides:
        clim = np.flatnonzero((side * zz <= -zmin) & (vm >= M) & (sig > 0))
        for q in clim:
            if q + 1 >= T - 1 or q < 12:
                continue
            O = org_hi[q - 1] if side > 0 else org_lo[q - 1]
            if not np.isfinite(O):
                continue
            body = side * (c[q - 1] - c[q])
            cand = [("any", q + 1, 1)]
            for d in range(1, 6):                         # first reversal minute within 5; a bigger climax in between ends the search
                t = q + d
                if t >= T - 1:
                    break
                if side * r[t] > 0 and v[t] < v[q] and side * (c[t] - c[t - 1]) >= body:
                    cand.append(("rev", t, d))
                    break
                if v[t] > v[q]:
                    break
            for kind, t, d in cand:
                X = l[q:t + 1].min() if side > 0 else h[q:t + 1].max()
                p = c[t]
                if side * (O - p) <= 5e-4 * p:
                    continue
                mid = X + 0.5 * (O - X)
                tg = [(mid, 0.5), (O, 0.5)] if side * (mid - p) > 0 else [(O, 1.0)]
                st = X * (1 - side * 1e-4)
                row = {"time": idx[t], "kind": kind, "side": side, "d": d, "z": -side * zz[q], "vm": vm[q], "fall": side * np.log(O / X), "sig": sig[q]}
                for lag in LAGS:
                    row[f"x{lag}"] = path(h, l, c, min(t + lag, T - 1), side, tg, st, 60) if t + lag < T else np.nan
                row["x1s"] = path(h, l, c, min(t + 1, T - 1), side, tg, st, 60, skip=1)
                for hh in HOLDS:
                    row[f"h{hh}"] = side * (c[t + hh] / p - 1) if t + hh < T else np.nan
                    if btc is not None:
                        row[f"b{hh}"] = side * (btc[t + hh] / btc[t] - 1) if t + hh < T else np.nan
                w = slice(t + 1, min(t + 61, T))
                row["mae"] = (l[w].min() / p - 1) if side > 0 else (p / h[w].max() - 1)
                # form c: first up-close minute after volume fell below half of the peak minute of the cascade (within 60 min)
                pk, e2 = v[q], None
                for j in range(q + 1, min(q + 61, T - 1)):
                    pk = max(pk, v[j])
                    if v[j] < 0.5 * pk and side * r[j] > 0:
                        e2 = j
                        break
                row["end_wait"] = (e2 - q) if e2 is not None else np.nan
                if e2 is not None:
                    X2 = l[q:e2 + 1].min() if side > 0 else h[q:e2 + 1].max()
                    row["end_x"] = path(h, l, c, e2, side, [(X2 + 0.5 * (O - X2), 0.5), (O, 0.5)] if side * (X2 + 0.5 * (O - X2) - c[e2]) > 0 else [(O, 1.0)],
                                        X2 * (1 - side * 1e-4), 60)
                    for hh in (60, 240):
                        row[f"end_h{hh}"] = side * (c[e2 + hh] / c[e2] - 1) if e2 + hh < T else np.nan
                    w2 = slice(e2 + 1, min(e2 + 61, T))
                    row["end_mae"] = (l[w2].min() / c[e2] - 1) if side > 0 else (c[e2] / h[w2].max() - 1)
                rows.append(row)
    return pd.DataFrame(rows)


def one(coin: str) -> pd.DataFrame:
    P = data.load_bn_minute_panel([coin])
    idx = P["close"].index
    b = data.load_bn_minute_panel(["BTC"])["close"]["BTC"].reindex(idx).ffill().to_numpy(dtype=float)
    c, h, l, v = (P[k][coin].to_numpy(dtype=np.float64) for k in ("close", "high", "low", "volume"))
    t = triggers(c, h, l, v, idx, b)
    day = pd.Series(v, idx).resample("1D").sum()
    t["dv30"] = day.rolling(30, min_periods=5).mean().shift(1).reindex(t["time"].dt.floor("D")).to_numpy()
    t["slip"] = ev.slip_per_day(P["volume"])[coin].reindex(t["time"].dt.floor("D")).to_numpy()
    t["coin"] = coin
    t["m"] = pd.cut(t["z"], [0, 5, 6, 8, 10, 15, 1e9], labels=False)
    print(coin, len(t), flush=True)
    return t


def coins() -> list[str]:
    return sorted(p.stem[:-4] for p in (data.DATA / "bn" / "klines_1m").glob("*USDT.parquet"))


def build(workers=3):
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(workers) as ex:
        t = pd.concat(ex.map(one, coins())).sort_values(["time", "coin"]).reset_index(drop=True)
    # causal breadth: coins with a climax (z >= 6) in the 30 min up to and including the entry minute
    a = t[(t.kind == "any") & (t.z >= 6)]
    for side in (1, -1):
        x = a[a.side == side]
        tm, cn = x["time"].to_numpy(), x["coin"].to_numpy()
        m = t.side == side
        hi = np.searchsorted(tm, t.loc[m, "time"].to_numpy(), side="right")
        lo = np.searchsorted(tm, (t.loc[m, "time"] - pd.Timedelta("30min")).to_numpy(), side="right")
        t.loc[m, "breadth"] = [len(set(cn[i:j])) for i, j in zip(lo, hi)]
    t.to_parquet(OUT / "lshock.parquet")
    print(len(t), "rows", t.groupby(["kind", "side"]).size().to_dict())


def checks():
    P = data.load_bn_minute_panel(["BTC", "DOGE", "AVAX"])
    P = {k: x[(x.index >= "2021-03-01") & (x.index < "2021-09-01")].astype("float64") for k, x in P.items()}

    def fn(p, zmin=4.0):
        out = []
        for k in p["close"]:
            t = triggers(*(p[f][k].to_numpy(dtype=float) for f in ("close", "high", "low", "volume")), p["close"].index, sides=(1,), zmin=zmin)
            if len(t):
                t = t[(t.kind == "rev") & t.x0.notna()]
                out.append(t.assign(coin=k, gross=t.x0))
        return pd.concat(out) if out else pd.DataFrame(columns=["time", "coin", "side", "gross"])
    L.null_check(fn, P, n=20)
    L.check_causal(fn, P, "2021-06-15")
    e = fn(P)
    print("real data, same sample:", len(e), round(e.gross.mean() * 1e4, 1), "bp")


# ------------------------------------------------------------------------------------------------ judging the forms
def sample(t: pd.DataFrame, s: str) -> pd.DataFrame:
    lo, hi = (pd.Timestamp(x, tz="UTC") for x in L.SAMPLES[s])
    t = t[(t.time >= lo) & (t.time < hi)]
    if s in ("explore", "confirmT"):
        return t[t.coin.isin(L.COINS10)]
    return t[~t.coin.isin(L.COINS10)] if s == "confirmC" else t


def rows(t, col, extra_bp=0.0, fee_bp=10.0):
    """One event per coin and 60 minutes; cost = taker both sides + modelled slippage both sides + extra per side."""
    x = t[t[col].notna()].sort_values(["coin", "time"])
    x = x[~(x.groupby("coin")["time"].diff() < pd.Timedelta("60min"))]
    return x.assign(gross=x[col], cost=(fee_bp + 2 * extra_bp) / 1e4 + 2 * x.slip)


def explore(s="explore", prefix="L1", zs=(4, 6, 8, 10)):
    T = pd.read_parquet(OUT / "lshock.parquet")
    t = sample(T, s)
    R, A = t[(t.kind == "rev") & (t.side == 1)], t[(t.kind == "any") & (t.side == 1)]
    note = "base/unconditional z>=8 was seen on all coins and years in passes 1-2"
    print("== reference: d=1 (old definition), author exit, entry at the close")
    for z in zs:
        L.card(f"{prefix}ref_z{z}", rows(R[(R.d == 1) & (R.z >= z)], "x0"), s, base=rows(A[A.z >= z], "x0"), note=note)
    print("== a: pessimistic fills (z >= 8, d = 1)")
    q = R[(R.d == 1) & (R.z >= 8)]
    for col in ("x0", "x1", "x1s", "x2", "x5"):
        for ex in (0, 30, 50):
            L.card(f"{prefix}a_{col}_{ex}", rows(q, col, ex), s, note=f"entry {col}, +{ex} bp per side; {note}")
    print("== b: cascade-only by breadth (z >= 6)")
    q = R[(R.d == 1) & (R.z >= 6)]
    for lo, hi in ((1, 2), (3, 4), (5, 9), (10, 19), (20, 99)):
        L.card(f"{prefix}b_{lo}", rows(q[(q.breadth >= lo) & (q.breadth <= hi)], "x1"), s, note=f"breadth {lo}-{hi}, entry 1 min late")
    L.card(f"{prefix}b", rows(q[q.breadth >= 5], "x1"), s, base=rows(A[(A.z >= 6) & (A.breadth >= 5)], "x1"), note="breadth >= 5, 1 min late; base = same cascade, no reversal bar")
    print("== c: wait for the end of the cascade (z >= 6 and 8), vs entering at the first reversal")
    for z in (6, 8):
        q = A[A.z >= z]
        L.card(f"{prefix}c_z{z}", rows(q, "end_x"), s, base=rows(R[(R.d == 1) & (R.z >= z)], "x0"), note="base = the reversal-bar entry")
        print("   adverse excursion bp: end", round(q.end_mae.mean() * 1e4), "reversal", round(R[(R.d == 1) & (R.z >= z)].mae.mean() * 1e4), "any", round(q.mae.mean() * 1e4),
              "| median wait", q.end_wait.median(), "min")
    print("== e: exits (z >= 8, d = 1)")
    q = R[(R.d == 1) & (R.z >= 8)]
    for col in ("x0", "h5", "h15", "h60", "h240"):
        L.card(f"{prefix}e_{col}", rows(q, col), s, note=f"exit {col}")
    print("== f: hedged with BTC (alts only, z >= 8)")
    q = R[(R.d == 1) & (R.z >= 8) & (R.coin != "BTC")]
    for hh in (15, 60, 240):
        x = rows(q.assign(hx=q[f"h{hh}"] - q[f"b{hh}"]), "hx", fee_bp=20.0)
        L.card(f"{prefix}f_{hh}", x, s, note=f"long coin, short BTC, {hh} min; BTC leg alone {q[f'b{hh}'].mean() * 1e4:+.0f} bp")
    print("== g: liquidity terciles (z >= 6)")
    q = R[(R.d == 1) & (R.z >= 6)]
    k = q.groupby(q.time.dt.to_period("Q").astype(str))["dv30"].transform(lambda x: pd.qcut(x.rank(method="first"), 3, labels=False) if len(x) > 2 else 1)
    for i, nm in enumerate(("thin", "mid", "liquid")):
        L.card(f"{prefix}g_{nm}", rows(q[k == i], "x1"), s, note=f"{nm} tercile, 1 min late")
    print("== h: reversal 2-5 minutes after the climax")
    for z in (6, 8):
        L.card(f"{prefix}h_z{z}", rows(R[(R.d >= 2) & (R.z >= z)], "x0"), s, base=rows(A[A.z >= z], "x0"), note="d = 2..5")
        L.card(f"{prefix}h_all_z{z}", rows(R[R.z >= z], "x1"), s, note="d = 1..5, 1 min late")
    print("== short side (mirror, z >= 8)")
    L.card(f"{prefix}short_z8", rows(T[lambda d: d.index.isin(t.index) & (d.kind == "rev") & (d.side == -1) & (d.d == 1) & (d.z >= 8)], "x0"), s)


def premium(s="explore"):
    """Form d: split by the perp's discount to its index. Daily premiumIndexKlines files (public archive), only for trigger days."""
    import io
    import time
    import zipfile

    import requests
    t = sample(pd.read_parquet(OUT / "lshock.parquet"), s)
    R = t[(t.kind == "rev") & (t.side == 1) & (t.z >= 6)].copy()
    cache = OUT / "premium.json"
    import json
    got = json.loads(cache.read_text()) if cache.exists() else {}
    for (coin, day), g in R.groupby(["coin", R.time.dt.strftime("%Y-%m-%d")]):
        if f"{coin}|{day}" in got:
            continue
        u = f"https://data.binance.vision/data/futures/um/daily/premiumIndexKlines/{coin}USDT/1m/{coin}USDT-1m-{day}.zip"
        try:
            r = requests.get(u, timeout=60)
        except requests.RequestException:
            continue
        if r.ok:
            z = zipfile.ZipFile(io.BytesIO(r.content))
            rows_ = [x.split(",") for x in z.read(z.namelist()[0]).decode().splitlines() if x[:1].isdigit()]
            got[f"{coin}|{day}"] = {str(int(float(x[0]) // 60000)): [float(x[3]), float(x[4])] for x in rows_}
        else:
            got[f"{coin}|{day}"] = {}
        time.sleep(0.5)
    cache.write_text(json.dumps(got))
    lowp, nowp = [], []
    for tm, coin in zip(R.time, R.coin):
        d = got.get(f"{coin}|{tm.strftime('%Y-%m-%d')}", {})
        m = int(tm.timestamp() // 60)
        x = [d[str(k)] for k in range(m - 6, m + 1) if str(k) in d]
        pre = [d[str(k)][1] for k in range(m - 60, m - 10) if str(k) in d]
        lowp.append(min(a for a, _ in x) - np.median(pre) if len(x) >= 5 and len(pre) >= 20 else np.nan)
        nowp.append(x[-1][1] if x else np.nan)
    R["dprem"], R["prem"] = lowp, nowp
    print(f"premium found for {R.dprem.notna().sum()}/{len(R)} triggers; drop vs the hour before, deciles bp:", (R.dprem.quantile([.1, .25, .5, .75, .9]) * 1e4).round(1).to_dict())
    q = R[R.dprem.notna()]
    for nm, g in (("deep", q[q.dprem <= q.dprem.quantile(1 / 3)]), ("mid", q[(q.dprem > q.dprem.quantile(1 / 3)) & (q.dprem <= q.dprem.quantile(2 / 3))]), ("none", q[q.dprem > q.dprem.quantile(2 / 3)])):
        L.card(f"L1d_{nm}", rows(g, "x1"), s, note=f"tercile of premium drop, z>=6, d 1-5, 1 min late; mean z {g.z.mean():.1f}, fall {g.fall.mean() * 1e4:.0f} bp")
    print("does the discount add to the size of the fall? rank corr of x1 with dprem / fall / z:",
          [round(float(q[["x1", k]].corr(method="spearman").iloc[0, 1]), 2) for k in ("dprem", "fall", "z")])
    res = q.assign(f3=pd.qcut(q.fall.rank(method="first"), 3, labels=["small", "mid", "big"]))
    print(res.groupby(["f3", res.dprem <= res.dprem.median()], observed=True)["x1"].agg(["size", lambda x: round(x.mean() * 1e4)]))


def confirm():
    """The two frozen forms (research/is3/prereg.json: L1h, L1f). One run per sample."""
    T = pd.read_parquet(OUT / "lshock.parquet")
    for s in ("confirmT", "confirmC"):
        t = sample(T, s)
        R, A = t[(t.kind == "rev") & (t.side == 1) & (t.z >= 8)], t[(t.kind == "any") & (t.side == 1) & (t.z >= 8)]
        L.card("L1h", rows(R, "x1"), s, base=rows(A, "x1"), note="z>=8, reversal 1-5 min after the climax, entry 1 min late, author exit")
        for col, ex in (("x1", 30), ("x2", 0), ("x2", 30)):       # secondary, reported, not part of the rule
            q = L.stats(rows(R, col, ex), reps=500)
            print(f"   L1h stress {col} +{ex} bp/side: net {q['net_bp']['own_cost']:+.1f} bp, ex-top3 gross {q['mean_ex_top3_bp']}")
        q = R[(R.coin != "BTC") & (R.d == 1)]
        L.card("L1f", rows(q.assign(hx=q.h15 - q.b15), "hx", fee_bp=20.0), s, note="z>=8, d=1, long coin short BTC, 15 min, four taker legs")
        x = rows(R, "x1")
        for nm, g in (("breadth<20", x[x.breadth < 20]), ("breadth>=20", x[x.breadth >= 20])):
            print(f"   L1h {nm}: n={len(g)} days={g.time.dt.floor('D').nunique()} mean {g.gross.mean() * 1e4:+.0f} bp, net {(g.gross - g.cost).mean() * 1e4:+.0f}")


if __name__ == "__main__":
    {"build": lambda: build(int(sys.argv[2]) if len(sys.argv) > 2 else 3), "checks": checks, "explore": explore, "confirm": confirm, "premium": premium}[sys.argv[1]]()
