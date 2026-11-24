"""O1 oscillators: pinned extremes mean trend (R29; tg:86, 91-92; wa 18.10.36/37). Explore 2021-2023.
Panels: COINS10 1h and 4h (Binance 1-min klines), bnall daily top-100 by trailing 30-d volume (clean universe). RSI14 (Wilder).
Baseline for every form: same coin, same decile of the trailing 14-bar return (the thing RSI is built from), 3 matched bars.

a  RSI > 70 for k = 1/3/6 bars in a row (the bar the run reaches k) -> long H bars; mirror RSI < 30 -> short.
b  re-entry: RSI was > 70 within 10 bars, dipped into 55-70 without touching 50, turns up -> long.
c  failed reversal signals: RSI crosses down through 70 and price makes a new 20-bar high within 10 bars = a failed signal; at the
   3rd failure within 40 bars -> long, vs at the 1st failure.
d  RSI falls through 50 after > 70 within 20 bars -> short (his 'return from the extreme to the mean is the signal').
e  filter: the live ladder's explore fills (T1k30, data/is3/e2_k-30.parquet) by the coin's daily RSI at the prior close.

    nice -n 19 .venv/bin/python -m research.studies.is3_o1     -> research/is3/O1__explore.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from kripto import data
from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
LO, HI = "2021-01-01", "2024-01-01"
HZ = {"1h": (6, 24), "4h": (6, 18), "1d": (5, 10)}


def rsi(c: pd.DataFrame, n: int = 14) -> pd.DataFrame:
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def panels() -> dict:
    out = {}
    cols = {}
    for coin in L.COINS10:
        k = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet", columns=["t", "c"])
        k.index = pd.to_datetime(k.t, unit="ms", utc=True)
        cols[coin] = k.c[(k.index >= "2020-11-01") & (k.index < "2024-01-15")]
    m = pd.DataFrame(cols)
    out["1h"] = m.resample("1h").last()
    out["4h"] = m.resample("4h").last()
    p = data.load_panel("bnall", "1d")
    c, v = p["close"], p["volume"]
    top = v.rolling(30, min_periods=20).mean().shift(1).rank(axis=1, ascending=False) <= 100
    out["1d"] = c.where(top)[(c.index >= "2020-09-01") & (c.index < "2024-02-01")]
    return out


def long_frame(c: pd.DataFrame) -> pd.DataFrame:
    r = rsi(c)
    ret14 = c / c.shift(14) - 1
    f = {}
    for H in sorted({h for hz in HZ.values() for h in hz}):
        f[H] = c.shift(-H) / c - 1
    x = pd.DataFrame({"rsi": r.stack(future_stack=True), "ret14": ret14.stack(future_stack=True), **{f"f{H}": f[H].stack(future_stack=True) for H in f}})
    x.index.names = ["time", "coin"]
    return x.reset_index()


def events(c: pd.DataFrame, tf: str) -> pd.DataFrame:
    r = rsi(c)
    rows = []
    for coin in c.columns:
        x = r[coin].to_numpy(); p = c[coin].to_numpy(); idx = c.index
        hi20 = pd.Series(p).rolling(20).max().to_numpy()
        run_up = run_dn = 0
        fails = []
        sig_open = []
        for t in range(25, len(x) - 1):
            if not np.isfinite(x[t]) or not np.isfinite(p[t]):
                run_up = run_dn = 0
                continue
            run_up = run_up + 1 if x[t] > 70 else 0
            run_dn = run_dn + 1 if x[t] < 30 else 0
            for kk in (1, 3, 6):
                if run_up == kk:
                    rows.append((idx[t], coin, f"a_up_k{kk}", 1))
                if run_dn == kk:
                    rows.append((idx[t], coin, f"a_dn_k{kk}", -1))
            w = x[max(0, t - 10):t]
            if (w > 70).any() and 55 <= x[t - 1] < 70 and x[t] > x[t - 1]:
                last70 = t - 10 + int(np.flatnonzero(w > 70)[-1]) if t >= 10 else 0
                if (x[last70:t] >= 50).all() and x[t - 1] == x[last70 + 1:t].min():
                    rows.append((idx[t], coin, "b_reentry", 1))
            if x[t - 1] > 70 >= x[t]:
                sig_open.append(t)
            sig_open = [s for s in sig_open if t - s <= 10]
            if sig_open and p[t] >= hi20[t - 1] and np.isfinite(hi20[t - 1]):
                fails.append(t); sig_open = []
                fails = [f_ for f_ in fails if t - f_ <= 40]
                rows.append((idx[t], coin, f"c_fail{min(len(fails), 3)}", 1))
            if x[t - 1] >= 50 > x[t] and (x[max(0, t - 20):t] > 70).any():
                rows.append((idx[t], coin, "d_to_mean_short", -1))
    e = pd.DataFrame(rows, columns=["time", "coin", "form", "side"])
    return e[(e.time >= LO) & (e.time < HI)]


def run() -> dict:
    res = {}
    P = panels()
    for tf, c in P.items():
        lf = long_frame(c)
        lf = lf[(lf.time >= LO) & (lf.time < HI)].dropna(subset=["ret14", "rsi"])
        lf["m"] = (lf.groupby("coin").ret14.rank(pct=True) * 9.999).astype(int)
        ev = events(c, tf).merge(lf, on=["time", "coin"], how="inner")
        res[tf] = {}
        for form, x in ev.groupby("form"):
            ekey = set(zip(x.time, x.coin))
            pool = lf[[(t, k) not in ekey for t, k in zip(lf.time, lf.coin)]] if len(lf) < 3_000_000 else lf
            base = L.matched(x, pool, k=3)
            out = {}
            for H in HZ[tf]:
                xs = x.dropna(subset=[f"f{H}"]); bs = base.dropna(subset=[f"f{H}"])
                s = L.stats(xs.assign(gross=xs[f"f{H}"] * xs.side)[["time", "coin", "side", "gross"]],
                            bs.assign(side=int(xs.side.iloc[0]), gross=bs[f"f{H}"] * int(xs.side.iloc[0]))[["time", "coin", "side", "gross"]], reps=500)
                out[f"H{H}"] = {"n": s["n"], "mean_bp": s["mean_bp"], "matched_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
            res[tf][form] = out
            h0 = f"H{HZ[tf][0]}"
            print(tf, form, out[h0])
    # e: ladder fills by the coin's daily RSI at the previous close
    f = pd.read_parquet(ROOT / "data/is3/e2_k-30.parquet")
    f = f[(f.time >= LO) & (f.time < HI)]
    r1 = rsi(data.load_panel("bnall", "1d")["close"]).shift(1)
    f["rsi_d"] = [r1[cn].get(dy, np.nan) if cn in r1.columns else np.nan for cn, dy in zip(f.coin, f.day)]
    f = f.dropna(subset=["rsi_d"])
    groups = {"rsi<30 (pinned down)": f.rsi_d < 30, "30-50": (f.rsi_d >= 30) & (f.rsi_d < 50), ">=50": f.rsi_d >= 50}
    res["e_ladder_fills_by_daily_rsi"] = {}
    for nm, msk in groups.items():
        x = f[msk]
        s = L.stats(x.assign(side=1, gross=x.h60)[["time", "coin", "side", "gross"]], reps=500)
        res["e_ladder_fills_by_daily_rsi"][nm] = {"n": s["n"], "h60_bp": s["mean_bp"], "ci95_bp": s["ci95_bp"]}
    a, b = f[f.rsi_d < 30], f[f.rsi_d >= 30]
    s = L.stats(a.assign(side=1, gross=a.h60)[["time", "coin", "side", "gross"]], b.assign(side=1, gross=b.h60)[["time", "coin", "side", "gross"]], reps=1000)
    res["e_pinned_down_vs_rest"] = {"diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
    print("e", res["e_ladder_fills_by_daily_rsi"], res["e_pinned_down_vs_rest"])
    return res


if __name__ == "__main__":
    r = run()
    (ROOT / "research/is3/O1__explore.json").write_text(json.dumps(r, indent=1, default=float))
