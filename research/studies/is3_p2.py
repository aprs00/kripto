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


SESS = [(0, 420, "asia"), (420, 810, "london"), (810, 1155, "cme"), (1155, 1440, "preclose")]


def form_jh() -> dict:
    """j session initial balance (first 60 min) high/low: first later touch in the session; back 0.25 IB-width inside before
    0.25 beyond (random walk 50%) and 30-min return inward (one bar late), vs placebo levels 0.37 IB-width outside the IB.
    h daily rotation factor (48 half-hours, +-1 for higher/lower highs and lows): next-day range / ATR and next-day return
    signed with R/F, by |R/F| quintile, range controlled by today's range quintile."""
    J, Hh = [], []
    for coin in L.COINS10:
        k = P.load(coin, LO, "2024-01-10")
        h, l, c = k.h.to_numpy(), k.l.to_numpy(), k.c.to_numpy()
        ix = pd.Series(np.arange(len(k)), index=k.index.floor("D")).groupby(level=0).agg(["min", "max"])
        ix = ix[(ix["max"] - ix["min"]) == 1439]
        days = list(ix.index)
        rf, rng, ret = {}, {}, {}
        for d in days:
            a = int(ix.loc[d, "min"])
            hh = h[a:a + 1440].reshape(48, 30).max(1); ll = l[a:a + 1440].reshape(48, 30).min(1)
            rf[d] = int(np.sign(np.diff(hh)).sum() + np.sign(np.diff(ll)).sum())
            rng[d] = hh.max() / ll.min() - 1
            ret[d] = c[a + 1439] / c[a - 1] - 1 if a > 0 else np.nan
            if not (pd.Timestamp(LO, tz="UTC") <= d < pd.Timestamp(HI, tz="UTC")):
                continue
            for s0, s1, nm in SESS:
                i0, i1 = a + s0, a + s1 - 1
                ibh, ibl = h[i0:i0 + 60].max(), l[i0:i0 + 60].min()
                w = ibh - ibl
                if w <= 0:
                    continue
                for kind, up, dn in (("real", ibh, ibl), ("placebo", ibh + 0.37 * w, ibl - 0.37 * w)):
                    r = touches(h, l, c, i0 + 60, i1, up, dn, w, i1)
                    if r is None or r["t"] + 31 > i1 + 60:
                        continue
                    t = r["t"]
                    J.append({"time": k.index[t + 1], "coin": coin, "kind": kind, "sess": nm, "side": -r["edge_side"], "reject": r["reject"],
                              "r30": -r["edge_side"] * (c[t + 31] / c[t + 1] - 1)})
        atr = pd.Series(rng).rolling(20).mean().shift(1)
        for n, d in enumerate(days[:-1]):
            if not (pd.Timestamp(LO, tz="UTC") <= d < pd.Timestamp(HI, tz="UTC")) or not atr.get(d, np.nan) > 0:
                continue
            nx = days[n + 1]
            Hh.append({"time": d, "coin": coin, "side": int(np.sign(rf[d])) or 1, "rf": rf[d], "trng": rng[d] / atr[d], "nrange": rng[nx] / atr[d],
                       "nret": (np.sign(rf[d]) or 1) * ret[nx]})
    res = {}
    j = pd.DataFrame(J)
    # the touches() first passage uses 'end' = session end; reject nan = neither reached
    for kind, x in j.groupby("kind"):
        y = x.dropna(subset=["reject"])
        res[f"j_{kind}"] = {"n": int(len(x)), "reject": round(float(y.reject.mean()), 4), "r30_bp": round(float(x.r30.mean() * 1e4), 2),
                            "by_sess": {s: round(float(z.reject.mean()), 3) for s, z in y.groupby("sess")}}
    re, pl = j[j.kind == "real"].dropna(subset=["reject"]), j[j.kind == "placebo"].dropna(subset=["reject"])
    s = L.stats(re.assign(gross=re.reject)[["time", "coin", "side", "gross"]], pl.assign(gross=pl.reject)[["time", "coin", "side", "gross"]], reps=2000)
    res["j_reject_real_vs_placebo"] = {"diff_pp": round(s["vs_base_bp"] / 100, 2), "p": s["p_vs_base"], "mde_pp": round(s["mde80_bp"] / 100, 2)}
    s = L.stats(re.assign(gross=re.r30)[["time", "coin", "side", "gross"]], pl.assign(gross=pl.r30)[["time", "coin", "side", "gross"]], reps=2000)
    res["j_r30_real_vs_placebo"] = {"real_bp": s["mean_bp"], "placebo_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
    hh = pd.DataFrame(Hh)
    hh["aq"] = pd.qcut(hh.rf.abs().rank(method="first"), 5, labels=False)
    hh["tq"] = pd.qcut(hh.trng.rank(method="first"), 5, labels=False)
    res["h_by_absRF_quintile"] = {int(q): {"absRF_max": int(z.rf.abs().max()), "n": int(len(z)), "next_range_atr": round(float(z.nrange.mean()), 3),
                                           "next_ret_with_RF_bp": round(float(z.nret.mean() * 1e4), 1)} for q, z in hh.groupby("aq")}
    res["h_range_controlled"] = {f"tq{t}": {f"aq{q}": round(float(zz.nrange.mean()), 3) for q, zz in z.groupby("aq")} for t, z in hh.groupby("tq")}
    for q in (0, 4):
        z = hh[hh.aq == q]
        s = L.stats(z.assign(gross=z.nret)[["time", "coin", "side", "gross"]].assign(side=1), reps=2000)
        res[f"h_next_ret_with_RF_q{q}"] = {"n": s["n"], "mean_bp": s["mean_bp"], "ci95_bp": s["ci95_bp"], "p": s["p"], "mde_bp": s["mde80_bp"]}
    return res


def sess_profile(h, l, v, i0, i1, binw):
    """TPO (30-min periods) and volume per log bin of width binw over minutes [i0, i1]."""
    lb = np.floor(np.log(l[i0:i1 + 1]) / binw).astype(np.int64)
    hb = np.floor(np.log(h[i0:i1 + 1]) / binw).astype(np.int64)
    b0, n = int(lb.min()), int(hb.max() - lb.min() + 1)
    dv, dt = np.zeros(n + 1), np.zeros(n + 1)
    w = v[i0:i1 + 1] / (hb - lb + 1)
    np.add.at(dv, lb - b0, w); np.add.at(dv, hb - b0 + 1, -w)
    for s0 in range(0, len(lb), 30):
        dt[lb[s0:s0 + 30].min() - b0] += 1; dt[hb[s0:s0 + 30].max() - b0 + 1] -= 1
    return b0, np.cumsum(dv)[:n], np.cumsum(dt)[:n]


def single_bands(tpo, minrows):
    """runs of bins touched by exactly one period, inside the range (not touching either end = tails excluded), >= minrows."""
    one = tpo == 1
    out, i = [], 0
    while i < len(one):
        if one[i]:
            j = i
            while j + 1 < len(one) and one[j + 1]:
                j += 1
            if i > 0 and j < len(one) - 1 and j - i + 1 >= minrows:
                out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def rw80(H, Lw, C, t0, tgt, stop, end):
    """+1 target first, 0 stop first or neither; and the random-walk odds |stop - p| / |target - stop|."""
    from research.studies.is2_profile import first_passage
    p0 = C[t0]
    up, dn = (tgt, stop) if tgt > p0 else (stop, tgt)
    r, _ = first_passage(H, Lw, C, t0, up, dn, end - t0)
    if r == 0:                                  # neither level within the horizon: unresolved (random-walk odds are conditional on resolution)
        return np.nan, abs(stop - p0) / abs(tgt - stop)
    hit = float((r == 1 and tgt > p0) or (r == -1 and tgt < p0))
    return hit, abs(stop - p0) / abs(tgt - stop)


def form_del() -> dict:
    """d 80% rule on session profiles and 5-day composites; e single-print band adjacent to a big session POC vs other bands;
    l single prints at 4-bp rows (>= 3 rows) vs the same band geometry 8 days earlier moved to today's price."""
    D80, E, Lr = [], [], []
    for coin in L.COINS10:
        k = P.load(coin, LO, "2024-01-10")
        h, l, c, v = k.h.to_numpy(), k.l.to_numpy(), k.c.to_numpy(), k.qv.to_numpy()
        ix = pd.Series(np.arange(len(k)), index=k.index.floor("D")).groupby(level=0).agg(["min", "max"])
        ix = ix[(ix["max"] - ix["min"]) == 1439]
        days = list(ix.index)
        sess = []                                             # (day, name, i0, i1)
        for d in days:
            a = int(ix.loc[d, "min"])
            for s0, s1, nm in SESS:
                sess.append((d, nm, a + s0, a + s1 - 1))
        bands4 = {}
        for q in range(1, len(sess)):
            d, nm, i0, i1 = sess[q]
            pd_, pn, p0, p1 = sess[q - 1]
            if not (pd.Timestamp(LO, tz="UTC") <= d < pd.Timestamp(HI, tz="UTC")) or p1 + 1 != i0 or i1 + 2880 >= len(c):
                continue
            # d (session): previous session's value area
            b0, vol, tpo = sess_profile(h, l, v, p0, p1, P.BIN)
            poc, va, vb = value_area(vol)
            VAL, VAH = np.exp((b0 + va) * P.BIN), np.exp((b0 + vb + 1) * P.BIN)
            op = c[i0 - 1]
            if op > VAH or op < VAL:
                closes = c[i0 + 29:i1 + 1:30]
                inside = (closes > VAL) & (closes < VAH)
                for m in range(1, len(inside)):
                    if inside[m] and inside[m - 1]:
                        t0 = i0 + 29 + 30 * m + 1
                        if t0 >= i1:
                            break
                        wv = VAH - VAL
                        tgt, stop = (VAL, VAH + 0.25 * wv) if op > VAH else (VAH, VAL - 0.25 * wv)
                        hit, odds = rw80(h, l, c, t0, tgt, stop, i1)
                        D80.append({"time": k.index[t0], "coin": coin, "kind": "session", "hit": hit, "rw": odds})
                        break
            # e: single-print bands of the previous session (10 bp rows, >= 3 rows), adjacent (<= 2 bins) to its POC
            share = vol[poc] / vol.sum()
            for (x0, x1) in single_bands(tpo, 3):
                adj = (x1 < poc and poc - x1 <= 2) or (x0 > poc and x0 - poc <= 2)
                lo_p, hi_p = np.exp((b0 + x0) * P.BIN), np.exp((b0 + x1 + 1) * P.BIN)
                cl = c[p1]
                if lo_p <= cl <= hi_p:
                    continue
                far = lo_p if cl > hi_p else hi_p
                seg = slice(p1 + 1, p1 + 2881)
                filled = float((l[seg] <= far).any()) if cl > hi_p else float((h[seg] >= far).any())
                near = hi_p if cl > hi_p else lo_p
                E.append({"time": k.index[p1], "coin": coin, "side": 1, "adj_big": bool(adj and share >= 0.06), "adj": bool(adj), "share": share,
                          "filled": filled, "dist": abs(np.log(cl / near)), "width": abs(np.log(hi_p / lo_p))})
            # l: 4-bp rows, >= 3 rows, real vs 8-days-earlier geometry
            B4 = np.log(1.0004)
            b04, _, tpo4 = sess_profile(h, l, v, p0, p1, B4)
            bands4[(pd_, pn)] = (b04, single_bands(tpo4, 3), c[p1])
            prev8 = (pd_ - pd.Timedelta("8D"), pn)
            for kind, key in (("real", (pd_, pn)), ("placebo", prev8)):
                if key not in bands4:
                    continue
                bb0, bl, ref = bands4[key]
                cl = c[p1]
                for (x0, x1) in bl:
                    lo_p, hi_p = np.exp((bb0 + x0) * B4) * cl / ref, np.exp((bb0 + x1 + 1) * B4) * cl / ref
                    if lo_p <= cl <= hi_p:
                        continue
                    above = lo_p > cl
                    near, far = (lo_p, hi_p) if above else (hi_p, lo_p)
                    dist = abs(near - cl)
                    seg_h, seg_l = h[p1 + 1:p1 + 2881], l[p1 + 1:p1 + 2881]
                    # fill = far edge reached before price moves the same distance (to the far edge) the other way
                    other = cl - (far - cl)
                    hf = (seg_h >= far) if above else (seg_l <= far)
                    ho = (seg_l <= other) if above else (seg_h >= other)
                    a_ = int(np.argmax(hf)) if hf.any() else 10**9
                    b_ = int(np.argmax(ho)) if ho.any() else 10**9
                    if a_ == b_ == 10**9:
                        continue
                    Lr.append({"time": k.index[p1], "coin": coin, "side": 1, "kind": kind, "fill_first": 0.5 if a_ == b_ else float(a_ < b_),
                               "width_bp": abs(np.log(hi_p / lo_p)) * 1e4, "dist_bp": dist / cl * 1e4})
        # d (5-day composite): previous 5 days' value area, today's open outside, two 30-min closes inside
        for n_, d in enumerate(days):
            for NB in (1, 5):
                if n_ < NB or not (pd.Timestamp(LO, tz="UTC") <= d < pd.Timestamp(HI, tz="UTC")) or (d - days[n_ - NB]).days != NB:
                    continue
                a0 = int(ix.loc[days[n_ - NB], "min"]); a1 = int(ix.loc[days[n_ - 1], "max"])
                b0, vol, _ = sess_profile(h, l, v, a0, a1, P.BIN)
                poc, va, vb = value_area(vol)
                VAL, VAH = np.exp((b0 + va) * P.BIN), np.exp((b0 + vb + 1) * P.BIN)
                i0 = int(ix.loc[d, "min"]); i1 = i0 + 1439
                op = c[i0 - 1]
                if not (op > VAH or op < VAL):
                    continue
                closes = c[i0 + 29:i1 + 1:30]
                inside = (closes > VAL) & (closes < VAH)
                for m in range(1, len(inside)):
                    if inside[m] and inside[m - 1]:
                        t0 = i0 + 29 + 30 * m + 1
                        if t0 >= i1:
                            break
                        wv = VAH - VAL
                        tgt, stop = (VAL, VAH + 0.25 * wv) if op > VAH else (VAH, VAL - 0.25 * wv)
                        hit, odds = rw80(h, l, c, t0, tgt, stop, i1)
                        D80.append({"time": k.index[t0], "coin": coin, "kind": f"composite{NB}", "hit": hit, "rw": odds})
                        break
    res = {}
    d8 = pd.DataFrame(D80)
    res["d_unresolved_share"] = {kk: round(float(z.hit.isna().mean()), 3) for kk, z in d8.groupby("kind")}
    d8 = d8.dropna(subset=["hit"])
    for kind, x in d8.groupby("kind"):
        s = L.stats(x.assign(side=1, gross=x.hit - x.rw)[["time", "coin", "side", "gross"]], reps=2000)
        res[f"d_{kind}"] = {"n": int(len(x)), "hit": round(float(x.hit.mean()), 4), "rw_odds": round(float(x.rw.mean()), 4),
                            "diff_pp": round(s["mean_bp"] / 100, 2), "ci95_pp": [round(v_ / 100, 2) for v_ in s["ci95_bp"]], "p": s["p"]}
    e = pd.DataFrame(E)
    e["m"] = pd.qcut((e.dist / e.width).rank(method="first"), 10, labels=False)
    big = e.share >= e.share.quantile(2 / 3)
    for nm_, evm in (("adjacent_any_poc", e.adj), ("adjacent_top_third_poc", e.adj & big)):
        ev_, pool_ = e[evm], e[~e.adj]
        b_ = L.matched(ev_, pool_, k=3)
        s_ = L.stats(ev_.assign(gross=ev_.filled)[["time", "coin", "side", "gross"]], b_.assign(gross=b_.filled)[["time", "coin", "side", "gross"]], reps=2000)
        res[f"e_{nm_}_vs_other"] = {"n": s_["n"], "fill": round(float(ev_.filled.mean()), 4), "fill_matched_other": round(float(b_.filled.mean()), 4),
                                    "diff_pp": round(s_["vs_base_bp"] / 100, 2), "p": s_["p_vs_base"], "mde_pp": round(s_["mde80_bp"] / 100, 2)}
    ev, pool = e[e.adj_big], e[~e.adj]
    base = L.matched(ev, pool, k=3)
    s = L.stats(ev.assign(gross=ev.filled)[["time", "coin", "side", "gross"]], base.assign(gross=base.filled)[["time", "coin", "side", "gross"]], reps=2000)
    res["e_adjacent_big_poc_vs_other"] = {"n": s["n"], "fill": round(float(ev.filled.mean()), 4), "fill_matched_other": round(float(base.filled.mean()), 4),
                                          "diff_pp": round(s["vs_base_bp"] / 100, 2), "p": s["p_vs_base"], "mde_pp": round(s["mde80_bp"] / 100, 2), "n_bands": int(len(e))}
    lr = pd.DataFrame(Lr)
    re_, pl = lr[lr.kind == "real"], lr[lr.kind == "placebo"]
    s = L.stats(re_.assign(gross=re_.fill_first)[["time", "coin", "side", "gross"]], pl.assign(gross=pl.fill_first)[["time", "coin", "side", "gross"]], reps=2000)
    res["l_4bp_real_vs_placebo"] = {"n_real": int(len(re_)), "n_placebo": int(len(pl)), "real": round(float(re_.fill_first.mean()), 4), "placebo": round(float(pl.fill_first.mean()), 4),
                                     "diff_pp": round(s["vs_base_bp"] / 100, 2), "p": s["p_vs_base"], "mde_pp": round(s["mde80_bp"] / 100, 2),
                                     "width_bp_median": round(float(re_.width_bp.median()), 1), "dist_bp_median": round(float(re_.dist_bp.median()), 1)}
    return res


if __name__ == "__main__":
    f = sys.argv[1]
    r = {"ab": form_ab, "gfi": form_gfi, "jh": form_jh, "del": form_del}[f]()
    print(json.dumps(r, indent=1, default=float))
    (ROOT / f"research/is3/P2{f}__explore.json").write_text(json.dumps(r, indent=1, default=float))
