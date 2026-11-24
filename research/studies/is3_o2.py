"""O2 the author's own indicators (R30; tg:90, 98-100; Crayons V3.4, FSVZO V2.8 guides). Explore 2021-2023.
Panels: COINS10 1h / 4h (Binance 1-min klines) and bnall daily top-100 (clean). Open = previous close (klines carry no open).
Baseline for every event form: same coin, same decile of the trailing 14-bar return, 3 matched bars, same side.
Forms (definitions in research/is3/notes.md, O2 think-through): a RSI-vs-VZO sham pumps, b MACD-cross fade, c Hull Suite,
d Leledc exhaustion, e VZO alert end, i camarilla pivots (1h only, prior UTC day), j failed extension (H), k invalidated
exhaustion bar, l VZO midline rejection, m VZO veto on breakout entries.

    nice -n 19 .venv/bin/python -m research.studies.is3_o2      -> research/is3/O2__explore.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from kripto import data
from research.studies import is3_lib as L
from research.studies.is3_o1 import rsi

ROOT = Path(__file__).resolve().parents[2]
LO, HI = "2021-01-01", "2024-01-01"
HZ = {"1h": (6, 24), "4h": (6, 18), "1d": (5, 10)}


def panels() -> dict:
    out = {}
    hh, ll, cc, vv = {}, {}, {}, {}
    for coin in L.COINS10:
        k = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet", columns=["t", "h", "l", "c", "qv"])
        k.index = pd.to_datetime(k.t, unit="ms", utc=True)
        k = k[(k.index >= "2020-10-01") & (k.index < "2024-01-15")]
        hh[coin], ll[coin], cc[coin], vv[coin] = k.h, k.l, k.c, k.qv
    H, Lw, C, V = (pd.DataFrame(x) for x in (hh, ll, cc, vv))
    for tf in ("1h", "4h"):
        out[tf] = {"h": H.resample(tf).max(), "l": Lw.resample(tf).min(), "c": C.resample(tf).last(), "v": V.resample(tf).sum()}
    p = data.load_panel("bnall", "1d")
    top = p["volume"].rolling(30, min_periods=20).mean().shift(1).rank(axis=1, ascending=False) <= 100
    keep = top.loc["2020-09-01":"2024-02-01"].any()
    cols = keep[keep].index
    sl = lambda x: x.loc["2020-06-01":"2024-02-01", cols]
    out["1d"] = {"h": sl(p["high"]), "l": sl(p["low"]), "c": sl(p["close"]).where(sl(top)), "v": sl(p["volume"])}
    return out


def wma(x: pd.DataFrame, n: int) -> pd.DataFrame:
    w = np.arange(1, n + 1, dtype=float)
    return x.rolling(n).apply(lambda a: np.dot(a, w) / w.sum(), raw=True)


def hma(x: pd.DataFrame, n: int) -> pd.DataFrame:
    return wma(2 * wma(x, n // 2) - wma(x, n), int(np.sqrt(n)))


def vzo(c, v, n=14):
    r = np.sign(c.diff()) * v
    return 100 * r.ewm(span=n, adjust=False).mean() / v.ewm(span=n, adjust=False).mean()


def frame(P: dict) -> pd.DataFrame:
    c = P["c"]
    ret14 = c / c.shift(14) - 1
    d = {"ret14": ret14.stack(future_stack=True)}
    for H in sorted({h for hz in HZ.values() for h in hz}):
        d[f"f{H}"] = (c.shift(-H) / c - 1).stack(future_stack=True)
    x = pd.DataFrame(d)
    x.index.names = ["time", "coin"]
    x = x.reset_index()
    x = x[(x.time >= LO) & (x.time < HI)].dropna(subset=["ret14"])
    x["m"] = (x.groupby("coin").ret14.rank(pct=True) * 9.999).astype(int)
    return x


def ev_from_mask(mask: pd.DataFrame, side, form: str) -> pd.DataFrame:
    s = mask.stack(future_stack=True)
    s = s[s.fillna(False).astype(bool)]
    e = s.reset_index()[["level_0", "level_1"]] if "level_0" in s.reset_index().columns else s.reset_index().iloc[:, :2]
    e.columns = ["time", "coin"]
    if isinstance(side, pd.DataFrame):
        sv = side.stack(future_stack=True)
        e["side"] = [int(sv.get((t, c), 0)) for t, c in zip(e.time, e.coin)]
    else:
        e["side"] = side
    e["form"] = form
    return e[(e.time >= LO) & (e.time < HI) & (e.side != 0)]


def build_events(P: dict, tf: str) -> pd.DataFrame:
    h, l, c, v = P["h"], P["l"], P["c"], P["v"]
    o = c.shift(1)
    sig = np.log(c).diff().rolling(60, min_periods=30).std().shift(1)
    z = np.log(c).diff() / sig
    R = rsi(c)
    Z = vzo(c, v)
    FZ = wma(Z, 4)
    E = []
    # a: pump bar >= 2 sigma with RSI > 70: sham (|VZO| < 20) -> short, real (VZO > 40) -> short too (fade), compared
    pump = (z >= 2) & (R > 70)
    E.append(ev_from_mask(pump & (Z.abs() < 20), -1, "a_sham_pump_fade"))
    E.append(ev_from_mask(pump & (Z > 40), -1, "a_real_pump_fade"))
    # b: MACD cross, fade for 2 bars (use horizon 2 separately below via f2)
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    sg = macd.ewm(span=9, adjust=False).mean()
    up = (macd > sg) & (macd.shift(1) <= sg.shift(1))
    dn = (macd < sg) & (macd.shift(1) >= sg.shift(1))
    E.append(ev_from_mask(up, -1, "b_macd_up_cross_fade"))
    E.append(ev_from_mask(dn, 1, "b_macd_dn_cross_fade"))
    # c: Hull Suite turn (HMA55 vs 2 bars ago), with/without HMA180 slope filter
    h55 = hma(c, 55)
    s55 = np.sign(h55 - h55.shift(2))
    turn = (s55 != s55.shift(1)) & s55.notna() & s55.shift(1).notna() & (s55 != 0)
    h180 = hma(c, 180)
    s180 = np.sign(h180 - h180.shift(2))
    for sgn, nm in ((1, "up"), (-1, "dn")):                 # one side per form: the matched baseline takes the form's side
        E.append(ev_from_mask(turn & (s55 == sgn), sgn, f"c_hull55_turn_{nm}"))
        E.append(ev_from_mask(turn & (s55 == sgn) & (s180 == sgn), sgn, f"c_hull55_turn_with_180_{nm}"))
    # d: Leledc exhaustion
    cu = (c > c.shift(4)).astype(int); cd = (c < c.shift(4)).astype(int)
    bind = cu.copy() * 0; sind = cd.copy() * 0
    cuv, cdv = cu.to_numpy(), cd.to_numpy()
    bi, si = np.zeros_like(cuv), np.zeros_like(cdv)
    for t in range(1, len(cuv)):
        bi[t] = (bi[t - 1] + 1) * cuv[t]
        si[t] = (si[t - 1] + 1) * cdv[t]
    bind.iloc[:, :] = bi; sind.iloc[:, :] = si
    bear_ex = (bind.shift(1) > 6) & (c < o) & (h >= h.rolling(30).max())
    bull_ex = (sind.shift(1) > 6) & (c > o) & (l <= l.rolling(30).min())
    E.append(ev_from_mask(bear_ex, -1, "d_leledc_bear"))
    E.append(ev_from_mask(bull_ex, 1, "d_leledc_bull"))
    # k: invalidation of an exhaustion bar: a later close (within 10 bars) beyond its open on the opposite side -> trade it
    for ex, sgn, nm in ((bear_ex, 1, "k_bear_ex_invalidated_long"), (bull_ex, -1, "k_bull_ex_invalidated_short")):
        lvl = o.where(ex).ffill(limit=10)
        age_ok = ex.astype(float).replace(0, np.nan).ffill(limit=10).notna()
        cross = (sgn * (c - lvl) > 0) & (sgn * (c.shift(1) - lvl.shift(1)) <= 0) & age_ok & ~ex
        E.append(ev_from_mask(cross, sgn, nm))
    # k baseline: the same kind of close beyond the open of an ordinary opposite-colour bar 1-10 bars back (no exhaustion condition)
    red = c < o
    lvl0 = o.where(red).ffill(limit=10)
    E.append(ev_from_mask((c > lvl0) & (c.shift(1) <= lvl0.shift(1)) & ~red, 1, "k_placebo_close_above_red_open"))
    # e: end of a VZO alert run (first bar back inside), dose by threshold: after abnormal selling -> long, buying -> short
    for X in (40, 60, 80):
        endsell = (FZ.shift(1) < -X) & (FZ >= -X)
        endbuy = (FZ.shift(1) > X) & (FZ <= X)
        E.append(ev_from_mask(endsell, 1, f"e_vzo_sell_alert_end_{X}"))
        E.append(ev_from_mask(endbuy, -1, f"e_vzo_buy_alert_end_{X}"))
    # l: midline rejection (turn within 0..10 without crossing) vs the same turn at 30..40
    for lo_, hi_, nm in ((0, 10, "l_midline"), (30, 40, "l_placebo_30")):
        up_t = (FZ.shift(1) > lo_) & (FZ.shift(1) <= hi_) & (FZ > FZ.shift(1)) & (FZ.shift(1) < FZ.shift(2)) & (FZ.rolling(5).min() > 0)
        dn_t = (FZ.shift(1) < -lo_) & (FZ.shift(1) >= -hi_) & (FZ < FZ.shift(1)) & (FZ.shift(1) > FZ.shift(2)) & (FZ.rolling(5).max() < 0)
        E.append(ev_from_mask(up_t, 1, f"{nm}_up"))
        E.append(ev_from_mask(dn_t, -1, f"{nm}_dn"))
    # m: 20-bar breakout longs / breakdown shorts, with and without the veto (long into VZO > 60, short into VZO < -60)
    bo = c > h.shift(1).rolling(20).max()
    bd = c < l.shift(1).rolling(20).min()
    E.append(ev_from_mask(bo & (Z > 60), 1, "m_breakout_vetoed"))
    E.append(ev_from_mask(bo & (Z <= 60), 1, "m_breakout_allowed"))
    E.append(ev_from_mask(bd & (Z < -60), -1, "m_breakdown_vetoed"))
    E.append(ev_from_mask(bd & (Z >= -60), -1, "m_breakdown_allowed"))
    return pd.concat(E, ignore_index=True)


def camarilla(P: dict) -> pd.DataFrame:
    """1h panel: prior UTC day's H/L/C -> H3/L3 first touch (fade) and H4/L4 1-h close beyond (break), vs 0.63x / 1.37x distances."""
    h, l, c = P["h"], P["l"], P["c"]
    dh, dl, dc = h.resample("1D").max().shift(1), l.resample("1D").min().shift(1), c.resample("1D").last().shift(1)
    rows = []
    for mult, tag in ((1.0, "real"), (0.63, "near"), (1.37, "far")):
        rng = (dh - dl) * 1.1 * mult
        for lvl_name, off, side, kind in (("H3", 0.25, -1, "fade"), ("L3", -0.25, 1, "fade"), ("H4", 0.5, 1, "break"), ("L4", -0.5, -1, "break")):
            lv = (dc + off * rng).reindex(c.index, method="ffill")
            day = c.index.floor("D")
            if kind == "fade":
                hit = (h >= lv) if off > 0 else (l <= lv)
            else:
                hit = (c > lv) if off > 0 else (c < lv)
            first = hit & hit.astype(int).groupby(day).cumsum().eq(1)
            e = ev_from_mask(first, side, f"i_{lvl_name}_{kind}_{tag}")
            rows.append(e)
    return pd.concat(rows, ignore_index=True)


def run() -> dict:
    res = {}
    P = panels()
    for tf in ("1h", "4h", "1d"):
        fr = frame(P[tf])
        c = P[tf]["c"]
        f2 = (c.shift(-2) / c - 1).stack(future_stack=True).rename("f2b").reset_index()
        f2.columns = ["time", "coin", "f2b"]
        fr = fr.merge(f2, on=["time", "coin"], how="left")
        ev = build_events(P[tf], tf)
        if tf == "1h":
            ev = pd.concat([ev, camarilla(P[tf])], ignore_index=True)
        ev = ev.merge(fr, on=["time", "coin"], how="inner")
        res[tf] = {}
        for form, x in ev.groupby("form"):
            if len(x) < 30:
                res[tf][form] = {"n": int(len(x))}
                continue
            key = set(zip(x.time, x.coin))
            pool = fr[[(t, k) not in key for t, k in zip(fr.time, fr.coin)]]
            base = L.matched(x, pool, k=3)
            out = {}
            hs = (["f2b"] if form.startswith("b_") else []) + [f"f{H}" for H in HZ[tf]]
            for H in hs:
                xs = x.dropna(subset=[H]); bs = base.dropna(subset=[H])
                assert xs.side.nunique() == 1, f"{form}: mixed sides break the matched baseline"
                sd = int(xs.side.iloc[0])
                s = L.stats(xs.assign(gross=xs[H] * xs.side)[["time", "coin", "side", "gross"]],
                            bs.assign(side=sd, gross=bs[H] * sd)[["time", "coin", "side", "gross"]], reps=300)
                out[H] = {"n": s["n"], "mean_bp": s["mean_bp"], "matched_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
            res[tf][form] = out
            k0 = hs[0]
            print(f"{tf} {form:34s} n={out[k0]['n']:6d} {k0}: {out[k0]['mean_bp']:+7.1f} vs {out[k0]['matched_bp']:+7.1f} diff {out[k0]['diff_bp']:+7.1f} p {out[k0]['p']:.3f} mde {out[k0]['mde_bp']}")
        (ROOT / "research/is3/O2__explore.json").write_text(json.dumps(res, indent=1, default=float))
    return res




def form_j() -> dict:
    """j Crayons H / W (p12-13): failed extension = the wick makes a new 20-bar high (low) but the close stays below the old high
    (above the old low). H in an uptrend (ret14 > 0) -> short; W in a downtrend -> short (his 'continuation'); W in an uptrend ->
    long (his 'only a pause'). Baseline: same coin, bars of the same trend state NOT at a new extreme with the same wick-size
    quintile (wick / close), same side."""
    P = panels()
    res = {}
    for tf in ("1h", "4h", "1d"):
        h, l, c = P[tf]["h"], P[tf]["l"], P[tf]["c"]
        o = c.shift(1)
        ph, pl = h.shift(1).rolling(20).max(), l.shift(1).rolling(20).min()
        r14 = c / c.shift(14) - 1
        uw = (h - np.maximum(c, o)) / c
        lw = (np.minimum(c, o) - l) / c
        rows = []
        for H in HZ[tf]:
            pass
        fwd = {H: c.shift(-H) / c - 1 for H in HZ[tf]}
        def st(mask, wick, side):
            d = {"ev": mask, "wick": wick, **{f"f{H}": fwd[H] for H in HZ[tf]}}
            x = pd.concat({k: v.stack(future_stack=True) for k, v in d.items()}, axis=1).reset_index()
            x.columns = ["time", "coin"] + list(d)
            return x[(x.time >= LO) & (x.time < HI)].dropna()
        for nm, ext, wick, trend, side in (("H_uptrend_short", (h > ph) & (c < ph), uw, r14 > 0, -1),
                                           ("W_downtrend_short", (l < pl) & (c > pl), lw, r14 < 0, -1),
                                           ("W_uptrend_long", (l < pl) & (c > pl), lw, r14 > 0, 1)):
            x = st(ext & trend, wick, side)
            x["ev"] = x.ev.astype(bool)
            pool_all = st(trend & ~((h > ph) | (l < pl)), wick, side)
            edges = np.quantile(x.loc[x.ev, "wick"], [0, .2, .4, .6, .8, 1]) if x.ev.sum() > 30 else None
            if edges is None:
                res[f"{tf}_{nm}"] = {"n": int(x.ev.sum())}
                continue
            edges[-1] += 1; edges[0] = -1
            ev = x[x.ev].assign(side=side, m=lambda d: pd.cut(d.wick, edges, labels=False))
            pool = pool_all[pool_all.ev.astype(bool)].assign(side=side, m=lambda d: pd.cut(d.wick, edges, labels=False)).dropna(subset=["m"])
            base = L.matched(ev, pool, k=3)
            out = {}
            for H in HZ[tf]:
                s = L.stats(ev.assign(gross=ev[f"f{H}"] * side)[["time", "coin", "side", "gross"]], base.assign(gross=base[f"f{H}"] * side)[["time", "coin", "side", "gross"]], reps=300)
                out[f"f{H}"] = {"n": s["n"], "mean_bp": s["mean_bp"], "matched_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
            res[f"{tf}_{nm}"] = out
            print(tf, nm, out)
    (ROOT / "research/is3/O2j__explore.json").write_text(json.dumps(res, indent=1, default=float))
    return res


def form_h() -> dict:
    """h linear-regression channel (tg:77, wa 18.10.43(2)): rolling OLS of log price on time over N = 100 bars, bands = fit at the
    last bar +- 2 residual sd. First bar whose low (high) reaches the lower (upper) band from inside -> long (short). Placebo bands
    at 0.63x and 1.37x the width (same construction, wrong distance). Baseline = same coin, same trailing-14-bar return decile."""
    P = panels()
    res = {}
    N = 100
    for tf in ("1h", "4h", "1d"):
        h, l, c = P[tf]["h"], P[tf]["l"], P[tf]["c"]
        y = np.log(c)
        t = pd.DataFrame(np.arange(len(y), dtype=float)[:, None].repeat(y.shape[1], 1), index=y.index, columns=y.columns)
        cov = (y * t).rolling(N).mean() - y.rolling(N).mean() * t.rolling(N).mean()
        vt = t.rolling(N).var(ddof=0)
        slope = cov / vt
        fit = y.rolling(N).mean() + slope * (N - 1) / 2
        rsd = np.sqrt((y.rolling(N).var(ddof=0) - slope ** 2 * vt).clip(lower=0))
        fr = frame(P[tf])
        for mult, tag in ((1.0, "real"), (0.63, "inner"), (1.37, "outer")):
            ub, lb = np.exp(fit.shift(1) + 2 * mult * rsd.shift(1)), np.exp(fit.shift(1) - 2 * mult * rsd.shift(1))
            lo_t = (l <= lb) & (l.shift(1) > lb.shift(1))
            hi_t = (h >= ub) & (h.shift(1) < ub.shift(1))
            for side, m, nm in ((1, lo_t, "lower_long"), (-1, hi_t, "upper_short")):
                x = ev_from_mask(m, side, f"h_{nm}_{tag}").merge(fr, on=["time", "coin"], how="inner")
                key = set(zip(x.time, x.coin))
                pool = fr[[(a, b) not in key for a, b in zip(fr.time, fr.coin)]]
                base = L.matched(x, pool, k=3)
                H = f"f{HZ[tf][0]}"
                x, base = x.dropna(subset=[H]), base.dropna(subset=[H])
                s_ = L.stats(x.assign(gross=x[H] * side)[["time", "coin", "side", "gross"]], base.assign(side=side, gross=base[H] * side)[["time", "coin", "side", "gross"]], reps=300)
                res[f"{tf}_{nm}_{tag}"] = {"n": s_["n"], "mean_bp": s_["mean_bp"], "matched_bp": s_["base_bp"], "diff_bp": s_["vs_base_bp"], "p": s_["p_vs_base"], "mde_bp": s_["mde80_bp"], "H": H}
                print(tf, nm, tag, res[f"{tf}_{nm}_{tag}"])
    (ROOT / "research/is3/O2h__explore.json").write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    import sys
    {"j": form_j, "h": form_h}.get((sys.argv[1:] or [""])[0], run)()
