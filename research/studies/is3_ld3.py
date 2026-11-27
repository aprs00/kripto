"""InSilico pass 3, LD3: ladder fills in liquidity holes vs heavy-volume flushes (library N14). Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_ld3 build      # features per LD1 candidate minute -> data/is3/ld3_feat.parquet
  nice -n 19 .venv/bin/python -m research.studies.is3_ld3 explore    # forms a, b on 2021-01-01 .. 2023-12-31 -> data/is3/ld3_explore.json

Pre-registration: research/is3/notes.md "LD3". Fill model = LD1 one-bar-late k30 rule (entry at the quote p = cp (1 - 30 sp)).
Fill-minute features are known only at the close of the fill minute t: the live-relevant return is c[t+1] -> exit.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from research.studies import is3_ladtop as T
from research.studies import ld1_ladder_skew as L

OUT = L.OUT
H = (1, 2, 5, 61, 62, 65, 241, 1441)


def series_full(coin, lo, hi):
    """Like is3_ladtop.series but keeps n and tbqv (trade count, taker-buy quote volume)."""
    dfs = []
    for d in T.DIRS:
        f = d / f"{coin}USDT.parquet"
        if f.exists():
            x = pd.read_parquet(f, columns=["t", "h", "l", "c", "qv", "n", "tbqv"])
            x.index = pd.to_datetime(x["t"].where(x["t"] < 1e14, x["t"] // 1000), unit="ms", utc=True)
            dfs.append(x.drop(columns="t"))
    if not dfs:
        return None
    x = pd.concat(dfs)
    x = x[~x.index.duplicated()].sort_index()
    x = x[(x.index >= lo - pd.Timedelta("32D")) & (x.index < hi + pd.Timedelta("2D"))].astype(float)
    ix = pd.date_range(x.index[0], x.index[-1] + pd.Timedelta("1500min"), freq="1min")
    c = x["c"].reindex(ix).ffill()
    return pd.DataFrame({"l": x["l"].reindex(ix).fillna(c), "c": c, "qv": x["qv"].reindex(ix).fillna(0.0),
                         "n": x["n"].reindex(ix).fillna(0.0), "tbqv": x["tbqv"].reindex(ix).fillna(0.0)})


def feat_one(coin, times):
    x = series_full(coin, times.min(), times.max())
    if x is None:
        return None
    c, qv, n = x["c"], x["qv"], x["n"]
    r = np.log(c).diff().abs()
    ami = (r / qv.where(qv > 0)).where(r > 0)
    # trailing 30-d medians from daily medians, lagged one day (causal)
    def norm(s):
        d = s.groupby(s.index.floor("D")).median()
        return d.rolling(30, min_periods=15).median().shift(1)
    ami_n, qv_n, n_n = norm(ami), norm(qv.where(qv > 0)), norm(n.where(n > 0))
    pos = x.index.get_indexer(times)
    assert (pos >= 1).all() and (pos >= 0).all()
    day = times.floor("D")
    lt, cprev, qt = x["l"].to_numpy()[pos], c.to_numpy()[pos - 1], qv.to_numpy()[pos]
    out = pd.DataFrame({"time": times, "coin": coin,
                        "ami": np.abs(np.log(lt / cprev)) / np.where(qt > 0, qt, np.nan),
                        "qv": qt, "n": n.to_numpy()[pos], "sell": 1 - x["tbqv"].to_numpy()[pos] / np.where(qt > 0, qt, np.nan),
                        "ami_n": ami_n.reindex(day).to_numpy(), "qv_n": qv_n.reindex(day).to_numpy(), "n_n": n_n.reindex(day).to_numpy()})
    for h in H:
        out[f"c{h}"] = c.to_numpy()[pos + h]
    return out


def build():
    t = pd.read_parquet(OUT / "ld1_cand.parquet")
    parts = []
    for coin, g in t.groupby("coin"):
        f = feat_one(coin, pd.DatetimeIndex(g.time))
        if f is not None:
            parts.append(f)
    f = pd.concat(parts)
    m = t.merge(f, on=["time", "coin"], how="left", suffixes=("", "_re"))
    assert len(m) == len(t)
    ok = np.isclose(m.c61, m.c61_re, rtol=1e-9)
    print("c61 reconstruction matches LD1:", round(float(ok.mean()), 4), flush=True)
    assert ok.mean() > 0.99
    m.to_parquet(OUT / "ld3_feat.parquet")
    print(len(m), "rows; missing ami_n", int(m.ami_n.isna().sum()), flush=True)


LO, SPLIT = L.LO, L.SPLIT


def events(lo, hi):
    """LD1 candidates with the k30 band rule and a 60-min per-coin lock (no slot rule): every fill the ladder could take."""
    t = pd.read_parquet(OUT / "ld3_feat.parquet").sort_values(["time", "rank"])
    t = t[(t.time >= lo) & (t.time < hi) & (L.K * t.sp <= t.band)]
    keep, last = [], {}
    for i, tm, c in zip(t.index, t.time, t.coin):
        if c in last and tm <= last[c] + pd.Timedelta(minutes=L.HOLD):
            continue
        last[c] = tm
        keep.append(i)
    e = t.loc[keep].copy()
    e["p"] = e.cp * (1 - L.K * e.sp)
    e["cost"] = L.COST + e.slip
    for h in (61, 241, 1441):
        e[f"q{h}"] = e[f"c{h}"] / e.p - 1 - e.cost          # from our quote, net of the ladder's cost
    e["r1_61"] = e.c61 / e.c1 - 1                            # live-relevant: after the fill minute closed (gross)
    e["r1_1441"] = e.c1441 / e.c1 - 1
    e["illiq"] = e.ami / e.ami_n
    e["relvol"] = e.qv / e.qv_n
    e["reln"] = e.n / e.n_n
    e["avgtr"] = e.qv / e.n.where(e.n > 0)                   # mean trade size in the fill minute
    e["kt"] = pd.qcut(e.kreach, 3, labels=False)
    e["multi"] = e.groupby("time").coin.transform("size") > 1
    e["side"] = 1
    return e.dropna(subset=["illiq"]).reset_index(drop=True)


def split_card(e, col, name, ret="r1_61", hi_is_hole=True, sample="explore"):
    from research.studies import is3_lib as IL
    med = e[col].median()
    a, b = (e[e[col] > med], e[e[col] <= med]) if hi_is_hole else (e[e[col] <= med], e[e[col] > med])
    A, B = a.assign(gross=a[ret]), b.assign(gross=b[ret])
    c = IL.card(f"LD3_{name}_{ret}", A, sample, base=B, note=f"{col} {'top' if hi_is_hole else 'bottom'} half vs other half, thr {med:.4g}")
    q = pd.qcut(e[col], 5, labels=False)
    qm = e.groupby(q)[ret].mean() * 1e4
    qmed = e.groupby(q)[ret].median() * 1e4
    rc = float(pd.Series(qm.values).corr(pd.Series(range(5)), method="spearman")) * (1 if hi_is_hole else -1)
    yrs = {int(y): round(float(g[g[col] > med][ret].mean() - g[g[col] <= med][ret].mean()) * 1e4 * (1 if hi_is_hole else -1), 1) for y, g in e.groupby(e.time.dt.year)}
    kts = {int(k): round(float(g[g[col] > g[col].median()][ret].mean() - g[g[col] <= g[col].median()][ret].mean()) * 1e4 * (1 if hi_is_hole else -1), 1) for k, g in e.groupby("kt")}
    print(f"  quintiles mean {qm.round(1).tolist()} median {qmed.round(1).tolist()} rank-corr {rc:+.2f} | diff by year {yrs} | by kreach tercile {kts}", flush=True)
    ok = (c.get("vs_base_bp", -1) >= 13 and c.get("p_vs_base", 1) < 0.05 and all(v > 0 for v in yrs.values())
          and sum(v > 0 for v in kts.values()) >= 2 and rc >= 0.6)
    return {"card": {k: c.get(k) for k in ("n", "mean_bp", "median_bp", "base_bp", "vs_base_bp", "p_vs_base", "mde80_bp", "by_year")},
            "q_mean_bp": qm.round(2).tolist(), "q_median_bp": qmed.round(2).tolist(), "rankcorr": round(rc, 2), "diff_by_year": yrs, "diff_by_kt": kts, "pass": ok}


def explore():
    e = events(LO, SPLIT)
    print(len(e), "events,", e.coin.nunique(), "coins, multi-coin minutes", round(float(e.multi.mean()), 2), flush=True)
    print(e[["illiq", "relvol", "reln", "sell", "kreach", "avgtr"]].corr(method="spearman").round(2).to_string(), flush=True)
    # hand check of one event
    x = e.iloc[len(e) // 2]
    print("hand check", x.time, x.coin, "cp", x.cp, "sp", round(x.sp, 5), "p", round(x.p, 6), "c1", x.c1, "c61", x.c61, "illiq", round(x.illiq, 2), "relvol", round(x.relvol, 1), flush=True)
    out = {"n": len(e)}
    for ret in ("r1_61", "q61", "q241", "q1441", "r1_1441"):
        out[f"a_{ret}"] = split_card(e, "illiq", "a_illiq", ret)
    out["b_relvol"] = split_card(e, "relvol", "b_relvol", "r1_61", hi_is_hole=False)
    out["b_reln"] = split_card(e, "reln", "b_reln", "r1_61", hi_is_hole=False)
    out["b_sell"] = split_card(e, "sell", "b_sell", "r1_61", hi_is_hole=False)
    out["b_avgtr"] = split_card(e, "avgtr", "b_avgtr", "r1_61", hi_is_hole=False)
    # placebo: random halves (100 draws) of the diff in r1_61
    rng = np.random.default_rng(5)
    pl = [float(e.r1_61[m].mean() - e.r1_61[~m].mean()) * 1e4 for m in (rng.random(len(e)) < 0.5 for _ in range(100))]
    out["placebo_random_half_bp"] = [round(float(np.quantile(pl, q)), 1) for q in (0.05, 0.5, 0.95)]
    out["multi_split"] = {str(k): [int(len(g)), round(float(g.r1_61.mean()) * 1e4, 1), round(float(g.illiq.median()), 2)] for k, g in e.groupby("multi")}
    print("placebo random-half diff 5/50/95%", out["placebo_random_half_bp"], "| multi-coin minute split [n, r1_61 bp, median illiq]", out["multi_split"], flush=True)
    (OUT / "ld3_explore.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"build": build, "explore": explore}[a[0]]()
