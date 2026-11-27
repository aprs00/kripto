"""InSilico pass 3, FST: Binance 8-h funding settlement, price drift into / out of 00/08/16 UTC vs the funding rate. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_fst a    # pre/post-settlement hour vs placebo, dose in |rate|, explore 2021-23 half 0 -> research/is3/fst_a.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data
from research.studies import is3_lib as L

THR = (0.0001, 0.0003, 0.0006, 0.0010)       # |previous print| buckets: 1 / 3 / 6 / 10 bp per 8 h (0.01 % = the base rate)


def settlements(panel):
    """Per coin, settlement hours S in {0, 8, 16}: rate = prints in bars S-1 or S (print-time convention puts most at S-1), previous = the one before."""
    f = panel["funding"]
    nz = f.where(f.notna() & (f != 0))
    idx = f.index
    rows = []
    hours = idx.hour
    off = ~np.isin(hours, [23, 0, 7, 8, 15, 16])
    four_h = nz[off].notna().groupby(idx[off].floor("1D")).any()    # a print at another hour that day = 4-h (or 1-h) interval: skip that coin-day
    for S in (0, 8, 16):
        pre_lab = (S - 1) % 24
        a = nz[hours == pre_lab]
        a.index = a.index + pd.Timedelta(hours=1)
        b = nz[hours == S]
        rate = a.reindex(b.index).fillna(0.0) + b.fillna(0.0)
        rate = rate.where(a.reindex(b.index).notna() | b.notna())
        rows.append(rate)
    rate = pd.concat(rows).sort_index()          # index = settlement time S
    prev = rate.shift(1)
    skip = four_h.reindex(rate.index.floor("1D")).fillna(False)
    skip.index = rate.index
    return rate, prev, skip


def events(panel, hour="pre", signal="prev", min_abs=THR[0], max_abs=None, placebo=0):
    """One event per coin-settlement with |signal| in [min_abs, max_abs): side = -sign(signal) (against the payer); gross = side * market-relative return of
    the hour ending at S ('pre', bar S-1) or starting at S ('post', bar S). placebo = shift the measured hour by that many hours (-4 = 4 h earlier)."""
    c = panel["close"]
    r = c / c.shift(1) - 1
    r = r.where(np.isfinite(r))
    mkt = r.mean(axis=1)
    rel = r.sub(mkt, axis=0)
    rate, prev, skip = settlements(panel)
    sig = prev if signal == "prev" else rate
    out = []
    lag = (-1 if hour == "pre" else 0) + placebo
    for coin in c.columns:
        s = sig[coin]
        ok = s.notna() & (s.abs() >= min_abs) & (~skip[coin].astype(bool) if coin in skip else True)
        if max_abs is not None:
            ok &= s.abs() < max_abs
        t = s.index[ok]
        bars = t + pd.Timedelta(hours=lag)
        v = rel[coin].reindex(bars).to_numpy()
        side = -np.sign(s[ok].to_numpy())
        m = np.isfinite(v)
        out.append(pd.DataFrame({"time": t[m] + pd.Timedelta(hours=lag), "coin": coin, "side": side[m].astype(int), "gross": side[m] * v[m]}))
    e = pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["time", "coin", "side", "gross"])
    return e.sort_values("time").reset_index(drop=True)


def sub(panel, lo, hi, half=0):
    cols = [c for c in panel["close"].columns if L.half(c) == half]
    return {k: v.loc[lo:hi, [c for c in cols if c in v.columns]] for k, v in panel.items()}


def run_a():
    p = data.load_panel("bn", "1h")
    p = {k: p[k] for k in ("close", "funding", "high", "low", "volume")}
    ex = sub(p, "2020-12-25", "2023-12-31 23:00")
    e0 = lambda q: events(q)
    print("null:", L.null_check(e0, ex, n=10))
    print("causal:", L.check_causal(e0, ex, "2022-06-01"))
    clip = lambda e: e[(e.time >= "2021-01-01") & (e.time < "2024-01-01")]
    out = {"cards": {}, "dose": {}}
    for hour in ("pre", "post"):
        e = clip(events(ex, hour))
        base = clip(events(ex, hour, placebo=-4))
        out["cards"][hour] = L.card(f"fst_{hour}", e, "explore", base=base, note="side = against the payer (prev print); base = same coin 4 h earlier")
        dose = {}
        for lo, hi in zip(THR, THR[1:] + (None,)):
            x = clip(events(ex, hour, min_abs=lo, max_abs=hi))
            xb = clip(events(ex, hour, min_abs=lo, max_abs=hi, placebo=-4))
            st = L.stats(x, xb, reps=500) if len(x) > 30 else {"n": len(x)}
            dose[f">={lo * 1e4:.0f}bp"] = {k: st.get(k) for k in ("n", "mean_bp", "base_bp", "vs_base_bp", "p_vs_base", "mde80_bp", "by_year", "by_side")}
            print(hour, lo, dose[f">={lo * 1e4:.0f}bp"], flush=True)
        out["dose"][hour] = dose
    # check: the realised (current) print instead of the previous one
    out["current_print_pre"] = {k: v for k, v in L.stats(clip(events(ex, "pre", signal="cur")), clip(events(ex, "pre", signal="cur", placebo=-4)), reps=500).items()
                                if k in ("n", "mean_bp", "base_bp", "vs_base_bp", "p_vs_base", "by_year")}
    print("current print:", out["current_print_pre"])
    json.dump(out, open("research/is3/fst_a.json", "w"), indent=1, default=float)


def xs_events(panel, k=2, q=0.2, placebo=0, post=False):
    """Cross-section at each settlement: coins in the top / bottom q of the previous print (among coins on the 8-h schedule that day); side = against the payer;
    gross = side * market-relative return over the k hours before S (or after, post=True); placebo shifts the window."""
    c = panel["close"]
    r = c / c.shift(1) - 1
    r = r.where(np.isfinite(r))
    rel = r.sub(r.mean(axis=1), axis=0)
    win = rel.rolling(k, min_periods=k).sum()        # bar L: sum of bars L-k+1..L
    rate, prev, skip = settlements(panel)
    sig = prev.where(~skip.astype(bool))
    rk = sig.rank(axis=1, pct=True)
    end = (k - 1 if post else -1) + placebo          # window ending at bar S-1 (pre) or S+k-1 (post)
    out = []
    for coin in c.columns:
        m = (rk[coin] >= 1 - q) | (rk[coin] <= q)
        t = sig.index[m.fillna(False).to_numpy()]
        v = win[coin].reindex(t + pd.Timedelta(hours=end)).to_numpy()
        side = -np.sign(sig[coin].reindex(t).to_numpy())
        ok = np.isfinite(v) & (side != 0)
        out.append(pd.DataFrame({"time": t[ok] + pd.Timedelta(hours=end), "coin": coin, "side": side[ok].astype(int), "gross": side[ok] * v[ok]}))
    return pd.concat(out, ignore_index=True).sort_values("time").reset_index(drop=True)


def run_b():
    p = data.load_panel("bn", "1h")
    p = {k: p[k] for k in ("close", "funding", "high", "low", "volume")}
    ex = sub(p, "2020-12-25", "2023-12-31 23:00")
    print("null:", L.null_check(lambda q: xs_events(q), ex, n=10))
    print("causal:", L.check_causal(lambda q: xs_events(q), ex, "2022-06-01"))
    clip = lambda e: e[(e.time >= "2021-01-01") & (e.time < "2024-01-01")]
    out = {}
    for lab, kw in (("pre2h", {}), ("post2h", {"post": True}), ("pre4h", {"k": 4}), ("pre2h_q10", {"q": 0.1})):
        e, b = clip(xs_events(ex, **kw)), clip(xs_events(ex, placebo=-4, **kw))
        out[lab] = L.card(f"fst_b_{lab}", e, "explore", base=b, note="xs extremes of the previous print, against the payer; base = window 4 h earlier")
    json.dump(out, open("research/is3/fst_b.json", "w"), indent=1, default=float)


def run_c():
    """Usable form: the BN daily books trade at ~04:14 UTC; a trade that ADDS to the paying side (by the previous print's sign) deferred to 08:01 skips the 08:00 print.
    Saving per year = sum |dw_payer-add| * |08:00 print| (scored on the real print), 2024-01..2026-10 (confirm years, 82 coins with hourly funding), per unit of book equity."""
    from kripto import strategies as S
    p1 = data.load_panel("bn", "1h")
    rate, prev, skip = settlements({"funding": p1["funding"]})
    r8, pv8 = rate[rate.index.hour == 8], prev[prev.index.hour == 8]
    r8.index, pv8.index = r8.index.floor("1D"), pv8.index.floor("1D")
    del p1
    pd_ = data.load_panel("bnall", "1d")
    books = {"flow@bn": ("flow", {"lookback": 3, "cap": 0.05}), "blend_nested@bn": ("blend", {"components": {"carry_trend": {}, "carry": {}, "xsmom": {}}})}
    out = {}
    for lab, (fn, prm) in books.items():
        w = S.REGISTRY[fn](pd_, **prm).ffill().fillna(0.0)
        cols = [c for c in w.columns if c in r8.columns]
        # weights decided on bar D (closes D+1 00:00) are traded on D+1 ~04:14: the trade happens on calendar day D+1, before that day's 08:00 print
        dw = w[cols].diff().shift(1).loc["2024-01-01":"2026-10-31"]
        wprev = w[cols].shift(2).loc[dw.index]
        rr, ps = r8.reindex(index=dw.index, columns=cols), pv8.reindex(index=dw.index, columns=cols)
        payer = np.sign(ps)                              # +1: longs pay (by the previous print)
        add = (np.sign(dw) == payer) & (np.abs(wprev + dw) > np.abs(wprev)) & (dw != 0)
        saved = (dw.abs() * (rr * payer)).where(add, 0.0)        # funding the moved trade would have paid at 08:00 (negative if the print flipped)
        yrs = len(dw) / 365
        out[lab] = {"saving_pct_yr": round(float(saved.sum().sum() / yrs) * 100, 3), "by_year": {int(y): round(float(x.sum().sum()) * 100, 3) for y, x in saved.groupby(saved.index.year)},
                    "moved_turnover_yr": round(float(dw.abs().where(add, 0).sum().sum() / yrs), 1), "total_turnover_yr": round(float(dw.abs().sum().sum() / yrs), 1),
                    "coverage_share_of_turnover": round(float(dw.abs().sum().sum() / w.diff().abs().loc["2024-01-01":"2026-10-31"].sum().sum()), 2)}
        print(lab, out[lab], flush=True)
    json.dump(out, open("research/is3/fst_c.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": run_a, "b": run_b, "c": run_c}[sys.argv[1]]()
