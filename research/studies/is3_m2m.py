"""M2 e/f on 1-min klines (COINS10, explore 2021-23). e: engine-lag proxy (trades/min burst still rising = continuation; burst unclogging = reversal).
f: exhaustion row (moves >= 2 sigma over 60 min; slope of trades/min and of mean trade size over the last 20 min).
Decision at minute t's close, entry at t+1's close (1 min late), outcomes in the move's direction (continuation; negative = reversal).
Baseline = cell means of all minutes of the same coin, year and move-size decile (aggregated, unbiased).

    nice -n 19 .venv/bin/python -m research.studies.is3_m2m explore
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
H = (15, 60, 240)


def coin_frame(coin: str, lo: str, hi: str) -> pd.DataFrame:
    m = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet", columns=["t", "c", "qv", "n"])
    m.index = pd.to_datetime(m.t, unit="ms", utc=True)
    m = m.loc[pd.Timestamp(lo, tz="UTC") - pd.Timedelta("2D"): pd.Timestamp(hi, tz="UTC") + pd.Timedelta("1D")]
    m = m[~m.index.duplicated()].asfreq("1min")
    c, n = m.c.ffill(), m.n.astype(float)
    norm = n.rolling(1440, min_periods=720).median().shift(1)
    x = n / norm.clip(lower=1)
    lr1 = np.log(c).diff()
    sig = lr1.rolling(1440, min_periods=720).std().shift(1)
    r15, r60 = c / c.shift(15) - 1, c / c.shift(60) - 1
    d = pd.DataFrame({"x": x, "xp": x.shift(1), "xmax15": x.rolling(15).max(), "r15": r15, "r60": r60,
                      "z15": r15 / (sig * np.sqrt(15)), "z60": r60 / (sig * np.sqrt(60))})
    # slopes over the last 20 min by closed form (faster than polyfit): cov(t, y) / var(t)
    tt = np.arange(20) - 9.5
    def slope(y: pd.Series) -> pd.Series:
        return y.rolling(20).apply(lambda a: float(tt @ a) / float(tt @ tt), raw=True, engine="cython")
    d["sn"] = slope(np.log(n.clip(lower=1)))
    d["ss"] = slope(np.log((m.qv / n.clip(lower=1)).clip(lower=1e-9)))
    entry = c.shift(-1)
    for h in H:
        d[f"f{h}"] = c.shift(-1 - h) / entry - 1
    d = d.loc[pd.Timestamp(lo, tz="UTC"): pd.Timestamp(hi, tz="UTC") - pd.Timedelta("1s")]
    d["coin"], d["year"] = coin, d.index.year
    return d.dropna(subset=["x", "z15", "z60", "f240"])


def aggs(d: pd.DataFrame, zcol: str, side: pd.Series) -> pd.DataFrame:
    dec = np.minimum((d[zcol].abs().rank(pct=True) * 10).astype(int), 9)
    g = pd.DataFrame({f"g{h}": side * d[f"f{h}"] for h in H}).assign(coin=d.coin, year=d.year, dec=dec)
    a = g.groupby(["coin", "year", "dec"])
    return a.sum().add_prefix("s_").join(a.size().rename("n")), dec


def ev(d, mask, side, dec, tag):
    e = pd.DataFrame({f"g{h}": (side * d[f"f{h}"])[mask] for h in H})
    e["time"], e["coin"], e["year"], e["dec"], e["side"], e["tag"] = d.index[mask], d.coin[mask], d.year[mask], dec[mask], side[mask].astype(int), tag
    return e


def run(lo: str, hi: str, coins=L.COINS10):
    EV, AG15, AG60 = [], [], []
    for coin in coins:
        d = coin_frame(coin, lo, hi)
        s15, s60 = np.sign(d.r15), np.sign(d.r60)
        a15, dec15 = aggs(d, "z15", s15)
        a60, dec60 = aggs(d, "z60", s60)
        AG15.append(a15); AG60.append(a60)
        for K in (5, 10, 20):
            clog = (d.x >= K) & (d.x > d.xp)
            unclog = (d.xmax15 >= K) & (d.x < 0.5 * d.xmax15)
            EV.append(ev(d, clog & (s15 != 0), s15, dec15, f"e_clog_{K}"))
            EV.append(ev(d, unclog & (s15 != 0), s15, dec15, f"e_unclog_{K}"))
        big = d.z60.abs() >= 2
        for nm, m in (("f_fallboth", (d.sn < 0) & (d.ss < 0)), ("f_risboth", (d.sn > 0) & (d.ss > 0))):
            EV.append(ev(d, big & m, s60, dec60, nm))
        # dose: slope-of-count tercile within big moves
        q = d.sn[big].rank(pct=True)
        for k, (a, b) in enumerate(((0, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 1.01))):
            mm = pd.Series(False, d.index); mm[q.index[(q >= a) & (q < b)]] = True
            EV.append(ev(d, mm, s60, dec60, f"f_sn_t{k}"))
        print(coin, len(d), flush=True)
    return pd.concat(EV, ignore_index=True), pd.concat(AG15).groupby(level=[0, 1, 2]).sum(), pd.concat(AG60).groupby(level=[0, 1, 2]).sum()


def base_for(e: pd.DataFrame, A: pd.DataFrame, h: int) -> pd.Series:
    mu = A[f"s_g{h}"] / A["n"]
    return pd.Series(mu.reindex(pd.MultiIndex.from_arrays([e.coin, e.year, e.dec])).to_numpy(), e.index)


def explore() -> None:
    E, A15, A60 = run("2021-01-01", "2024-01-01")
    E.to_parquet(ROOT / "data/is3/m2m_explore_events.parquet")
    print("\n tag | n | per horizon: mean bp vs matched (diff) | by year diff g60")
    for tag, e in E.groupby("tag", sort=False):
        A = A60 if tag.startswith("f") else A15
        s = f"{tag:14s} n={len(e):7d}"
        for h in H:
            b = base_for(e, A, h)
            s += f" | g{h} {e[f'g{h}'].mean() * 1e4:+6.1f} vs {b.mean() * 1e4:+6.1f} ({(e[f'g{h}'] - b).mean() * 1e4:+5.1f})"
        b = base_for(e, A, 60)
        s += " | yrs " + " ".join(f"{y}:{((g.g60 - b[g.index]).mean() * 1e4):+.1f}" for y, g in e.groupby("year"))
        print(s, flush=True)
    for tag in ("e_clog_10", "e_unclog_10", "f_fallboth"):
        e = E[E.tag == tag].copy()
        A = A60 if tag.startswith("f") else A15
        e["gross"] = e.g60 - base_for(e, A, 60)
        L.card(f"M2{tag}", e.dropna(subset=["gross"])[["time", "coin", "side", "gross"]], "explore",
               note="1-min klines COINS10, 1 min late, 60 min, in the move's direction; gross = minus same coin/year/move-size-decile mean")


if __name__ == "__main__":
    {"explore": explore}[sys.argv[1]]()
