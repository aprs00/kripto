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


if __name__ == "__main__":
    {"explore": explore}[sys.argv[1]]()
