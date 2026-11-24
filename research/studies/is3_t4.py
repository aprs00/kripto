"""T4: exits as decisions, not timers, on the LIVE trade (T1k30 ladder, one-bar-late fills, data/is3/e2_k-30.parquet).

Explore = fills of 2021-2023. Entry = the resting bid p (limit). Baseline exit = market at the close 61 min after the
fill (the live rule, h60). Rules fixed before the run (research/is3/notes.md, T4 think-through); every decision uses
closed bars and acts at the NEXT close (one bar late):
  a  stall: from fill+2, leave once (i) the last 2 closes made no new high above the post-fill high and (ii) up-minute
     volume < down-minute volume over the last 5 minutes; cap 240 min.
  a2 the same, but not before 15 min (lets the first spring play out).
  b  first opposite climax: leave after a new down-climax (1-min log return <= -4 x 24-h sigma on >= 5 x 24-h mean volume); cap 240.
  c  hindsight bounds within 240 min: best high (unattainable), best close (oracle).
All exits pay the same one round trip, so gross differences are net differences.

    nice -n 19 .venv/bin/python -m research.studies.is3_t4      -> research/is3/T4__exits.json + cards
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L
from research.studies import is3_ladtop as T

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "is3" / "T4__exits.json"
CAP = 240


def exits_for(x: pd.DataFrame, fills: pd.DataFrame) -> list[dict]:
    c, h, l, v = (x[k].to_numpy() for k in ("c", "h", "l", "qv"))
    r = np.diff(np.log(c), prepend=np.nan)
    sig = pd.Series(r).rolling(1440, min_periods=720).std().shift(1).to_numpy()
    vb = pd.Series(v).rolling(1440, min_periods=720).mean().shift(1).to_numpy()
    clim = (r <= -4 * sig) & (v >= 5 * vb)
    up = np.r_[False, c[1:] > c[:-1]]
    out = []
    for _, f in fills.iterrows():
        t = x.index.get_indexer([f.time])[0]
        if t < 0 or t + CAP + 2 >= len(c):
            continue
        p = c[t - 2] * (1 - f.depth)                     # the resting bid (quote from the close two bars back)
        row = {"time": f.time, "coin": f.coin, "side": 1, "base": c[t + 61] / p - 1, "h60_check": f.h60}
        hi = -np.inf
        ex = {"a": None, "a2": None, "b": None}
        for j in range(t + 1, t + CAP + 1):
            prev_hi = hi
            hi = max(hi, h[j])
            if j >= t + 2:
                stall = c[j] <= prev_hi and c[j - 1] <= max(prev_hi, -np.inf) and \
                    v[j - 4:j + 1][up[j - 4:j + 1]].sum() < v[j - 4:j + 1][~up[j - 4:j + 1]].sum()
                if stall and ex["a"] is None:
                    ex["a"] = j + 1
                if stall and ex["a2"] is None and j >= t + 15:
                    ex["a2"] = j + 1
            if clim[j] and j > t and ex["b"] is None:
                ex["b"] = j + 1
        for k, j in ex.items():
            j = j if j is not None else t + CAP + 1
            row[k] = c[j] / p - 1
            row[f"{k}_min"] = j - t
        row["c_high"] = h[t + 1:t + CAP + 1].max() / p - 1
        row["c_close"] = c[t + 1:t + CAP + 2].max() / p - 1
        out.append(row)
    return out


def main() -> None:
    f = pd.read_parquet(ROOT / "data/is3/e2_k-30.parquet")
    f = f[f.time < pd.Timestamp("2024-01-01", tz="UTC")]
    lo, hi = pd.Timestamp("2021-01-01", tz="UTC"), pd.Timestamp("2024-01-01", tz="UTC")
    rows = []
    for coin, g in f.groupby("coin"):
        for x in T.series(coin, lo, hi):
            gg = g[(g.time >= x.index[0]) & (g.time <= x.index[-1])]
            if len(gg):
                rows += exits_for(x, gg)
    R = pd.DataFrame(rows).sort_values("time").reset_index(drop=True)
    tm = R.time.astype("int64").to_numpy()
    R["breadth"] = np.searchsorted(tm, tm + 120 * 10**9, side="right") - np.searchsorted(tm, tm - 120 * 10**9, side="left")
    R.to_parquet(ROOT / "data/is3/t4_exits.parquet")
    chk = (R.base - R.h60_check).abs().max()
    print(f"fills {len(f)} explore, evaluated {len(R)}; baseline reproduces stored h60 to {chk:.2e}")
    res = {"n": int(len(R)), "h60_check_maxdiff": float(chk)}
    cols = ["time", "coin", "side", "gross"]
    base = R.assign(gross=R.base)[cols]
    for k in ("a", "a2", "b"):
        e = R.assign(gross=R[k])[cols]
        s = L.stats(e, base, reps=2000)
        res[k] = {kk: s[kk] for kk in ("mean_bp", "median_bp", "win", "p", "vs_base_bp", "p_vs_base", "mde80_bp", "mean_ex_top3_bp", "by_year")} | {"median_hold_min": float(R[f"{k}_min"].median())}
        print(f"exit {k:3s}: {s['mean_bp']:+.1f} bp (median {s['median_bp']:+.1f}, win {s['win']:.0%}) vs base {s['base_bp']:+.1f} -> diff {s['vs_base_bp']:+.1f} (p {s['p_vs_base']:.3f}, mde {s['mde80_bp']:.0f}); median hold {R[f'{k}_min'].median():.0f} min; years {s['by_year']}")
    lone = R.breadth < 3
    R["d"] = np.where(lone, R.a2, R.base)
    s = L.stats(R.assign(gross=R.d)[cols], base, reps=2000)
    res["d"] = {kk: s[kk] for kk in ("mean_bp", "p", "vs_base_bp", "p_vs_base", "mde80_bp", "by_year")} | {"lone_share": float(lone.mean()),
               "lone_base_bp": round(R.base[lone].mean() * 1e4, 1), "lone_a2_bp": round(R.a2[lone].mean() * 1e4, 1),
               "cascade_base_bp": round(R.base[~lone].mean() * 1e4, 1), "cascade_a2_bp": round(R.a2[~lone].mean() * 1e4, 1)}
    print(f"exit d (a2 on lone fills, timer on cascades): {s['mean_bp']:+.1f} vs base -> diff {s['vs_base_bp']:+.1f} (p {s['p_vs_base']:.3f}, mde {s['mde80_bp']:.0f}); "
          f"lone {lone.mean():.0%}: base {res['d']['lone_base_bp']} / a2 {res['d']['lone_a2_bp']} | cascade: base {res['d']['cascade_base_bp']} / a2 {res['d']['cascade_a2_bp']}")
    res["c"] = {"base_bp": round(R.base.mean() * 1e4, 1), "best_close_bp": round(R.c_close.mean() * 1e4, 1), "best_high_bp": round(R.c_high.mean() * 1e4, 1)}
    print(f"bound c: base {res['c']['base_bp']} bp, oracle best close {res['c']['best_close_bp']} bp, best high {res['c']['best_high_bp']} bp")
    OUT.write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
