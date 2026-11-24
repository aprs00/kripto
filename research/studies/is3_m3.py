"""M3 e: the mousetrap as narrated (tg:169-171; notes.md section M3). BTC ETH SOL micro bars, range bars 0.2% (>= 1-s bars judged separately).

Per UTC day, level Lv = previous day's low (form a adds the 7-day low). Episode = consecutive bars whose low <= Lv * (1 + 10 bp).
First test = the first episode of the day; a later episode counts as the SECOND test only if price closed >= 30 bp above Lv in between.
Trap = the second test undercuts Lv (low < Lv) and the episode ends with a close back above Lv. Entry = the first bar after the undercut
whose taker delta > 0 and close > Lv ("buyers take over"), bought 5 min after that bar's close; exits 60 / 240 min later, and a stop variant
(exit at the trap low if touched before 240 min, 5 bp worse). Dose = volume of the second test / volume of the first.
Baselines: (1) the same trap with ratio < 1 (no volume surge), (2) every bar of the same coin-day that closes above Lv within 20 bp of it
(placebo 'near the level' entry, same exits).

    nice -n 19 .venv/bin/python -m research.studies.is3_m3 explore
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from kripto import mbars
from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
BAD = json.loads((L.OUT / "mbars_bad_days.json").read_text())
W = 0.002


def load(sym: str, lo: str, hi: str) -> dict:
    fs = [f for f in sorted((mbars.DIR / sym).glob("????-??-??.npz")) if lo <= f.stem < hi]
    if not fs:
        raise FileNotFoundError(sym)
    parts = []
    for f in fs:
        z = np.load(f)
        b, s = z["buy"].sum(1, dtype=np.float64), z["sell"].sum(1, dtype=np.float64)
        parts.append({k: z[k] for k in ("t0", "t1", "o", "h", "l", "c")} | {"v": b + s, "d": b - s})
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


def rbars(b: dict, w: float) -> dict:
    h, l = b["h"], b["l"]
    ends, H, Lo = [], -np.inf, np.inf
    for i in range(len(h)):
        H, Lo = max(H, h[i]), min(Lo, l[i])
        if H / Lo - 1 >= w:
            ends.append(i)
            H, Lo = -np.inf, np.inf
    e = np.asarray(ends, dtype=np.int64)
    st = np.concatenate([[0], e[:-1] + 1])
    return {"t0": b["t0"][st], "t1": b["t1"][e], "o": b["o"][st], "c": b["c"][e], "h": np.maximum.reduceat(h, st),
            "l": np.minimum.reduceat(l, st), "v": np.add.reduceat(b["v"], st), "d": np.add.reduceat(b["d"], st)}


def exits(bt, bcl, bl, t_entry, stop=None):
    """entry price = micro close at t_entry; returns (g60, g240, g240_stop)."""
    k0 = np.minimum(np.searchsorted(bt, t_entry), len(bt) - 1)
    px = bcl[k0]
    out = []
    for mins in (60, 240):
        k = np.searchsorted(bt, t_entry + mins * 60_000)
        out.append(bcl[k] / px - 1 if k < len(bt) else np.nan)
    k = np.searchsorted(bt, t_entry + 240 * 60_000)
    if stop is not None and k < len(bt):
        hit = np.flatnonzero(bl[k0 + 1:k + 1] < stop)
        out.append((stop * (1 - 5e-4)) / px - 1 if len(hit) else out[1])
    else:
        out.append(out[1])
    return out


def coin_events(sym: str, lo: str, hi: str) -> pd.DataFrame:
    b = load(sym, lo, hi)
    bt, bcl, bl = b["t1"], b["c"], b["l"]
    r = rbars(b, W)
    day = r["t1"] // 86_400_000
    days = np.unique(day)
    lows = {d: r["l"][day == d].min() for d in days}
    rows = []
    for dd in days[1:]:
        if dd - 1 not in lows:
            continue
        Lv = lows[dd - 1]
        ix = np.flatnonzero(day == dd)
        near = r["l"][ix] <= Lv * 1.001
        if not near.any():
            continue
        # episodes = runs of consecutive 'near' bars
        eps, cur = [], []
        for j, f in zip(ix, near):
            if f:
                cur.append(j)
            elif cur:
                eps.append(cur); cur = []
        if cur:
            eps.append(cur)
        first = eps[0]
        v1 = r["v"][first].sum()
        for ep in eps[1:]:
            between = np.arange(first[-1] + 1, ep[0])
            if not len(between) or r["c"][between].max() < Lv * 1.003:
                continue
            under = [j for j in ep if r["l"][j] < Lv]
            if not under:
                continue
            j_u = under[0]
            # first later bar (within the episode or right after it) with positive delta and close above the level
            cand = [j for j in range(j_u, min(ep[-1] + 4, len(r["c"]))) if r["d"][j] > 0 and r["c"][j] > Lv]
            if not cand:
                break
            je = cand[0]
            trap_low = r["l"][ep[0]:je + 1].min()
            t_e = int(r["t1"][je]) + 5 * 60_000
            g60, g240, g240s = exits(bt, bcl, bl, t_e, stop=trap_low)
            v2 = r["v"][ep[0]:je + 1].sum()
            rows.append({"time": pd.to_datetime(t_e, unit="ms", utc=True), "ratio": v2 / max(v1, 1.0), "g60": g60, "g240": g240, "g240s": g240s,
                         "slow": (r["t1"][je] - r["t0"][je]) >= 1000, "depth": Lv / trap_low - 1, "kind": "trap"})
            break                                                  # one trap per day and level
        # placebo: bars of the same day closing within 20 bp above the level, entered the same way (5 min late)
        pl = ix[(r["c"][ix] > Lv) & (r["c"][ix] < Lv * 1.002)]
        for j in pl[:: max(1, len(pl) // 10)]:
            t_e = int(r["t1"][j]) + 5 * 60_000
            g60, g240, _ = exits(bt, bcl, bl, t_e)
            rows.append({"time": pd.to_datetime(t_e, unit="ms", utc=True), "ratio": np.nan, "g60": g60, "g240": g240, "g240s": g240,
                         "slow": True, "depth": 0.0, "kind": "placebo"})
    d = pd.DataFrame(rows)
    if len(d):
        d["coin"] = sym.replace("USDT", "")
        bad = {pd.Timestamp(x, tz="UTC") for x in BAD.get(sym, {})}
        d = d[~d.time.dt.floor("D").isin(bad)].dropna(subset=["g240"])
    return d


def collect(lo: str, hi: str) -> pd.DataFrame:
    out = []
    for sym in COINS:
        for y in range(int(lo[:4]), int(hi[:4])):
            for q in range(4):
                a = f"{y}-{3 * q + 1:02d}-01"
                z = f"{y}-{3 * q + 4:02d}-01" if q < 3 else f"{y + 1}-01-01"
                try:
                    # one extra day before, so the first day's level exists
                    d = coin_events(sym, str((pd.Timestamp(max(lo, a)) - pd.Timedelta("1D")).date()), min(hi, z))
                except FileNotFoundError:
                    continue
                out.append(d)
        print(sym, flush=True)
    return pd.concat(out, ignore_index=True)


def explore() -> None:
    D = collect("2021-01-01", "2024-01-01")
    D = D[(D.time >= pd.Timestamp("2021-01-01", tz="UTC")) & (D.time < pd.Timestamp("2024-01-01", tz="UTC"))]
    D.to_parquet(ROOT / "data/is3/m3e_explore.parquet")
    T, P = D[D.kind == "trap"], D[D.kind == "placebo"]
    bp = lambda x: round(float(np.nanmean(x)) * 1e4, 1)
    print(f"traps {len(T)} (slow {T.slow.mean():.0%}), placebo {len(P)}; placebo g60 {bp(P.g60)} g240 {bp(P.g240)}")
    for lab, m in (("ratio<1", T.ratio < 1), ("1-2", (T.ratio >= 1) & (T.ratio < 2)), ("2-5", (T.ratio >= 2) & (T.ratio < 5)), (">=5", T.ratio >= 5), ("all", T.ratio > -1)):
        x = T[m]
        print(f"  {lab:8s} n={len(x):5d} g60 {bp(x.g60):+6.1f} g240 {bp(x.g240):+6.1f} stop {bp(x.g240s):+6.1f} | vs placebo g240 {bp(x.g240) - bp(P.g240):+.1f}"
              f" | yrs " + " ".join(f"{y}:{bp(g.g240):+.0f}" for y, g in x.groupby(x.time.dt.year)) + " | coins " + " ".join(f"{c}:{bp(g.g240):+.0f}" for c, g in x.groupby('coin')))
    e = T[T.ratio >= 2].assign(side=1)
    pb = P.assign(side=1)
    L.card("M3e_trap_ratio2_g240", e.assign(gross=e.g240)[["time", "coin", "side", "gross"]], "explore",
           base=pb.assign(gross=pb.g240)[["time", "coin", "side", "gross"]], note="prev-day-low mousetrap, 2nd/1st test volume >= 2, long 5 min after the buyers' bar, 240 min; base = near-level placebo entries")
    L.card("M3e_trap_ratio2_stop", e.assign(gross=e.g240s)[["time", "coin", "side", "gross"]], "explore",
           base=pb.assign(gross=pb.g240)[["time", "coin", "side", "gross"]], note="same with a stop at the trap low (5 bp slip)")


if __name__ == "__main__":
    {"explore": explore, "b": lambda: None}[sys.argv[1]]()


# ------------------------------------------------------------------ form b: absorption bars
def runlen(x):
    out, k = np.zeros(len(x), dtype=np.int32), 0
    for i, v in enumerate(x):
        k = k + 1 if v else 0
        out[i] = k
    return out


def b_coin(sym: str, lo: str, hi: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Absorption = a bar whose taker delta share points AGAINST the bar's direction (dirn * ds <= -thr). Side = the bar's direction
    (the passive absorber won it). Entry 5 min after the close, 60 / 240 min. Base: aggregated cells (coin, w, day, side, prior run, slow)."""
    b = load(sym, lo, hi)
    bt, bcl = b["t1"], b["c"]
    E, A = [], []
    for w in (0.002, 0.0043):
        r = rbars(b, w)
        dirn = np.sign(r["c"] - r["o"])
        ds = r["d"] / np.maximum(r["v"], 1e-9)
        x = -dirn * ds                                           # > 0: takers pushed against where the bar went
        up = dirn > 0
        pl = np.minimum(np.where(up, runlen(up), runlen(~up)), 4)
        t_e = r["t1"] + 5 * 60_000
        k0 = np.minimum(np.searchsorted(bt, t_e), len(bt) - 1)
        g = {}
        for mins in (60, 240):
            k = np.searchsorted(bt, t_e + mins * 60_000)
            gg = np.full(len(t_e), np.nan)
            ok = k < len(bt)
            gg[ok] = dirn[ok] * (bcl[k[ok]] / bcl[k0[ok]] - 1)
            g[mins] = gg
        d = pd.DataFrame({"time": pd.to_datetime(t_e, unit="ms", utc=True), "w": w, "x": x, "side": dirn.astype(int), "g60": g[60], "g240": g[240],
                          "slow": (r["t1"] - r["t0"]) >= 1000, "m": (r["t1"] // 86_400_000) * 100 + (dirn + 1) * 10 + pl})
        d = d[(d.side != 0) & d.g240.notna()]
        A.append(d[d.x < 0].groupby(["w", "m", "slow"])[["g60", "g240"]].agg(["sum", "count"]))
        E.append(d[d.x >= 0.2])
    E, A = pd.concat(E, ignore_index=True), pd.concat(A)
    E["coin"] = sym.replace("USDT", "")
    A.columns = ["s60", "n60", "s240", "n240"]
    A = A.reset_index().assign(coin=sym.replace("USDT", ""))
    bad = {pd.Timestamp(x, tz="UTC") for x in BAD.get(sym, {})}
    return E[~E.time.dt.floor("D").isin(bad)], A


def form_b() -> None:
    EE, AA = [], []
    for sym in COINS:
        for y in (2021, 2022, 2023):
            for q in range(4):
                a = f"{y}-{3 * q + 1:02d}-01"
                z = f"{y}-{3 * q + 4:02d}-01" if q < 3 else f"{y + 1}-01-01"
                e, ag = b_coin(sym, a, z)
                EE.append(e); AA.append(ag)
        print(sym, flush=True)
    E, A = pd.concat(EE, ignore_index=True), pd.concat(AA, ignore_index=True)
    A = A.groupby(["coin", "w", "m", "slow"]).sum()
    for h in (60, 240):
        E = E.join((A[f"s{h}"] / A[f"n{h}"]).rename(f"b{h}"), on=["coin", "w", "m", "slow"])
    E = E.dropna(subset=["b240"])
    bp = lambda s: round(float(s.mean()) * 1e4, 1)
    print("\nabsorption bars (takers against the bar), slow >= 1 s only; event - within-day matched (bars with takers WITH the bar)")
    for w, X in E[E.slow].groupby("w"):
        for lo_, hi_ in ((0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)):
            x = X[(X.x >= lo_) & (X.x < hi_)]
            print(f"w={w} x {lo_:.1f}-{hi_:.1f} n={len(x):6d} g60 {bp(x.g60):+6.1f} ({bp(x.g60 - x.b60):+5.1f}) g240 {bp(x.g240):+6.1f} ({bp(x.g240 - x.b240):+5.1f}) | yrs "
                  + " ".join(f"{y}:{bp(g.g60 - g.b60):+.1f}" for y, g in x.groupby(x.time.dt.year)), flush=True)
    x = E[E.slow & (E.w == 0.0043) & (E.x >= 0.4)]
    L.card("M3b_absorb_w43_x40", x.assign(gross=x.g60 - x.b60)[["time", "coin", "side", "gross"]], "explore",
           note="0.43% >= 1-s bars, taker delta share >= .4 against the bar's direction, follow the bar 5 min late, 60 min; gross = minus within-day matched (takers with the bar)")
    print("all bars incl sub-1s, w=0.0043 x>=.4: diff g60", bp(E[(E.w == 0.0043) & (E.x >= 0.4)].pipe(lambda z: z.g60 - z.b60)))


if __name__ == "__main__" and sys.argv[1:2] == ["b"]:
    form_b()
