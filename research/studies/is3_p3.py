"""P3 naked and composite POCs (R15; tg:29, 38, 44-47). Explore COINS10 2021-2023, Binance 1-min klines, 10-bp volume profiles.

a/d  naked POC (and VAH/VAL for weekly/monthly) of a day / ISO week / month: evaluated once at the close of the first day after the
     period if untouched that day; touched within 5 / 10 / 20 days vs its mirror level (same distance on the other side of that close).
c/d  first touch: 60-min return (one bar late) signed away from the approach, and +-30 bp first passage (bounce first), vs the mirror
     level's first touch; daily form also vs the first re-touch of today's open after price left it by >= the same distance.
b    20-day composite POC as magnet: days whose close is 2-5 daily sigmas from it -> 1/3/5-day return toward it, vs days at the
     same sigma distance from the 20-day mean close (plain mean reversion), matched by distance bin.

    nice -n 19 .venv/bin/python -m research.studies.is3_p3      -> research/is3/P3__explore.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L
from research.studies import is3_p1 as P
from research.studies.is2_profile import value_area
from research.studies.is3_p2 import sess_profile

ROOT = Path(__file__).resolve().parents[2]
LO, HI = "2021-01-01", "2024-01-01"


def touch(h, l, c, i0, i1, lev):
    """first minute in [i0, i1] whose range contains lev; reaction = 60-min return one bar late signed away from the approach
    and the +-30 bp first passage (1 = bounce first)."""
    m = (l[i0:i1 + 1] <= lev) & (h[i0:i1 + 1] >= lev)
    if not m.any():
        return None
    t = i0 + int(np.argmax(m))
    if t + 1500 >= len(c) or t < 1:
        return None
    s = 1 if c[t - 1] > lev else -1                  # approached from above -> bounce = up
    up, dn = c[t + 1] * 1.003, c[t + 1] / 1.003
    hh, ll = h[t + 2:t + 1442], l[t + 2:t + 1442]
    iu = int(np.argmax(hh >= up)) if (hh >= up).any() else 10**9
    idn = int(np.argmax(ll <= dn)) if (ll <= dn).any() else 10**9
    fp = np.nan if iu == idn == 10**9 else (0.5 if iu == idn else float((iu < idn) == (s > 0)))
    return {"t": t, "side": s, "r60": s * (c[t + 61] / c[t + 1] - 1), "bounce30": fp}


def run() -> dict:
    T, R, B = [], [], []
    for coin in L.COINS10:
        k = P.load(coin, LO, "2024-02-15")
        h, l, c, v = k.h.to_numpy(), k.l.to_numpy(), k.c.to_numpy(), k.qv.to_numpy()
        ix = pd.Series(np.arange(len(k)), index=k.index.floor("D")).groupby(level=0).agg(["min", "max"])
        ix = ix[(ix["max"] - ix["min"]) == 1439]
        days = list(ix.index)
        pos = {d: n for n, d in enumerate(days)}
        periods = []                                   # (kind, last day of period, first index, last index, horizon days)
        for d in days:
            periods.append(("day", d, int(ix.loc[d, "min"]), int(ix.loc[d, "max"]), 5))
        for kind, key, hz in (("week", lambda x: x.to_period("W"), 10), ("month", lambda x: x.to_period("M"), 20)):
            grp = pd.Series(days, index=days).groupby([key(d.tz_localize(None)) for d in days])
            for _, ds in grp:
                ds = list(ds)
                if len(ds) >= (6 if kind == "week" else 26):
                    periods.append((kind, ds[-1], int(ix.loc[ds[0], "min"]), int(ix.loc[ds[-1], "max"]), hz))
        for kind, last, a0, a1, hz in periods:
            if last not in pos or pos[last] + hz + 1 >= len(days):
                continue
            d1 = days[pos[last] + 1]
            if not (pd.Timestamp(LO, tz="UTC") <= d1 < pd.Timestamp(HI, tz="UTC")) or (d1 - last).days != 1:
                continue
            b0, vol, _ = sess_profile(h, l, v, a0, a1, P.BIN)
            poc, va, vb = value_area(vol)
            levels = {"POC": np.exp((b0 + poc + 0.5) * P.BIN)}
            if kind != "day":
                levels.update({"VAH": np.exp((b0 + vb + 1) * P.BIN), "VAL": np.exp((b0 + va) * P.BIN)})
            e0, e1 = int(ix.loc[d1, "min"]), int(ix.loc[d1, "max"])
            ref = c[e1]
            fwd0, fwd1 = e1 + 1, int(ix.loc[days[pos[last] + 1 + hz], "max"])
            for nm, lev in levels.items():
                if (l[e0:e1 + 1] <= lev).any() and (h[e0:e1 + 1] >= lev).any():
                    continue                           # touched on the first day after: not naked
                if abs(lev / ref - 1) < 0.002:
                    continue
                mir = 2 * ref - lev
                tr, tm = touch(h, l, c, fwd0, fwd1, lev), touch(h, l, c, fwd0, fwd1, mir)
                T.append({"time": k.index[e1], "coin": coin, "side": 1, "kind": kind, "lvl": nm, "dist": abs(np.log(lev / ref)),
                          "hit": float(tr is not None), "hit_m": float(tm is not None)})
                for tag, r in (("real", tr), ("mirror", tm)):
                    if r is not None:
                        R.append({"time": k.index[r["t"] + 1], "coin": coin, "side": r["side"], "kind": kind, "lvl": nm, "tag": tag,
                                  "r60": r["r60"], "bounce30": r["bounce30"], "dist": abs(np.log(lev / ref)), "fat": float(vol.max() / vol.sum()),
                                  "wait_min": r["t"] - fwd0})
            if kind == "day":
                # daily open re-touch after leaving it by >= the POC's distance (his comparison), same day window
                op = c[e0 - 1]
                dist = abs(levels["POC"] / ref - 1)
                away = np.flatnonzero(np.abs(c[e0:fwd1] / op - 1) >= max(dist, 0.002))
                if len(away):
                    r = touch(h, l, c, e0 + int(away[0]) + 1, fwd1, op)
                    if r is not None:
                        R.append({"time": k.index[r["t"] + 1], "coin": coin, "side": r["side"], "kind": "day", "lvl": "OPEN", "tag": "open",
                                  "r60": r["r60"], "bounce30": r["bounce30"]})
        # b composite magnet vs mean reversion
        info = {}
        for d in days:
            a_, b_ = int(ix.loc[d, "min"]), int(ix.loc[d, "max"])
            b0, vol, _ = sess_profile(h, l, v, a_, b_, P.BIN)
            info[d] = (b0, vol, c[b_])
        cl = pd.Series({d: info[d][2] for d in days})
        sd = np.log(cl).diff().rolling(20).std().shift(1)
        for n in range(21, len(days) - 5):
            d = days[n]
            if not (pd.Timestamp(LO, tz="UTC") <= d < pd.Timestamp(HI, tz="UTC")) or not sd[d] > 0:
                continue
            comp = {}
            for dd in days[n - 20:n]:
                b0, vol, _ = info[dd]
                for j, vv in enumerate(vol):
                    comp[b0 + j] = comp.get(b0 + j, 0.0) + vv
            cp = np.exp((max(comp, key=comp.get) + 0.5) * P.BIN)
            mean = float(cl.iloc[n - 20:n].mean())
            for kind, lev in (("node", cp), ("mean", mean)):
                z = np.log(cl[d] / lev) / sd[d]
                if 2 <= abs(z) <= 5:
                    s = -int(np.sign(z))
                    row = {"time": d, "coin": coin, "kind": kind, "side": s, "m": int(abs(z) * 2)}
                    for H in (1, 3, 5):
                        row[f"f{H}"] = s * (cl.iloc[n + H] / cl[d] - 1)
                    B.append(row)
    res = {}
    t = pd.DataFrame(T)
    for (kind, nm), x in t.groupby(["kind", "lvl"]):
        s = L.stats(x.assign(gross=x.hit - x.hit_m)[["time", "coin", "side", "gross"]], reps=1000)
        res[f"touch_{kind}_{nm}"] = {"n": s["n"], "hit": round(float(x.hit.mean()), 4), "mirror": round(float(x.hit_m.mean()), 4), "diff_pp": round(s["mean_bp"] / 100, 2),
                                     "ci95_pp": [round(q / 100, 2) for q in s["ci95_bp"]], "p": s["p"], "dist_bp_median": round(float(x.dist.median() * 1e4), 1)}
    r = pd.DataFrame(R)
    r.to_parquet(ROOT / "data/is3/p3_reactions.parquet")
    for (kind, nm), x in r[r.tag != "open"].groupby(["kind", "lvl"]):
        re_, mi = x[x.tag == "real"], x[x.tag == "mirror"]
        s = L.stats(re_.assign(gross=re_.r60)[["time", "coin", "side", "gross"]], mi.assign(gross=mi.r60)[["time", "coin", "side", "gross"]], reps=1000)
        rb, mb = re_.dropna(subset=["bounce30"]), mi.dropna(subset=["bounce30"])
        s2 = L.stats(rb.assign(gross=rb.bounce30)[["time", "coin", "side", "gross"]], mb.assign(gross=mb.bounce30)[["time", "coin", "side", "gross"]], reps=1000)
        res[f"reaction_{kind}_{nm}"] = {"n": s["n"], "r60_bp": s["mean_bp"], "mirror_r60_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"],
                                        "bounce30": round(float(rb.bounce30.mean()), 4), "mirror_bounce30": round(float(mb.bounce30.mean()), 4), "bounce_diff_pp": round(s2["vs_base_bp"] / 100, 2), "bounce_p": s2["p_vs_base"]}
    re_, op = r[(r.kind == "day") & (r.lvl == "POC") & (r.tag == "real")], r[r.tag == "open"]
    s = L.stats(re_.assign(gross=re_.r60)[["time", "coin", "side", "gross"]], op.assign(gross=op.r60)[["time", "coin", "side", "gross"]], reps=1000)
    res["c_daily_naked_poc_vs_daily_open_r60"] = {"poc_bp": s["mean_bp"], "open_bp": s["base_bp"], "n_open": int(len(op)), "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"],
                                                  "open_bounce30": round(float(op.bounce30.mean()), 4)}
    b = pd.DataFrame(B)
    for H in ("f1", "f3", "f5"):
        ev, pool = b[b.kind == "node"], b[b.kind == "mean"]
        base = L.matched(ev, pool, k=3)
        s = L.stats(ev.assign(gross=ev[H])[["time", "coin", "side", "gross"]], base.assign(gross=base[H])[["time", "coin", "side", "gross"]], reps=1000)
        res[f"b_toward_composite_poc_{H}"] = {"n": s["n"], "mean_bp": s["mean_bp"], "toward_mean_matched_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
    return res


if __name__ == "__main__":
    r = run()
    print(json.dumps(r, indent=1, default=float))
    (ROOT / "research/is3/P3__explore.json").write_text(json.dumps(r, indent=1, default=float))
