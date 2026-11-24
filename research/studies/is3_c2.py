"""C2 time of day (tg:66-69, wa 18.11.01(2), 18.10.35, 18.11.03, 18.10.26(4)). Explore = COINS10 2021-2023, Binance 1-min klines
aggregated to 5-min bars; New York clock with DST. Simple returns. Every number vs a stated placebo, day-block bootstrap.

    nice -n 19 .venv/bin/python -m research.studies.is3_c2 all     -> research/is3/C2__explore.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
LO, HI = "2021-01-01", "2024-01-01"
NY = "America/New_York"


def bars(coin: str) -> pd.DataFrame:
    k = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet")
    k.index = pd.to_datetime(k.t, unit="ms", utc=True)
    k = k[(k.index >= pd.Timestamp(LO, tz="UTC") - pd.Timedelta("40D")) & (k.index < pd.Timestamp(HI, tz="UTC") + pd.Timedelta("3D"))]
    b = pd.DataFrame({"c": k.c.resample("5min").last(), "h": k.h.resample("5min").max(), "l": k.l.resample("5min").min(),
                      "qv": k.qv.resample("5min").sum(), "tb": k.tbqv.resample("5min").sum()})
    b["c"] = b.c.ffill()
    return b


def at(b: pd.DataFrame, ts) -> float:
    i = b.index.searchsorted(ts) - 1           # close of the last 5-min bar that ENDS at or before ts (bar labelled by its start)
    return float(b.c.iloc[i]) if 0 <= i < len(b) else np.nan


def ret(b, t0, t1):
    a, z = at(b, t0), at(b, t1)
    return z / a - 1 if a > 0 else np.nan


def ev(rows):
    return pd.DataFrame(rows)


def stat(e, base=None, reps=1000):
    cols = ["time", "coin", "side", "gross"]
    return L.stats(e[cols], base[cols] if base is not None else None, reps=reps)


def nyday(day, hh, mm=0):
    return pd.Timestamp(day.year, day.month, day.day, hh, mm).tz_localize(NY).tz_convert("UTC")


def run() -> dict:
    A, Ap, B, Bp, C, D, E, F, G = [], [], [], [], [], [], [], [], []
    for coin in L.COINS10:
        b = bars(coin)
        days = pd.date_range(LO, pd.Timestamp(HI) - pd.Timedelta("1D"), freq="D")
        for d in days:
            wd = d.weekday()
            if wd >= 5:
                continue
            t = {x: nyday(d, x) for x in (2, 5, 7, 10, 13, 16, 17, 18, 20)}
            rl, rf, rn = ret(b, t[2], t[5]), ret(b, t[5], t[7]), ret(b, t[7], t[10])
            if not np.isfinite(rl + rf + rn):
                continue
            # a kill-zone continuation; placebo = a 3-h window starting 2-4 h earlier or later -> next 3-h window after a 2-h gap
            A.append({"time": t[7], "coin": coin, "side": int(np.sign(rl)) or 1, "gross": (np.sign(rl) or 1) * rn})
            for sh in (-4, 4, 8):
                p0 = t[2] + pd.Timedelta(hours=sh)
                r1, r2 = ret(b, p0, p0 + pd.Timedelta("3h")), ret(b, p0 + pd.Timedelta("5h"), p0 + pd.Timedelta("8h"))
                if np.isfinite(r1 + r2):
                    Ap.append({"time": p0 + pd.Timedelta("5h"), "coin": coin, "side": int(np.sign(r1)) or 1, "gross": (np.sign(r1) or 1) * r2})
            # b filler given back in the NY zone (sign), and the London zone's busiest 5-min close as the target
            B.append({"time": t[7], "coin": coin, "side": -(int(np.sign(rf)) or 1), "gross": -(np.sign(rf) or 1) * rn})
            seg = b[(b.index >= t[2]) & (b.index < t[5])]
            ny = b[(b.index >= t[7]) & (b.index < t[10])]
            if len(seg) and len(ny):
                poc = float(seg.c[seg.qv.idxmax()])
                p7 = at(b, t[7])
                if abs(poc / p7 - 1) > 5e-4:
                    mir = 2 * p7 - poc
                    hit_t = ny.index[((ny.l <= poc) & (ny.h >= poc)).to_numpy()]
                    hit_m = ny.index[((ny.l <= mir) & (ny.h >= mir)).to_numpy()]
                    ft = hit_t[0] if len(hit_t) else None
                    fm = hit_m[0] if len(hit_m) else None
                    if ft is not None or fm is not None:
                        Bp.append({"time": t[7], "coin": coin, "side": 1,
                                   "gross": 0.5 if ft == fm else float(fm is None or (ft is not None and ft < fm)),
                                   "filler_toward": float(np.sign(rf) == np.sign(poc - at(b, t[5])) * -1) if np.isfinite(rf) else np.nan})
            # f Monday US-open window 13:30-17:00 UTC vs Tue-Fri
            u0, u1 = pd.Timestamp(d.year, d.month, d.day, 13, 30, tz="UTC"), pd.Timestamp(d.year, d.month, d.day, 17, 0, tz="UTC")
            w = b[(b.index >= u0) & (b.index < u1)]
            if len(w) and w.qv.sum() > 0:
                F.append({"time": u0, "coin": coin, "side": 1, "mon": wd == 0, "gross": ret(b, u0, u1), "imb": float((2 * w.tb.sum() - w.qv.sum()) / w.qv.sum())})
            # g Friday post-cash 16-20 NY vs Mon-Thu
            G.append({"time": t[16], "coin": coin, "side": 1, "fri": wd == 4, "gross": ret(b, t[16], t[20])})
            # c the CME break hour 17-18 NY; 16:15-16:30 NY until the halt ended (2021-06-25)
            C.append({"time": t[17], "coin": coin, "side": 1, "kind": "17-18NY", "gross": ret(b, t[17], t[18])})
            if d < pd.Timestamp("2021-06-25"):
                C.append({"time": t[16], "coin": coin, "side": 1, "kind": "16:15-16:30NY", "gross": ret(b, nyday(d, 16, 15), nyday(d, 16, 30))})
        # c baseline: every other clock hour (1-h returns), d illiquid-hour moves, e same clock half-hour persistence
        hc = b.c.resample("1h").last(); hv = b.qv.resample("1h").sum()
        hr = hc.pct_change(fill_method=None)
        hidx = hr.index
        inr = (hidx >= LO) & (hidx < HI)
        nyh = hidx.tz_convert(NY)
        base_h = hr[inr & (nyh.hour != 17)].dropna()
        C.extend({"time": t_, "coin": coin, "side": 1, "kind": "other_hours", "gross": g_} for t_, g_ in base_h.sample(frac=0.1, random_state=1).items())
        how = hidx.weekday * 24 + hidx.hour
        liq = pd.Series(hv.to_numpy(), index=how).groupby(level=0).mean()
        illiq = set(liq.index[liq <= liq.quantile(0.25)])
        sig = np.log(hc).diff().rolling(720, min_periods=360).std().shift(1)
        z = np.log(hc).diff() / sig
        isl = pd.Series([h_ in illiq for h_ in how], index=hidx)
        cv = hc.to_numpy()
        for j in np.flatnonzero((z.abs() >= 2).to_numpy() & inr):
            # fade until the end of the first liquid hour after the move (max 12 h)
            k_ = j + 1
            while k_ < len(cv) - 1 and k_ - j <= 12 and isl.iloc[k_]:
                k_ += 1
            if k_ + 1 >= len(cv):
                continue
            s_ = -int(np.sign(z.iloc[j]))
            D.append({"time": hidx[j], "coin": coin, "side": s_, "illiq": bool(isl.iloc[j]), "m": int(min(abs(z.iloc[j]), 5) * 2),
                      "gross": s_ * (cv[k_ + 1] / cv[j] - 1), "f4": s_ * (cv[min(j + 4, len(cv) - 1)] / cv[j] - 1)})
        h30 = b.c.resample("30min").last(); q30 = b.qv.resample("30min").sum(); t30 = b.tb.resample("30min").sum()
        r30 = h30.pct_change(fill_method=None); im30 = (2 * t30 - q30) / q30.replace(0, np.nan)
        x = pd.DataFrame({"r": r30, "im": im30})
        for lag in (47, 48, 49):
            x[f"r{lag}"] = r30.shift(lag); x[f"im{lag}"] = im30.shift(lag)
        x = x[(x.index >= LO) & (x.index < HI)].dropna()
        x["coin"] = coin
        E.append(x)
    res = {}
    a, ap = ev(A), ev(Ap)
    s = stat(a, ap)
    res["a_london_zone_sign_x_ny_zone"] = {"n": s["n"], "mean_bp": s["mean_bp"], "placebo_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
    bb, bp = ev(B), ev(Bp)
    s = stat(bb, ap.assign(gross=-ap.gross))
    res["b_filler_given_back_in_ny_zone"] = {"n": s["n"], "mean_bp": s["mean_bp"], "placebo_reversal_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
    s = stat(bp.assign(gross=bp.gross - 0.5))
    res["b_london_poc_before_mirror_in_ny_zone"] = {"n": s["n"], "hit": round(float(bp.gross.mean()), 4), "diff_vs_50_pp": round(s["mean_bp"] / 100, 2), "ci95_pp": [round(v / 100, 2) for v in s["ci95_bp"]], "p": s["p"]}
    c = ev(C)
    for kind in ("17-18NY", "16:15-16:30NY"):
        x = c[c.kind == kind]; base = c[c.kind == "other_hours"]
        base = base[base.time < x.time.max()] if kind != "17-18NY" else base
        s = stat(x, base)
        res[f"c_{kind}"] = {"n": s["n"], "mean_bp": s["mean_bp"], "other_hours_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"],
                            "by_year": s["by_year"], "coins_positive": s["coins_positive"]}
    d = ev(D)
    for H in ("gross", "f4"):
        e_, pool = d[d.illiq], d[~d.illiq]
        base = L.matched(e_, pool, k=3)
        s = stat(e_.assign(gross=e_[H]), base.assign(gross=base[H]))
        res[f"d_illiquid_hour_moves_fade_{'until_liquid' if H == 'gross' else '4h'}"] = {"n": s["n"], "mean_bp": s["mean_bp"], "liquid_matched_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
    e = pd.concat(E)
    res["e_same_halfhour_yesterday"] = {}
    for v in ("r", "im"):
        cors = {lag: float(e.groupby("coin").apply(lambda g: g[v].corr(g[f"{v}{lag}"])).mean()) for lag in (47, 48, 49)}
        res["e_same_halfhour_yesterday"][v] = {f"corr_lag{lag}": round(cc, 4) for lag, cc in cors.items()}
        res["e_same_halfhour_yesterday"][v]["lag48_minus_avg_47_49"] = round(cors[48] - (cors[47] + cors[49]) / 2, 4)
    # trade view of e on returns: sign of yesterday's same half-hour return
    tr = pd.DataFrame({"time": e.index, "coin": e.coin.to_numpy(), "side": np.sign(e.r48.to_numpy()), "gross": np.sign(e.r48.to_numpy()) * e.r.to_numpy()})
    trp = pd.DataFrame({"time": e.index, "coin": e.coin.to_numpy(), "side": np.sign(e.r47.to_numpy()), "gross": np.sign(e.r47.to_numpy()) * e.r.to_numpy()})
    s = stat(tr, trp, reps=300)
    res["e_trade_sign_of_same_halfhour_yesterday"] = {"n": s["n"], "mean_bp": s["mean_bp"], "lag47_placebo_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
    f = ev(F)
    s = stat(f[f.mon], f[~f.mon])
    res["f_monday_us_open_drift"] = {"n": s["n"], "mean_bp": s["mean_bp"], "tue_fri_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"], "by_year": s["by_year"]}
    res["f_monday_imbalance"] = {"mon": round(float(f[f.mon].imb.mean()), 4), "tue_fri": round(float(f[~f.mon].imb.mean()), 4)}
    fm = f[f.mon].sort_values("time").copy()
    fm["prev_imb"] = fm.groupby("coin").imb.shift(1)
    fm = fm.dropna(subset=["prev_imb"])
    res["f_prev_monday_imbalance_predicts"] = {"corr_imb": round(float(fm.groupby("coin").apply(lambda g: g.imb.corr(g.prev_imb)).mean()), 4),
                                               "corr_ret_on_prev_imb": round(float(fm.groupby("coin").apply(lambda g: g.gross.corr(g.prev_imb)).mean()), 4), "n": int(len(fm))}
    g = ev(G)
    s = stat(g[g.fri], g[~g.fri])
    res["g_friday_16_20_ny"] = {"n": s["n"], "mean_bp": s["mean_bp"], "mon_thu_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"], "by_year": s["by_year"],
                                "sign_share_fri": round(float((g[g.fri].gross > 0).mean()), 3)}
    return res


if __name__ == "__main__":
    r = run()
    print(json.dumps(r, indent=1, default=float))
    (ROOT / "research/is3/C2__explore.json").write_text(json.dumps(r, indent=1, default=float))
