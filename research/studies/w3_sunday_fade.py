"""W3 replication (pre-registered in journal/2026-11-19.md BEFORE any bn100 number was computed): fade the Sunday 12:00 -> 18:00
New York move (|log move| >= 1%) for the next 24 h, on bn100 coins that are NOT among the hand-picked 82 (data.BN_SYMBOLS),
in the point-in-time top-100 (st.universe top_n=100, min_days=30, computed on all of bn100) at the decision bar.
Fade return = -sign(move) * SIMPLE return over 24 h (funding over the day ignored; ≈ ±1 bp). Decision: CONFIRMED iff mean > +20 bp
AND t on event-day means >= 2.0 over 2020-26 AND both periods (<= 2023-12-31, >= 2024-01-01) positive.
Plumbing check (not part of the decision): the 82 inside bn100 in LOG terms should resemble 11-15 (+20 bp to 2023, +105 bp from 2024).

  nice -n 19 .venv/bin/python -m research.studies.w3_sunday_fade
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from kripto import data, strategies as st


def tday(x: pd.Series) -> float:
    d = x.groupby(level=0).mean()
    return float(d.mean() / d.std() * np.sqrt(len(d))) if len(d) > 5 and d.std() > 0 else float("nan")


def show(name, x):
    x = x.dropna()
    print(f"  {name:44s} n={len(x):5d} days={x.index.get_level_values(0).nunique():3d} mean={x.mean() * 1e4:+7.1f} bp "
          f"median={x.median() * 1e4:+6.1f} bp t_day={tday(x):+.2f} hit={(x > 0).mean():.0%}")


def main():
    p = data.load_panel("bn100", "1h")
    c = p["close"]
    uni = st.universe(p, top_n=100, min_days=30).to_numpy()
    idx = c.index
    ny = (idx + pd.Timedelta(hours=1)).tz_convert("America/New_York")
    C = c.to_numpy()
    rows_s, rows_l, rows_d = [], [], []
    for i in np.flatnonzero((np.asarray(ny.day_of_week) == 6) & (np.asarray(ny.hour) == 18)):
        j, k = i - 6, i + 24
        if j < 0 or k >= len(idx) or idx[i] - idx[j] != pd.Timedelta(hours=6) or idx[k] - idx[i] != pd.Timedelta(hours=24):
            continue
        a, b, e = C[j].astype(float), C[i].astype(float), C[k].astype(float)
        mv = np.log(b / a)
        ok = uni[i] & np.isfinite(mv) & np.isfinite(e) & (np.abs(mv) >= 0.01)
        day = idx[i].floor("D")
        rows_s.append(pd.Series(np.where(ok, -np.sign(mv) * (e / b - 1.0), np.nan), c.columns, name=day))
        rows_d.append(pd.Series(np.where(ok, np.sign(mv), np.nan), c.columns, name=day))
        rows_l.append(pd.Series(np.where(ok, -np.sign(mv) * np.log(e / b), np.nan), c.columns, name=day))
    S, L = pd.DataFrame(rows_s), pd.DataFrame(rows_l)
    old = [s.removesuffix("USDT") for s in data.BN_SYMBOLS]
    new = [x for x in c.columns if x not in old]
    old = [x for x in old if x in c.columns]
    print(f"W3 Sunday 12->18 NY fade 24 h | bn100 {c.shape[1]} coins, {len(new)} not in the 82 | {S.index.min():%Y-%m-%d} .. {S.index.max():%Y-%m-%d}")
    for lab, sel in (("all", slice(None)), ("<= 2023", S.index < "2024-01-01"), (">= 2024", S.index >= "2024-01-01")):
        print(f" period {lab}")
        show("NEW coins, SIMPLE (decision sample)", S.loc[sel, new].stack())
        show("NEW coins, log", L.loc[sel, new].stack())
        show("the 82, log (plumbing check vs 11-15)", L.loc[sel, old].stack())
        show("the 82, simple", S.loc[sel, old].stack())
    x = S[new].stack().dropna()
    yrs = x.groupby(x.index.get_level_values(0).year).agg(["count", "mean"])
    print(" NEW coins by year (simple, bp):", ", ".join(f"{y}: {m * 1e4:+.0f} (n={n})" for y, (n, m) in yrs.iterrows()))
    D = pd.DataFrame(rows_d)
    for lab, sgn in (("fade UP moves (short)", 1), ("fade DOWN moves (long)", -1)):
        show("NEW coins, simple, " + lab, S[new].where(D[new] == sgn).stack())


if __name__ == "__main__":
    main()
