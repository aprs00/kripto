"""InSilico second pass, the families the first pass never tested (research/insilico_pass2.md section 4). Descriptive.

  nice -n 19 .venv/bin/python -m research.studies.is2_misc [explore|confirm]      # explore: to 2023-12-31; confirm: 2024-01-01 on

V  volume at extremes (R8, R6), bnall daily, point-in-time top-100 coins: a new 20-day closing high on a volume spike should
   be a top and on low volume should keep going; a new 20-day low on thin volume "is not a bottom". Forward returns in excess
   of the equal-weight universe (market-neutral), one observation per coin-day, t clustered by day.
U  unit-price bias (R28): cheapest fifth of coins by price per unit (1000-prefixed contracts divided back) minus the dearest
   fifth and minus the universe, next 7 days, weekly non-overlapping; also only in "alt seasons" (universe beat BTC over 30 d).
W  weekend variants (R21), Binance hourly, all coins with data: W1 fade the Friday->Sunday move until Monday (first pass);
   W2 Friday's own move reverses by Saturday; W3 the Sunday move before the futures reopen reverses in the next 24 h.
E  empty moves (R9), 1-minute bars, 10 coins: a 4-sigma 5-minute move on LOW volume should be given back, on high volume not.
"""
from __future__ import annotations

import re
import sys

import numpy as np
import pandas as pd

from kripto import data
from kripto import strategies as st

CUT = "2024-01-01"


def sel(x, sample):
    return x[x.index < CUT] if sample == "explore" else x[x.index >= CUT]


def tday(x: pd.Series) -> float:
    d = x.dropna().groupby(level=0).mean()
    return float(d.mean() / d.std() * np.sqrt(len(d))) if len(d) > 5 and d.std() > 0 else float("nan")


def line(name, x):
    x = x.dropna()
    print(f"   {name:58s} n={len(x):6d} mean={x.mean() * 1e4:+7.1f} bp (t {tday(x):+.1f})")


def volume_extremes(sample):
    p = data.load_bn_all_panel()
    c, v = p["close"], p["volume"]
    uni = st.universe(p, top_n=100, min_days=60)
    lv = np.log(v.where(v > 0))
    vz = (lv - lv.rolling(30, min_periods=15).mean().shift(1)) / lv.rolling(30, min_periods=15).std().shift(1)
    hi = (c >= c.rolling(20).max()) & uni
    lo = (c <= c.rolling(20).min()) & uni
    print(f"V volume at 20-day extremes, bnall daily top-100, sample {sample}; forward return in excess of the universe mean")
    for h in (1, 3, 5, 10):
        f = np.log(c.shift(-h) / c)
        ex = f.sub(f.where(uni).mean(axis=1), axis=0)
        ex = sel(ex, sample)
        m = lambda mask: ex.where(sel(mask, sample)).stack()
        print(f"  +{h}d")
        line("new high, volume spike (z >= 2)", m(hi & (vz >= 2)))
        line("new high, ordinary volume (0 < z < 2)", m(hi & (vz > 0) & (vz < 2)))
        line("new high, low volume (z <= 0)", m(hi & (vz <= 0)))
        line("new low, volume spike (z >= 2)  [capitulation]", m(lo & (vz >= 2)))
        line("new low, low volume (z <= 0)    [thin low]", m(lo & (vz <= 0)))


def unit_price(sample):
    p = data.load_bn_all_panel()
    c = p["close"]
    uni = st.universe(p, top_n=100, min_days=60)
    mult = pd.Series({k: float(m.group(1)) if (m := re.match(r"^(1[0M]+)", k)) and False else 1.0 for k in c.columns})
    for k in c.columns:
        m = re.match(r"^(10+)[A-Z]", k)
        if m:
            mult[k] = float(m.group(1))
        elif k.startswith("1M"):
            mult[k] = 1e6
    unit = c.div(mult, axis=1).where(uni)
    rk = unit.rank(axis=1, pct=True)
    f7 = np.log(c.shift(-7) / c).where(uni)
    cheap, dear, allm = f7.where(rk <= 0.2).mean(axis=1), f7.where(rk >= 0.8).mean(axis=1), f7.mean(axis=1)
    r30 = np.log(c / c.shift(30))
    alt = (r30.where(uni).mean(axis=1) > r30["BTC"])
    wk = slice(None, None, 7)
    print(f"U unit-price bias, bnall daily top-100, sample {sample}; 7-day forward returns, weekly non-overlapping (t over weeks)")
    for name, x in (("cheapest fifth minus dearest fifth", cheap - dear), ("cheapest fifth minus universe", cheap - allm),
                    ("  same, alt season only (universe beat BTC over 30 d)", (cheap - allm).where(alt)),
                    ("  same, not alt season", (cheap - allm).where(~alt)),
                    ("dearest fifth minus universe", dear - allm)):
        y = sel(x, sample).iloc[wk].dropna()
        t = y.mean() / y.std() * np.sqrt(len(y)) if len(y) > 5 else float("nan")
        print(f"   {name:58s} weeks={len(y):4d} mean={y.mean() * 1e4:+7.1f} bp/week (t {t:+.1f})")


def weekend(sample):
    p = data.load_bn_panel("1h")
    c = p["close"]
    ny = (c.index + pd.Timedelta(hours=1)).tz_convert("America/New_York")
    wd, hr = np.asarray(ny.day_of_week), np.asarray(ny.hour)
    at = lambda d, h: np.flatnonzero((wd == d) & (hr == h))
    thu, fri, sat, sun12, sun, mon = at(3, 17), at(4, 17), at(5, 17), at(6, 12), at(6, 18), at(0, 17)
    C = c.to_numpy(dtype=float)
    rows = {"W1": [], "W2": [], "W3": []}
    for f in fri:
        nxt = lambda arr: arr[np.searchsorted(arr, f)] if np.searchsorted(arr, f) < len(arr) else None
        prev = thu[np.searchsorted(thu, f) - 1] if np.searchsorted(thu, f) > 0 else None
        s6, s12, s18, m = nxt(sat), nxt(sun12), nxt(sun), nxt(mon)
        if None in (s6, s12, s18, m, prev) or m - f > 100 or f - prev > 30:
            continue
        day = c.index[f].floor("D")
        g = np.log(C[s18] / C[f])
        rows["W1"].append(pd.Series(np.where(np.abs(g) >= 0.01, -np.sign(g) * np.log(C[m] / C[s18]), np.nan), c.columns, name=day))
        fr = np.log(C[f] / C[prev])
        rows["W2"].append(pd.Series(np.where(np.abs(fr) >= 0.02, -np.sign(fr) * np.log(C[s6] / C[f]), np.nan), c.columns, name=day))
        sp = np.log(C[s18] / C[s12])
        rows["W3"].append(pd.Series(np.where(np.abs(sp) >= 0.01, -np.sign(sp) * np.log(C[min(s18 + 24, len(C) - 1)] / C[s18]), np.nan), c.columns, name=day))
    print(f"W weekend variants, Binance hourly, {c.shape[1]} coins, sample {sample}; return of FADING the move (positive = it reversed)")
    for k, name in (("W1", "W1 fade Friday->Sunday move (>= 1%) until Monday close"), ("W2", "W2 fade Friday's own move (>= 2%) until Saturday"),
                    ("W3", "W3 fade the Sunday pre-open move (>= 1%) for 24 h")):
        d = sel(pd.DataFrame(rows[k]), sample)
        line(name + " | all coins", d.stack())
        line(name + " | BTC, ETH", d[["BTC", "ETH"]].stack())


def empty_moves(sample):
    P = data.load_bn_minute_panel(data.MINUTE_COINS)
    P = {k: sel(v, sample) for k, v in P.items()}
    out = {}
    for coin in P["close"].columns:
        c, v = P["close"][coin].astype("float64"), P["volume"][coin].astype("float64")
        lc = np.log(c)
        r5 = lc - lc.shift(5)
        sig = lc.diff().rolling(1440, min_periods=720).std().shift(5) * np.sqrt(5)
        vr = v.rolling(5).sum() / (v.rolling(1440, min_periods=720).mean().shift(5) * 5)
        ev = (r5.abs() >= 4 * sig)
        ev &= ~ev.shift(1, fill_value=False)                     # first bar of an episode only
        for h in (15, 60, 240):
            f = -(np.sign(r5)) * (lc.shift(-h) - lc)
            for nm, m in (("low volume (< 1.5x usual)", ev & (vr < 1.5)), ("medium (1.5-5x)", ev & (vr >= 1.5) & (vr < 5)),
                          ("high volume (>= 5x)", ev & (vr >= 5))):
                out.setdefault((h, nm), []).append(f[m])
    print(f"E empty moves, 1-minute bars, 10 coins, sample {sample}; return of FADING a 4-sigma 5-minute move (positive = it was given back)")
    for (h, nm), parts in out.items():
        x = pd.concat(parts)
        x.index = x.index.floor("D")
        line(f"+{h:3d} min, {nm}", x)


REP = "DOT BCH TRX ATOM ETC XLM FIL NEAR UNI AAVE MATIC ARB OP APT SUI INJ SAND MANA AXS FTM".split()


def volume_extremes_intraday(sample, rule):
    """The volume-at-extremes test (V) on shorter bars (owner 2026-11-15: "test shorter timeframes also, hours, minutes").
    rule = 1h (Binance hourly, 82 coins) or 15min / 5min (30 coins with 1-minute data). New 20-bar closing high / low;
    volume z-score of log volume against the previous week of bars. Forward SIMPLE returns (what a position earns; log
    returns flattered the daily short) minus the cross-sectional mean of all coins, mean and median, t clustered by day."""
    if rule == "1h":
        p = data.load_bn_panel("1h")
        c, v = p["close"], p["volume"]
    else:
        p = data.load_bn_minute_panel(data.MINUTE_COINS + REP, rule=rule)
        c, v = p["close"].astype("float64"), p["volume"].astype("float64")
    bpd = int(round(pd.Timedelta(days=1) / (c.index[1] - c.index[0])))
    wk = 7 * bpd
    lv = np.log(v.where(v > 0))
    vz = (lv - lv.rolling(wk, min_periods=wk // 2).mean().shift(1)) / lv.rolling(wk, min_periods=wk // 2).std().shift(1)
    hi, lo = c >= c.rolling(20).max(), c <= c.rolling(20).min()
    print(f"V intraday, {rule} bars, {c.shape[1]} coins, sample {sample}: new 20-bar extreme, forward SIMPLE return minus the cross-sectional mean")
    for h in (1, 4, 12, 48):
        f = c.shift(-h) / c - 1
        ex = sel(f.sub(f.mean(axis=1), axis=0), sample)
        print(f"  +{h} bars")
        for name, mask in (("new high, volume spike (z >= 2)", hi & (vz >= 2)), ("new high, low volume (z <= 0)", hi & (vz <= 0)),
                           ("new low, volume spike (z >= 2)", lo & (vz >= 2)), ("new low, low volume (z <= 0)", lo & (vz <= 0))):
            x = ex.where(sel(mask, sample)).stack()
            x.index = x.index.get_level_values(0).floor("D")
            print(f"   {name:36s} n={len(x):7d} mean={x.mean() * 1e4:+7.1f} bp median={x.median() * 1e4:+6.1f} (t {tday(x):+.1f})")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "VI":
        for rule in sys.argv[3:] or ["1h", "15min", "5min"]:
            volume_extremes_intraday(sys.argv[1], rule)
        sys.exit()
    s = sys.argv[1] if len(sys.argv) > 1 else "explore"
    which = sys.argv[2:] or ["V", "U", "W", "E"]
    for k, fn in (("V", volume_extremes), ("U", unit_price), ("W", weekend), ("E", empty_moves)):
        if k in which:
            fn(s)
