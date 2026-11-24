"""M4 a/e: capitulation scored by the MAGNITUDE of size-bucket selling, buckets adaptive to the coin's own trade sizes. notes.md section M4.

12 fixed notional bins (kripto/tsize.py) -> 7 groups whose cut points are the reference period's cumulative-volume septiles
(reference = previous day, variant previous 30 days; coarse because there are only 12 bins: said in the result).
Events: day return <= -3% (BTC ETH SOL, the coins with trade-size history), long at the day close, simple 1/3/5-day returns.
Baseline: other <= -3% days of the same coin and day-return decile (L.matched).

    .venv/bin/python -m research.studies.is3_m4 dist | explore
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from kripto import data, tsize
from research.studies import is3_lib as L

SYMS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT"}
NG = 7


def adaptive(sym: str, ref_days: int = 1) -> pd.DataFrame:
    """Per day: min group delta share, the largest two groups' delta share, all-negative flag (groups with >= 1% of volume)."""
    z = tsize.load(sym)
    B, S = z["buy"].astype(np.float64).sum(1), z["sell"].astype(np.float64).sum(1)       # (D, 12)
    V, Dl = B + S, B - S
    ref = pd.DataFrame(V).rolling(ref_days, min_periods=ref_days).sum().shift(1).to_numpy()  # previous ref_days only
    rows = []
    for i in range(len(V)):
        r = ref[i]
        if not np.isfinite(r).all() or r.sum() <= 0 or V[i].sum() <= 0:
            rows.append((np.nan, np.nan, np.nan, np.nan))
            continue
        mid = (np.cumsum(r) - r / 2) / r.sum()
        g = np.minimum((mid * NG).astype(int), NG - 1)
        gv, gd = np.bincount(g, V[i], NG), np.bincount(g, Dl[i], NG)
        live = gv >= 0.01 * V[i].sum()
        sh = np.where(live, gd / np.where(gv > 0, gv, 1), np.nan)
        top = np.flatnonzero(live)[-2:]
        rows.append((np.nanmin(sh), gd[top].sum() / gv[top].sum(), float(np.all(sh[live] < 0)), float(Dl[i].sum() / V[i].sum())))
    return pd.DataFrame(rows, index=pd.DatetimeIndex(z["days"]).tz_localize("UTC"), columns=["fmin", "flarge", "allneg", "ftot"])


def panel(ref_days: int = 1) -> dict:
    p = data.load_panel("bnall", "1d")
    cols = list(SYMS)
    out = {k: p[k][cols].astype(float) for k in ("close", "high", "low", "volume")}
    for f in ("fmin", "flarge", "allneg", "ftot"):
        out[f] = pd.DataFrame({c: adaptive(s, ref_days)[f] for c, s in SYMS.items()}).reindex(out["close"].index)
    return out


def events(p: dict, feat: str = "fmin", lo: float = -np.inf, hi: float = np.inf, H: int = 3, sample: str = "explore") -> pd.DataFrame:
    """All <= -3% days with lo < feature <= hi (feature known at the day's close); gross = long close -> close H days later."""
    c = p["close"]
    r = c / c.shift(1) - 1
    fwd = c.shift(-H) / c - 1
    a, b = (pd.Timestamp(x, tz="UTC") for x in L.SAMPLES[sample])
    rows = []
    for coin in c.columns:
        dec = pd.qcut(r[coin].where(r[coin] <= -0.03), 10, labels=False, duplicates="drop")
        f = p[feat][coin]
        ok = (r[coin] <= -0.03) & (f > lo) & (f <= hi) & fwd[coin].notna() & (c.index >= a) & (c.index < b)
        for t in c.index[ok.to_numpy()]:
            rows.append({"time": t, "coin": coin, "side": 1, "gross": float(fwd.at[t, coin]), "m": int(dec[t]) if pd.notna(dec[t]) else -1,
                         "ret": float(r.at[t, coin]), "f": float(f[t])})
    return pd.DataFrame(rows, columns=["time", "coin", "side", "gross", "m", "ret", "f"])


def dist() -> None:
    for ref in (1, 30):
        p = panel(ref)
        e = events(p, "fmin")
        print(f"ref {ref} d: down days {len(e)}; fmin quantiles", np.round(np.nanquantile(e.f, [.1, .2, .4, .6, .8, .9]), 3))
        e2 = events(p, "flarge")
        print(f"ref {ref} d: flarge quantiles", np.round(np.nanquantile(e2.f, [.1, .2, .4, .6, .8, .9]), 3),
              "allneg share", round(float(p['allneg'].where(p['close'].pct_change() <= -0.03).stack().mean()), 3))


def explore() -> None:
    for ref in (1, 30):
        p = panel(ref)
        for feat in ("fmin", "flarge"):
            pool = events(p, feat)
            qs = np.nanquantile(pool.f, [0.2, 0.4, 0.6, 0.8])
            for H in (1, 3, 5):
                pool = events(p, feat, H=H)
                tab = []
                for k, (lo, hi) in enumerate(zip([-np.inf, *qs], [*qs, np.inf])):
                    x = pool[(pool.f > lo) & (pool.f <= hi)]
                    tab.append(f"Q{k + 1}({hi:+.2f}) {x.gross.mean() * 1e4:+.0f}bp n{len(x)}")
                print(f"ref{ref} {feat} H{H}: " + " | ".join(tab), flush=True)
            # card: most negative quintile vs matched other down days, H = 3 (his 2-5 d window)
            fn = lambda pp, f=feat, q=qs[0]: events(pp, f, hi=q, H=3)
            e = fn(p)
            rest = events(p, feat, lo=qs[0], H=3)
            base = L.matched(e, rest)
            name = f"M4a_ref{ref}_{feat}_q1"
            L.card(name, e[["time", "coin", "side", "gross", "m"]], "explore", base,
                   note=f"most negative quintile of {feat} (<= {qs[0]:+.3f}, thresholds from the explore pool, not outcomes) on <= -3% days, long 3 d; ref {ref} d buckets")
            if ref == 1 and feat == "fmin":
                L.null_check(fn, p, n=100)
                L.check_causal(fn, p, "2022-07-01", "6D")


if __name__ == "__main__":
    {"dist": dist, "explore": explore}[sys.argv[1]]()
