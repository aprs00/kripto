"""F1 e/f: location filters for the Binance books (value area, round numbers, poor extremes). notes.md section F1 (e/f think-through).

    .venv/bin/python -m research.studies.is3_f1loc feat        # per-coin day profiles from bn100 1h -> data/is3/f1loc_feat.parquet
    .venv/bin/python -m research.studies.is3_f1loc e|f         # F0 judges, explore only
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from kripto import data
from research.studies import is3_filter as F
from research.studies.is2_profile import value_area

FEAT = Path("data/is3/f1loc_feat.parquet")
NB = 30
BOOKS = {"flow": {"lookback": 3, "cap": 0.05}, "xsmom": {"lookback": 28, "every_days": 1, "cap": 0.05}}


def day_profiles(k: pd.DataFrame) -> pd.DataFrame:
    """One row per complete UTC day (24 hourly bars): close, VA bounds at 50/70/85%, poor low/high (extreme bin touched by >= 2 hours)."""
    k = k.copy()
    k["time"] = pd.to_datetime(k.t, unit="ms", utc=True)
    k["day"] = k.time.dt.floor("D")
    k = k[(k.h > 0) & (k.l > 0)]
    full = k.groupby("day").size()
    k = k[k.day.isin(full[full == 24].index)].sort_values("time")
    if k.empty:
        return pd.DataFrame()
    days = k.day.unique()
    H, Lo, V = (k[c].to_numpy().reshape(len(days), 24) for c in ("h", "l", "qv"))
    C = k.c.to_numpy().reshape(len(days), 24)[:, -1]
    lh, ll = np.log(H), np.log(Lo)
    dlo, dhi = ll.min(1, keepdims=True), lh.max(1, keepdims=True)
    width = np.maximum(dhi - dlo, 1e-9)
    edges = dlo[:, :, None] + width[:, :, None] * np.linspace(0, 1, NB + 1)[None, None, :]       # (D,1,NB+1)
    blo, bhi = edges[..., :-1], edges[..., 1:]
    ov = np.clip(np.minimum(lh[..., None], bhi) - np.maximum(ll[..., None], blo), 0, None)      # (D,24,NB) overlap
    span = np.maximum(lh - ll, 1e-12)[..., None]
    point = (lh - ll)[..., None] <= 1e-12
    inbin = (ll[..., None] >= blo) & (ll[..., None] <= bhi)
    share = np.where(point, inbin.astype(float), ov / span)
    share = share / np.maximum(share.sum(-1, keepdims=True), 1e-12)
    vol = (share * V[..., None]).sum(1)
    tpo = ((ov > 0) | (point & inbin)).sum(1)
    rows = []
    lc = np.log(C)
    for i, d in enumerate(days):
        r = {"day": d, "close": C[i]}
        x = (lc[i] - dlo[i, 0]) / width[i, 0] * NB
        for frac in (0.5, 0.7, 0.85):
            _, a, b = value_area(vol[i], frac)
            r[f"loc{int(frac * 100)}"] = 1 if x > b + 1 else (-1 if x < a else 0)     # above VAH / below VAL / inside
        r["poor_lo"], r["poor_hi"] = bool(tpo[i, 0] >= 2), bool(tpo[i, -1] >= 2)
        rows.append(r)
    return pd.DataFrame(rows).set_index("day")


def feat() -> None:
    cols = data.load_panel("bnall", "1d")["close"].columns
    out = []
    for n, coin in enumerate(cols):
        f = data.BN100_DIR / f"{coin}USDT.parquet"
        if not f.exists():
            continue
        d = day_profiles(pd.read_parquet(f, columns=["t", "h", "l", "c", "qv"]))
        if len(d):
            d["coin"] = coin
            out.append(d.reset_index())
        if n % 100 == 0:
            print(n, coin, flush=True)
    df = pd.concat(out, ignore_index=True)
    FEAT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(FEAT)
    print("coins", df.coin.nunique(), "rows", len(df))


def wide(col: str, index, columns) -> pd.DataFrame:
    df = pd.read_parquet(FEAT, columns=["day", "coin", col])
    return df.pivot(index="day", columns="coin", values=col).reindex(index=index, columns=columns)


def coverage(w: pd.DataFrame, have: pd.DataFrame) -> float:
    a = F.cut(w.abs().sum(axis=1), "explore")
    b = F.cut(w.where(have.reindex_like(w).fillna(False).astype(bool), 0).abs().sum(axis=1), "explore")
    return round(float(b.sum() / a.sum()), 3)


def touched(w, mask, side) -> float:
    ww = F.apply(w, mask, side)
    a, b = F.cut(w.abs().sum(axis=1), "explore"), F.cut((w - ww).abs().sum(axis=1), "explore")
    return round(float(b.sum() / a.sum()), 4)


def per_year(w, p, s, mask, side) -> str:
    b, f = F.run(w, p, s), F.run(F.apply(w, mask, side), p, s)
    o = []
    for y in (2021, 2022, 2023):
        sb, sf = F.stats(b[str(y)]), F.stats(f[str(y)])
        o.append(f"{y}:{sf['sr'] - sb['sr']:+.2f}")
    return " ".join(o)


def judge(tag, name, w, p, s, mask, side, n, note):
    note = f"{note}; touched {touched(w, mask, side)}; per-year dSR {per_year(w, p, s, mask, side)}"
    return F.judge(f"F1{tag}_{name}", w, p, s, mask, "explore", side=side, n_random=n, note=note)


def run_e() -> None:
    for name, prm in BOOKS.items():
        w, p, s = F.book(name, "bnall", prm)
        print(name, "hourly-profile coverage of book weight (explore):", coverage(w, wide("loc70", w.index, w.columns).notna()), flush=True)
        for frac, n in ((70, 100), (50, 30), (85, 30)):
            loc = wide(f"loc{frac}", w.index, w.columns)
            sgn = np.sign(w)
            m_against = ~(((sgn > 0) & (loc == -1)) | ((sgn < 0) & (loc == 1)))
            judge(f"e1_va{frac}", name, w, p, s, m_against, None, n, f"block positions against location (long below VAL, short above VAH), VA {frac}%")
            m_inside = ~(loc == 0)
            judge(f"e2_va{frac}", name, w, p, s, m_inside, None, n, f"block positions while close inside VA {frac}%")
            if frac == 70:
                m_chase = ~(((sgn > 0) & (loc == 1)) | ((sgn < 0) & (loc == -1)))
                judge(f"e3_va{frac}", name, w, p, s, m_chase, None, n, "block longs above VAH / shorts below VAL (responsive reading)")


def next_round(c: pd.DataFrame) -> pd.DataFrame:
    x = c.where(c > 0)
    e = np.floor(np.log10(x))
    m = x / 10 ** e                                                                # mantissa in [1, 10)
    nxt = np.select([m < 2, m < 5], [2.0, 5.0], 10.0)
    return pd.DataFrame(nxt, index=c.index, columns=c.columns) * 10 ** e


def run_f() -> None:
    for name, prm in BOOKS.items():
        w, p, s = F.book(name, "bnall", prm)
        c = p["close"]
        dist = next_round(c) / c - 1                                                  # > 0: distance up to the next round level
        for pct, n in ((0.03, 100), (0.02, 30), (0.01, 30)):
            m = ~(dist <= pct)
            judge(f"f1_round{int(pct * 100)}", name, w, p, s, m, -1, n, f"R26: block shorts within {pct:.0%} below the next 1/2/5x10^k level")
        plo, phi = wide("poor_lo", w.index, w.columns), wide("poor_hi", w.index, w.columns)
        judge("f2_poorlo", name, w, p, s, ~(plo == True), 1, 100, "block longs whose day low is poor (bottom bin >= 2 hours)")   # noqa: E712
        judge("f2_poorhi", name, w, p, s, ~(phi == True), -1, 100, "block shorts whose day high is poor")                       # noqa: E712


if __name__ == "__main__":
    {"feat": feat, "e": run_e, "f": run_f}[sys.argv[1]]()
