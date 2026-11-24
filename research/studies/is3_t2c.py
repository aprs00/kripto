"""T2c (daily family): analogs of InSilico's 4 capitulation days (T2a/T2b) on unseen days, vs matched down days.

Explore sample only (2021-2023), BTC/ETH/SOL. Pool = coin-days with ret <= -3 %. Features standardised per coin over the
pool; events = the 15 nearest pool days to each of his 4 BTC days (never within +-5 d of an example); long at the day's
close, gross = simple 3-day return. Baseline = 5 pool days per event, same coin and same ret decile (is3_lib.matched).
Checks: causality (features on data cut at 2022-06-30 == full), null (coin-toss signs per day, 400 copies).

    nice -n 19 .venv/bin/python -m research.studies.is3_t2c    -> research/is3/T2c__explore.json (card)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.studies import is3_lib as L
from research.studies.is3_t2b import EXAMPLES, daily_sym

FEATS = ["ret_z", "range_atr", "qv_z", "n_z", "taker", "avg_trade", "dd5", "dd20", "dd90", "clv", "peak_min", "tsz_min", "tsz_large"]
COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
K, HOLD, LO, HI = 15, 3, "2021-02-01", "2023-12-27"


def pool() -> pd.DataFrame:
    rows = []
    for c in COINS:
        d = daily_sym(c)
        d["fwd"] = d.c.shift(-HOLD) / d.c - 1
        d = d.loc[LO:HI]
        p = d[d.ret <= -0.03].dropna(subset=FEATS + ["fwd"]).copy()
        z = (p[FEATS] - p[FEATS].mean()) / p[FEATS].std()
        p[[f"z_{f}" for f in FEATS]] = z.to_numpy()
        p["coin"], p["time"] = c, p.index
        p["m"] = pd.qcut(p.ret, 10, labels=False, duplicates="drop")
        rows.append(p)
    return pd.concat(rows, ignore_index=True)


def events(P: pd.DataFrame, examples: list[str] = EXAMPLES) -> pd.DataFrame:
    zc = [f"z_{f}" for f in FEATS]
    ex_t = [pd.Timestamp(x, tz="UTC") for x in examples]
    far = np.ones(len(P), bool)
    for t in ex_t:
        far &= (P.time - t).abs().to_numpy() > pd.Timedelta(days=5)
    cand = P[far]
    pick = set()
    for t in ex_t:
        x = P[(P.coin == "BTCUSDT") & (P.time == t)][zc].to_numpy()
        if not len(x):
            raise SystemExit(f"example {t.date()} not in the pool (ret > -3 % on Binance?)")
        dist = np.sqrt(((cand[zc].to_numpy() - x) ** 2).sum(axis=1))
        pick |= set(cand.index[np.argsort(dist)[:K]])
    e = P.loc[sorted(pick)].copy()
    e["side"], e["gross"] = 1, e.fwd
    return e


def causal_ok() -> bool:
    full = daily_sym("BTCUSDT")
    cut = daily_sym("BTCUSDT", end="2022-06-30")
    a, b = full.loc[:"2022-06-29", FEATS], cut.loc[:"2022-06-29", FEATS]
    ok = bool(np.allclose(a.to_numpy(float), b.to_numpy(float), equal_nan=True))
    print("causality check:", "ok" if ok else "FAIL")
    return ok


def main(examples: list[str] = EXAMPLES, name: str = "T2c_analog3d") -> None:
    """T2d reuses this with his stay-out day: python -m research.studies.is3_t2c 2021-09-21"""
    assert causal_ok()
    P = pool()
    e = events(P, examples)
    base = L.matched(e, P.assign(side=1, gross=P.fwd), k=5)
    rng = np.random.default_rng(11)
    nulls = []
    for i in range(400):                     # coin-toss sign per calendar day, same for events and baseline (20 was too few: sd 140 bp)
        days = pd.Index(pd.to_datetime(P.time).dt.floor("D").unique())
        s = pd.Series(rng.choice([-1, 1], len(days)), index=days)
        f = lambda x: x.gross.to_numpy() * s.reindex(pd.to_datetime(x.time).dt.floor("D")).to_numpy()
        nulls.append(f(e).mean() - f(base).mean())
    print(f"null (coin-toss) diff mean {np.mean(nulls)*1e4:+.1f} bp, sd {np.std(nulls)*1e4:.1f} bp")
    print(f"pool {len(P)} coin-days; events {len(e)} ({e.coin.value_counts().to_dict()}); baseline {len(base)}")
    L.card(name, e[["time", "coin", "side", "gross"]], "explore", base[["time", "coin", "side", "gross"]],
           note=f"examples {examples}, k={K}/example, hold {HOLD} d, BTC/ETH/SOL ret<=-3% pool, null diff {np.mean(nulls)*1e4:+.1f} bp")
    # dose: distance rank (nearest 5 vs 6-15) is not available after union; report by coin instead
    print("by coin:", e.groupby("coin").gross.agg(["size", "mean"]).round(4).to_dict())


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        main(sys.argv[1:], "T2d_stayout3d")
    else:
        main()
