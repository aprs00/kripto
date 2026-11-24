"""C1 calendar claims (InSilico R22-R25 + the Almanac he shared). Daily simple returns of BTC and an equal-weight top-30 basket
(bnall clean universe, top 30 by trailing 30-day volume, shift 1; single-coin daily returns clipped to +-50% against bad prints).
Every tag is compared with the untagged days by is3_lib.stats (day-block bootstrap). explore = 2021-2023; `--all` adds 2024-25
as a second column (only to be read for forms whose explore effect beats costs AND whose MDE is below the effect).

    nice -n 19 .venv/bin/python -m research.studies.is3_c1 [a|b|c|e|f|g|h|i|d]   -> research/is3/C1<form>__explore.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from kripto import data
from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = {"explore": ("2021-01-01", "2024-01-01"), "later": ("2024-01-01", "2026-01-01")}
SYN = 29.530588853
NEW0 = pd.Timestamp("2000-01-06 18:14", tz="UTC")
CNY = ["2021-02-12", "2022-02-01", "2023-01-22", "2024-02-10", "2025-01-29"]
FOMC: list[str] = []          # filled from research/is3/C1_dates.json (official calendars) when present


def series() -> tuple[pd.DataFrame, pd.DataFrame]:
    p = data.load_panel("bnall", "1d")
    c, v = p["close"], p["volume"]
    r = c.pct_change(fill_method=None).clip(-0.5, 0.5)
    top = v.rolling(30, min_periods=20).mean().shift(1).rank(axis=1, ascending=False) <= 30
    ew = r.where(top).mean(axis=1)
    s = pd.DataFrame({"BTC": r["BTC"], "EW30": ew}).dropna()
    s.index = s.index.normalize()
    return s, r.where(v.rolling(30, min_periods=20).mean().shift(1).rank(axis=1, ascending=False) <= 100)


def test(s: pd.DataFrame, tag: pd.Series, name: str, res: dict, reps: int = 1000) -> None:
    out = {}
    for smp, (lo, hi) in SAMPLES.items():
        for col in ("BTC", "EW30"):
            x = s[(s.index >= lo) & (s.index < hi)]
            t = tag.reindex(x.index).fillna(False).astype(bool)
            ev = pd.DataFrame({"time": x.index[t], "coin": col, "side": 1, "gross": x[col][t].to_numpy()})
            ba = pd.DataFrame({"time": x.index[~t], "coin": col, "side": 1, "gross": x[col][~t].to_numpy()})
            if len(ev) < 3:
                continue
            st = L.stats(ev, ba, reps=reps)
            out[f"{smp}_{col}"] = {"n_days": st["n"], "mean_bp": st["mean_bp"], "rest_bp": st["base_bp"], "diff_bp": st["vs_base_bp"], "p": st["p_vs_base"], "mde_bp": st["mde80_bp"]}
    res[name] = out
    e = out.get("explore_EW30", {}); b = out.get("explore_BTC", {})
    print(f"{name:28s} EW30 n={e.get('n_days')} diff {e.get('diff_bp')} p {e.get('p')} mde {e.get('mde_bp')} | BTC diff {b.get('diff_bp')} p {b.get('p')}")


def last_fridays(idx: pd.DatetimeIndex) -> list[pd.Timestamp]:
    out = []
    for m in pd.period_range(idx.min(), idx.max(), freq="M"):
        d = m.end_time.normalize().tz_localize("UTC") if m.end_time.tzinfo is None else m.end_time.normalize()
        while d.weekday() != 4:
            d -= pd.Timedelta("1D")
        out.append(d)
    return out


def third_fridays(idx) -> list[pd.Timestamp]:
    out = []
    for m in pd.period_range(idx.min(), idx.max(), freq="M"):
        d = pd.Timestamp(m.start_time).tz_localize("UTC")
        fr = [d + pd.Timedelta(days=i) for i in range(31) if (d + pd.Timedelta(days=i)).month == d.month and (d + pd.Timedelta(days=i)).weekday() == 4]
        out.append(fr[2])
    return out


def window(idx, anchors, a: int, b: int) -> pd.Series:
    t = pd.Series(False, index=idx)
    for x in anchors:
        for k in range(a, b + 1):
            y = x + pd.Timedelta(days=k)
            if y in t.index:
                t[y] = True
    return t


def form_a(s, res):
    rows = []
    k0 = int((pd.Timestamp("2020-01-01", tz="UTC") - NEW0) / pd.Timedelta(days=SYN)) + 1
    for k in range(k0, k0 + 90):
        new = (NEW0 + pd.Timedelta(days=k * SYN)).normalize()
        full = (NEW0 + pd.Timedelta(days=k * SYN + SYN / 2)).normalize()
        nxt = (NEW0 + pd.Timedelta(days=(k + 1) * SYN)).normalize()
        if nxt not in s.index or new not in s.index or full not in s.index:
            continue
        for col in ("BTC", "EW30"):
            wax = (1 + s[col][(s.index > new) & (s.index <= full)]).prod() - 1
            wan = (1 + s[col][(s.index > full) & (s.index <= nxt)]).prod() - 1
            rows.append({"time": new, "coin": col, "side": 1, "gross": wax - wan})
    e = pd.DataFrame(rows)
    out = {}
    for smp, (lo, hi) in SAMPLES.items():
        for col in ("BTC", "EW30"):
            x = e[(e.coin == col) & (e.time >= lo) & (e.time < hi)]
            st = L.stats(x, reps=2000)
            out[f"{smp}_{col}"] = {"cycles": st["n"], "wax_minus_wane_bp": st["mean_bp"], "ci95_bp": st["ci95_bp"], "p": st["p"], "mde_bp": st["mde80_bp"]}
    res["a_lunar_waxing_minus_waning_per_cycle"] = out
    print("a", {k: v for k, v in out.items() if k.startswith("explore")})


def form_b(s, res):
    lf = last_fridays(s.index)
    q = [d for d in lf if d.month in (3, 6, 9, 12)]
    test(s, window(s.index, lf, -6, 0), "b_monthly_expiry_week_before", res)
    test(s, window(s.index, lf, 1, 7), "b_monthly_expiry_week_after", res)
    test(s, window(s.index, q, -6, 0), "b_quarterly_expiry_week_before", res)
    test(s, window(s.index, q, 1, 7), "b_quarterly_expiry_week_after", res)
    eq = [pd.Timestamp(f"{y}-{md}", tz="UTC") for y in range(2020, 2026) for md in ("03-20", "09-22")]
    test(s, window(s.index, eq, -3, 3), "b_equinox_pm3d", res)


def form_c(s, res):
    tab = {}
    for dw, nm in enumerate("Mon Tue Wed Thu Fri Sat Sun".split()):
        test(s, pd.Series(s.index.weekday == dw, index=s.index), f"c_dow_{nm}", tab)
    tom = pd.Series((s.index.day <= 3) | (s.index + pd.Timedelta("1D")).day == 1, index=s.index)
    tom = pd.Series(((s.index.day <= 3) | ((s.index + pd.Timedelta("1D")).day == 1)), index=s.index)
    test(s, tom, "c_turn_of_month_last_plus_first3", tab)
    # hour of week, BTC 1-min klines -> hourly simple returns, explore only
    k = pd.read_parquet(ROOT / "data/bn/klines_1m/BTCUSDT.parquet", columns=["t", "c"])
    k.index = pd.to_datetime(k.t, unit="ms", utc=True)
    hc = k.c.resample("1h").last()
    hr = hc.pct_change(fill_method=None)
    hr = hr[(hr.index >= "2021-01-01") & (hr.index < "2024-01-01")].dropna()
    how = hr.index.weekday * 24 + hr.index.hour
    ps, cells = {}, {}
    for hw in range(168):
        t = how == hw
        ev = pd.DataFrame({"time": hr.index[t], "coin": "BTC", "side": 1, "gross": hr[t].to_numpy()})
        ba = pd.DataFrame({"time": hr.index[~t], "coin": "BTC", "side": 1, "gross": hr[~t].to_numpy()})
        st = L.stats(ev, ba, reps=300)
        cells[hw] = (st["mean_bp"], st["vs_base_bp"], st["p_vs_base"])
        ps[f"h{hw}"] = st["p_vs_base"]
    for nm, v in tab.items():
        ps[nm] = v.get("explore_EW30", {}).get("p", 1.0)
    keep = L.bh(ps, 0.10)
    top = sorted(cells.items(), key=lambda kv: -abs(kv[1][1]))[:6]
    res["c_table"] = tab
    res["c_hour_of_week_top6_by_abs_diff"] = {f"{'Mon Tue Wed Thu Fri Sat Sun'.split()[hw // 24]} {hw % 24:02d}h": {"mean_bp": m, "diff_bp": dd, "p": p_} for hw, (m, dd, p_) in top}
    res["c_fdr10_survivors"] = sorted(keep)
    res["c_cells_tested"] = len(ps)
    print("c FDR survivors:", sorted(keep))


def form_e(s, res):
    test(s, pd.Series(s.index.month == 9, index=s.index), "e_september", res)
    santa = pd.Series(((s.index.month == 12) & (s.index.day >= 25)) | ((s.index.month == 1) & (s.index.day <= 2)), index=s.index)
    test(s, santa, "e_santa_dec25_jan2", res)
    test(s, pd.Series(s.index.month.isin([5, 6, 7, 8, 9, 10]), index=s.index), "e_may_to_october", res)
    cny = [pd.Timestamp(x, tz="UTC") for x in CNY]
    test(s, window(s.index, cny, -7, -1), "e_cny_week_before", res)
    test(s, window(s.index, cny, 0, 6), "e_cny_week_after", res)


def form_f(s, res):
    from pandas.tseries.holiday import USFederalHolidayCalendar
    from dateutil.easter import easter
    hol = list(USFederalHolidayCalendar().holidays("2020-01-01", "2026-01-01"))
    hol += [pd.Timestamp(easter(y)) - pd.Timedelta("2D") for y in range(2020, 2026)]
    hol = [pd.Timestamp(h).tz_localize("UTC") for h in hol if pd.Timestamp(h).weekday() < 5]
    # the last weekday before each holiday
    pre = []
    for h in hol:
        d = h - pd.Timedelta("1D")
        while d.weekday() >= 5 or d in hol:
            d -= pd.Timedelta("1D")
        pre.append(d)
    test(s, window(s.index, pre, 0, 0), "f_pre_us_holiday", res)
    tf = [d for d in third_fridays(s.index) if d.month in (3, 6, 9, 12)]
    test(s, window(s.index, tf, -4, 0), "f_triple_witching_week_mon_fri", res)
    test(s, window(s.index, tf, 3, 7), "f_week_after_triple_witching", res)


def form_g(s, res):
    out = {}
    for col in ("BTC", "EW30"):
        x = s[col]
        fwd = {H: (1 + x).rolling(H).apply(np.prod, raw=True).shift(-H) - 1 for H in (5, 20)}
        rows = []
        for i in range(1, len(x)):
            d = x.index[i]
            if d.weekday() == 0 and x.index[i - 1] == d - pd.Timedelta("3D") or (d.weekday() == 0 and x.index[i - 3] == d - pd.Timedelta("3D")):
                pass
            if d.weekday() != 0:
                continue
            fri = d - pd.Timedelta("3D")
            if fri not in x.index:
                continue
            rows.append({"time": d, "coin": col, "side": 1, "fri": x[fri], "mon": x[d], "two": (1 + x[fri]) * (1 + x[d]) - 1,
                         "f5": fwd[5].get(d), "f20": fwd[20].get(d)})
        e = pd.DataFrame(rows).dropna()
        # any two consecutive down days (any weekdays) of matched size
        y = pd.DataFrame({"time": x.index, "coin": col, "side": 1, "a": x.shift(1), "b": x, "f5": fwd[5], "f20": fwd[20]}).dropna()
        anyd = y[(y.a < 0) & (y.b < 0)].assign(two=lambda z: (1 + z.a) * (1 + z.b) - 1)
        for smp, (lo, hi) in SAMPLES.items():
            ee = e[(e.time >= lo) & (e.time < hi)]
            dd = ee[(ee.fri < 0) & (ee.mon < 0)]
            du = ee[(ee.fri < 0) & (ee.mon > 0)]
            pool = anyd[(anyd.time >= lo) & (anyd.time < hi) & (anyd.time.dt.weekday != 0)]
            q = pd.qcut(pd.concat([dd.two, pool.two]).rank(method="first"), 5, labels=False)
            dd = dd.assign(m=q.iloc[:len(dd)].to_numpy()); pool = pool.assign(m=q.iloc[len(dd):].to_numpy())
            base = L.matched(dd.assign(coin=col), pool.assign(coin=col), k=3)
            for H in ("f5", "f20"):
                st = L.stats(dd.assign(gross=dd[H])[["time", "coin", "side", "gross"]], base.assign(gross=base[H])[["time", "coin", "side", "gross"]], reps=1000)
                st2 = L.stats(du.assign(gross=du[H])[["time", "coin", "side", "gross"]], reps=500)
                out[f"{smp}_{col}_{H}"] = {"n_downfri_downmon": st["n"], "fwd_bp": st["mean_bp"], "vs_matched_two_down_days_bp": st["base_bp"],
                                          "diff_bp": st["vs_base_bp"], "p": st["p_vs_base"], "mde_bp": st["mde80_bp"], "downfri_upmon_fwd_bp": st2["mean_bp"], "n_downfri_upmon": st2["n"]}
    res["g_down_friday_down_monday"] = out
    print("g", {k: (v["fwd_bp"], v["diff_bp"], v["p"]) for k, v in out.items() if k.startswith("explore")})


def form_h(s, R, res):
    c = data.load_panel("bnall", "1d")["close"]
    c.index = c.index.normalize()
    low52 = c.rolling(365, min_periods=200).min()
    rows = []
    for y in range(2020, 2026):
        for m in range(1, 13):
            d = pd.Timestamp(f"{y}-{m:02d}-15", tz="UTC")
            e_ = d + pd.DateOffset(months=2)
            if d not in c.index or e_ not in c.index:
                continue
            univ = R.loc[d].dropna().index
            near = (c.loc[d, univ] / low52.loc[d, univ] - 1) <= 0.05
            fwd = (c.loc[e_, univ] / c.loc[d, univ] - 1).clip(-0.95, 5)
            if near.sum() < 3 or (~near).sum() < 10:
                continue
            rows.append({"time": d, "coin": "XS", "side": 1, "dec": m == 12, "gross": float(fwd[near].mean() - fwd[~near].mean()), "n_near": int(near.sum())})
    e = pd.DataFrame(rows)
    dec, oth = e[e.dec], e[~e.dec]
    res["h_tax_loss"] = {"dec_spreads_bp": {str(t.year): round(g * 1e4, 1) for t, g in zip(dec.time, dec.gross)},
                         "dec_mean_bp": round(float(dec.gross.mean() * 1e4), 1), "other_months_mean_bp": round(float(oth.gross.mean() * 1e4), 1),
                         "other_months_sd_bp": round(float(oth.gross.std() * 1e4), 1), "n_dec": int(len(dec)), "n_other": int(len(oth)),
                         "dec_rank_among_all_months_pct": [round(float((e.gross < g).mean()), 3) for g in dec.gross],
                         "mde_bp_for_mean_of_n_dec": round(float(2.8 * oth.gross.std() / np.sqrt(max(len(dec), 1)) * 1e4), 1)}
    print("h", res["h_tax_loss"])


def form_i(s, res):
    test(s, pd.Series(s.index.day == 1, index=s.index), "i_first_day_of_month", res)
    last = (s.index + pd.Timedelta("1D")).day == 1
    test(s, pd.Series(last | (s.index.day <= 4), index=s.index), "i_last_plus_first4", res)


def form_d(s, res):
    f = ROOT / "research/is3/C1_dates.json"
    dates = json.loads(f.read_text())
    for kind in ("fomc", "cpi"):
        ds = [pd.Timestamp(x, tz="UTC") for x in dates.get(kind, [])]
        if not ds:
            continue
        test(s, window(s.index, ds, -1, -1), f"d_{kind}_day_before", res)
        test(s, window(s.index, ds, 0, 0), f"d_{kind}_day", res)
        test(s, window(s.index, ds, 1, 1), f"d_{kind}_day_after", res)


if __name__ == "__main__":
    form = sys.argv[1]
    s, R = series()
    res: dict = {}
    if form == "h":
        form_h(s, R, res)
    else:
        globals()[f"form_{form}"](s, res)
    (ROOT / f"research/is3/C1{form}__explore.json").write_text(json.dumps(res, indent=1, default=float))
