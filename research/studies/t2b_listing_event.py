"""T2b(b) (2026-11-12): event study of new perp listings, descriptive (no backtest, nothing registered).
For each listing (first traded day ≥ 30 d after the panel starts), abnormal return = coin − BTC daily simple return,
from day 1 (entry at the close of the first full day, as listing_short skip_days=1) for 120 days. Events need $1M
7-day mean volume at entry (the strategy's min_dv). Reports mean / median CAR, share negative, by cohort half, and
(HL) the funding a short received over the same days (where HL funding history exists)."""
import sys
import numpy as np, pandas as pd
from kripto import data, strategies as S

H = (3, 7, 14, 30, 60, 90, 120)
for ds in ("hl", "bnall"):
    p = data.load_panel(ds, "1d")
    c, v = p["close"], p["volume"]
    r = c.pct_change(fill_method=None)
    ab = r.sub(r["BTC"], axis=0)
    traded = (v.fillna(0) > 0) & c.notna()
    first = traded.idxmax().where(traded.any())
    t_cut = traded.any(axis=1).idxmax() + pd.Timedelta(days=30)
    dv = S.dollar_volume(p)
    rows = []
    for coin, t0 in first.dropna().items():
        if coin == "BTC" or t0 < t_cut:
            continue
        i0 = c.index.get_loc(t0) + 1          # entry at close of day 1
        if i0 + 1 >= len(c) or not (dv[coin].iloc[i0] >= 1e6):
            continue
        path = ab[coin].iloc[i0 + 1: i0 + 1 + max(H)]
        car = np.log1p(path.fillna(0)).cumsum()
        rec = {"coin": coin, "t0": t0, "n": len(path)}
        for h in H:
            rec[h] = car.iloc[h - 1] if len(path) >= h else np.nan
        if "funding" in p and coin in p["funding"]:
            f = p["funding"][coin].iloc[i0 + 1: i0 + 61]
            rec["fund60_short"] = f.sum() if f.notna().mean() > 0.8 else np.nan   # a short RECEIVES positive funding
        rows.append(rec)
    e = pd.DataFrame(rows)
    print(f"\n== {ds}: {len(e)} listing events ({e.t0.min().date()} .. {e.t0.max().date()})")
    for h in H:
        x = e[h].dropna()
        print(f"  day {h:3d}: n={len(x):3d} mean CAR {x.mean():+.1%} median {x.median():+.1%} share<0 {(x < 0).mean():.0%}")
    mid = e.t0.sort_values().iloc[len(e) // 2]
    for name, g in (("early half", e[e.t0 < mid]), ("late half", e[e.t0 >= mid])):
        print(f"  {name}: day30 median {g[30].median():+.1%}  day60 median {g[60].median():+.1%} (n={g[60].notna().sum()})")
    for y, g in e.groupby(e.t0.dt.year):
        print(f"  {y}: n={len(g)} day60 mean {g[60].mean():+.1%} median {g[60].median():+.1%}")
    if "fund60_short" in e:
        f = e["fund60_short"].dropna()
        print(f"  funding to a short over 60 d (events with history: {len(f)}/{len(e)}): mean {f.mean():+.2%} median {f.median():+.2%} "
              f"worst {f.min():+.2%}")
