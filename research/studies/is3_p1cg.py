"""P1 c / e / g (gap fill, continued; profiles as in is3_p1.py, explore COINS10 2021-2023).

c  delta gaps: bins of yesterday's range (volume >= 20% of its median bin) with the LOWEST |net taker delta| / volume (one
   third) vs the highest third: next-day volume share in them vs the mirror bins around the next open.
e  law 5 'what doesn't happen' (wa 18.10.57(1)): yesterday's deepest interior low-volume node, NOT touched over the next
   5 days; approaches = hours whose 1-min range came within 3 bins (30 bp) of it without touching. From the close of
   day 5: simple return over 24 h / 72 h signed AWAY from the node, by approach count (0 / 1-2 / 3-5 / 6+).
   Matched baseline for the >= 3 groups: same coin, never-approached untouched nodes in the same quintile of the 5-day
   return signed away from the node (momentum is the obvious confound).
g  hourly salad (wa 18.10.31(2)): hour t+1's volume share in hour t's least / most traded third of bins vs mirror,
   and the nearest prior-hour LVN reached before the mirror distance within hour t+1 (random walk 50%).

    nice -n 19 .venv/bin/python -m research.studies.is3_p1cg c | e | g     -> research/is3/P1{c,e,g}__explore.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L
from research.studies import is3_p1 as P

ROOT = Path(__file__).resolve().parents[2]
LO, HI = "2021-01-01", "2024-01-01"


def form_c() -> dict:
    rows = []
    for coin in L.COINS10:
        D = P.profiles(P.load(coin, LO, HI), delta=True)
        for d in sorted(D):
            nx = d + pd.Timedelta("1D")
            if nx not in D or not (pd.Timestamp(LO, tz="UTC") <= nx < pd.Timestamp(HI, tz="UTC")):
                continue
            off, p, _, _, _, ad = D[d]
            T, ob = D[nx], D[nx][4]
            ok = np.flatnonzero(p >= 0.2 * np.median(p[p > 0]))
            if len(ok) < 9:
                continue
            ratio = ad[ok] / p[ok]
            o = ok[np.argsort(ratio, kind="stable")]
            t = len(o) // 3
            lo_b, hi_b = off + o[:t], off + o[-t:]
            row = {"time": nx, "coin": coin, "lowd": P.share(T, lo_b), "lowd_m": P.share(T, 2 * ob - lo_b),
                   "highd": P.share(T, hi_b), "highd_m": P.share(T, 2 * ob - hi_b)}
            # volume-controlled: inside each volume tercile of the bins, the low-|delta|/volume half vs the high half
            vt = np.array_split(ok[np.argsort(p[ok], kind="stable")], 3)
            lo_v, hi_v = [], []
            for g in vt:
                og = g[np.argsort(ad[g] / p[g], kind="stable")]
                lo_v.append(og[:len(og) // 2]); hi_v.append(og[len(og) - len(og) // 2:])
            lo_v, hi_v = off + np.concatenate(lo_v), off + np.concatenate(hi_v)
            row.update({"vlow": P.share(T, lo_v) - P.share(T, 2 * ob - lo_v), "vhigh": P.share(T, hi_v) - P.share(T, 2 * ob - hi_v)})
            rows.append(row)
    e = pd.DataFrame(rows)
    return {"n": len(e), "low_delta_third": P._diff(e, "lowd", "lowd_m"), "high_delta_third": P._diff(e, "highd", "highd_m"),
            "volume_controlled_low_minus_high_delta": P._diff(e, "vlow", "vhigh")}


def form_e(all_nodes: bool = False, appr_bins: int = 3) -> dict:
    rows = []
    for coin in L.COINS10:
        k = P.load(coin, LO, "2024-01-10")
        D = P.profiles(k)
        c = k.c.to_numpy()
        lb = np.floor(np.log(k.l.to_numpy()) / P.BIN).astype(np.int64)
        hb = np.floor(np.log(k.h.to_numpy()) / P.BIN).astype(np.int64)
        hour = k.index.floor("h").asi8
        dayix = pd.Series(np.arange(len(k)), index=k.index.floor("D")).groupby(level=0).agg(["min", "max"])
        for d in sorted(D):
            if not (pd.Timestamp(LO, tz="UTC") <= d < pd.Timestamp(HI, tz="UTC")):
                continue
            d1, d5, d6 = d + pd.Timedelta("1D"), d + pd.Timedelta("5D"), d + pd.Timedelta("6D")
            if d1 not in dayix.index or d5 not in dayix.index or d6 not in dayix.index:
                continue
            off, p = D[d][0], D[d][1]
            s = P.smooth(p)
            nodes = P.lvns(p, off)
            if not len(nodes):
                continue
            a, b = int(dayix.loc[d1, "min"]), int(dayix.loc[d5, "max"])
            e0 = b + 1
            if e0 + 4320 >= len(c):
                continue
            for node in (nodes if all_nodes else [int(nodes[np.argmin(s[nodes - off])])]):
              node = int(node)
              touch = (lb[a:b + 1] <= node) & (hb[a:b + 1] >= node)
              if touch.any():
                  continue
              dist = np.minimum(np.abs(lb[a:b + 1] - node), np.abs(hb[a:b + 1] - node))
              appr = len(np.unique(hour[a:b + 1][dist <= appr_bins]))
              p0 = c[b]
              away = 1 if np.log(p0) / P.BIN > node else -1
              rows.append({"time": k.index[b], "coin": coin, "side": away, "appr": appr, "dist_bins": float(abs(np.log(p0) / P.BIN - node)),
                         "ret5": away * (c[b] / c[int(dayix.loc[d1, "min"]) - 1] - 1),
                         "f24": away * (c[e0 + 1440] / c[e0] - 1), "f72": away * (c[e0 + 4320] / c[e0] - 1)})
    e = pd.DataFrame(rows).drop_duplicates(["time", "coin", "side", "appr"])
    e["grp"] = pd.cut(e.appr, [-1, 0, 2, 5, 10**6], labels=["0", "1-2", "3-5", "6+"])
    e["m"] = pd.qcut(e.ret5.rank(method="first"), 5, labels=False)
    res = {"n_untouched": int(len(e))}
    for g, x in e.groupby("grp", observed=True):
        for H in ("f24", "f72"):
            s = L.stats(x.assign(gross=x[H])[["time", "coin", "side", "gross"]], reps=500)
            res[f"appr_{g}_{H}"] = {"n": s["n"], "mean_bp": s["mean_bp"], "ci95_bp": s["ci95_bp"]}
    ev, pool = e[e.appr >= 3], e[e.appr == 0]
    base = L.matched(ev, pool, k=3)
    for H in ("f24", "f72"):
        s = L.stats(ev.assign(gross=ev[H])[["time", "coin", "side", "gross"]], base.assign(gross=base[H])[["time", "coin", "side", "gross"]], reps=2000)
        res[f"appr3plus_vs_matched_{H}"] = {k: s.get(k) for k in ("n", "mean_bp", "ci95_bp", "mde80_bp", "base_bp", "vs_base_bp", "p_vs_base", "by_year")}
    return res


def form_g() -> dict:
    rows = []
    for coin in L.COINS10:
        H = P.profiles(P.load(coin, LO, HI), freq="h", minbars=50)
        for t in sorted(H):
            nx = t + pd.Timedelta("1h")
            if nx not in H or not (pd.Timestamp(LO, tz="UTC") <= nx < pd.Timestamp(HI, tz="UTC")):
                continue
            off, p = H[t][0], H[t][1]
            if len(p) < 9:
                continue
            T, ob = H[nx], H[nx][4]
            o = np.argsort(p, kind="stable"); third = len(p) // 3
            lv, hv = off + o[:third], off + o[-third:]
            row = {"time": nx, "coin": coin, "lv": P.share(T, lv), "lv_m": P.share(T, 2 * ob - lv), "hv": P.share(T, hv), "hv_m": P.share(T, 2 * ob - hv)}
            nodes = P.lvns(p, off)
            if len(nodes) and off <= ob < off + len(p):
                tn = int(nodes[np.argmin(np.abs(nodes - ob))])
                if tn != ob:
                    row["lvn_hit"] = P.first_passage(T[2], T[3], ob, tn)
            rows.append(row)
    e = pd.DataFrame(rows)
    x = e.dropna(subset=["lvn_hit"])
    return {"n_hours": len(e), "LV_third": P._diff(e, "lv", "lv_m", reps=500), "HV_third": P._diff(e, "hv", "hv_m", reps=500),
            "lvn_first_passage": {"n": int(len(x)), "hit": round(float(x.lvn_hit.mean()), 4),
                                  "ci95_daycluster": L.stats(x.assign(side=1, gross=x.lvn_hit - 0.5)[["time", "coin", "side", "gross"]], reps=500)["ci95_bp"]}}


if __name__ == "__main__":
    f = sys.argv[1]
    r = {"c": form_c, "e": form_e, "e2": lambda: form_e(True, 5), "g": form_g}[f]()
    print(json.dumps(r, indent=1, default=float))
    (ROOT / f"research/is3/P1{f}__explore.json").write_text(json.dumps(r, indent=1, default=float))
