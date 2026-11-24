"""M4 f: pitstop, not top (tg:206, 216-222). notes.md section M4 (f think-through). BTC/ETH/SOL 1-h bars from 5-min trade-size data.

    .venv/bin/python -m research.studies.is3_m4f explore
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from kripto import tsize
from research.studies import is3_lib as L

SYMS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT"}
NG = 7


def hourly(sym: str) -> pd.DataFrame:
    z = tsize.load(sym)
    B, S = z["buy"].astype(np.float64), z["sell"].astype(np.float64)
    D = len(B)
    Vh, Dh = (B + S).reshape(D, 24, 12, 12).sum(2), (B - S).reshape(D, 24, 12, 12).sum(2)
    Vd = (B + S).sum(1)
    sign = np.zeros((D, 24))
    for i in range(1, D):
        r = Vd[i - 1]
        if r.sum() <= 0:
            continue
        g = np.minimum((((np.cumsum(r) - r / 2) / r.sum()) * NG).astype(int), NG - 1)
        for j in range(24):
            v, d = Vh[i, j], Dh[i, j]
            if v.sum() <= 0:
                continue
            gv, gd = np.bincount(g, v, NG), np.bincount(g, d, NG)
            live = gv >= 0.01 * v.sum()
            if live.sum() < 2:
                continue
            sign[i, j] = 1 if (gd[live] > 0).all() else (-1 if (gd[live] < 0).all() else 0)
    idx = pd.DatetimeIndex(z["days"]).tz_localize("UTC").repeat(24) + pd.to_timedelta(np.tile(np.arange(24), D), unit="h")
    k = pq.read_table(f"data/bn/klines_1m/{sym}.parquet", columns=["t", "h", "l", "c"]).to_pandas()
    k.index = pd.to_datetime(k.t, unit="ms", utc=True)
    h = k.resample("1h").agg({"h": "max", "l": "min", "c": "last"})
    h["ts"] = pd.Series(sign.ravel(), idx).reindex(h.index)
    lr = np.log(h.c).diff()
    h["z24"] = np.log(h.c / h.c.shift(24)) / (lr.rolling(720, min_periods=500).std().shift(1) * np.sqrt(24))
    h["hi24"] = h.h.rolling(24).max().shift(1)
    h["mid"] = (h.c.shift(24) + h.c) / 2
    return h


def seq_events(h: pd.DataFrame, coin: str, zlo: float, zhi: float, H: int, delay: int = 0) -> list[dict]:
    """Pitstop bar (all-negative, high >= prior 24-h high, z24 in [zlo, zhi)) -> first all-positive bar within 12 h whose rotation held
    above the move's midpoint -> long at that bar's close (+delay bars), simple return H bars later."""
    ts, hi, lo, c, z, hi24, mid = (h[x].to_numpy() for x in ("ts", "h", "l", "c", "z24", "hi24", "mid"))
    out, last = [], -1
    n = len(c)
    for t in np.flatnonzero((ts == -1) & (hi >= hi24) & (z >= zlo) & (z < zhi)):
        if t <= last:
            continue
        for u in range(t + 1, min(t + 13, n)):
            if lo[t:u + 1].min() < mid[t]:
                break
            if ts[u] == 1:
                e = u + delay
                if e + H < n and np.isfinite(c[e + H]):
                    out.append({"time": h.index[e], "coin": coin, "side": 1, "gross": c[e + H] / c[e] - 1, "m": int(np.clip(z[t], -5, 5) * 2)})
                    last = e + H
                break
    return out


def explore() -> None:
    hs = {c: hourly(s) for c, s in SYMS.items()}
    a, b = (pd.Timestamp(x, tz="UTC") for x in L.SAMPLES["explore"])
    cut = lambda df: df[(df.time >= a) & (df.time < b)].reset_index(drop=True)
    for H in (4, 12, 24):
        for zlo in (1.5, 2.0, 3.0):
            e = cut(pd.DataFrame(sum((seq_events(h, c, zlo, 99, H) for c, h in hs.items()), [])))
            ctl = cut(pd.DataFrame(sum((seq_events(h, c, -99, 1.0, H) for c, h in hs.items()), [])))
            # baseline 2: all-positive bars in a strong move (same z band), no pitstop sequence; matched on coin + z bin
            pool = []
            for c, h in hs.items():
                ok = (h.ts == 1) & (h.z24 >= zlo) & h.c.shift(-H).notna()
                x = h[ok.to_numpy()]
                pool.append(pd.DataFrame({"time": x.index, "coin": c, "side": 1, "gross": (h.c.shift(-H) / h.c - 1)[ok.to_numpy()].to_numpy(),
                                          "m": (np.clip(x.z24, -5, 5) * 2).astype(int).to_numpy()}))
            pool = cut(pd.concat(pool, ignore_index=True))
            if len(e) < 5:
                print(f"H{H} z>={zlo}: n={len(e)}")
                continue
            print(f"H{H} z>={zlo}: pitstop n={len(e)} {e.gross.mean() * 1e4:+.0f}bp | same sequence outside strong moves n={len(ctl)} {ctl.gross.mean() * 1e4:+.0f}bp | "
                  f"green bars in strong moves n={len(pool)} {pool.gross.mean() * 1e4:+.0f}bp", flush=True)
            if H == 12:
                L.card(f"M4f_pitstop_z{zlo}_H12", e, "explore", L.matched(e, pool),
                       note=f"pitstop (all-neg bar at a 24-h high, z24 >= {zlo}) -> first all-green bar within 12 h, rotation held above the move's midpoint; long 12 h; vs green bars in strong moves (coin, z bin)")
    # delay stress on the main variant
    e = cut(pd.DataFrame(sum((seq_events(h, c, 2.0, 99, 12, delay=1) for c, h in hs.items()), [])))
    print("z>=2 H12 one bar late:", len(e), f"{e.gross.mean() * 1e4:+.0f}bp")


if __name__ == "__main__":
    {"explore": explore}[sys.argv[1]]()
