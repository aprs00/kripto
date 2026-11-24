"""N1 round numbers (R26; tg:119 'hundy roll', wa 18.10.24(1)). Round = one significant digit (d x 10^k); placebo = the level 37% of the
way to the next round level (same geometry, not round). Explore 2021-2023.
a  daily, bnall clean, half-0 coins in the point-in-time top 100: close enters 2-3% below a level from below while above its close 20 days
   earlier -> +6% before -3% (daily highs/lows, 30 days, same day both = 0.5).
b  1-min COINS10: first touch after price was >= 2% away; 60-min return one bar late signed away from the approach; side-matched.
c  daily: first close 1-2% beyond a level after crossing it -> back to the level within 5 days.

    nice -n 19 .venv/bin/python -m research.studies.is3_n1      -> research/is3/N1__explore.json
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


def levels(lo: float, hi: float) -> tuple[np.ndarray, np.ndarray]:
    out = []
    for k in range(int(np.floor(np.log10(lo))) - 1, int(np.ceil(np.log10(hi))) + 1):
        out += [d * 10.0 ** k for d in range(1, 10)]
    r = np.array(sorted(set(out)))
    nxt = np.append(r[1:], r[-1] * 2)
    plc = r + 0.37 * (nxt - r)
    keep = (r >= lo / 1.2) & (r <= hi * 1.2)
    return r[keep], plc[keep]


def daily_forms() -> tuple[list, list]:
    p = data.load_panel("bnall", "1d")
    c, h, l, v = p["close"], p["high"], p["low"], p["volume"]
    top = v.rolling(30, min_periods=20).mean().shift(1).rank(axis=1, ascending=False) <= 100
    A, C = [], []
    for coin in c.columns:
        if L.half(coin) != 0 or not top[coin].loc[LO:HI].any():
            continue
        cc, hh, ll, tt = c[coin].to_numpy(), h[coin].to_numpy(), l[coin].to_numpy(), top[coin].to_numpy()
        idx = c.index
        ok = np.isfinite(cc)
        if ok.sum() < 60:
            continue
        R, PL = levels(np.nanmin(cc[ok]), np.nanmax(cc[ok]))
        for kind, lv in (("real", R), ("placebo", PL)):
            for Lv in lv:
                for t in range(21, len(cc) - 31):
                    if not (tt[t] and idx[t] >= pd.Timestamp(LO, tz="UTC") and idx[t] < pd.Timestamp(HI, tz="UTC")) or not np.isfinite(cc[t - 1] + cc[t]):
                        continue
                    # a
                    if 0.97 * Lv <= cc[t] <= 0.98 * Lv and cc[t - 1] < 0.97 * Lv and cc[t] > cc[t - 20]:
                        up, dn = cc[t] * 1.06, cc[t] * 0.97
                        res = np.nan
                        for j in range(t + 1, t + 31):
                            u, d_ = hh[j] >= up, ll[j] <= dn
                            if u and d_:
                                res = 0.5; break
                            if u or d_:
                                res = float(u); break
                        if np.isfinite(res):
                            A.append({"time": idx[t], "coin": coin, "side": 1, "kind": kind, "hit": res})
                    # c (both directions)
                    for s in (1, -1):
                        if s * (cc[t - 1] - Lv) < 0 and 1.01 <= (cc[t] / Lv) ** s <= 1.02:
                            back = bool((ll[t + 1:t + 6] <= Lv).any()) if s > 0 else bool((hh[t + 1:t + 6] >= Lv).any())
                            C.append({"time": idx[t], "coin": coin, "side": s, "kind": kind, "back": float(back)})
    return A, C


def form_b() -> list:
    B = []
    for coin in L.COINS10:
        k = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet", columns=["t", "h", "l", "c"])
        k.index = pd.to_datetime(k.t, unit="ms", utc=True)
        k = k[(k.index >= LO) & (k.index < HI)].dropna()
        h, l, c = k.h.to_numpy(), k.l.to_numpy(), k.c.to_numpy()
        R, PL = levels(c.min(), c.max())
        for kind, lv in (("real", R), ("placebo", PL)):
            for Lv in lv:
                touch = (l <= Lv) & (h >= Lv)
                far = np.abs(c / Lv - 1) >= 0.02
                state = np.where(touch, 1, np.where(far, 2, 0)).astype(np.int8)
                last = pd.Series(np.where(state > 0, state, np.nan)).ffill().shift(1).to_numpy()
                ev = np.flatnonzero(touch & (last == 2))
                for t in ev:
                    if t < 1 or t + 62 >= len(c):
                        continue
                    s = 1 if c[t - 1] > Lv else -1
                    B.append({"time": k.index[t + 1], "coin": coin, "side": s, "kind": kind, "m": s, "gross": s * (c[t + 61] / c[t + 1] - 1)})
    return B


def main() -> dict:
    res = {}
    A, C = daily_forms()
    a = pd.DataFrame(A)
    re_, pl = a[a.kind == "real"], a[a.kind == "placebo"]
    s = L.stats(re_.assign(gross=re_.hit)[["time", "coin", "side", "gross"]], pl.assign(gross=pl.hit)[["time", "coin", "side", "gross"]], reps=1000)
    res["a_hundy_roll_6_before_3"] = {"n_real": int(len(re_)), "n_placebo": int(len(pl)), "real": round(float(re_.hit.mean()), 4), "placebo": round(float(pl.hit.mean()), 4),
                                      "random_walk": 0.333, "diff_pp": round(s["vs_base_bp"] / 100, 2), "p": s["p_vs_base"], "mde_pp": round(s["mde80_bp"] / 100, 2)}
    cdf = pd.DataFrame(C)
    for sd in (1, -1):
        re_, pl = cdf[(cdf.kind == "real") & (cdf.side == sd)], cdf[(cdf.kind == "placebo") & (cdf.side == sd)]
        s = L.stats(re_.assign(gross=re_.back)[["time", "coin", "side", "gross"]], pl.assign(gross=pl.back)[["time", "coin", "side", "gross"]], reps=1000)
        res[f"c_overshoot_return_{'up' if sd > 0 else 'down'}"] = {"n_real": int(len(re_)), "real": round(float(re_.back.mean()), 4), "placebo": round(float(pl.back.mean()), 4),
                                                                    "diff_pp": round(s["vs_base_bp"] / 100, 2), "p": s["p_vs_base"], "mde_pp": round(s["mde80_bp"] / 100, 2)}
    b = pd.DataFrame(form_b())
    re_, pl = b[b.kind == "real"], b[b.kind == "placebo"]
    base = L.matched(re_, pl, k=3)
    s = L.stats(re_[["time", "coin", "side", "gross"]], base[["time", "coin", "side", "gross"]], reps=1000)
    res["b_first_touch_r60_side_matched"] = {"n_real": s["n"], "real_bp": s["mean_bp"], "placebo_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"],
                                             "by_side_real": s["by_side"]}
    for k_, v_ in res.items():
        print(k_, v_)
    (ROOT / "research/is3/N1__explore.json").write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    main()
