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
            "l": np.minimum.reduceat(l, st), "v": np.add.reduceat(b["v"], st), "d": np.add.reduceat(b["d"], st), "st": st}


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
    {"explore": explore, "b": lambda: None, "a": lambda: None, "cd": lambda: None}[sys.argv[1]]()


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


# ------------------------------------------------------------------ form a: level types x small-sell / large-buy split
def load_split(sym: str, lo: str, hi: str) -> dict:
    fs = [f for f in sorted((mbars.DIR / sym).glob("????-??-??.npz")) if lo <= f.stem < hi]
    if not fs:
        raise FileNotFoundError(sym)
    parts = []
    for f in fs:
        z = np.load(f)
        B, S = z["buy"].astype(np.float64), z["sell"].astype(np.float64)
        parts.append({k: z[k] for k in ("t0", "t1", "o", "h", "l", "c")} | {"v": B.sum(1) + S.sum(1), "d": B.sum(1) - S.sum(1),
                     "dsm": B[:, :3].sum(1) - S[:, :3].sum(1), "dlg": B[:, 6:].sum(1) - S[:, 6:].sum(1)})
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


def a_coin(sym: str, lo: str, hi: str) -> pd.DataFrame:
    """Traps (undercut + reclaim, entry on the first positive-delta bar above the level, 5 min late) at the previous day's low and at the
    7-day low (min of the previous 7 UTC days), with the trap's small-trade (< 10k USD) and large-trade (>= 60k) taker deltas."""
    b = load_split(sym, lo, hi)
    bt, bcl, bl = b["t1"], b["c"], b["l"]
    r = rbars(b, W)
    # re-aggregate the split deltas onto the range bars
    r["dsm"], r["dlg"] = np.add.reduceat(b["dsm"], r["st"]), np.add.reduceat(b["dlg"], r["st"])
    day = r["t1"] // 86_400_000
    days = np.unique(day)
    lows = pd.Series({d: r["l"][day == d].min() for d in days})
    rows = []
    for dd in days[7:]:
        ix = np.flatnonzero(day == dd)
        prev = lows.reindex(range(dd - 7, dd)).dropna()
        if len(prev) < 7:
            continue
        for kind, Lv in (("pd", prev.iloc[-1]), ("7d", prev.min())):
            near = r["l"][ix] <= Lv * 1.001
            if not near.any():
                continue
            # first undercut of the day that follows a close >= 30 bp above the level, then the reclaim bar
            above = np.maximum.accumulate(r["c"][ix] >= Lv * 1.003)
            und = np.flatnonzero((r["l"][ix] < Lv) & np.concatenate([[False], above[:-1]]))
            if not len(und):
                continue
            j_u = ix[und[0]]
            cand = [j for j in range(j_u, min(j_u + 20, len(r["c"]))) if r["d"][j] > 0 and r["c"][j] > Lv]
            if not cand:
                continue
            je = cand[0]
            seg = slice(j_u, je + 1)
            trap_low = r["l"][seg].min()
            t_e = int(r["t1"][je]) + 5 * 60_000
            g60, g240, g240s = exits(bt, bcl, bl, t_e, stop=trap_low)
            rows.append({"time": pd.to_datetime(t_e, unit="ms", utc=True), "kind": kind, "g60": g60, "g240": g240, "g240s": g240s,
                         "dsm": r["dsm"][seg].sum(), "dlg": r["dlg"][seg].sum(), "slow": (r["t1"][je] - r["t0"][je]) >= 1000})
    d = pd.DataFrame(rows)
    if len(d):
        d["coin"] = sym.replace("USDT", "")
        bad = {pd.Timestamp(x, tz="UTC") for x in BAD.get(sym, {})}
        d = d[~d.time.dt.floor("D").isin(bad)].dropna(subset=["g240"])
    return d


def form_a() -> None:
    out = []
    for sym in COINS:
        for y in (2021, 2022, 2023):
            for q in range(4):
                a = f"{y}-{3 * q + 1:02d}-01"
                z = f"{y}-{3 * q + 4:02d}-01" if q < 3 else f"{y + 1}-01-01"
                a0 = str((pd.Timestamp(a) - pd.Timedelta("8D")).date())
                d = a_coin(sym, a0, z)
                out.append(d[(d.time >= pd.Timestamp(a, tz="UTC"))] if len(d) else d)
        print(sym, flush=True)
    D = pd.concat(out, ignore_index=True)
    D.to_parquet(ROOT / "data/is3/m3a_explore.parquet")
    P = pd.read_parquet(ROOT / "data/is3/m3e_explore.parquet").query("kind == 'placebo'")
    bp = lambda s: round(float(np.nanmean(s)) * 1e4, 1)
    print(f"\nplacebo near prev-day low: g60 {bp(P.g60)} g240 {bp(P.g240)}")
    for kind, X in D.groupby("kind"):
        for lab, m in (("small-sell large-buy", (X.dsm < 0) & (X.dlg > 0)), ("small-buy large-sell", (X.dsm > 0) & (X.dlg < 0)),
                       ("both sell", (X.dsm < 0) & (X.dlg <= 0)), ("all", X.g240.notna())):
            x = X[m]
            print(f"{kind} {lab:22s} n={len(x):4d} g60 {bp(x.g60):+6.1f} g240 {bp(x.g240):+6.1f} stop {bp(x.g240s):+6.1f} | yrs "
                  + " ".join(f"{y}:{bp(g.g240):+.0f}" for y, g in x.groupby(x.time.dt.year)))
    e = D[(D.dsm < 0) & (D.dlg > 0)].assign(side=1)
    base = D[~((D.dsm < 0) & (D.dlg > 0))].assign(side=1)
    L.card("M3a_trap_split_g240", e.assign(gross=e.g240)[["time", "coin", "side", "gross"]], "explore",
           base=base.assign(gross=base.g240)[["time", "coin", "side", "gross"]],
           note="prev-day and 7-day-low traps where small takers (<10k) net sold and large (>=60k) net bought; base = the same traps without that split")


if __name__ == "__main__" and sys.argv[1:2] == ["a"]:
    form_a()


# ------------------------------------------------------------------ forms c and d
def cd_coin(sym: str, lo: str, hi: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """c: price spends >= 30 min below the previous day's low, then the first 0.2% bar closing back above it = re-cross (entry 5 min late).
    Trapped cohort = net taker SELLING below the level by small (< 10k) and large (>= 60k) trades, scaled by the coin's previous-day volume.
    d: for every >= 1-s 0.43% bar, the share of its volume traded in the extreme quarter of its range in the direction it went against
    (bottom quarter of a down bar = 'volume at the low'); side = against the bar (reversal); within-day matched like M2."""
    b = load_split(sym, lo, hi)
    bt, bcl, bl = b["t1"], b["c"], b["l"]
    r = rbars(b, W)
    r["dsm"], r["dlg"] = np.add.reduceat(b["dsm"], r["st"]), np.add.reduceat(b["dlg"], r["st"])
    day = r["t1"] // 86_400_000
    days = np.unique(day)
    lows = {d: r["l"][day == d].min() for d in days}
    vols = {d: r["v"][day == d].sum() for d in days}
    rows = []
    for dd in days[1:]:
        if dd - 1 not in lows:
            continue
        Lv, V = lows[dd - 1], vols[dd - 1]
        ix = np.flatnonzero(day == dd)
        below = r["c"][ix] < Lv
        k = 0
        while k < len(ix):
            if not below[k]:
                k += 1
                continue
            s0 = k
            while k < len(ix) and below[k]:
                k += 1
            if k >= len(ix):
                break
            j0, j1 = ix[s0], ix[k]                                 # first bar below, re-cross bar
            if r["t1"][j1] - r["t1"][j0] < 30 * 60_000:
                continue
            seg = slice(j0, j1)
            t_e = int(r["t1"][j1]) + 5 * 60_000
            g60, g240, _ = exits(bt, bcl, bl, t_e)
            rows.append({"time": pd.to_datetime(t_e, unit="ms", utc=True), "g60": g60, "g240": g240, "sm": -r["dsm"][seg].sum() / V,
                         "lg": -r["dlg"][seg].sum() / V, "all": -r["d"][seg].sum() / V, "mins": (r["t1"][j1] - r["t1"][j0]) / 6e4})
            break                                                  # first re-cross of the day
    C = pd.DataFrame(rows)
    # d
    r4 = rbars(b, 0.0043)
    n = len(r4["st"])
    ends = np.concatenate([r4["st"][1:] - 1, [len(b["c"]) - 1]])
    mid = np.sqrt(b["h"] * b["l"])
    bar_of = np.repeat(np.arange(n), ends - r4["st"] + 1)
    lo4, hi4 = r4["l"][bar_of], r4["h"][bar_of]
    dirn = np.sign(r4["c"] - r4["o"])
    pos = (mid - lo4) / np.maximum(hi4 - lo4, 1e-12)              # 0 = bar low, 1 = bar high
    ext = np.where(dirn[bar_of] < 0, pos <= 0.25, pos >= 0.75)
    vext = np.bincount(bar_of, weights=b["v"] * ext, minlength=n)
    share = vext / np.maximum(r4["v"], 1e-9)
    up = dirn > 0
    def runlen(x):
        out, kk = np.zeros(len(x), dtype=np.int32), 0
        for i, v in enumerate(x):
            kk = kk + 1 if v else 0
            out[i] = kk
        return out
    pl = np.minimum(np.where(up, runlen(up), runlen(~up)), 4)
    t_e = r4["t1"] + 5 * 60_000
    k0 = np.minimum(np.searchsorted(bt, t_e), len(bt) - 1)
    k = np.searchsorted(bt, t_e + 60 * 60_000)
    g = np.full(n, np.nan)
    ok = k < len(bt)
    g[ok] = -dirn[ok] * (bcl[k[ok]] / bcl[k0[ok]] - 1)
    Dd = pd.DataFrame({"time": pd.to_datetime(t_e, unit="ms", utc=True), "share": share, "side": (-dirn).astype(int), "g60": g,
                       "slow": (r4["t1"] - r4["t0"]) >= 1000, "m": (r4["t1"] // 86_400_000) * 100 + (dirn + 1) * 10 + pl})
    Dd = Dd[(Dd.side != 0) & Dd.g60.notna() & Dd.slow]
    Dd["q"] = np.minimum((Dd.share * 5).astype(int), 4)
    A = Dd.groupby(["m", "q"]).g60.agg(["sum", "count"]).reset_index()
    for X in (C, Dd, A):
        X["coin"] = sym.replace("USDT", "")
    bad = {pd.Timestamp(x, tz="UTC") for x in BAD.get(sym, {})}
    if len(C):
        C = C[~C.time.dt.floor("D").isin(bad)].dropna(subset=["g240"])
    Dd = Dd[~Dd.time.dt.floor("D").isin(bad)]
    return C, Dd[Dd.share >= 0.6], A


def form_cd() -> None:
    CC, DD, AA = [], [], []
    for sym in COINS:
        for y in (2021, 2022, 2023):
            for q in range(4):
                a = f"{y}-{3 * q + 1:02d}-01"
                z = f"{y}-{3 * q + 4:02d}-01" if q < 3 else f"{y + 1}-01-01"
                c, d, ag = cd_coin(sym, str((pd.Timestamp(a) - pd.Timedelta("1D")).date()), z)
                lo_t = pd.Timestamp(a, tz="UTC")
                CC.append(c[c.time >= lo_t] if len(c) else c); DD.append(d[d.time >= lo_t]); AA.append(ag)
        print(sym, flush=True)
    C, Dd, A = pd.concat(CC, ignore_index=True), pd.concat(DD, ignore_index=True), pd.concat(AA, ignore_index=True)
    bp = lambda s: round(float(np.nanmean(s)) * 1e4, 1)
    P = pd.read_parquet(ROOT / "data/is3/m3e_explore.parquet").query("kind == 'placebo'")
    print(f"\nc: re-crosses of the prev-day low after >= 30 min below: n={len(C)}, g60 {bp(C.g60)} g240 {bp(C.g240)} (near-level placebo g240 {bp(P.g240)})")
    for col in ("sm", "lg", "all"):
        t = pd.qcut(C[col].rank(method="first"), 3, labels=False)
        print(f"  trapped {col:3s} terciles g240:", " ".join(f"{bp(C.g240[t == i]):+.1f}" for i in range(3)),
              "| top-bottom by year:", {y: round(bp(g.g240[t[g.index] == 2]) - bp(g.g240[t[g.index] == 0]), 1) for y, g in C.groupby(C.time.dt.year)})
    t = pd.qcut(C["sm"].rank(method="first"), 3, labels=False)
    e, base = C[t == 2].assign(side=1), C[t == 0].assign(side=1)
    L.card("M3c_trapped_small_sellers", e.assign(gross=e.g240)[["time", "coin", "side", "gross"]], "explore",
           base=base.assign(gross=base.g240)[["time", "coin", "side", "gross"]], note="re-cross of prev-day low after >= 30 min below; top vs bottom tercile of small-trade net selling below the level (/ prev-day volume), long 5 min late, 240 min")
    A = A.groupby(["coin", "m", "q"])[["sum", "count"]].sum()
    Ab = A.xs(0, level="q") if 0 in A.index.get_level_values("q") else None
    Abm = A.groupby(level=["coin", "m"]).sum()
    mu = (Abm["sum"] / Abm["count"]).rename("b")
    Dd = Dd.join(mu, on=["coin", "m"])
    print("\nd: share of a >= 1-s 0.43% bar's volume in its extreme quarter (against the bar); fade from 5 min late, 60 min; diff vs all bars of the same cell")
    for lo_, hi_ in ((0.6, 0.8), (0.8, 1.01)):
        x = Dd[(Dd.share >= lo_) & (Dd.share < hi_)]
        print(f"  share {lo_}-{hi_} n={len(x)} g60 {bp(x.g60):+.1f} diff {bp(x.g60 - x.b):+.1f} | yrs", {y: bp(g.g60 - g.b) for y, g in x.groupby(x.time.dt.year)},
              "| sides", {s: bp(g.g60 - g.b) for s, g in x.groupby("side")})
    x = Dd[Dd.share >= 0.6]
    L.card("M3d_volume_at_extreme", x.assign(gross=x.g60 - x.b)[["time", "coin", "side", "gross"]], "explore",
           note=">= 1-s 0.43% bars with >= 60% of volume in the extreme quarter they went to; fade 5 min late, 60 min; gross = minus same coin/day/side/prior-run cell mean")


if __name__ == "__main__" and sys.argv[1:2] == ["cd"]:
    form_cd()
