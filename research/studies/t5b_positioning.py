"""T5b: Binance positioning metrics (data/bn/metrics_full, 5-min) as cross-sectional daily signals. Descriptive IC study, not registered.

Pre-stated (journal 2026-11-27, before the first run): explore = 2023-03-05..2023-12-31, confirm = 2024-01-01.. (untouched until a form passes explore).
Universe: point-in-time top 60 by 30-d mean quote volume (data.bn_metrics_targets). Decision at the close of daily bar d (00:00 UTC d+1); features from
the last 5-min row of day d (<= 23:55); target = bar d+1 return (1d) and bars d+1..d+3 (3d, scored on every third day only).
F1 retail crowding: all_acct_ls z vs its own previous 30 daily values (expect IC < 0)
F2 top vs retail:   log(top_pos_ls) - log(all_acct_ls) (expect IC > 0)
F3 OI against price: 3-day log OI change x -sign(3-day return) (expect IC > 0)
Each raw and residual (cross-sectional OLS on ranks of funding (last 3 days) and 3-day return). Kill: |mean IC| < 0.02 or t < 2, or halves disagree.

    nice -n 19 .venv/bin/python -m research.studies.t5b_positioning [--confirm]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from kripto import data

OUT = Path(__file__).with_suffix(".json")
EXPLORE = ("2023-03-05", "2023-12-31")
CONFIRM = ("2024-01-01", "2026-12-31")


def daily_metrics(syms, start, end) -> dict[str, pd.DataFrame]:
    cols = ["oi", "top_pos_ls", "all_acct_ls"]
    out = {k: {} for k in cols}
    s0, s1 = pd.Timestamp(start, tz="UTC") - pd.Timedelta(days=40), pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    for sym in syms:
        f = data.METRICS_DIR / f"{sym}.parquet"
        if not f.exists():
            continue
        d = pd.read_parquet(f, columns=["t"] + cols)
        d = d[(d["t"] >= s0) & (d["t"] < s1)]
        if d.empty:
            continue
        d = d.set_index("t").sort_index()
        last = d.groupby(d.index.floor("1D")).last()        # last row of each UTC day (<= 23:55)
        for k in cols:
            out[k][sym.removesuffix("USDT")] = last[k]
    return {k: pd.DataFrame(v) for k, v in out.items()}


def resid(f: pd.Series, ctrl: list[pd.Series]) -> pd.Series:
    df = pd.concat([f] + ctrl, axis=1).dropna()
    if len(df) < 15:
        return pd.Series(dtype=float)
    r = df.rank()
    X = np.column_stack([np.ones(len(r))] + [r.iloc[:, i + 1] for i in range(len(ctrl))])
    b, *_ = np.linalg.lstsq(X, r.iloc[:, 0].to_numpy(), rcond=None)
    return pd.Series(r.iloc[:, 0].to_numpy() - X @ b, index=r.index)


def ic_series(feat: pd.DataFrame, fwd: pd.DataFrame, member: pd.DataFrame, ctrl: list[pd.DataFrame] | None, step: int) -> pd.Series:
    out = {}
    for i, d in enumerate(feat.index):
        if i % step or d not in fwd.index or d not in member.index:
            continue
        m = member.loc[d]
        names = m[m].index
        f = feat.loc[d].reindex(names)
        if ctrl:
            f = resid(f, [c.loc[d].reindex(names) if d in c.index else pd.Series(index=names, dtype=float) for c in ctrl])
        y = fwd.loc[d].reindex(f.index)
        ok = f.notna() & y.notna()
        if ok.sum() >= 15:
            out[d] = f[ok].rank().corr(y[ok].rank())
    return pd.Series(out)


def stats(ic: pd.Series) -> dict:
    ic = ic.dropna()
    if len(ic) < 10:
        return {"n": int(len(ic))}
    h = len(ic) // 2
    t = ic.mean() / (ic.std(ddof=1) / np.sqrt(len(ic)))
    return {"n": int(len(ic)), "mean_ic": round(float(ic.mean()), 4), "t": round(float(t), 2),
            "half1": round(float(ic.iloc[:h].mean()), 4), "half2": round(float(ic.iloc[h:].mean()), 4)}


def main():
    start, end = CONFIRM if "--confirm" in sys.argv else EXPLORE
    p = data.load_bn_all_panel()
    close = p["close"]
    dv = p["volume"].rolling(30, min_periods=7).mean()
    member = (dv.rank(axis=1, ascending=False) <= 60)
    lo, hi = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
    syms = [c + "USDT" for c in member.columns[member.loc[lo:hi].any()]]
    m = daily_metrics(syms, start, end)
    # bar labels: daily bar d opens 00:00 d; the metrics' "day d" last row is at 23:55 of d = just before bar d closes
    ret = close.pct_change(fill_method=None)
    fwd1 = ret.shift(-1)
    fwd3 = (close.shift(-3) / close - 1)
    ret3 = close / close.shift(3) - 1
    fund = p.get("funding")
    fund3 = fund.rolling(3).sum() if fund is not None else None
    coins = [c for c in m["oi"].columns if c in close.columns]
    idx = m["oi"].index.intersection(close.index)
    idx = idx[(idx >= lo) & (idx <= hi)]
    al = m["all_acct_ls"].reindex(columns=coins)
    z = (al - al.rolling(30, min_periods=20).mean().shift(1)) / al.rolling(30, min_periods=20).std().shift(1)
    f2 = np.log(m["top_pos_ls"].reindex(columns=coins)) - np.log(al)
    doi = np.log(m["oi"].reindex(columns=coins)).diff(3)
    f3 = doi * -np.sign(ret3.reindex(index=doi.index, columns=coins))
    feats = {"F1_retail_z": z, "F2_top_minus_retail": f2, "F3_oi_against_price": f3}
    ctrl = [c.reindex(columns=coins) for c in ([fund3] if fund3 is not None else []) + [ret3]]
    res = {"sample": "confirm" if "--confirm" in sys.argv else "explore", "window": [start, end], "coins": len(coins), "days": len(idx)}
    for name, f in feats.items():
        f = f.loc[f.index.isin(idx)]
        for h, fwd, step in (("1d", fwd1, 1), ("3d", fwd3, 3)):
            res[f"{name}|{h}|raw"] = stats(ic_series(f, fwd, member, None, step))
            res[f"{name}|{h}|resid"] = stats(ic_series(f, fwd, member, ctrl, step))
    print(json.dumps(res, indent=1))
    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    old[res["sample"]] = res
    OUT.write_text(json.dumps(old, indent=1))


if __name__ == "__main__":
    main()
