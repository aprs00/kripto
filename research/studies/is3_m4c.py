"""M4 c (R2): in an uptrend, the pullback day with the most one-sided selling of the trend's life is the bottom. notes.md section M4.

Daily taker delta for the whole Binance universe (bnall 1d, clean, coin half 0 = explore; liquid: 30-d median volume >= $20M, known the day before).
Uptrend: close >= 1.2 x close 30 days earlier (and above its 50-d mean). Pullback day: day return < 0.
Event: the day's taker delta share (2*taker_buy/volume - 1) is the lowest of the last N days (N = 20 / 60 / 120 = dose), also the notional delta.
Long at the close, simple 3- and 5-day returns. Baseline: other pullback days in uptrends of the same coin, same day-return decile.

    .venv/bin/python -m research.studies.is3_m4c explore
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from kripto import data
from research.studies import is3_lib as L


def panel() -> dict:
    p = data.load_panel("bnall", "1d")
    cols = [c for c in p["close"].columns if L.half(c) == 0]
    out = {k: p[k][cols].astype(float) for k in ("close", "high", "low", "volume")}
    out["tb"] = p["taker_buy"][cols].astype(float)
    return out


def events(p: dict, N: int = 60, kind: str = "share", H: int = 3, sample: str = "explore", want: str = "event") -> pd.DataFrame:
    c, v, tb = p["close"], p["volume"], p["tb"]
    r = c / c.shift(1) - 1
    liq = v.rolling(30, min_periods=20).median().shift(1) >= 2e7
    up = (c >= 1.2 * c.shift(30)) & (c > c.rolling(50, min_periods=50).mean())
    pull = up & liq & (r < 0)
    d = (2 * tb - v) / v if kind == "share" else (2 * tb - v)
    lowest = d <= d.rolling(N, min_periods=N).min()
    sel = pull & (lowest if want == "event" else ~lowest)
    fwd = c.shift(-H) / c - 1
    a, b = (pd.Timestamp(x, tz="UTC") for x in L.SAMPLES[sample])
    dec = r.where(pull).stack()
    edges = np.nanquantile(dec, np.linspace(0, 1, 11)[1:-1]) if len(dec) else []
    ok = sel & fwd.notna() & (c.index >= a)[:, None] & (c.index < b)[:, None]
    s = ok.stack()
    s = s[s]
    rows = [{"time": t, "coin": k, "side": 1, "gross": float(fwd.at[t, k]), "m": int(np.searchsorted(edges, r.at[t, k]))} for t, k in s.index]
    return pd.DataFrame(rows, columns=["time", "coin", "side", "gross", "m"])


def explore() -> None:
    p = panel()
    for kind in ("share", "notional"):
        for N in (20, 60, 120):
            for H in (3, 5):
                e = events(p, N, kind, H)
                base = L.matched(e, events(p, N, kind, H, want="pool"))
                c = L.card(f"M4c_{kind}_N{N}_H{H}", e, "explore", base,
                           note=f"uptrend (c >= 1.2 x c[-30], > 50-d mean) pullback day whose taker delta {kind} is the lowest of {N} d, liquid, half 0; long {H} d")
    fn = lambda pp: events(pp, 60, "share", 3)
    L.null_check(fn, p, n=40)
    L.check_causal(fn, p, "2022-07-01", "6D")


def breadth_events(p: dict, q: float = 0.8, H: int = 1, sample: str = "explore", z: float = 1.0) -> pd.DataFrame:
    """d: market state. Breadth = share of liquid coins whose taker delta share is >= z sd above their own 30-d mean (one-voiced buying).
    Events = days with breadth >= its expanding q-quantile (known at the close); gross = equal-weight liquid basket, close -> close H days.
    m = decile of the basket's own day return (matching: 'buying breadth' is mostly 'up day')."""
    c, v, tb = p["close"], p["volume"], p["tb"]
    liq = v.rolling(30, min_periods=20).median().shift(1) >= 2e7
    d = (2 * tb - v) / v
    zz = (d - d.rolling(30, min_periods=20).mean().shift(1)) / d.rolling(30, min_periods=20).std().shift(1)
    br = ((zz >= z) & liq).sum(axis=1) / liq.sum(axis=1).replace(0, np.nan)
    r = (c / c.shift(1) - 1).where(liq)
    mkt = r.mean(axis=1)
    fwd = sum(r.shift(-k).mean(axis=1) for k in range(1, H + 1))          # sum of daily equal-weight returns (rebalanced basket)
    thr = br.expanding(min_periods=250).quantile(q).shift(1)
    a, b = (pd.Timestamp(x, tz="UTC") for x in L.SAMPLES[sample])
    edges = np.nanquantile(mkt, np.linspace(0, 1, 11)[1:-1])
    df = pd.DataFrame({"time": c.index, "coin": "MKT", "side": 1, "gross": fwd.to_numpy(), "m": np.searchsorted(edges, mkt.fillna(0).to_numpy()),
                       "br": br.to_numpy(), "ev": (br >= thr).to_numpy()})
    df = df[(df.time >= a) & (df.time < b) & df.gross.notna() & pd.Series(thr.notna().to_numpy(), index=df.index)]
    return df


def explore_d() -> None:
    p = panel()
    for z in (1.0, 2.0):
        for H in (1, 3):
            all_ = breadth_events(p, 0.8, H, z=z)
            qs = all_.br.quantile([0.2, 0.4, 0.6, 0.8]).to_numpy()
            tab = []
            for k, (lo, hi) in enumerate(zip([-1, *qs], [*qs, 2])):
                x = all_[(all_.br > lo) & (all_.br <= hi)]
                tab.append(f"Q{k + 1} {x.gross.mean() * 1e4:+.0f}bp")
            print(f"breadth z{z} H{H}: " + " | ".join(tab), flush=True)
            for side in (1, -1):
                e = all_[all_.ev].copy()
                rest = all_[~all_.ev].copy()
                e["side"], rest["side"] = side, side
                e["gross"], rest["gross"] = side * e.gross, side * rest.gross
                L.card(f"M4d_breadth_z{int(z)}_H{H}_{'long' if side > 0 else 'short'}", e[["time", "coin", "side", "gross", "m"]], "explore",
                       L.matched(e, rest), note=f"breadth of one-voiced buying (share of liquid half-0 coins with delta-share z >= {z}) >= expanding 80th pct; equal-weight basket {H} d; vs days with the same basket return decile")
    fn = lambda pp: (lambda x: x[x.ev][["time", "coin", "side", "gross"]])(breadth_events(pp, 0.8, 1))
    L.null_check(fn, p, n=40)
    L.check_causal(fn, p, "2022-07-01", "3D")


if __name__ == "__main__":
    {"explore": explore, "d": explore_d}[sys.argv[1]]()
