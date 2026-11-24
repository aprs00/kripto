"""M2: order velocity x10 (InSilico R7; notes.md section M2). Explore = BTC ETH SOL 2021-23 micro bars (kripto.mbars).

Range bars of width w (0.1% = the micro bars themselves, his size; 0.2%, 0.43%). For each bar i: ratio = n_i / n_{i-1} (aggTrades
per bar; form c: duration ratio). Event at the close of bar i when |log ratio| >= log K (K = 5, 10, 20 = form d's dose), split into
'jump' (more trades) and 'drop'. Outcomes from the close of bar i (decision), against bar i's direction (side = -sign(c_i - o_i)):
g15 / g60 / g240 = simple return over 15 / 60 / 240 min; late = the same from 5 min later; calm = next-60-min range / previous-60-min range.
Baseline: non-event bars of the same coin, UTC day, side and prior same-direction run length (m = day_side_pl), re-weighted to the events' mix.
Form b: event bars whose high (low) is within the last 4 bars of the rolling 24 h high (low), and bars within 10 bp of the previous day's
value-area high / low (70% volume around the POC, 10-bp bins).
Null: trade counts shuffled within each day.

    nice -n 19 .venv/bin/python -m research.studies.is3_m2 explore [null]
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import mbars
from research.studies import is3_lib as L

COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
BAD = json.loads((L.OUT / "mbars_bad_days.json").read_text())
WIDTHS = [0.001, 0.002, 0.0043]
KEYS = ("t0", "t1", "o", "h", "l", "c", "n")


def load(sym: str, lo: str, hi: str) -> dict:
    fs = [f for f in sorted((mbars.DIR / sym).glob("????-??-??.npz")) if lo <= f.stem < hi]
    if not fs:
        raise FileNotFoundError(sym)
    parts = []
    for f in fs:
        z = np.load(f)
        parts.append({k: z[k] for k in KEYS} | {"v": (z["buy"].sum(1, dtype=np.float64) + z["sell"].sum(1, dtype=np.float64)).astype(np.float32)})
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


def rbars(b: dict, w: float) -> dict:
    if w <= 0.001:
        return {k: b[k] for k in ("t0", "t1", "o", "h", "l", "c", "n", "v")}
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
            "l": np.minimum.reduceat(l, st), "n": np.add.reduceat(b["n"].astype(np.int64), st), "v": np.add.reduceat(b["v"].astype(np.float64), st)}


def runlen(x: np.ndarray) -> np.ndarray:
    out, k = np.zeros(len(x), dtype=np.int32), 0
    for i, v in enumerate(x):
        k = k + 1 if v else 0
        out[i] = k
    return out


def pd_value_area(b: dict) -> tuple[np.ndarray, np.ndarray]:
    """per micro bar: previous UTC day's value-area high and low (70% of volume around the POC, 10-bp log bins)."""
    day = b["t1"] // 86_400_000
    vah, val = np.full(len(day), np.nan), np.full(len(day), np.nan)
    days = np.unique(day)
    prev = None
    for d in days:
        ix = np.flatnonzero(day == d)
        if prev is not None:
            vah[ix], val[ix] = prev
        mid = np.sqrt(b["h"][ix] * b["l"][ix])
        k = np.floor(np.log(mid) / 1e-3).astype(np.int64)
        k0 = k.min()
        vol = np.bincount(k - k0, weights=b["v"][ix].astype(np.float64))
        poc = int(vol.argmax())
        a = z = poc
        tot, acc = vol.sum(), vol[poc]
        while acc < 0.7 * tot and (a > 0 or z < len(vol) - 1):
            up = vol[z + 1] if z < len(vol) - 1 else -1
            dn = vol[a - 1] if a > 0 else -1
            if up >= dn:
                z += 1; acc += up
            else:
                a -= 1; acc += dn
        prev = (np.exp((k0 + z + 1) * 1e-3), np.exp((k0 + a) * 1e-3))
    return vah, val


def coin_events(sym: str, lo: str, hi: str, shuffle: bool = False) -> pd.DataFrame:
    b = load(sym, lo, hi)
    bt, bcl, bh, bl = b["t1"], b["c"], b["h"], b["l"]
    vah_m, val_m = pd_value_area(b)
    coin = sym.replace("USDT", "")
    rng = np.random.default_rng(5)
    out = []
    for w in WIDTHS:
        r = rbars(b, w)
        n = r["n"].astype(np.float64)
        day = r["t1"] // 86_400_000
        if shuffle:
            n = n.copy()
            for dd in np.unique(day):
                ix = np.flatnonzero(day == dd)
                n[ix] = n[rng.permutation(ix)]
        dur = np.maximum((r["t1"] - r["t0"]).astype(np.float64), 1.0)
        lr = np.concatenate([[np.nan], np.log(n[1:] / np.maximum(n[:-1], 1))])
        ld = np.concatenate([[np.nan], np.log(dur[1:] / dur[:-1])])
        dirn = np.sign(r["c"] - r["o"])
        side = -dirn
        up = dirn > 0
        pl = np.where(up, runlen(up), runlen(~up))
        # forward returns from the bar's close (decision), on micro-bar closes
        def fwd(mins: float, delay: float = 0.0) -> np.ndarray:
            t = r["t1"] + int(delay * 6e4)
            k0 = np.minimum(np.searchsorted(bt, t), len(bt) - 1)
            k = np.searchsorted(bt, t + int(mins * 6e4))
            ok = k < len(bt)
            g = np.full(len(t), np.nan)
            base = bcl[k0] if delay else r["c"]
            g[ok] = bcl[k[ok]] / base[ok] - 1
            return g
        # ranges over the previous / next 60 min (on micro bars, via cumulative max is awkward: use a loop on sorted windows)
        ts = pd.Series(bh, index=pd.to_datetime(bt, unit="ms"))
        hmax_prev = ts.rolling("60min").max().to_numpy()
        lmin_prev = pd.Series(bl, index=ts.index).rolling("60min").min().to_numpy()
        kidx = np.searchsorted(bt, r["t1"])                                  # micro bar of the decision
        kfwd = np.minimum(np.searchsorted(bt, r["t1"] + 3_600_000), len(bt) - 1)
        prev_rng = hmax_prev[kidx] / lmin_prev[kidx] - 1
        next_rng = hmax_prev[kfwd] / lmin_prev[kfwd] - 1
        calm = np.where(kfwd < len(bt) - 1, next_rng / np.maximum(prev_rng, 1e-6), np.nan)
        # references
        ix24 = pd.Series(r["h"], index=pd.to_datetime(r["t1"], unit="ms"))
        hh = ix24.rolling("24h").max().to_numpy()
        ll = pd.Series(r["l"], index=ix24.index).rolling("24h").min().to_numpy()
        at_hi = pd.Series(r["h"] >= hh - 1e-12).rolling(4, min_periods=1).max().to_numpy() > 0
        at_lo = pd.Series(r["l"] <= ll + 1e-12).rolling(4, min_periods=1).max().to_numpy() > 0
        extreme = np.where(up, at_hi, at_lo)
        vah, val = vah_m[kidx], val_m[kidx]
        near_va = (np.abs(r["c"] / vah - 1) < 1e-3) | (np.abs(r["c"] / val - 1) < 1e-3)
        d = pd.DataFrame({"time": pd.to_datetime(r["t1"], unit="ms", utc=True), "w": w, "lr": lr, "ld": ld, "side": side.astype(int),
                          "pl": np.minimum(pl, 4), "n": n, "fast": (r["t1"] - r["t0"]) < 1000,
                          "g15": side * fwd(15), "g60": side * fwd(60), "g240": side * fwd(240), "late60": side * fwd(60, 5.0),
                          "calm": calm, "extreme": extreme, "near_va": near_va})
        d = d[(d.side != 0) & np.isfinite(d.lr) & np.isfinite(d.g60)]
        d["m"] = (d.time.dt.floor("D").astype("int64") // 86_400_000_000) * 100 + (d.side + 1) * 10 + d.pl
        d["lcalm"] = np.log(d.calm.clip(1e-3, 1e3))
        bad = {pd.Timestamp(x, tz="UTC") for x in BAD.get(sym, {})}
        d = d[~d.time.dt.floor("D").isin(bad)]
        ev = d[(d.lr.abs() >= np.log(5)) | (d.ld.abs() >= np.log(5))]
        if w <= 0.001:                                   # micro width: events are most bars; a seeded 25% sample (baseline is aggregated, so unbiased)
            ev = ev[np.random.default_rng(int(r["t1"][0]) % 2**32).random(len(ev)) < 0.25]
        ev = ev.drop(columns=["n", "calm", "pl"]).copy()
        aggs = []
        for feat in ("lr", "ld"):
            bs = d[d[feat].abs() < np.log(2)]
            g = bs.groupby(["m", "fast", "extreme", "near_va"])[["g15", "g60", "g240", "late60", "lcalm"]]
            a = g.sum().add_prefix("s_").join(g.count().add_prefix("n_")).reset_index()
            a["feat"], a["w"] = feat, w
            aggs.append(a)
        ev["w"] = w
        out.append((ev, pd.concat(aggs, ignore_index=True)))
        del d
    E = pd.concat([o[0] for o in out], ignore_index=True)
    A = pd.concat([o[1] for o in out], ignore_index=True)
    E["coin"], A["coin"] = coin, coin
    return E, A


def collect(lo: str, hi: str, shuffle: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    E, A = [], []
    for sym in COINS:
        for y in range(int(lo[:4]), int(hi[:4])):
            for q in range(4):                         # quarters keep RAM < 1.5 GB
                a = f"{y}-{3 * q + 1:02d}-01"
                z = f"{y}-{3 * q + 4:02d}-01" if q < 3 else f"{y + 1}-01-01"
                try:
                    e, ag = coin_events(sym, max(lo, a), min(hi, z), shuffle)
                except FileNotFoundError:
                    continue
                E.append(e); A.append(ag)
                print(sym, a, len(e), flush=True)
    return pd.concat(E, ignore_index=True), pd.concat(A, ignore_index=True)


def rew(x: pd.DataFrame, A: pd.DataFrame, col: str) -> float:
    """baseline mean in the events' (coin, w, m) cells, re-weighted to the events' mix."""
    g = A.groupby(["coin", "w", "m"])[[f"s_{col}", f"n_{col}"]].sum()
    ym = g[f"s_{col}"] / g[f"n_{col}"].replace(0, np.nan)
    wt = x.groupby(["coin", "w", "m"]).size()
    k = wt.index.intersection(ym.dropna().index)
    return float((ym[k] * wt[k]).sum() / wt[k].sum()) if len(k) else np.nan


def bp(x) -> float:
    return round(float(np.nanmean(x)) * 1e4, 1)


def table(E: pd.DataFrame, A: pd.DataFrame, feat: str, label: str, sub=None) -> None:
    print(f"\n== {label}: events vs within-day matched (bp, against the event bar's direction) | mean log calm ratio, event - matched")
    A = A[A.feat == feat]
    if sub:
        E, A = E[E[sub]], A[A[sub]]
    for w, X in E.groupby("w"):
        Aw = A[A.w == w]
        for K in (5, 10, 20):
            for nm, msk in (("jump", X[feat] >= np.log(K)), ("drop", X[feat] <= -np.log(K))):
                e = X[msk]
                if len(e) < 20:
                    print(f"w={w:.4f} {K:2d}x {nm}: n={len(e)}")
                    continue
                s = f"w={w:.4f} {K:2d}x {nm}: n={len(e):6d} (sub1s {e.fast.mean():.0%})"
                for c in ("g15", "g60", "g240", "late60"):
                    s += f" | {c} {bp(e[c]):+6.1f} vs {bp(rew(e, Aw, c)):+6.1f}"
                s += f" | lcalm {np.nanmean(e.lcalm) - rew(e, Aw, 'lcalm'):+.2f}"
                es, As = e[~e.fast], Aw[~Aw.fast]
                s += f" | slow-only g60 {bp(es.g60) - bp(rew(es, As, 'g60')):+.1f} (n {len(es)})"
                s += " | yrs " + " ".join(f"{t}:{bp(g.g60) - bp(rew(g, Aw, 'g60')):+.1f}" for t, g in e.groupby(e.time.dt.year))
                print(s, flush=True)


def explore(null: bool = False) -> None:
    E, A = collect("2021-01-01", "2024-01-01", shuffle=null)
    print("events", len(E), "agg rows", len(A))
    if null:
        table(E, A, "lr", "NULL (counts shuffled within day)")
        return
    E.to_parquet(L.ROOT / "data/is3/m2_explore_events.parquet"); A.to_parquet(L.ROOT / "data/is3/m2_explore_base.parquet")
    table(E, A, "lr", "a/d trade-count ratio")
    table(E, A, "ld", "c duration ratio (jump = slower bar)")
    table(E, A, "lr", "b at a 24 h extreme (bar's high/low within 4 bars of it)", "extreme")
    table(E, A, "lr", "b within 10 bp of the previous day's VAH / VAL", "near_va")


if __name__ == "__main__":
    explore(null="null" in sys.argv)
