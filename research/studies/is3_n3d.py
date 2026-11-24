"""N3 daily forms b, e, f (tape behaviour). bnall clean, half-0 coins while in the point-in-time top 100, explore 2021-2023.
Baseline = same coin, same decile of the trailing 14-day return, 3 matched days, same side. imb = 2 x taker-buy / volume - 1,
z = (imb - 60-d mean) / 60-d sd (shift 1).
b  buyer streak (z > 0.5 for >= 3 days) whose imbalance today is positive but <= half the streak's mean -> short 3 / 5 days.
e  terminal shakeout: the low broke the prior 20-day (55-day) low within the last 3 days, today closes back above that level on the
   highest volume of 20 days -> long 5 / 10 days.
f  absorption: 3-day summed z <= -2 (heavy taker selling) with the 3-day return >= 0 -> long 3 / 5 days; dose = 3-day return tercile;
   cross-sectional version: each day regress 3-day return on 3-day z over coins, long the top-decile residual minus the bottom, 5 days.

    nice -n 19 .venv/bin/python -m research.studies.is3_n3d     -> research/is3/N3d__explore.json
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


def main() -> dict:
    p = data.load_panel("bnall", "1d")
    keep = [c for c in p["close"].columns if L.half(c) == 0]
    c, h, l, v, tb = (p[k][keep].loc["2020-06-01":"2024-02-01"] for k in ("close", "high", "low", "volume", "taker_buy"))
    top = v.rolling(30, min_periods=20).mean().shift(1).rank(axis=1, ascending=False) <= 100
    imb = 2 * tb / v - 1
    z = (imb - imb.rolling(60, min_periods=30).mean().shift(1)) / imb.rolling(60, min_periods=30).std().shift(1)
    ret14 = c / c.shift(14) - 1
    fw = {H: c.shift(-H) / c - 1 for H in (3, 5, 10)}
    fr = pd.concat({"ret14": ret14.stack(), **{f"f{H}": x.stack() for H, x in fw.items()}, "top": top.stack()}, axis=1).reset_index()
    fr.columns = ["time", "coin", "ret14", "f3", "f5", "f10", "top"]
    fr = fr[(fr.time >= LO) & (fr.time < HI) & fr.top.astype(bool)].dropna(subset=["ret14"])
    fr["m"] = (fr.groupby("coin").ret14.rank(pct=True) * 9.999).astype(int)

    def card(mask, side, nm, Hs, res):
        s_ = mask.where(top).stack()
        e = s_[s_.astype(bool)].reset_index().iloc[:, :2]
        e.columns = ["time", "coin"]
        e = e.merge(fr, on=["time", "coin"], how="inner")
        if len(e) < 20:
            res[nm] = {"n": int(len(e))}
            return e
        key = set(zip(e.time, e.coin))
        pool = fr[[(a, b) not in key for a, b in zip(fr.time, fr.coin)]]
        base = L.matched(e, pool, k=3)
        out = {}
        for H in Hs:
            x, b = e.dropna(subset=[H]), base.dropna(subset=[H])
            s = L.stats(x.assign(side=side, gross=x[H] * side)[["time", "coin", "side", "gross"]], b.assign(side=side, gross=b[H] * side)[["time", "coin", "side", "gross"]], reps=500)
            out[H] = {"n": s["n"], "mean_bp": s["mean_bp"], "matched_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"], "by_year": s["by_year"]}
            yd = {}
            for y in (2021, 2022, 2023):
                xy, by = x[x.time.dt.year == y], b[b.time.dt.year == y]
                if len(xy) > 20 and len(by) > 20:
                    sy = L.stats(xy.assign(side=side, gross=xy[H] * side)[["time", "coin", "side", "gross"]], by.assign(side=side, gross=by[H] * side)[["time", "coin", "side", "gross"]], reps=300)
                    yd[y] = {"diff_bp": sy["vs_base_bp"], "p": sy["p_vs_base"]}
            out[H]["diff_by_year"] = yd
        res[nm] = out
        print(nm, {k: {kk: vv for kk, vv in v_.items() if kk != "by_year"} for k, v_ in out.items()})
        return e

    res = {}
    # b
    pos = (z > 0.5).astype(int)
    run = pos.copy() * 0
    pv, rv = pos.to_numpy(), np.zeros(pos.shape)
    for t in range(1, len(pv)):
        rv[t] = (rv[t - 1] + 1) * pv[t]
    run.iloc[:, :] = rv
    streak_mean = imb.shift(1).rolling(3).mean()
    b_mask = (run.shift(1) >= 3) & (imb > 0) & (imb <= 0.5 * streak_mean) & (streak_mean > 0)
    card(b_mask, -1, "b_buyer_streak_halves_short", ("f3", "f5"), res)
    # e
    for n_ in (20, 55):
        prior_low = l.shift(1).rolling(n_).min()
        broke = (l < prior_low)
        lvl = prior_low.where(broke).ffill(limit=3)
        reclaim = (c > lvl) & broke.rolling(3).max().astype(bool) & (v >= v.rolling(20).max())
        card(reclaim, 1, f"e_shakeout_reclaim_{n_}d_low_record_volume", ("f5", "f10"), res)
    # f
    z3 = z.rolling(3).sum(); r3 = c / c.shift(3) - 1
    absorb = (z3 <= -2) & (r3 >= 0)
    e = card(absorb, 1, "f_absorption_long", ("f3", "f5"), res)
    if len(e) > 60:
        r3s = r3.stack().rename("r3").reset_index(); r3s.columns = ["time", "coin", "r3"]
        e = e.merge(r3s, on=["time", "coin"])
        q = pd.qcut(e.r3.rank(method="first"), 3, labels=False)
        res["f_dose_by_r3_tercile_f5_bp"] = [round(float(e[q == k].f5.mean() * 1e4), 1) for k in range(3)]
        print("f dose", res["f_dose_by_r3_tercile_f5_bp"])
    # f cross-sectional residual
    rows = []
    for d in z3.index[(z3.index >= LO) & (z3.index < HI)]:
        xs = pd.DataFrame({"z": z3.loc[d], "r": r3.loc[d], "f": fw[5].loc[d], "top": top.loc[d]}).dropna()
        xs = xs[xs.top.astype(bool)]
        if len(xs) < 20:
            continue
        b1 = np.polyfit(xs.z, xs.r, 1)
        res_ = xs.r - np.polyval(b1, xs.z)
        q = res_.rank(pct=True)
        rows.append({"time": d, "coin": "XS", "side": 1, "gross": float(xs.f[q >= 0.9].mean() - xs.f[q <= 0.1].mean())})
    xs_ = pd.DataFrame(rows)
    s = L.stats(xs_, reps=1000)
    res["f_cross_section_residual_top_minus_bottom_f5"] = {"days": s["n"], "mean_bp": s["mean_bp"], "ci95_bp": s["ci95_bp"], "p": s["p"], "mde_bp": s["mde80_bp"], "by_year": s["by_year"]}
    print("f xs", res["f_cross_section_residual_top_minus_bottom_f5"])
    (ROOT / "research/is3/N3d__explore.json").write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    main()
