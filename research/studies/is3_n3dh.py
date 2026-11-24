"""N3 d / h anchored VWAP (R45; wa 18.11.01(1)), COINS10 1h bars from 1-min klines, explore 2021-2023.
d  at each UTC day close: distance of the close from the week-to-date and month-to-date VWAP in units of the 20-day daily sd -> next
   24 h return, by distance quintile, split by volatility regime (20-day vol above / below its 1-year median). Slope sign = momentum (+)
   or reversion (-).
h  anchors: the bar of the 90-day high and of the 90-day low (as of each day), AVWAP from the anchor; first touch after price was >= 2%
   away -> 6-h return one bar late, signed away from the approach; vs AVWAP from a random anchor day in the same 90 days and vs the
   plain anchor price, compared within the same approach side.

    nice -n 19 .venv/bin/python -m research.studies.is3_n3dh    -> research/is3/N3dh__explore.json
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


def touches(c, h, l, lev, start, kind, coin, idx, out, end):
    away = False
    for t in range(start, end):
        if not away:
            away = abs(c[t] / lev - 1) >= 0.02
            continue
        if l[t] <= lev <= h[t]:
            if t + 7 < len(c):
                s = 1 if c[t - 1] > lev else -1
                out.append({"time": idx[t + 1], "coin": coin, "side": s, "kind": kind, "gross": s * (c[t + 7] / c[t + 1] - 1)})
            return


def main() -> dict:
    D, H = [], []
    rng = np.random.default_rng(5)
    for coin in L.COINS10:
        m = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet", columns=["t", "h", "l", "c", "qv"])
        m.index = pd.to_datetime(m.t, unit="ms", utc=True)
        m = m[(m.index >= "2020-01-01") & (m.index < "2024-01-10")]
        b = pd.DataFrame({"h": m.h.resample("1h").max(), "l": m.l.resample("1h").min(), "c": m.c.resample("1h").last(), "v": m.qv.resample("1h").sum()}).ffill()
        tp = (b.h + b.l + b.c) / 3
        pv = tp * b.v
        idx = b.index
        # d
        wk = idx.to_period("W").astype(str).to_numpy() if False else (idx - pd.to_timedelta(idx.weekday, unit="D")).floor("D")
        mo = idx.to_period("M").astype(str) if False else idx.strftime("%Y-%m")
        vw_w = pv.groupby(wk).cumsum() / b.v.groupby(wk).cumsum()
        vw_m = pv.groupby(mo).cumsum() / b.v.groupby(mo).cumsum()
        dc = b.c.resample("1D").last()
        sd = np.log(dc).diff().rolling(20).std()
        vol1y = sd.rolling(365, min_periods=200).median()
        f24 = b.c.shift(-24) / b.c - 1
        at = idx[idx.hour == 23]
        for t in at:
            if not (pd.Timestamp(LO, tz="UTC") <= t < pd.Timestamp(HI, tz="UTC")):
                continue
            d = t.floor("D")
            if not np.isfinite(sd.get(d, np.nan)) or not np.isfinite(f24.get(t, np.nan)):
                continue
            D.append({"time": t, "coin": coin, "zw": np.log(b.c[t] / vw_w[t]) / sd[d], "zm": np.log(b.c[t] / vw_m[t]) / sd[d],
                      "hivol": bool(sd[d] > vol1y.get(d, np.nan)), "f24": f24[t]})
        # h
        c, hh, ll = b.c.to_numpy(), b.h.to_numpy(), b.l.to_numpy()
        cpv, cv = np.cumsum(pv.to_numpy()), np.cumsum(b.v.to_numpy())
        days = pd.date_range(LO, HI, freq="7D", tz="UTC")              # one anchor set per week (avoid overlapping duplicates)
        for d in days:
            t0 = idx.searchsorted(d)
            if t0 < 2160 or t0 + 24 * 30 >= len(c):
                continue
            w0 = t0 - 2160
            for kind, ai in (("hi", w0 + int(np.argmax(hh[w0:t0]))), ("lo", w0 + int(np.argmin(ll[w0:t0]))), ("random", int(rng.integers(w0, t0)))):
                av = (cpv[t0 - 1] - (cpv[ai - 1] if ai > 0 else 0)) / (cv[t0 - 1] - (cv[ai - 1] if ai > 0 else 0))
                touches(c, hh, ll, av, t0, f"avwap_{kind}", coin, idx, H, min(t0 + 24 * 30, len(c) - 8))
                if kind != "random":
                    touches(c, hh, ll, hh[ai] if kind == "hi" else ll[ai], t0, f"price_{kind}", coin, idx, H, min(t0 + 24 * 30, len(c) - 8))
    res = {}
    d = pd.DataFrame(D)
    for z in ("zw", "zm"):
        for reg, x in d.groupby("hivol"):
            q = pd.qcut(x[z].rank(method="first"), 5, labels=False)
            means = [round(float(x[q == i].f24.mean() * 1e4), 1) for i in range(5)]
            top, bot = x[q == 4], x[q == 0]
            s = L.stats(top.assign(side=1, gross=top.f24)[COLS], bot.assign(side=1, gross=bot.f24)[COLS], reps=500)
            res[f"d_{z}_{'hivol' if reg else 'lovol'}"] = {"f24_by_distance_quintile_bp": means, "top_minus_bottom_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
            print(z, reg, res[f"d_{z}_{'hivol' if reg else 'lovol'}"])
    h = pd.DataFrame(H)
    h["m"] = h.side
    for kind in ("avwap_hi", "avwap_lo"):
        real = h[h.kind == kind]
        for pk in ("avwap_random", "price_" + kind.split("_")[1]):
            pool = h[h.kind == pk]
            base = L.matched(real, pool, k=3)
            s = L.stats(real[COLS], base[COLS], reps=500)
            res[f"h_{kind}_vs_{pk}"] = {"n": s["n"], "real_bp": s["mean_bp"], "base_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
            print(kind, pk, res[f"h_{kind}_vs_{pk}"])
    (ROOT / "research/is3/N3dh__explore.json").write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    main()
