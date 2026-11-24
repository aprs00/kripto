"""O2 g: Ehlers Fisher transform (length 10) turns on 1-minute bars (his original method), explore COINS10 2021-2023.
Turn up = fisher rises after falling (fish[t] > fish[t-1] < fish[t-2]) while fish[t-1] <= -X -> long; mirror -> short; X = 1.5 / 2 / 2.5
(dose). Entry one bar late (close of t+1), exit 15 / 60 min later, simple returns. Baseline: same coin, same side, minutes in the
same decile of the trailing 10-minute return (a 10% sample of all minutes as the pool), 3 per event. Costs: a taker round trip is 13 bp.

    nice -n 19 .venv/bin/python -m research.studies.is3_o2g    -> research/is3/O2g__explore.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
LO, HI = "2021-01-01", "2024-01-01"


def fisher(h: np.ndarray, l: np.ndarray, n: int = 10) -> np.ndarray:
    mid = (h + l) / 2
    mx = pd.Series(h).rolling(n).max().to_numpy(); mn = pd.Series(l).rolling(n).min().to_numpy()
    out = np.full(len(h), np.nan); v = f = 0.0
    for t in range(n, len(h)):
        rng = mx[t] - mn[t]
        x = (mid[t] - mn[t]) / rng - 0.5 if rng > 0 else 0.0
        v = min(max(0.66 * x + 0.67 * v, -0.999), 0.999)
        f = 0.5 * np.log((1 + v) / (1 - v)) + 0.5 * f
        out[t] = f
    return out


def main() -> dict:
    E, Pl = [], []
    for coin in L.COINS10:
        k = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet", columns=["t", "h", "l", "c"])
        k.index = pd.to_datetime(k.t, unit="ms", utc=True)
        k = k[(k.index >= LO) & (k.index < HI)].asfreq("1min")
        c = k.c.ffill().to_numpy(); h = k.h.fillna(k.c.ffill()).to_numpy(); l = k.l.fillna(k.c.ffill()).to_numpy()
        fz = fisher(h, l)
        r10 = np.full(len(c), np.nan); r10[10:] = c[10:] / c[:-10] - 1
        f15 = np.full(len(c), np.nan); f60 = np.full(len(c), np.nan)
        f15[:-17] = c[17:] / c[1:-16] - 1; f60[:-62] = c[62:] / c[1:-61] - 1        # entry at the close of t+1
        dec = pd.Series(r10).rank(pct=True).mul(9.999).fillna(-1).astype(int).to_numpy()
        up = (fz[2:] > fz[1:-1]) & (fz[1:-1] < fz[:-2]); dn = (fz[2:] < fz[1:-1]) & (fz[1:-1] > fz[:-2])
        ext = fz[1:-1]
        idx = k.index
        for X in (1.5, 2.0, 2.5):
            for side, m in ((1, up & (ext <= -X)), (-1, dn & (ext >= X))):
                t = np.flatnonzero(m) + 2
                t = t[np.isfinite(f60[t])]
                E.append(pd.DataFrame({"time": idx[t], "coin": coin, "side": side, "X": X, "m": dec[t], "f15": side * f15[t], "f60": side * f60[t]}))
        rng = np.random.default_rng(1)
        s = rng.choice(len(c) - 70, size=len(c) // 10, replace=False) + 20
        s = s[np.isfinite(f60[s]) & (dec[s] >= 0)]
        Pl.append(pd.DataFrame({"time": idx[s], "coin": coin, "m": dec[s], "r15": f15[s], "r60": f60[s]}))
    e = pd.concat(E, ignore_index=True); pool = pd.concat(Pl, ignore_index=True)
    res = {}
    for X in (1.5, 2.0, 2.5):
        for side in (1, -1):
            x = e[(e.X == X) & (e.side == side)]
            b = L.matched(x, pool, k=3).assign(side=side)
            out = {}
            for H in ("15", "60"):
                s = L.stats(x.assign(gross=x[f"f{H}"])[["time", "coin", "side", "gross"]], b.assign(gross=b[f"r{H}"] * side)[["time", "coin", "side", "gross"]], reps=300)
                out[f"f{H}"] = {"n": s["n"], "mean_bp": s["mean_bp"], "matched_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"], "net_taker_bp": s["net_bp"]["taker"]}
            res[f"X{X}_{'long' if side == 1 else 'short'}"] = out
            print(X, side, out)
    (ROOT / "research/is3/O2g__explore.json").write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    main()
