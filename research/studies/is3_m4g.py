"""M4 g: pitstop, not top, on 0.5% range bars (his bar type; tg:206, 216-222). notes.md section M4. BTC/ETH/SOL, M0 micro bars, author7 green/red (is3_m1.rbars).

    .venv/bin/python -m research.studies.is3_m4g explore
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from kripto import mbars
from research.studies import is3_lib as L
from research.studies.is3_m1 import BAD, COINS, fwd, rbars

W = 0.005


def coin(sym: str, lo: str, hi: str) -> dict:
    b = mbars.load(sym, lo, hi)
    r = rbars(b, W)
    t = pd.to_datetime(r["t1"], unit="ms", utc=True)
    s = pd.DataFrame({"c": r["c"], "h": r["h"], "l": r["l"]}, index=t)
    k = np.searchsorted(r["t1"], r["t1"] - 86_400_000)                 # first bar ending within the last 24 h
    c24 = r["c"][np.maximum(k - 1, 0)]
    mv = r["c"] / c24 - 1
    hi24 = s.h.rolling("24h").max().shift(1).to_numpy()
    return {"r": r, "bt": b["t1"], "bcl": b["c"], "mv": mv, "hi24": hi24, "mid": (c24 + r["c"]) / 2, "t": t,
            "bad": np.isin(t.floor("D"), pd.DatetimeIndex([pd.Timestamp(x, tz="UTC") for x in BAD.get(sym, {})]))}


def events(d: dict, name: str, kmin: float, kmax: float, hours: float, delay: int = 0) -> pd.DataFrame:
    r, mv, hi24, mid = d["r"], d["mv"], d["hi24"], d["mid"]
    red, green, lo, t1 = r["red"], r["green"], r["l"], r["t1"]
    rows, last = [], -1
    for i in np.flatnonzero(red & (r["h"] >= hi24) & (mv >= kmin) & (mv < kmax) & ~d["bad"]):
        if i <= last:
            continue
        j = i + 1
        while j < len(red) and t1[j] - t1[i] <= 12 * 3.6e6:
            if lo[j] < mid[i]:
                break
            if green[j]:
                e = min(j + delay, len(red) - 1)
                g = fwd(r, np.array([e]), d["bt"], d["bcl"], hours)[0]
                if np.isfinite(g):
                    rows.append({"time": d["t"][e], "coin": name, "side": 1, "gross": g, "m": int(min(mv[i], 0.3) * 50)})
                    last = j
                break
            j += 1
    return pd.DataFrame(rows, columns=["time", "coin", "side", "gross", "m"])


def pool(d: dict, name: str, kmin: float, hours: float) -> pd.DataFrame:
    r = d["r"]
    idx = np.flatnonzero(r["green"] & (d["mv"] >= kmin) & ~d["bad"])
    g = fwd(r, idx, d["bt"], d["bcl"], hours)
    return pd.DataFrame({"time": d["t"][idx], "coin": name, "side": 1, "gross": g, "m": (np.minimum(d["mv"][idx], 0.3) * 50).astype(int)}).dropna()


def explore() -> None:
    D = {}
    for s in COINS:
        D[s.replace("USDT", "")] = coin(s, "2020-12-30", "2024-01-01")
        print(s, "bars", len(D[s.replace("USDT", "")]["r"]["c"]), flush=True)
    a, b = (pd.Timestamp(x, tz="UTC") for x in L.SAMPLES["explore"])
    cut = lambda df: df[(df.time >= a) & (df.time < b)].reset_index(drop=True)
    for hours in (4, 12):
        for k in (0.03, 0.05, 0.08):
            e = cut(pd.concat([events(d, c, k, 9, hours) for c, d in D.items()], ignore_index=True))
            ctl = cut(pd.concat([events(d, c, -9, 0.0, hours) for c, d in D.items()], ignore_index=True))
            pl = cut(pd.concat([pool(d, c, k, hours) for c, d in D.items()], ignore_index=True))
            late = cut(pd.concat([events(d, c, k, 9, hours, delay=1) for c, d in D.items()], ignore_index=True))
            print(f"{hours}h move>={k:.0%}: pitstop n={len(e)} {e.gross.mean() * 1e4:+.1f}bp (one bar late {late.gross.mean() * 1e4:+.1f}) | same sequence after a 24-h fall "
                  f"n={len(ctl)} {ctl.gross.mean() * 1e4:+.1f} | green bars in strong moves n={len(pl)} {pl.gross.mean() * 1e4:+.1f}", flush=True)
            if len(e) >= 10:
                L.card(f"M4g_pitstop_rb_k{int(k * 100)}_{hours}h", e, "explore", L.matched(e, pl),
                       note=f"0.5% range bars, red bar at a 24-h high after a >= {k:.0%} 24-h rise -> first green bar within 12 h holding the midpoint; long {hours} h; vs green bars in strong moves")
    # null: colour labels shuffled within each day, main variant
    rng = np.random.default_rng(5)
    out = []
    for rep in range(20):
        es = []
        for c, d in D.items():
            r = dict(d["r"])
            day = d["t"].floor("D").asi8
            lab = np.where(r["green"], 1, np.where(r["red"], -1, 0))
            for dd in np.unique(day):
                ix = np.flatnonzero(day == dd)
                lab[ix] = rng.permutation(lab[ix])
            r["green"], r["red"] = lab == 1, lab == -1
            es.append(events({**d, "r": r}, c, 0.05, 9, 12))
        x = cut(pd.concat(es, ignore_index=True))
        pl = cut(pd.concat([pool({**d}, c, 0.05, 12) for c, d in D.items()], ignore_index=True))
        out.append(x.gross.mean() - pl.gross.mean())
        if rep == 2:
            print("null partial", np.round(np.array(out) * 1e4, 1), flush=True)
    print(f"null (labels shuffled within day, k 5%, 12 h): pitstop minus green-bar pool {np.mean(out) * 1e4:+.1f} bp (sd {np.std(out) * 1e4:.1f})")


if __name__ == "__main__":
    {"explore": explore}[sys.argv[1]]()
