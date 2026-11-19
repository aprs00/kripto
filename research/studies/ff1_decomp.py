"""FF1 decomposition (2026-11-19): friday_follow on bn100 1h, the WF-chosen config. Where does the P&L come from?
Per-event (per Friday) gross P&L, split into the hand-picked 82 (data.BN_SYMBOLS) vs the other coins, long vs short legs, by year;
event-clustered t, top-3-event share, result without the top 3. Gross of costs (costs ≈ 5.6%/yr come on top, see the WF result).

  nice -n 19 .venv/bin/python -m research.studies.ff1_decomp
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from kripto import data, strategies as st

PARAMS = {"thr": 0.04, "top_n": 80, "hold_h": 24, "cuts": [12, 15, 17, 20]}


def main():
    p = data.load_panel("bn100", "1h")
    c = p["close"]
    W = st.REGISTRY["friday_follow"](p, **PARAMS).to_numpy()
    C = c.to_numpy()
    old = set(s.removesuffix("USDT") for s in data.BN_SYMBOLS)
    is_old = np.array([x in old for x in c.columns])
    week = (c.index - pd.Timedelta(days=4)).floor("7D")       # buckets that hold one Friday each
    parts = {k: np.zeros(len(c)) for k in ("old_long", "old_short", "new_long", "new_short")}
    for t in range(1, len(c)):
        w = W[t - 1]
        if not w.any():
            continue
        r = C[t].astype(float) / C[t - 1].astype(float) - 1.0
        r[~np.isfinite(r)] = 0.0
        for grp, m in (("old", is_old), ("new", ~is_old)):
            parts[f"{grp}_long"][t] = float((np.clip(w, 0, None) * r)[m].sum())
            parts[f"{grp}_short"][t] = float((np.clip(w, None, 0) * r)[m].sum())
    df = pd.DataFrame(parts, c.index).groupby(week).sum()
    df = df[(df != 0).any(axis=1)]
    df["total"] = df.sum(axis=1)
    n = len(df)
    tot = df["total"]
    top3 = tot.nlargest(3)
    print(f"friday_follow bn100 {PARAMS}: {n} event weeks, gross per week mean {tot.mean() * 1e4:+.1f} bp, median {tot.median() * 1e4:+.1f} bp, "
          f"t {tot.mean() / tot.std() * np.sqrt(n):+.2f}, hit {(tot > 0).mean():.0%}")
    print(f"  top-3 weeks {', '.join(f'{d:%Y-%m-%d} {v * 1e4:+.0f} bp' for d, v in top3.items())} = {top3.sum() / tot.sum():.0%} of the sum; "
          f"without them mean {tot.drop(top3.index).mean() * 1e4:+.1f} bp (t {tot.drop(top3.index).mean() / tot.drop(top3.index).std() * np.sqrt(n - 3):+.2f})")
    print("  legs, sum over all weeks (fraction of equity): " + ", ".join(f"{k} {df[k].sum():+.2f}" for k in parts))
    y = df.groupby(df.index.year).agg(["sum"])
    y.columns = [a for a, _ in y.columns]
    print("  by year (sum of weekly gross, fraction of equity):")
    print(y.round(3).to_string())
    for lab, sel in (("2020-23", df.index < "2024-01-01"), ("2024-26", df.index >= "2024-01-01")):
        x = df.loc[sel, "total"]
        print(f"  {lab}: {len(x)} weeks, mean {x.mean() * 1e4:+.1f} bp, t {x.mean() / x.std() * np.sqrt(len(x)):+.2f}; "
              f"the 82: {df.loc[sel, ['old_long', 'old_short']].sum(axis=1).mean() * 1e4:+.1f} bp, others: "
              f"{df.loc[sel, ['new_long', 'new_short']].sum(axis=1).mean() * 1e4:+.1f} bp")


if __name__ == "__main__":
    main()
