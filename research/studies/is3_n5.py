"""N5 (R6, R8, R9 remaining forms), COINS10 Binance 1-min klines, explore 2021-2023.
a  5-min moves >= 4 x 24-h sigma: trades per bp of move in the coin's lowest 30-day quintile ('empty' by participation) -> fade 15 / 60
   min one bar late, vs same coin, same move-size bin, normal trade count.
b  1h / 4h: drift up (10-bar return > 1 sd x sqrt(10)) with the last 5 bars' volume < 0.7 x the first 5 bars' -> long 6 bars, vs the
   same drift on rising volume; squeeze bar (>= 2 sd up) without a volume candle (< 1.5 x median) vs with one (>= 3 x) -> fade 6 bars.
c  1h / 4h new 20-bar low on thin volume (< median of 24 bars) vs heavy (>= 2 x): lower low within 24 bars, and the 24-bar return.

    nice -n 19 .venv/bin/python -m research.studies.is3_n5      -> research/is3/N5__explore.json
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


def main() -> dict:
    A, B, C = [], [], []
    for coin in L.COINS10:
        m = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet", columns=["t", "h", "l", "c", "qv", "n"])
        m.index = pd.to_datetime(m.t, unit="ms", utc=True)
        m = m[(m.index >= "2020-11-01") & (m.index < "2024-01-10")]
        # a
        c5 = m.c.resample("5min").last().ffill(); n5 = m.n.resample("5min").sum()
        r5 = np.log(c5).diff()
        sig = r5.rolling(288, min_periods=144).std().shift(1)
        z = r5 / sig
        tpb = n5 / (r5.abs() * 1e4)
        tq = tpb.rolling(8640, min_periods=2000).rank(pct=True).shift(0)
        cv = c5.to_numpy()
        for i in np.flatnonzero((z.abs() >= 4).to_numpy()):
            t = c5.index[i]
            if not (pd.Timestamp(LO, tz="UTC") <= t < pd.Timestamp(HI, tz="UTC")) or i + 14 >= len(cv) or not np.isfinite(tq.iloc[i]):
                continue
            s = -int(np.sign(z.iloc[i]))
            A.append({"time": t, "coin": coin, "side": s, "emp": bool(tq.iloc[i] <= 0.2), "m": int(min(abs(z.iloc[i]), 9)),
                      "f15": s * (cv[i + 4] / cv[i + 1] - 1), "f60": s * (cv[i + 13] / cv[i + 1] - 1)})
        for tf in ("1h", "4h"):
            c = m.c.resample(tf).last().ffill(); v = m.qv.resample(tf).sum(); l = m.l.resample(tf).min()
            r = np.log(c).diff(); sd = r.rolling(240, min_periods=100).std().shift(1)
            f6 = c.shift(-6) / c - 1; f24 = c.shift(-24) / c - 1
            r10 = np.log(c / c.shift(10))
            vfall = v.rolling(5).sum() < 0.7 * v.shift(5).rolling(5).sum()
            vrise = v.rolling(5).sum() > 1.3 * v.shift(5).rolling(5).sum()
            drift = r10 > sd * np.sqrt(10)
            med = v.rolling(24).median().shift(1)
            sq = r >= 2 * sd
            df = pd.DataFrame({"time": c.index, "coin": coin, "tf": tf, "drift_vfall": (drift & vfall).to_numpy(), "drift_vrise": (drift & vrise).to_numpy(),
                               "sq_novol": (sq & (v < 1.5 * med)).to_numpy(), "sq_vol": (sq & (v >= 3 * med)).to_numpy(), "f6": f6.to_numpy()})
            B.append(df[(df.time >= LO) & (df.time < HI)].dropna())
            low20 = l.shift(1).rolling(20).min()
            newlow = l < low20
            ll_after = l[::-1].rolling(24, min_periods=1).min()[::-1].shift(-1)
            cdf = pd.DataFrame({"time": c.index, "coin": coin, "tf": tf, "thin": (newlow & (v < med)).to_numpy(), "heavy": (newlow & (v >= 2 * med)).to_numpy(),
                                "lower": (ll_after < l).to_numpy(), "f24": f24.to_numpy()})
            C.append(cdf[(cdf.time >= LO) & (cdf.time < HI)].dropna())
    res = {}
    a = pd.DataFrame(A)
    for H in ("f15", "f60"):
        ev, pool = a[a.emp], a[~a.emp]
        base = L.matched(ev, pool, k=3)
        s = L.stats(ev.assign(gross=ev[H])[COLS], base.assign(gross=base[H])[COLS], reps=1000)
        res[f"a_empty_by_tradecount_fade_{H}"] = {"n": s["n"], "mean_bp": s["mean_bp"], "matched_normal_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"], "by_year": s["by_year"]}
    b = pd.concat(B)
    for tf in ("1h", "4h"):
        x = b[b.tf == tf]
        for ev_col, base_col, side, nm in (("drift_vfall", "drift_vrise", 1, "drift_falling_vs_rising_volume_long"), ("sq_novol", "sq_vol", -1, "squeeze_without_vs_with_volume_fade")):
            e, bb = x[x[ev_col].astype(bool)], x[x[base_col].astype(bool)]
            s = L.stats(e.assign(side=side, gross=e.f6 * side)[COLS], bb.assign(side=side, gross=bb.f6 * side)[COLS], reps=500)
            res[f"b_{tf}_{nm}"] = {"n": s["n"], "mean_bp": s["mean_bp"], "n_base": int(len(bb)), "base_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
    cc = pd.concat(C)
    for tf in ("1h", "4h"):
        x = cc[cc.tf == tf]
        th, hv = x[x.thin.astype(bool)], x[x.heavy.astype(bool)]
        s = L.stats(th.assign(side=1, gross=th.lower.astype(float))[COLS], hv.assign(side=1, gross=hv.lower.astype(float))[COLS], reps=500)
        s2 = L.stats(th.assign(side=1, gross=th.f24)[COLS], hv.assign(side=1, gross=hv.f24)[COLS], reps=500)
        res[f"c_{tf}_thin_vs_heavy_low"] = {"n_thin": s["n"], "n_heavy": int(len(hv)), "lower_low_24_thin": round(float(th.lower.mean()), 4), "lower_low_24_heavy": round(float(hv.lower.mean()), 4),
                                            "diff_pp": round(s["vs_base_bp"] / 100, 2), "p": s["p_vs_base"], "f24_thin_bp": s2["mean_bp"], "f24_heavy_bp": s2["base_bp"], "f24_diff_bp": s2["vs_base_bp"], "f24_p": s2["p_vs_base"]}
    for k_, v_ in res.items():
        print(k_, {kk: vv for kk, vv in v_.items() if kk != "by_year"})
    (ROOT / "research/is3/N5__explore.json").write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    main()
