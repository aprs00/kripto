"""P1 gap fill (R14; tg:29-38, wa 18.10.31(2)): does the next UTC day put its volume where yesterday traded least?

Daily volume profiles from Binance 1-min klines: each minute's quote volume spread evenly over its [low, high] in 10-bp log
bins (approximation; exact profiles need M0). Day d's profile is compared with day d+1's volume.
a  share of d+1 volume inside d's least-traded third of its range bins (LV) and most-traded third (HV), each against the
   MIRROR placebo: the same bins reflected around d+1's open (same distances from where d+1 starts, other side).
f  bimodal days (smoothed profile with two humps >= 30% of the POC, >= 15 bins apart, valley <= 50% of the smaller hump):
   d+1 volume share inside the valley band (bins between the humps with volume <= 50% of the smaller hump) vs its mirror.
b  nearest interior low-volume node (local minimum of the smoothed profile, <= 30% of POC, inside d's range) above or below
   d+1's open: is it reached before price moves the same distance the other way (first passage on 1-min high/low within
   d+1; random walk 50%)? Placebo: the node set of d-8, moved to the same distance (so only the day differs).
Samples: explore COINS10 2021-2023 (this script's default). Outputs research/is3/P1__explore.json.

    nice -n 19 .venv/bin/python -m research.studies.is3_p1 build | report | checks
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
BIN = np.log(1.001)
TAB = ROOT / "data/is3/p1.parquet"
OUT = ROOT / "research/is3/P1__explore.json"


def load(coin: str, lo: str, hi: str) -> pd.DataFrame:
    k = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet")
    k.index = pd.to_datetime(k.t, unit="ms", utc=True)
    k = k[(k.index >= pd.Timestamp(lo, tz="UTC") - pd.Timedelta("10D")) & (k.index < pd.Timestamp(hi, tz="UTC") + pd.Timedelta("1D"))]
    return k.dropna(subset=["h", "l", "c"])


def profiles(k: pd.DataFrame, freq: str = "D", minbars: int = 1200, delta: bool = False) -> dict:
    """period -> (offset bin, volume per bin, minute arrays (lb, hb) for first passage, open bin[, |delta| per bin])."""
    lb = np.floor(np.log(k.l.to_numpy()) / BIN).astype(np.int64)
    hb = np.floor(np.log(k.h.to_numpy()) / BIN).astype(np.int64)
    w = k.qv.to_numpy() / (hb - lb + 1)
    wd = (2 * k.tbqv.to_numpy() - k.qv.to_numpy()) / (hb - lb + 1)
    day = k.index.floor(freq)
    out = {}
    for d, ix in pd.Series(np.arange(len(k)), index=day).groupby(level=0):
        i = ix.to_numpy()
        if len(i) < minbars:
            continue
        off = lb[i].min()
        size = hb[i].max() - off + 2
        diff = np.zeros(size)
        np.add.at(diff, lb[i] - off, w[i]); np.add.at(diff, hb[i] - off + 1, -w[i])
        prof = np.cumsum(diff)[:-1]
        open_bin = int(np.floor(np.log(k.c.to_numpy()[i[0] - 1] if i[0] > 0 else k.c.to_numpy()[i[0]]) / BIN))
        out[d] = (int(off), prof, lb[i], hb[i], open_bin)
        if delta:
            dd = np.zeros(size)
            np.add.at(dd, lb[i] - off, wd[i]); np.add.at(dd, hb[i] - off + 1, -wd[i])
            out[d] = out[d] + (np.abs(np.cumsum(dd)[:-1]),)
    return out


def smooth(p: np.ndarray, k: int = 5) -> np.ndarray:
    return np.convolve(p, np.ones(k) / k, mode="same")


def share(prof_next: tuple, bins: np.ndarray) -> float:
    off, p = prof_next[0], prof_next[1]
    j = bins - off
    j = j[(j >= 0) & (j < len(p))]
    return float(p[j].sum() / p.sum()) if p.sum() > 0 else np.nan


def bimodal(p: np.ndarray):
    s = smooth(p)
    pk = [i for i in range(1, len(s) - 1) if s[i] >= s[i - 1] and s[i] > s[i + 1] and s[i] >= 0.3 * s.max()]
    best = None
    for a in range(len(pk)):
        for b in range(a + 1, len(pk)):
            i, j = pk[a], pk[b]
            if j - i < 15:
                continue
            small = min(s[i], s[j])
            v = i + int(np.argmin(s[i:j + 1]))
            depth = s[v] / small
            if depth <= 0.5 and (best is None or depth < best[3]):
                best = (i, j, v, depth, small)
    if best is None:
        return None
    i, j, v, depth, small = best
    band = np.arange(i, j + 1)[s[i:j + 1] <= 0.5 * small]
    return band, depth, j - i


def first_passage(lb: np.ndarray, hb: np.ndarray, start: int, target: int) -> float:
    """1 if target bin is touched before the mirror bin (same distance from start, other side), 0 if the mirror first,
    nan if neither within the day. A minute touching both counts as 0.5."""
    m = 2 * start - target
    up, dn = (target, m) if target > start else (m, target)
    hit_up = hb >= up
    hit_dn = lb <= dn
    iu = int(np.argmax(hit_up)) if hit_up.any() else 10**9
    idn = int(np.argmax(hit_dn)) if hit_dn.any() else 10**9
    if iu == idn == 10**9:
        return np.nan
    if iu == idn:
        return 0.5
    first_up = iu < idn
    return float(first_up == (target > start))


def lvns(p: np.ndarray, off: int) -> np.ndarray:
    s = smooth(p)
    return np.array([off + i for i in range(3, len(s) - 3) if s[i] <= s[i - 1] and s[i] < s[i + 1] and s[i] <= 0.3 * s.max()], dtype=np.int64)


def one(coin: str, lo: str, hi: str) -> pd.DataFrame:
    P = profiles(load(coin, lo, hi))
    days = sorted(P)
    rows = []
    for n, d in enumerate(days):
        nx = d + pd.Timedelta("1D")
        if nx not in P or d < pd.Timestamp(lo, tz="UTC") - pd.Timedelta("1D") or nx >= pd.Timestamp(hi, tz="UTC"):
            continue
        off, p, *_ = P[d]
        T = P[nx]
        ob = T[4]
        order = np.argsort(p, kind="stable")
        third = max(len(p) // 3, 1)
        lv, hv = off + order[:third], off + order[-third:]
        row = {"time": nx, "coin": coin, "nbins": len(p), "open_in": bool(off <= ob < off + len(p)),
               "lv": share(T, lv), "lv_m": share(T, 2 * ob - lv), "hv": share(T, hv), "hv_m": share(T, 2 * ob - hv)}
        # dose: the thinnest tenth of the bins vs the next tenths
        tenth = max(len(p) // 10, 1)
        for q in range(3):
            b = off + order[q * tenth:(q + 1) * tenth]
            row[f"lv{q}"], row[f"lv{q}_m"] = share(T, b), share(T, 2 * ob - b)
        bm = bimodal(p)
        if bm is not None:
            band, depth, sep = bm
            b = off + band
            row.update({"bim": True, "depth": depth, "sep": sep, "valley": share(T, b), "valley_m": share(T, 2 * ob - b),
                        "valley_dist": float(np.abs(b - ob).mean())})
        else:
            row["bim"] = False
        nodes = lvns(p, off)
        prev = days[n - 8] if n >= 8 else None
        if len(nodes) and off <= ob < off + len(p):
            t = nodes[np.argmin(np.abs(nodes - ob))]
            if t != ob:
                row["lvn_dist"] = int(abs(t - ob))
                row["lvn_hit"] = first_passage(T[2], T[3], ob, int(t))
                if prev is not None and prev in P:
                    pn = lvns(P[prev][1], P[prev][0])
                    if len(pn):
                        # placebo: d-8's nearest node to d-8's own close, moved so it sits at its own distance from today's open
                        po = P[prev + pd.Timedelta("1D")][4] if prev + pd.Timedelta("1D") in P else int(pn.mean())
                        tp = pn[np.argmin(np.abs(pn - po))]
                        if tp != po:
                            row["plc_hit"] = first_passage(T[2], T[3], ob, int(ob + (tp - po)))
        rows.append(row)
    return pd.DataFrame(rows)


def build(lo: str = "2021-01-01", hi: str = "2024-01-01", out: Path = TAB) -> pd.DataFrame:
    e = pd.concat([one(c, lo, hi) for c in L.COINS10], ignore_index=True)
    e.to_parquet(out)
    print(len(e), "bimodal", int(e.bim.sum()))
    return e


def _diff(e: pd.DataFrame, a: str, b: str, reps: int = 2000) -> dict:
    x = e.dropna(subset=[a, b])
    s = L.stats(x.assign(side=1, gross=x[a] - x[b])[["time", "coin", "side", "gross"]], reps=reps)
    return {"n": s["n"], "mean": round(float(x[a].mean()), 4), "mirror": round(float(x[b].mean()), 4),
            "diff_pp": round(s["mean_bp"] / 100, 3), "ci95_pp": [round(v / 100, 3) for v in s["ci95_bp"]], "p": s["p"], "by_year_pp": {y: round(v[1] / 100, 3) for y, v in s["by_year"].items()}}


def report() -> None:
    e = pd.read_parquet(TAB)
    res = {"n_days": int(len(e))}
    for k, (a, b) in {"a_LV_third": ("lv", "lv_m"), "a_HV_third": ("hv", "hv_m"), "a_thinnest_10pct": ("lv0", "lv0_m"),
                      "a_2nd_10pct": ("lv1", "lv1_m"), "a_3rd_10pct": ("lv2", "lv2_m")}.items():
        res[k] = _diff(e, a, b)
    bm = e[e.bim]
    res["f_valley"] = _diff(bm, "valley", "valley_m")
    q = pd.qcut(bm.depth.rank(method="first"), 3, labels=["deep", "mid", "shallow"])
    for lab in ("deep", "mid", "shallow"):
        res[f"f_valley_{lab}"] = _diff(bm[q == lab], "valley", "valley_m", reps=800)
    x = e.dropna(subset=["lvn_hit"])
    res["b_lvn_first_passage"] = {"n": int(len(x)), "hit": round(float(x.lvn_hit.mean()), 4)}
    y = e.dropna(subset=["lvn_hit", "plc_hit"])
    res["b_vs_placebo"] = _diff(y, "lvn_hit", "plc_hit")
    for k, v in res.items():
        print(k, v)
    OUT.write_text(json.dumps(res, indent=1, default=float))


def checks() -> None:
    """Hand-check: print one bimodal day's profile summary and the next day's share, and verify the profile volume equals the
    day's klines volume (spreading must conserve volume)."""
    k = load("BTC", "2022-03-01", "2022-03-10")
    P = profiles(k)
    d = sorted(P)[3]
    tot = k[k.index.floor("D") == d].qv.sum()
    print("volume conserved:", round(P[d][1].sum() / tot, 9))
    e = pd.read_parquet(TAB)
    r = e[e.bim & (e.coin == "BTC")].iloc[0]
    print(r.to_dict())


if __name__ == "__main__":
    {"build": build, "report": report, "checks": checks}[sys.argv[1]]()
