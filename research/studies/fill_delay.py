"""Assumption row 20 (2026-11-22 retro): drift between the decision bar's close (what the backtest trades at) and the live fill's mid.

Signed so that a positive number is a COST: buys above the close, sells below it. Not part of fills.slip_bps (which is px vs mid at the fill).
Only fills 0-60 min after a 4h bar close count. Clustered by fill time (one cluster per run and venue).
usage: python -m research.studies.fill_delay
"""
import sqlite3

import numpy as np
import pandas as pd

from kripto import data, paper as P, venue_bn


def closes(venue, coin):
    if venue == "bn":
        f = venue_bn.LIVE_DIR / f"{coin}.parquet"
        t, c = "t", "c"
    else:
        f = data.DATA / "hl" / "candles_4h" / f"{coin}.parquet"
        t, c = "t", "c"
    if not f.exists():
        return None
    d = pd.read_parquet(f)
    return pd.Series(d[c].astype(float).to_numpy(), pd.to_datetime(d[t], unit="ms", utc=True) + pd.Timedelta(hours=4))


def main():
    c = sqlite3.connect(f"file:{P.DB}?mode=ro", uri=True)
    f = pd.read_sql("select * from fills where book like 'shadow:%' and book not like '%@pair'", c)
    f["ts"] = pd.to_datetime(f["ts"], utc=True, format="ISO8601")
    f["venue"] = np.where(f["book"].str.endswith("@bn"), "bn", "hl")
    f["bar"] = f["ts"].dt.floor("4h")
    f["delay_min"] = (f["ts"] - f["bar"]).dt.total_seconds() / 60
    f = f[f["delay_min"] <= 60]
    cache = {}
    ref = []
    for v, coin, b in zip(f["venue"], f["coin"], f["bar"]):
        if (v, coin) not in cache:
            cache[v, coin] = closes(v, coin)
        s = cache[v, coin]
        ref.append(s.get(b, np.nan) if s is not None else np.nan)
    f["ref"] = ref
    f = f.dropna(subset=["ref"])
    f["drift"] = np.sign(f["size"]) * (f["mid"] / f["ref"] - 1) * 1e4
    f["ntl"] = (f["size"] * f["px"]).abs()
    for v, g in f.groupby("venue"):
        runs = g.groupby("bar").apply(lambda x: np.average(x["drift"], weights=x["ntl"]), include_groups=False)
        print(f"{v}: fills {len(g)} runs {len(runs)} median delay {g['delay_min'].median():.0f} min | drift notional-weighted "
              f"{np.average(g['drift'], weights=g['ntl']):+.1f} bp, mean {g['drift'].mean():+.1f}, median {g['drift'].median():+.1f}, "
              f"run mean {runs.mean():+.1f} (t {runs.mean() / runs.std() * np.sqrt(len(runs)):.2f}); mean |drift| {g['drift'].abs().mean():.0f}; slip {np.average(g['slip_bps'], weights=g['ntl']):.1f}")
        for lab, h in (("without each book's first bar", g[g["bar"] > g.groupby("book")["bar"].transform("min")]),
                       ("BTC leg only", g[g["coin"] == "BTC"]), ("alts only", g[g["coin"] != "BTC"])):
            # one row per (bar, coin, direction): books trading the same coin share one observation
            u = h.groupby(["bar", "coin", h["size"] > 0]).agg(drift=("drift", "first"), ntl=("ntl", "sum")).reset_index()
            rr = u.groupby("bar").apply(lambda x: pd.Series({"d": np.average(x["drift"], weights=x["ntl"]), "ntl": x["ntl"].sum()}), include_groups=False)
            tot = (rr["d"] * rr["ntl"]).sum()
            top2 = (rr["d"] * rr["ntl"]).abs().sort_values().index[-2:]
            rest = rr.drop(top2)
            print(f"   {lab}: obs {len(u)} runs {len(rr)} weighted {tot / rr['ntl'].sum():+.1f} run mean {rr['d'].mean():+.1f} "
                  f"(t {rr['d'].mean() / rr['d'].std() * np.sqrt(len(rr)):.2f}) median run {rr['d'].median():+.1f}; without the 2 largest runs weighted "
                  f"{(rest['d'] * rest['ntl']).sum() / rest['ntl'].sum():+.1f}")
        print(g.groupby("book").apply(lambda x: pd.Series({"n": len(x), "drift_w": np.average(x["drift"], weights=x["ntl"]),
                                                              "median": x["drift"].median()}), include_groups=False).round(1).to_string())


if __name__ == "__main__":
    main()
