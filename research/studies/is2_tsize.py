"""InSilico second pass, trade-size buckets as ABNORMAL flow (research/insilico_pass2.md section 1, T1-T3, T6). Descriptive.

  nice -n 19 .venv/bin/python -m research.studies.is2_tsize [explore|confirm]

First pass: the sign of each bucket's delta, every day. Here: each bucket's delta/volume as a z-score against its own trailing
90 days (removes the structural sell bias of a hedging venue), and the event is conditioned on where it happens.
T1  big down day (<= -1.5 daily sigma) on which every bucket is abnormally negative (z < -1) vs other big down days.
T2  the same inside an uptrend (yesterday's close above its 50-day mean).
T3  big down day where large trades (>= 110k USD) bought abnormally while small ones (< 30k) sold abnormally, and the mirror.
T6  big up day on which every bucket is abnormally positive vs other big up days (continuation; feeds the `flow` book).
Forward close-to-close log returns in bp, before costs. Sample explore = 2021-01..2023-12, BTC ETH SOL.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from kripto import data, tsize

SAMPLES = {"explore": ("2021-01-01", "2024-01-01"), "confirm": ("2024-01-01", "2026-11-01")}


def tstat(x) -> float:
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


def welch(a, b) -> float:
    a, b = pd.Series(a).dropna(), pd.Series(b).dropna()
    if len(a) < 3 or len(b) < 3:
        return float("nan")
    return float((a.mean() - b.mean()) / np.sqrt(a.var() / len(a) + b.var() / len(b)))


def features(p, coin: str) -> pd.DataFrame:
    c = p["close"][coin]
    d = tsize.group(p["ts_delta"][coin].to_numpy(float), "author7")
    v = tsize.group(p["ts_vol"][coin].to_numpy(float), "author7")
    x = pd.DataFrame(np.where(v > 0, d / np.where(v > 0, v, 1), np.nan), c.index)
    z = (x - x.rolling(90, min_periods=45).mean().shift(1)) / x.rolling(90, min_periods=45).std().shift(1)
    live = pd.DataFrame(v / v.sum(axis=1, keepdims=True) >= 0.01, c.index)
    r = np.log(c / c.shift(1))
    sig = r.rolling(30, min_periods=15).std().shift(1)
    zs = z.where(live)
    big = np.where(v[:, 3:].sum(axis=1) > 0, d[:, 3:].sum(axis=1) / np.where(v[:, 3:].sum(axis=1) > 0, v[:, 3:].sum(axis=1), 1), np.nan)
    big = pd.Series(big, c.index)
    zbig = (big - big.rolling(90, min_periods=45).mean().shift(1)) / big.rolling(90, min_periods=45).std().shift(1)
    tot = pd.Series(d.sum(axis=1) / v.sum(axis=1), c.index)
    ztot = (tot - tot.rolling(90, min_periods=45).mean().shift(1)) / tot.rolling(90, min_periods=45).std().shift(1)
    f = pd.DataFrame({"coin": coin, "rz": r / sig, "all_neg": (zs.max(axis=1) < -1) & (live.sum(axis=1) >= 2),
                      "all_pos": (zs.min(axis=1) > 1) & (live.sum(axis=1) >= 2), "zsmall": z[0], "zbig": zbig, "ztot": ztot,
                      "up": (c.shift(1) > c.rolling(50).mean().shift(1))})
    for h in (1, 3, 5):
        f[f"f{h}"] = np.log(c.shift(-h) / c)
    return f


def compare(name: str, a: pd.DataFrame, b: pd.DataFrame):
    out = [f"  {name:58s} n={len(a):4d} vs {len(b):4d}"]
    for h in (1, 3, 5):
        k = f"f{h}"
        out.append(f"+{h}d {a[k].mean() * 1e4:+7.1f} vs {b[k].mean() * 1e4:+7.1f} (diff t {welch(a[k], b[k]):+.1f})")
    per = [np.sign(a[a.coin == c].f3.mean() - b[b.coin == c].f3.mean()) for c in sorted(set(a.coin)) if len(a[a.coin == c]) >= 3]
    print(" | ".join(out) + f" | coins with +3d diff > 0: {int(sum(x > 0 for x in per))}/{len(per)}")


def run(sample="explore"):
    start, end = SAMPLES[sample]
    p = data.load_bn_tsize_panel("1d")
    F = pd.concat([features(p, c) for c in p["close"].columns])
    F = F[(F.index >= start) & (F.index < end)].dropna(subset=["rz"])
    print(f"sample {sample}: {start}..{end}, coins {sorted(set(F.coin))}, coin-days {len(F)}; event group vs its matched baseline, forward returns in bp")
    dn, up = F[F.rz <= -1.5], F[F.rz >= 1.5]
    print(f"big down days {len(dn)}, of which every bucket abnormally negative {int(dn.all_neg.sum())}; big up days {len(up)}, every bucket abnormally positive {int(up.all_pos.sum())}")
    compare("T1 down day, all buckets z<-1  vs other big down days", dn[dn.all_neg], dn[~dn.all_neg])
    compare("T1b down day, total delta z<-2 vs other big down days", dn[dn.ztot < -2], dn[~(dn.ztot < -2)])
    compare("T2 in uptrend: all z<-1        vs other big down days in uptrend", dn[dn.all_neg & dn.up], dn[~dn.all_neg & dn.up])
    compare("T2b uptrend down day           vs downtrend down day", dn[dn.up], dn[~dn.up])
    compare("T3 down day: big buy, small sell vs other big down days", dn[(dn.zbig > 0.5) & (dn.zsmall < -0.5)], dn[~((dn.zbig > 0.5) & (dn.zsmall < -0.5))])
    compare("T3m down day: big sell, small buy vs other big down days", dn[(dn.zbig < -0.5) & (dn.zsmall > 0.5)], dn[~((dn.zbig < -0.5) & (dn.zsmall > 0.5))])
    compare("T6 up day, all buckets z>+1    vs other big up days", up[up.all_pos], up[~up.all_pos])
    compare("T6b up day: big buy z>1        vs other big up days", up[up.zbig > 1], up[~(up.zbig > 1)])
    compare("any day all z<-1               vs all other days", F[F.all_neg], F[~F.all_neg])
    compare("any day all z>+1               vs all other days", F[F.all_pos], F[~F.all_pos])
    compare("big down days                  vs all other days", dn, F[F.rz > -1.5])
    return F


def intraday(sample="explore"):
    """T4 rotation exhaustion on 5-minute bars: at a 1-day high, a bar whose size buckets are ALL abnormally negative
    ("price go up, TS green, TS becomes bright red? its over"), and the mirror at a 1-day low. z-scores against the
    previous 7 days of the same bucket. Forward returns signed in the direction the author predicts (down after a top
    signal, up after a bottom signal), compared with other bars at the same location. t on daily means."""
    start, end = SAMPLES[sample]
    px = data.load_bn_minute_panel(data.TSIZE_COINS, rule="5min")
    rows = []
    for coin in px["close"].columns:
        dd, vv = tsize.frames(coin + "USDT", "author7", "5min")
        dd, vv = dd.reindex(px["close"].index), vv.reindex(px["close"].index)
        c, h, l = (px[k][coin].astype("float64") for k in ("close", "high", "low"))
        x = (dd / vv.where(vv > 0))
        z = (x - x.rolling(2016, min_periods=576).mean().shift(1)) / x.rolling(2016, min_periods=576).std().shift(1)
        live = vv.div(vv.sum(axis=1), axis=0) >= 0.02
        zs = z.where(live)
        n_live = live.sum(axis=1)
        all_neg, all_pos = (zs.max(axis=1) < -1) & (n_live >= 3), (zs.min(axis=1) > 1) & (n_live >= 3)
        at_high = c >= 0.998 * h.rolling(288).max()
        at_low = c <= 1.002 * l.rolling(288).min()
        f = pd.DataFrame({"coin": coin, "all_neg": all_neg, "all_pos": all_pos, "at_high": at_high, "at_low": at_low})
        for hh, nm in ((12, "f1h"), (48, "f4h"), (288, "f24h")):
            f[nm] = np.log(c.shift(-hh) / c)
        rows.append(f[(f.index >= start) & (f.index < end)])
    F = pd.concat(rows)
    print(f"T4 intraday, sample {sample}: {start}..{end}, coins {sorted(set(F.coin))}, 5-min bars {len(F)}")

    def cmp(name, a, b, sign):
        out = [f"  {name:62s} n={len(a):6d} vs {len(b):7d}"]
        for k in ("f1h", "f4h", "f24h"):
            da, db = sign * a[k].groupby(a.index.floor("D")).mean(), sign * b[k].groupby(b.index.floor("D")).mean()
            out.append(f"{k[1:]} {sign * a[k].mean() * 1e4:+6.1f} vs {sign * b[k].mean() * 1e4:+6.1f} (t {welch(da, db):+.1f})")
        print(" | ".join(out))
    cmp("top signal: at 1-day high, all buckets abnormally NEGATIVE (down=+)", F[F.at_high & F.all_neg], F[F.at_high & ~F.all_neg], -1)
    cmp("bottom signal: at 1-day low, all buckets abnormally POSITIVE (up=+)", F[F.at_low & F.all_pos], F[F.at_low & ~F.all_pos], 1)
    cmp("continuation check: at 1-day high, all buckets POSITIVE (up=+)", F[F.at_high & F.all_pos], F[F.at_high & ~F.all_pos], 1)
    cmp("capitulation check: at 1-day low, all buckets NEGATIVE (up=+)", F[F.at_low & F.all_neg], F[F.at_low & ~F.all_neg], 1)
    cmp("anywhere: all buckets abnormally negative (up=+)", F[F.all_neg], F[~F.all_neg], 1)
    cmp("anywhere: all buckets abnormally positive (up=+)", F[F.all_pos], F[~F.all_pos], 1)
    return F


def trap(sample="explore"):
    """Mousetrap at REAL levels (R4, second formulation): the first 5-minute bar of the day that trades below yesterday's low
    and closes back above it (mirror: above yesterday's high, closes back below). With and without the size split (small
    trades sold, large bought), and against placebo levels (yesterday's close moved by the low/close ratio of 8 days earlier).
    Forward simple returns in the direction of the trap (long after a failed break of the low), bp, t on daily means."""
    start, end = SAMPLES[sample]
    P = data.load_bn_tsize_panel("5m")
    rows = []
    for coin in P["close"].columns:
        c, h, l, v = (P[k][coin].astype("float64") for k in ("close", "high", "low", "volume"))
        ds, dl = P["d_small"][coin].astype("float64"), P["d_large"][coin].astype("float64")
        day = c.index.floor("D")
        dlo, dhi, dcl = l.groupby(day).min(), h.groupby(day).max(), c.groupby(day).last()
        heavy = v >= 2 * v.rolling(288, min_periods=144).mean().shift(1)
        for kind, lo_lvl, hi_lvl in (("real", dlo.shift(1), dhi.shift(1)),
                                     ("placebo", dcl.shift(1) * (dlo.shift(9) / dcl.shift(9)), dcl.shift(1) * (dhi.shift(9) / dcl.shift(9)))):
            for side, lvl in ((1, lo_lvl), (-1, hi_lvl)):
                L = lvl.reindex(day).to_numpy()
                t = ((l.to_numpy() < L) & (c.to_numpy() > L)) if side > 0 else ((h.to_numpy() > L) & (c.to_numpy() < L))
                ev = pd.Series(t, c.index)
                ev &= ev.groupby(day).cumsum() == 1                      # first trap of the day at that level
                f = pd.DataFrame({"coin": coin, "kind": kind, "side": side, "heavy": heavy, "split": (side * ds < 0) & (side * dl > 0)})[ev]
                for hh, nm in ((12, "f1h"), (48, "f4h"), (288, "f24h")):
                    f[nm] = side * (c.shift(-hh) / c - 1)[ev]
                rows.append(f[(f.index >= start) & (f.index < end)])
    F = pd.concat(rows)
    print(f"R4 mousetrap at yesterday's low/high, 5-min bars, sample {sample}: {start}..{end}, coins {sorted(set(F.coin))}")

    def row(name, a):
        out = [f"  {name:58s} n={len(a):5d}"]
        for k in ("f1h", "f4h", "f24h"):
            d = a[k].groupby(a.index.floor("D")).mean()
            out.append(f"{k[1:]} {a[k].mean() * 1e4:+6.1f} (t {tstat(d):+.1f})")
        print(" | ".join(out))
    for kind in ("real", "placebo"):
        a = F[F.kind == kind]
        row(f"{kind}: all failed breaks", a)
        row(f"{kind}: on heavy volume", a[a.heavy])
        row(f"{kind}: heavy volume + small sold / large bought", a[a.heavy & a.split])
        row(f"{kind}: failed break of the LOW (long)", a[a.side == 1])
        row(f"{kind}: failed break of the HIGH (short)", a[a.side == -1])
    return F


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "explore"
    if a == "trap":
        trap(sys.argv[2] if len(sys.argv) > 2 else "explore")
        sys.exit()
    if a == "intraday":
        intraday(sys.argv[2] if len(sys.argv) > 2 else "explore")
    else:
        run(a)
