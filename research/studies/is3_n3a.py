"""N3 a successive swings (R37/R38): zigzag with a 2 x ATR14 reversal threshold on COINS10 1h / 4h closes, explore 2021-2023.
At the bar that CONFIRMS a swing high (price 2 ATR below it), compare the last up-swing with the previous one: 'weakening' = smaller
(size) or slower (size per bar). Outcome = short return over the next 6 / 24 bars from that confirmation close. Baseline = the same
confirmations where the last up-swing was larger (or faster). Mirror for swing lows (long). Day-block bootstrap.

    nice -n 19 .venv/bin/python -m research.studies.is3_n3a     -> research/is3/N3a__explore.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
LO, HI = "2021-01-01", "2024-01-01"
COLS = ["time", "coin", "side", "gross"]


def zigzag(c: np.ndarray, atr: np.ndarray):
    """yields (confirm_index, pivot_index, pivot_type) with pivot_type +1 = high, -1 = low."""
    out, mode, ext_i = [], 0, 0
    for t in range(1, len(c)):
        if not np.isfinite(atr[t]):
            continue
        if mode >= 0 and c[t] > c[ext_i] if mode == 1 else False:
            ext_i = t
        if mode == 0:
            if c[t] > c[ext_i] + 2 * atr[t]:
                mode, ext_i = 1, t
            elif c[t] < c[ext_i] - 2 * atr[t]:
                mode, ext_i = -1, t
            continue
        if mode == 1:
            if c[t] > c[ext_i]:
                ext_i = t
            elif c[t] < c[ext_i] - 2 * atr[t]:
                out.append((t, ext_i, 1)); mode, ext_i = -1, t
        else:
            if c[t] < c[ext_i]:
                ext_i = t
            elif c[t] > c[ext_i] + 2 * atr[t]:
                out.append((t, ext_i, -1)); mode, ext_i = 1, t
    return out


def main() -> dict:
    rows = []
    for coin in L.COINS10:
        m = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet", columns=["t", "c"])
        m.index = pd.to_datetime(m.t, unit="ms", utc=True)
        m = m[(m.index >= "2020-11-01") & (m.index < "2024-01-10")]
        for tf in ("1h", "4h"):
            c = m.c.resample(tf).last().ffill()
            cv = c.to_numpy()
            atr = pd.Series(np.abs(np.diff(cv, prepend=np.nan))).rolling(14).mean().to_numpy()
            piv = zigzag(cv, atr)
            for n in range(3, len(piv)):
                t, pi, typ = piv[n]
                prev_opp = piv[n - 1]                      # the pivot before (opposite type)
                same_prev, opp_prev2 = piv[n - 2], piv[n - 3]
                if not (prev_opp[2] == -typ and same_prev[2] == typ and opp_prev2[2] == -typ):
                    continue
                last = abs(cv[pi] - cv[prev_opp[1]]); last_bars = max(pi - prev_opp[1], 1)
                prev = abs(cv[same_prev[1]] - cv[opp_prev2[1]]); prev_bars = max(same_prev[1] - opp_prev2[1], 1)
                if t + 25 >= len(cv) or not (LO <= str(c.index[t]) < HI):
                    continue
                side = -typ                                 # after a swing high: short
                rows.append({"time": c.index[t], "coin": coin, "tf": tf, "side": side, "smaller": last < prev, "slower": last / last_bars < prev / prev_bars,
                             "f6": side * (cv[t + 6] / cv[t] - 1), "f24": side * (cv[t + 24] / cv[t] - 1)})
    e = pd.DataFrame(rows)
    res = {}
    for tf in ("1h", "4h"):
        for crit in ("smaller", "slower", "both"):
            x = e[e.tf == tf]
            flag = (x.smaller & x.slower) if crit == "both" else x[crit]
            for H in ("f6", "f24"):
                a, b = x[flag], x[~flag]
                s = L.stats(a.assign(gross=a[H])[COLS], b.assign(gross=b[H])[COLS], reps=500)
                res[f"{tf}_{crit}_{H}"] = {"n_weak": s["n"], "weak_bp": s["mean_bp"], "n_strong": int(len(b)), "strong_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
                print(tf, crit, H, res[f"{tf}_{crit}_{H}"])
    (ROOT / "research/is3/N3a__explore.json").write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    main()
