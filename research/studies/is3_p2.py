"""P2 balance laws (tg:288, tg:52-57), explore COINS10 2021-2023, 1-min Binance klines, 10-bp volume profiles (is3_p1).

a  Balance = 3 consecutive UTC days whose 70% value areas share a common price band. Edges = the 3 days' high and low,
   width w. Day 4 opens inside; first touch of an edge: does price come back 0.25 w inside before going 0.25 w beyond
   (random walk 50%)? and the 60-min return (one bar late) signed back inside.
   Placebo = the composite of 8 days earlier (also a balance), its edges moved to today's price (x close(d-1)/close(d-9)).
b  same touches, dose = 'build': how many of the 6 half-hours before the touch closed within 0.15 w of that edge.
   Law: time building at an edge -> break (reject falls as build rises).

    nice -n 19 .venv/bin/python -m research.studies.is3_p2 ab
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L
from research.studies import is3_p1 as P
from research.studies.is2_profile import value_area

ROOT = Path(__file__).resolve().parents[2]
LO, HI = "2021-01-01", "2024-01-01"


def daily(k: pd.DataFrame) -> pd.DataFrame:
    """per UTC day: first/last minute index, high, low, close, value area (lo, hi) in price."""
    D = P.profiles(k)
    day = k.index.floor("D")
    ix = pd.Series(np.arange(len(k)), index=day).groupby(level=0).agg(["min", "max"])
    rows = {}
    for d, (off, prof, *_r) in D.items():
        poc, a, b = value_area(prof)
        rows[d] = {"i0": int(ix.loc[d, "min"]), "i1": int(ix.loc[d, "max"]), "val": np.exp((off + a) * P.BIN), "vah": np.exp((off + b + 1) * P.BIN),
                   "poc": np.exp((off + poc + 0.5) * P.BIN)}
    out = pd.DataFrame(rows).T
    h, l, c = k.h.to_numpy(), k.l.to_numpy(), k.c.to_numpy()
    out["hi"] = [h[int(a):int(b) + 1].max() for a, b in zip(out.i0, out.i1)]
    out["lo"] = [l[int(a):int(b) + 1].min() for a, b in zip(out.i0, out.i1)]
    out["close"] = [c[int(b)] for b in out.i1]
    return out


def composite(D: pd.DataFrame, days: list) -> tuple | None:
    if any(x not in D.index for x in days):
        return None
    sub = D.loc[days]
    if sub.val.max() >= sub.vah.min():          # no common value band -> not a balance
        return None
    return float(sub.hi.max()), float(sub.lo.min())


def touches(h, l, c, i0, i1, hi, lo, w, end):
    """first touch of hi or lo between i0 and i1 (price opened inside); returns dict or None."""
    hh, ll = h[i0:i1 + 1] >= hi, l[i0:i1 + 1] <= lo
    th = int(np.argmax(hh)) if hh.any() else 10**9
    tl = int(np.argmax(ll)) if ll.any() else 10**9
    if th == tl:
        return None
    t = i0 + min(th, tl)
    side = 1 if th < tl else -1                  # 1 = touched the high edge
    edge = hi if side == 1 else lo
    inside, beyond = edge - side * 0.25 * w, edge + side * 0.25 * w
    e = min(t + 1440, end)
    seg_h, seg_l = h[t + 1:e + 1], l[t + 1:e + 1]
    hit_in = (seg_l <= inside) if side == 1 else (seg_h >= inside)
    hit_out = (seg_h >= beyond) if side == 1 else (seg_l <= beyond)
    a = int(np.argmax(hit_in)) if hit_in.any() else 10**9
    b = int(np.argmax(hit_out)) if hit_out.any() else 10**9
    reject = np.nan if a == b == 10**9 else (0.5 if a == b else float(a < b))
    if t - 180 < 0 or t + 61 >= len(c):
        return None
    hc = c[t - 180:t].reshape(6, 30)[:, -1]
    build = int((np.abs(hc - edge) <= 0.15 * w).sum())
    return {"t": t, "edge_side": side, "reject": reject, "r60": -side * (c[t + 61] / c[t + 1] - 1), "build": build, "w_rel": w / c[t]}


def form_ab() -> dict:
    rows = []
    for coin in L.COINS10:
        k = P.load(coin, LO, HI)
        D = daily(k)
        h, l, c = k.h.to_numpy(), k.l.to_numpy(), k.c.to_numpy()
        days = list(D.index)
        for n in range(11, len(days)):
            d = days[n]
            if not (pd.Timestamp(LO, tz="UTC") <= d < pd.Timestamp(HI, tz="UTC")) or (d - days[n - 11]).days != 11:
                continue
            i0, i1 = int(D.loc[d, "i0"]), int(D.loc[d, "i1"])
            op = c[i0 - 1]
            for kind, src, scale in (("real", days[n - 3:n], 1.0), ("placebo", days[n - 11:n - 8], D.loc[days[n - 1], "close"] / D.loc[days[n - 9], "close"])):
                cp = composite(D, src)
                if cp is None:
                    continue
                hi, lo = cp[0] * scale, cp[1] * scale
                if not (lo < op < hi):
                    continue
                r = touches(h, l, c, i0, i1, hi, lo, hi - lo, len(c) - 1)
                if r is None:
                    continue
                r.update({"time": k.index[r["t"] + 1], "coin": coin, "kind": kind, "side": -r["edge_side"]})
                rows.append(r)
    e = pd.DataFrame(rows)
    e.to_parquet(ROOT / "data/is3/p2ab.parquet")
    res = {"n": {k: int(v) for k, v in e.kind.value_counts().items()}}
    for kind, x in e.groupby("kind"):
        y = x.dropna(subset=["reject"])
        s = L.stats(y.assign(gross=y.reject - 0.5)[["time", "coin", "side", "gross"]], reps=1000)
        s60 = L.stats(x.assign(gross=x.r60)[["time", "coin", "side", "gross"]], reps=1000)
        res[kind] = {"reject_rate": round(float(y.reject.mean()), 4), "reject_ci_pp": [round(v / 100 + 50, 2) for v in s["ci95_bp"]],
                     "r60_bp": s60["mean_bp"], "r60_ci": s60["ci95_bp"], "w_rel_median": round(float(x.w_rel.median()), 4),
                     "by_build": {int(b): {"n": int(len(g)), "reject": round(float(g.reject.mean()), 3), "r60_bp": round(float(g.r60.mean() * 1e4), 1)}
                                  for b, g in y.groupby(np.minimum(y.build, 4))}}
    re, pl = e[e.kind == "real"].dropna(subset=["reject"]), e[e.kind == "placebo"].dropna(subset=["reject"])
    s = L.stats(re.assign(gross=re.reject)[["time", "coin", "side", "gross"]], pl.assign(gross=pl.reject)[["time", "coin", "side", "gross"]], reps=2000)
    res["real_vs_placebo_reject_pp"] = {"diff_pp": round(s["vs_base_bp"] / 100, 2), "p": s["p_vs_base"], "mde_pp": round(s["mde80_bp"] / 100, 2)}
    s = L.stats(re.assign(gross=re.r60)[["time", "coin", "side", "gross"]], pl.assign(gross=pl.r60)[["time", "coin", "side", "gross"]], reps=2000)
    res["real_vs_placebo_r60_bp"] = {"diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
    return res


def form_gfi() -> dict:
    """g poor vs tailed lows/highs (retest within 5 days), f close through the 20-day composite POC vs the 20-day median close,
    i TPO POC vs volume POC disagreement -> next-day range and direction."""
    from research.studies.is2_profile import profile
    G, F, I = [], [], []
    for coin in L.COINS10:
        k = P.load(coin, LO, "2024-01-10")
        h, l, c, v = k.h.to_numpy(), k.l.to_numpy(), k.c.to_numpy(), k.qv.to_numpy()
        ix = pd.Series(np.arange(len(k)), index=k.index.floor("D")).groupby(level=0).agg(["min", "max"])
        ix = ix[(ix["max"] - ix["min"]) >= 1430]
        days = list(ix.index)
        info = {}
        for d in days:
            a, b = int(ix.loc[d, "min"]), int(ix.loc[d, "max"])
            b0, vol, tpo = profile(h[a:b + 1], l[a:b + 1], v[a:b + 1])
            poc, va, vb = value_area(vol)
            info[d] = dict(a=a, b=b, b0=b0, vol=vol, tpo=tpo, poc=poc, va=va, vb=vb, hi=h[a:b + 1].max(), lo=l[a:b + 1].min(), close=c[b])
        rng = pd.Series({d: info[d]["hi"] / info[d]["lo"] - 1 for d in days})
        atr = rng.rolling(20).mean().shift(1)
        for n, d in enumerate(days):
            if not (pd.Timestamp(LO, tz="UTC") <= d < pd.Timestamp(HI, tz="UTC")) or n < 21 or n + 6 >= len(days):
                continue
            x = info[d]
            # g: tail length in bins = bins from the extreme touched by exactly one half-hour
            for side, ext, arr in ((1, "lo", x["tpo"]), (-1, "hi", x["tpo"][::-1])):
                tail = int(np.argmax(arr > 1)) if (arr > 1).any() else len(arr)
                after = slice(info[days[n + 1]]["a"], info[days[n + 5]]["b"] + 1)
                lev = x[ext]
                retest = bool((l[after] <= lev).any()) if side == 1 else bool((h[after] >= lev).any())
                G.append({"time": d, "coin": coin, "side": side, "tl": tail, "retest": float(retest),
                          "dist": abs(np.log(x["close"] / lev)) / atr[d] if atr[d] > 0 else np.nan})
            # f: 20-day composite POC (sum of daily volume profiles on the absolute bin grid)
            comp = {}
            for dd in days[n - 20:n]:
                y = info[dd]
                for j, vv in enumerate(y["vol"]):
                    comp[y["b0"] + j] = comp.get(y["b0"] + j, 0.0) + vv
            cpoc = np.exp((max(comp, key=comp.get) + 0.5) * P.BIN)
            med = float(np.median([info[dd]["close"] for dd in days[n - 20:n]]))
            prev = info[days[n - 1]]["close"]
            for kind, lev in (("node", cpoc), ("median", med)):
                if (prev - lev) * (x["close"] - lev) < 0:
                    sgn = 1 if x["close"] > lev else -1
                    row = {"time": d, "coin": coin, "kind": kind, "side": sgn}
                    for H in (1, 3, 5):
                        row[f"f{H}"] = sgn * (info[days[n + H]]["close"] / x["close"] - 1)
                    F.append(row)
            # i: TPO POC vs volume POC
            tp = int(np.argmax(x["tpo"]))
            width = max(x["vb"] - x["va"] + 1, 1)
            nx = info[days[n + 1]]
            dirn = np.sign(x["poc"] - tp) if x["poc"] != tp else 0
            I.append({"time": d, "coin": coin, "side": int(dirn) if dirn else 1, "gap": abs(x["poc"] - tp) / width, "dir": dirn,
                      "nrange": (nx["hi"] / nx["lo"] - 1) / atr[d] if atr[d] > 0 else np.nan,
                      "nret": (nx["close"] / x["close"] - 1) * (dirn if dirn else 1)})
    res = {}
    g = pd.DataFrame(G).dropna(subset=["dist"])
    g["poor"] = g.tl == 0
    g["m"] = pd.qcut(g.dist.rank(method="first"), 10, labels=False)
    res["g_tail_counts"] = {"poor (tail 0)": int(g.poor.sum()), "tail 1-2": int(((g.tl >= 1) & (g.tl <= 2)).sum()), "tail >= 3": int((g.tl >= 3).sum())}
    for side, nm in ((1, "lows"), (-1, "highs")):
        y = g[g.side == side]
        ev, pool = y[y.poor], y[y.tl >= 3]
        base = L.matched(ev, pool, k=3)
        s = L.stats(ev.assign(gross=ev.retest)[["time", "coin", "side", "gross"]], base.assign(gross=base.retest)[["time", "coin", "side", "gross"]], reps=2000)
        res[f"g_{nm}"] = {"n_poor": s["n"], "retest_poor": round(float(ev.retest.mean()), 4), "retest_tailed_matched": round(float(base.retest.mean()), 4),
                          "diff_pp": round(s["vs_base_bp"] / 100, 2), "p": s["p_vs_base"], "mde_pp": round(s["mde80_bp"] / 100, 2),
                          "by_tail": {str(t): round(float(z.retest.mean()), 3) for t, z in y.groupby(np.minimum(y.tl, 5))}}
    f = pd.DataFrame(F)
    for H in ("f1", "f3", "f5"):
        a, b = f[f.kind == "node"], f[f.kind == "median"]
        s = L.stats(a.assign(gross=a[H])[["time", "coin", "side", "gross"]], b.assign(gross=b[H])[["time", "coin", "side", "gross"]], reps=2000)
        res[f"f_{H}"] = {"n_node": s["n"], "node_bp": s["mean_bp"], "n_median": int(len(b)), "median_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
    i = pd.DataFrame(I).dropna(subset=["nrange"])
    i["q"] = pd.qcut(i.gap.rank(method="first"), 5, labels=False)
    res["i_by_gap_quintile"] = {int(q): {"gap_hi": round(float(z.gap.max()), 3), "n": int(len(z)), "next_range_atr": round(float(z.nrange.mean()), 3),
                                         "next_ret_toward_volpoc_bp": round(float(z[z.dir != 0].nret.mean() * 1e4), 1)} for q, z in i.groupby("q")}
    top = i[(i.q == 4) & (i.dir != 0)]
    s = L.stats(top.assign(gross=top.nret)[["time", "coin", "side", "gross"]].assign(side=1), reps=2000)
    res["i_top_gap_direction"] = {"n": s["n"], "mean_bp": s["mean_bp"], "ci95_bp": s["ci95_bp"], "p": s["p"], "mde_bp": s["mde80_bp"]}
    lo_q, hi_q = i[i.q == 0], i[i.q == 4]
    s = L.stats(hi_q.assign(gross=hi_q.nrange / 1e4)[["time", "coin", "side", "gross"]].assign(side=1), lo_q.assign(gross=lo_q.nrange / 1e4)[["time", "coin", "side", "gross"]].assign(side=1), reps=2000)
    res["i_range_top_vs_bottom_gap"] = {"diff_atr": round(s["vs_base_bp"], 3), "p": s["p_vs_base"]}
    return res


if __name__ == "__main__":
    f = sys.argv[1]
    r = {"ab": form_ab, "gfi": form_gfi}[f]()
    print(json.dumps(r, indent=1, default=float))
    (ROOT / f"research/is3/P2{f}__explore.json").write_text(json.dumps(r, indent=1, default=float))
