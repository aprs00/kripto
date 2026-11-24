"""M1c follow-up: one-voiced range bars (|delta share| top decile) REVERSE over the next hour in explore (-22 bp signed, monotone).
Bug / artefact checks before believing it: sub-1-s (torn book) bars, entry 60 s / 5 min late, the bar close vs a 1-minute VWAP-ish
entry, outliers (by-side means), dose in |delta share| and bar width. Fade side = -sign(delta share).
Usage: python -m research.studies.is3_m1c explore|confirmT   (prints tables; cards: M1c2_*)
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from kripto import mbars
from research.studies import is3_lib as L
from research.studies.is3_m1 import BAD, COINS, rbars

WIDTHS = (0.0043, 0.008)


def feats(sym: str, lo: str, hi: str) -> pd.DataFrame:
    b = mbars.load(sym, lo, hi)
    bt, bcl = b["t1"], b["c"]
    out = []
    for w in WIDTHS:
        r = rbars(b, w)
        t = r["t1"]

        def px(dt_ms):
            k = np.searchsorted(bt, t + dt_ms, side="right") - 1      # last micro close at or before t + dt
            return bcl[np.clip(k, 0, len(bcl) - 1)]
        p0, p60, p300 = r["c"], px(60_000), px(300_000)
        p1h, p1h60, p1h300, p4h = px(3_600_000), px(3_660_000), px(3_900_000), px(14_400_000)
        ok = t + 14_400_000 <= bt[-1]
        vr = pd.Series(r["vol"]).rolling(50, min_periods=20).median().shift(1).to_numpy()
        d = pd.DataFrame({"time": pd.to_datetime(t, unit="ms", utc=True), "w": np.float32(w), "ds": r["ds"].astype(np.float32),
                          "dur": ((t - r["t0"]) / 1e3).astype(np.float32), "relvol": (r["vol"] / vr).astype(np.float32),
                          "barret": (r["c"] / r["o"] - 1).astype(np.float32),
                          "r0": (p1h / p0 - 1).astype(np.float32), "r60": (p1h60 / p60 - 1).astype(np.float32),
                          "r300": (p1h300 / p300 - 1).astype(np.float32), "r4h": (p4h / p300 - 1).astype(np.float32),
                          "jump60": (p60 / p0 - 1).astype(np.float32)})[ok]
        out.append(d)
    d = pd.concat(out, ignore_index=True)
    d["coin"] = sym.replace("USDT", "")
    bad = {pd.Timestamp(x, tz="UTC") for x in BAD.get(sym, {})}
    return d[~d["time"].dt.floor("D").isin(bad)]


def collect(lo: str, hi: str) -> pd.DataFrame:
    parts = []
    for sym in COINS:
        for y in range(int(lo[:4]), int(hi[:4])):
            try:
                parts.append(feats(sym, max(lo, f"{y}-01-01"), min(hi, f"{y + 1}-01-01")))
            except FileNotFoundError:
                continue
            print(sym, y, len(parts[-1]), flush=True)
    return pd.concat(parts, ignore_index=True)


def table(D: pd.DataFrame) -> None:
    D["fade"] = -np.sign(D.ds)
    for w, x in D.groupby("w"):
        q = pd.qcut(x.ds.abs(), 10, labels=False, duplicates="drop")
        for col in ("r0", "r60", "r300", "r4h"):
            m = (x[col] * x.fade).groupby(q).mean() * 1e4
            print(f"w={w:.4f} {col:5s} fade by |ds| decile: " + " ".join(f"{v:+.1f}" for v in m))
        top = x[q == q.max()]
        g = top.r300 * top.fade
        print(f"  top decile n={len(top)} |ds|>={top.ds.abs().min():.2f}: fade r300 mean {g.mean()*1e4:+.1f} median {g.median()*1e4:+.1f}; sub-1s share {(top.dur < 1).mean():.2f}"
              f" -> sub1s {(g[top.dur < 1]).mean()*1e4:+.1f} / >=1s {(g[top.dur >= 1]).mean()*1e4:+.1f}; jump in first 60 s (fade dir) {(top.jump60 * top.fade).mean()*1e4:+.1f}")
        print("  by side (fade r300): " + " ".join(f"{int(s)}: n {len(v)} mean {(v.r300 * v.fade).mean()*1e4:+.1f} med {(v.r300 * v.fade).median()*1e4:+.1f}" for s, v in top.groupby(top.fade)))
        print("  by year: " + " ".join(f"{yy}: {(v.r300 * v.fade).mean()*1e4:+.1f}" for yy, v in top.groupby(top.time.dt.year))
              + " | by coin: " + " ".join(f"{c}: {(v.r300 * v.fade).mean()*1e4:+.1f}" for c, v in top.groupby("coin")))
        # is it just the bar's own move reverting? same-size bars (|barret| tercile) with middling |ds|
        x2 = x.assign(q=q, bq=pd.qcut(x.barret.abs(), 3, labels=False, duplicates="drop"))
        print("  fade r300 by |bar return| tercile, top-|ds| vs mid-|ds| (deciles 4-6): " + " ".join(
            f"t{b}: {(v[v.q == q.max()].r300 * v[v.q == q.max()].fade).mean()*1e4:+.1f} vs {(v[v.q.between(4, 6)].r300 * v[v.q.between(4, 6)].fade).mean()*1e4:+.1f}"
            for b, v in x2.groupby("bq")))


def events(D: pd.DataFrame, w: float, col: str = "r300") -> tuple[pd.DataFrame, pd.DataFrame]:
    """card rows: top |ds| decile (threshold from the explore sample, fixed in prereg) vs mid deciles, matched coin x day x bar-move tercile."""
    x = D[D.w == np.float32(w)].copy()
    x["side"] = -np.sign(x.ds).astype(int)
    x["gross"] = x[col] * x.side
    x["m"] = x.time.dt.strftime("%Y%m%d") + "_" + pd.qcut(x.barret.abs(), 3, labels=False, duplicates="drop").astype(str) + "_" + x.side.astype(str)
    return x, x


if __name__ == "__main__":
    sample = sys.argv[1]
    lo, hi = L.SAMPLES[sample]
    D = collect(lo, hi)
    print(f"rows {len(D)}")
    table(D)
