"""T5d: relative version of T5a. For every non-BTC T5a event (explore COINS10 2021-23): beta = 24-h rolling beta of the
coin's 1-min returns on BTC's (shift 1); idio = 1 - beta * r_btc / r_coin in the move minute (1 = all own move, 0 = all BTC);
outcome = BTC-hedged fade: f60 - beta * side * BTC 60-min return over the same window (decision one bar late, as T5a).
Dose: deciles of idio. Card: top idio decile vs matched T5a events (same coin, same z decile), hedged.

    nice -n 19 .venv/bin/python -m research.studies.is3_t5d     -> research/is3/T5d__relative.json + card
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research/is3/T5d__relative.json"


def rets(coin: str) -> pd.Series:
    k = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet", columns=["t", "c"])
    k.index = pd.to_datetime(k.t, unit="ms", utc=True)
    k = k[(k.index >= "2020-12-20") & (k.index < "2024-01-02")].asfreq("1min")
    return k.c.ffill()


def main() -> None:
    e = pd.read_parquet(ROOT / "data/is3/t5a.parquet")
    e = e[e.coin != "BTC"].copy()
    bc = rets("BTC")
    rb = np.log(bc).diff()
    out = []
    for coin, g in e.groupby("coin"):
        cc = rets(coin)
        rc = np.log(cc).diff().reindex(rb.index)
        beta = (rc.rolling(1440, min_periods=720).cov(rb) / rb.rolling(1440, min_periods=720).var()).shift(1)
        q = g.time - pd.Timedelta(minutes=1)                     # move minute
        b = beta.reindex(q).to_numpy()
        rq_c, rq_b = rc.reindex(q).to_numpy(), rb.reindex(q).to_numpy()
        p_b, f_b = bc.reindex(g.time).to_numpy(), bc.reindex(g.time + pd.Timedelta(minutes=60)).to_numpy()
        g = g.assign(beta=b, idio=1 - b * rq_b / rq_c, hedged=g.f60 - b * g.side * (f_b / p_b - 1))
        out.append(g)
    e = pd.concat(out).replace([np.inf, -np.inf], np.nan).dropna(subset=["idio", "hedged"])
    e["m"] = e.groupby("coin").z.transform(lambda x: pd.qcut(x.rank(method="first"), 10, labels=False))
    x = e.assign(b=pd.qcut(e.idio.rank(method="first"), 10, labels=False))
    cv = []
    for b, gg in x.groupby("b"):
        s = L.stats(gg.assign(gross=gg.hedged)[["time", "coin", "side", "gross"]], reps=300)
        cv.append({"b": int(b), "lo": round(float(gg.idio.min()), 2), "hi": round(float(gg.idio.max()), 2), "n": s["n"], "mean_bp": s["mean_bp"], "ci95_bp": s["ci95_bp"]})
    print(f"n {len(e)}; hedged fade all {e.hedged.mean()*1e4:+.1f} bp; by idio decile: " + " | ".join(f"{c['lo']:+.2f}..{c['hi']:+.2f} {c['mean_bp']:+.1f} [{c['ci95_bp'][0]:+.0f},{c['ci95_bp'][1]:+.0f}]" for c in cv))
    top = x[x.b == 9].assign(gross=lambda d: d.hedged)
    pool = x[x.b < 9].assign(gross=lambda d: d.hedged)
    cols = ["time", "coin", "side", "gross"]
    card = L.card("T5d_idio_top_h60", top[cols], "explore", L.matched(top, pool, k=3)[cols], note="most idiosyncratic decile of 1-min >= 3 sigma moves, BTC-hedged 60-min fade")
    OUT.write_text(json.dumps({"n": int(len(e)), "curve": cv, "card": {k: card.get(k) for k in ("n", "mean_bp", "p", "vs_base_bp", "p_vs_base", "mde80_bp", "passes")}}, indent=1, default=float))


if __name__ == "__main__":
    main()
