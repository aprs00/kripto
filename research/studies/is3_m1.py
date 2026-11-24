"""M1: rotation momentum / exhaustion on range bars (InSilico R3, tg:199-223). Explore = BTC ETH SOL 2021-23 micro bars.

a  run of r all-green range bars, entry bar closes up, (every non-empty author7 size group has delta > 0, >= 4 groups non-empty) -> long, exit at the
   first all-red bar (shorts mirror). Baseline: same r consecutive UP bars that are not all-green, same exit (m = w, r, side).
b  first all-red bar after a green run with the run's high = the 24 h (7 d) high -> short, 1/4/8 h. Baseline: other bars at the high.
c  delta share deciles -> signed 1 h return (dose); card = top decile vs middle deciles.
e  thin fast one-voiced bar (all-green, volume < median of last 20 bars, duration < median/2, delta share >= .5) -> long to first all-red.
   Baseline: all-green bars that are not thin+fast, same exit.
Null: colour labels shuffled within the day (keeps their frequency) -> a vs baseline must be ~0.
Usage: python -m research.studies.is3_m1 explore|confirmT [widths...]
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import mbars
from kripto.tsize import SCHEMES
from research.studies import is3_lib as L

COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
BAD = json.loads((L.OUT / "mbars_bad_days.json").read_text())
G7 = SCHEMES["author7"]
CAP = 500


def rbars(b: dict, width: float) -> dict:
    h, l = b["h"], b["l"]
    ends, H, Lo = [], -np.inf, np.inf
    for i in range(len(h)):
        H, Lo = max(H, h[i]), min(Lo, l[i])
        if H / Lo - 1 >= width:
            ends.append(i)
            H, Lo = -np.inf, np.inf
    e = np.asarray(ends, dtype=np.int64)
    st = np.concatenate([[0], e[:-1] + 1])
    buy, sell = np.add.reduceat(b["buy"], st, axis=0), np.add.reduceat(b["sell"], st, axis=0)
    gb = np.stack([buy[:, a:z + 1].sum(1) for a, z in G7], 1).astype(np.float64)
    gs = np.stack([sell[:, a:z + 1].sum(1) for a, z in G7], 1).astype(np.float64)
    d, v = gb - gs, gb + gs
    ne = (v > 0).sum(1)
    green = ((d > 0) | (v == 0)).all(1) & (ne >= 4)
    red = ((d < 0) | (v == 0)).all(1) & (ne >= 4)
    return {"end": e, "t0": b["t0"][st], "t1": b["t1"][e], "o": b["o"][st], "c": b["c"][e], "h": np.maximum.reduceat(h, st),
            "l": np.minimum.reduceat(l, st), "vol": v.sum(1), "ds": d.sum(1) / np.maximum(v.sum(1), 1e-9), "green": green, "red": red}


def runlen(x: np.ndarray) -> np.ndarray:
    out, k = np.zeros(len(x), dtype=np.int32), 0
    for i, v in enumerate(x):
        k = k + 1 if v else 0
        out[i] = k
    return out


def next_true(x: np.ndarray) -> np.ndarray:
    """index of the first True strictly after i (len(x) if none)."""
    nxt, out = len(x), np.empty(len(x), dtype=np.int64)
    for i in range(len(x) - 1, -1, -1):
        out[i] = nxt
        if x[i]:
            nxt = i
    return out


def rides(r: dict, entries: np.ndarray, side: int, bcl: np.ndarray) -> pd.DataFrame:
    """entries (bar idx) -> ride to the first opposite one-voiced bar (cap CAP bars)."""
    opp = r["red"] if side > 0 else r["green"]
    nx = next_true(opp)
    j = np.minimum(nx[entries], entries + CAP)
    ok = j < len(r["c"])
    i, j = entries[ok], j[ok]
    late = bcl[np.minimum(r["end"][i] + 1, len(bcl) - 1)]
    return pd.DataFrame({"time": pd.to_datetime(r["t1"][i], unit="ms", utc=True), "side": side,
                         "gross": side * (r["c"][j] / r["c"][i] - 1), "gross_late": side * (r["c"][j] / late - 1),
                         "fast": (r["t1"][i] - r["t0"][i]) < 1000, "hold_h": (r["t1"][j] - r["t1"][i]) / 3.6e6, "nb": j - i,
                         "t_exit": r["t1"][j]})


def fwd(r: dict, idx: np.ndarray, bt: np.ndarray, bcl: np.ndarray, hours: float) -> np.ndarray:
    k = np.searchsorted(bt, r["t1"][idx] + int(hours * 3.6e6))
    out = np.full(len(idx), np.nan)
    ok = k < len(bt)
    out[ok] = bcl[k[ok]] / r["c"][idx[ok]] - 1
    return out


def coin_events(sym: str, lo: str, hi: str, widths: list[float], shuffle: bool = False) -> dict:
    b = mbars.load(sym, lo, hi)
    bt, bcl = b["t1"], b["c"]
    coin = sym.replace("USDT", "")
    bad = {pd.Timestamp(x, tz="UTC") for x in BAD.get(sym, {})}
    out = {k: [] for k in ("a", "a_base", "b", "b_base", "c", "e", "e_base")}
    rng = np.random.default_rng(11)
    for w in widths:
        r = rbars(b, w)
        if shuffle:   # null: permute colour labels within each day
            day = r["t1"] // 86_400_000
            g, rd = r["green"].copy(), r["red"].copy()
            for dd in np.unique(day):
                ix = np.flatnonzero(day == dd)
                p = rng.permutation(ix)
                g[ix], rd[ix] = r["green"][p], r["red"][p]
            r["green"], r["red"] = g, rd
        up, dn = r["c"] > r["o"], r["c"] < r["o"]
        for side, col, pr in ((1, r["green"], up), (-1, r["red"], dn)):
            rl, pl = runlen(col), runlen(pr)
            for k in (1, 2, 3):
                ev = np.flatnonzero((rl == k) & pr)
                bs = np.flatnonzero(pr & ~col)
                for name, ix in (("a", ev), ("a_base", bs if k == 1 else bs[:0])):
                    d = rides(r, ix, side, bcl)
                    d["w"], d["r"], d["pl"] = w, k, np.minimum(pl[ix], 4)[:len(d)]
                    d["m"] = d["time"].dt.strftime("%Y%m%d") + "_" + str(side) + "_" + d["pl"].astype(str)
                    out[name].append(d)
            # e: thin fast one-voiced bar
            vol = pd.Series(r["vol"]).rolling(20, min_periods=20).median().shift(1).to_numpy()
            dur = pd.Series((r["t1"] - r["t0"]).astype(float)).rolling(20, min_periods=20).median().shift(1).to_numpy()
            tf = col & (r["vol"] < vol) & ((r["t1"] - r["t0"]) < dur / 2) & (side * r["ds"] >= 0.5)
            for name, ix in (("e", np.flatnonzero(tf & pr)), ("e_base", np.flatnonzero(col & ~tf & pr & ~np.isnan(vol)))):
                d = rides(r, ix, side, bcl)
                d["w"], d["r"], d["pl"] = w, 0, np.minimum(runlen(pr)[ix], 4)[:len(d)]
                d["m"] = d["time"].dt.strftime("%Y%m%d") + "_" + str(side) + "_" + d["pl"].astype(str)
                out[name].append(d)
        # b: first all-red after a green run, run high = 24 h / 7 d high
        s = pd.Series(r["h"], index=pd.to_datetime(r["t1"], unit="ms"))
        for win in ("24h", "7D"):
            hh = s.rolling(win).max().to_numpy()
            ath = r["h"] >= hh - 1e-12                         # bar printed the rolling high
            recent = pd.Series(ath).rolling(4, min_periods=1).max().to_numpy() > 0   # high set within the last 4 bars
            prev_green = np.concatenate([[False], r["green"][:-1]])
            ev = np.flatnonzero(r["red"] & prev_green & recent)
            bs = np.flatnonzero(~r["red"] & recent)
            for name, ix in (("b", ev), ("b_base", bs)):
                d = pd.DataFrame({"time": pd.to_datetime(r["t1"][ix], unit="ms", utc=True), "side": -1,
                                  **{f"g{hz}": -fwd(r, ix, bt, bcl, hz) for hz in (1, 4, 8)}})
                d["w"], d["win"], d["m"] = w, win, f"{w}_{win}"
                out[name].append(d)
        # c: delta share deciles -> signed 1 h return
        g1 = fwd(r, np.arange(len(r["c"])), bt, bcl, 1.0)
        d = pd.DataFrame({"time": pd.to_datetime(r["t1"], unit="ms", utc=True), "ds": r["ds"], "side": np.sign(r["ds"]).astype(int),
                          "gross": np.sign(r["ds"]) * g1, "w": w})
        out["c"].append(d.dropna())
    res = {}
    for k, v in out.items():
        d = pd.concat(v, ignore_index=True) if v else pd.DataFrame()
        if len(d):
            d["coin"] = coin
            d = d[~d["time"].dt.floor("D").isin(bad)]
            if "t_exit" in d:
                d = d[~pd.to_datetime(d["t_exit"], unit="ms", utc=True).dt.floor("D").isin(bad)]
        res[k] = d
    return res


def collect(lo: str, hi: str, widths: list[float], shuffle: bool = False) -> dict:
    acc = {}
    for sym in COINS:
        for y in range(int(lo[:4]), int(hi[:4])):
            a, z = max(lo, f"{y}-01-01"), min(hi, f"{y + 1}-01-01")
            try:
                res = coin_events(sym, a, z, widths, shuffle)
            except FileNotFoundError:
                continue
            for k, v in res.items():
                acc.setdefault(k, []).append(v)
            print(sym, y, {k: len(v) for k, v in res.items()}, flush=True)
    return {k: pd.concat(v, ignore_index=True) for k, v in acc.items()}


def rew(x: pd.DataFrame, y: pd.DataFrame, col: str = "gross") -> float:
    """baseline mean re-weighted to the events' mix of (coin, day, side, prior price-run length)."""
    ym = y.groupby(["coin", "m"])[col].mean()
    w = x.groupby(["coin", "m"]).size()
    k = w.index.intersection(ym.index)
    return float((ym[k] * w[k]).sum() / w[k].sum()) if len(k) else np.nan


def bp(x) -> float:
    return round(float(np.nanmean(x)) * 1e4, 1)


def report(D: dict, sample: str, card: bool = True) -> None:
    a, ab = D["a"], D["a_base"]
    print("\n== a: ride all-green run -> first all-red (mean bp | base bp | n | median hold h | late-entry mean)")
    for (w, r), x in a.groupby(["w", "r"]):
        y = ab[(ab.w == w) & (ab.r == 1)]
        print(f"w={w:.4f} r={r}: {bp(x.gross):+7.1f} | base {bp(rew(x, y)):+7.1f} late {bp(rew(x, y, 'gross_late')):+.1f} | n {len(x):6d}/{len(y):6d} | hold {x.hold_h.median():.2f}h"
              f" | late {bp(x.gross_late):+7.1f} | no-sub1s {bp(x[~x.fast].gross):+7.1f} | by yr "
              + " ".join(f"{t}:{bp(g.gross) - bp(rew(g, y[y.time.dt.year == t])):+.1f}" for t, g in x.groupby(x.time.dt.year)))
    e, eb = D["e"], D["e_base"]
    print("\n== e: thin fast one-voiced bar -> first opposite (mean | base | n)")
    for w, x in e.groupby("w"):
        y = eb[eb.w == w]
        print(f"w={w:.4f}: {bp(x.gross):+7.1f} | base {bp(rew(x, y)):+7.1f} | n {len(x)}/{len(y)} | late {bp(x.gross_late):+.1f} vs {bp(rew(x, y, 'gross_late')):+.1f} | by yr "
              + " ".join(f"{t}:{bp(g.gross) - bp(rew(g, y[y.time.dt.year == t])):+.1f}" for t, g in x.groupby(x.time.dt.year)))
    b, bb = D["b"], D["b_base"]
    print("\n== b: short first all-red after green run at the high (1/4/8 h, bp) vs other bars at the high")
    for (w, win), x in b.groupby(["w", "win"]):
        y = bb[(bb.w == w) & (bb.win == win)]
        print(f"w={w:.4f} {win}: n {len(x)} " + " ".join(f"{h}: {bp(x[h]):+.1f} vs {bp(y[h]):+.1f}" for h in ("g1", "g4", "g8")))
    c = D["c"]
    print("\n== c: |delta share| decile -> signed 1 h return (bp)")
    for w, x in c.groupby("w"):
        q = pd.qcut(x.ds.abs(), 10, labels=False, duplicates="drop")
        print(f"w={w:.4f}: " + " ".join(f"{bp(g):+.1f}" for _, g in x.groupby(q)["gross"]))
    if not card:
        return
    W = 0.0043
    x, y = a[(a.w == W) & (a.r == 1)], ab[(ab.w == W) & (ab.r == 1)]
    L.card("M1a_r1_w43", x, sample, base=L.matched(x, y), note="ride all-green -> first all-red, 0.43% bars")
    x, y = e[e.w == W], eb[eb.w == W]
    L.card("M1e_w43", x, sample, base=L.matched(x, y), note="thin fast one-voiced bar, 0.43% bars")
    x, y = b[(b.w == W) & (b.win == "24h")].assign(gross=lambda d: d.g8), bb[(bb.w == W) & (bb.win == "24h")].assign(gross=lambda d: d.g8)
    L.card("M1b_24h_w43", x.dropna(subset=["gross"]), sample, base=y.dropna(subset=["gross"]), note="short first all-red at 24h high, 8h")
    x = c[c.w == W]
    q = pd.qcut(x.ds.abs(), 10, labels=False, duplicates="drop")
    L.card("M1c_w43", x[q == q.max()], sample, base=x[(q >= 3) & (q <= 6)], note="top |delta share| decile, signed 1h")


if __name__ == "__main__":
    sample = sys.argv[1]
    widths = [float(v) for v in sys.argv[2:]] or [0.002, 0.0043, 0.008]
    if sample == "null":
        D = collect("2022-01-01", "2023-01-01", [0.0043], shuffle=True)
        report(D, "explore", card=False)
    else:
        lo, hi = L.SAMPLES[sample]
        D = collect(lo, hi, widths)
        report(D, sample)
