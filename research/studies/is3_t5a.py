"""T5a: all 1-min moves >= 3 sigma (no volume filter), fade vs continuation by context, explore (COINS10, 2021-2023).

Event: minute q with |log r| >= 3 x 24-h sigma (shift 1). Decision at the close of q+1 (one bar late); outcome = simple
return over 15 / 60 min in the FADE direction (side = -sign(move)). One event per coin per 15 min (first one).
Features known at the decision: z (|r|/sigma), vm (volume / 24-h mean), taker (taker-buy share of the move minute, signed
toward the move: > 0.5 = takers pushed it), tpb (trades per bp of move), lvl_d (distance of the move's extreme to the prior
UTC-day high (up moves) / low (down moves) in sigma, negative = beyond it), lvl_w (same for the prior 7 days), rnd
(distance of the extreme to the nearest 1/2/5 x 10^k level, in sigma), ats (average trade size of the move minute / its
24-h average: > 1 = few large trades, < 1 = many small = T5b), hour, trend (24-h return signed toward the move),
breadth (COINS10 with >= 3 sigma in the same direction in the same minute).

    nice -n 19 .venv/bin/python -m research.studies.is3_t5a build    -> data/is3/t5a.parquet
    nice -n 19 .venv/bin/python -m research.studies.is3_t5a curves   -> research/is3/T5a__curves.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "data/is3/t5a.parquet"
OUT = ROOT / "research/is3/T5a__curves.json"
LO, HI = "2021-01-01", "2024-01-01"
FEATS = ["z", "vm", "taker", "tpb", "ats", "lvl_d", "lvl_w", "rnd", "hour", "trend", "breadth"]


def round_dist(x: np.ndarray) -> np.ndarray:
    e = np.floor(np.log10(x))
    cands = np.stack([m * 10 ** (e + s) for s in (-1, 0, 1) for m in (1, 2, 5)], axis=1)
    return np.abs(cands - x[:, None]).min(axis=1)


def one(coin: str) -> pd.DataFrame:
    k = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet")
    k.index = pd.to_datetime(k.t, unit="ms", utc=True)
    k = k[(k.index >= pd.Timestamp(LO, tz="UTC") - pd.Timedelta("8D")) & (k.index < pd.Timestamp(HI, tz="UTC") + pd.Timedelta("1D"))]
    k = k.asfreq("1min")
    c = k.c.ffill().to_numpy(); h = k.h.fillna(k.c.ffill()).to_numpy(); l = k.l.fillna(k.c.ffill()).to_numpy()
    v = k.qv.fillna(0).to_numpy(); n = k.n.fillna(0).to_numpy(); tb = k.tbqv.fillna(0).to_numpy()
    r = np.diff(np.log(c), prepend=np.nan)
    sig = pd.Series(r).rolling(1440, min_periods=720).std().shift(1).to_numpy()
    vb = pd.Series(v).rolling(1440, min_periods=720).mean().shift(1).to_numpy()
    nb = pd.Series(n).rolling(1440, min_periods=720).mean().shift(1).to_numpy()
    day = k.index.floor("D")
    dh = pd.Series(h, index=k.index).groupby(day).max(); dl = pd.Series(l, index=k.index).groupby(day).min()
    pdh = dh.shift(1).reindex(day).to_numpy(); pdl = dl.shift(1).reindex(day).to_numpy()
    wh = dh.shift(1).rolling(7).max().reindex(day).to_numpy(); wl = dl.shift(1).rolling(7).min().reindex(day).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        z = np.abs(r) / sig
    cand = np.flatnonzero((z >= 3) & np.isfinite(z) & (np.arange(len(c)) + 61 < len(c)))
    rows, last = [], -10**9
    for q in cand:
        if q - last < 15 or q < 1440:
            continue
        last = q
        s = int(np.sign(r[q]))            # move direction
        ext = h[q] if s > 0 else l[q]
        p = c[q + 1]
        sg = sig[q] * c[q]
        rows.append({"time": k.index[q + 1], "coin": coin, "side": -s, "z": z[q], "vm": v[q] / vb[q] if vb[q] > 0 else np.nan,
                     "taker": (tb[q] / v[q] if s > 0 else 1 - tb[q] / v[q]) if v[q] > 0 else np.nan,
                     "tpb": n[q] / (abs(r[q]) * 1e4),
                     "ats": (v[q] / n[q]) / (vb[q] / nb[q]) if n[q] > 0 and nb[q] > 0 and vb[q] > 0 else np.nan,
                     "lvl_d": ((pdh[q] - ext) if s > 0 else (ext - pdl[q])) / sg, "lvl_w": ((wh[q] - ext) if s > 0 else (ext - wl[q])) / sg,
                     "rnd": round_dist(np.array([ext]))[0] / sg, "hour": k.index[q].hour, "trend": s * (c[q] / c[q - 1440] - 1),
                     "f15": -s * (c[q + 16] / p - 1), "f60": -s * (c[q + 61] / p - 1), "dirq": s})
    e = pd.DataFrame(rows)
    return e[(e.time >= LO) & (e.time < HI)]


def build() -> None:
    e = pd.concat([one(c) for c in L.COINS10], ignore_index=True)
    key = e.time.dt.floor("min").astype("int64").astype(str) + e.dirq.astype(str)
    e["breadth"] = key.map(key.value_counts())
    e.to_parquet(TAB)
    print(len(e), e.groupby("coin").size().to_dict())


def curves() -> None:
    e = pd.read_parquet(TAB)
    res = {"n": int(len(e)), "all": {}}
    for H in ("f15", "f60"):
        s = L.stats(e.assign(gross=e[H])[["time", "coin", "side", "gross"]], reps=500)
        res["all"][H] = {"mean_bp": s["mean_bp"], "ci95_bp": s["ci95_bp"]}
    print(f"all events n={len(e)}: fade 15 min {res['all']['f15']['mean_bp']:+.1f} bp, 60 min {res['all']['f60']['mean_bp']:+.1f} bp")
    for f in FEATS:
        x = e.dropna(subset=[f])
        nb = 10 if x[f].nunique() > 10 else x[f].nunique()
        x = x.assign(b=pd.qcut(x[f].rank(method="first"), nb, labels=False))
        cv = []
        for b, g in x.groupby("b"):
            s = L.stats(g.assign(gross=g.f60)[["time", "coin", "side", "gross"]], reps=300)
            cv.append({"b": int(b), "lo": round(float(g[f].min()), 3), "hi": round(float(g[f].max()), 3), "n": s["n"], "mean_bp": s["mean_bp"], "ci95_bp": s["ci95_bp"]})
        means = [c["mean_bp"] for c in cv]
        rho = float(pd.Series(means).corr(pd.Series(range(len(means))), method="spearman"))
        res[f] = {"curve": cv, "spearman": rho, "spread_bp": round(means[-1] - means[0], 1)}
        print(f"{f:8s} rho {rho:+.2f} spread {means[-1]-means[0]:+6.1f} | " + " ".join(f"{m:+.0f}" for m in means))
    OUT.write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    {"build": build, "curves": curves}[sys.argv[1]]()
