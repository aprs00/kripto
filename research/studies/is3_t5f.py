"""T5f: effort without result (tg:173 / wa 18.10.24(2)). Among 1-min bars with volume >= 10x the 24-h median (shift 1) at a 60-min
low after a 60-min decline (mirror: 60-min high after a rise, short), the return in the FADE direction as a function of
rr = bar range / 24-h median range (small rr = much effort, little result = his absorption bar).
Variants: plain (entry at the close of q+1, one bar late) and his confirmation (q+1 opposite colour with volume < 0.5x the
effort bar; entry at the close of q+2). Horizons 15 / 60 / 240 min, simple returns. One event per coin per 30 min.
Baseline = same coin, same vm bin, rr in the top half (high effort WITH result), is3_lib.matched.

    nice -n 19 .venv/bin/python -m research.studies.is3_t5f build | curves | checks
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "data/is3/t5f.parquet"
OUT = ROOT / "research/is3/T5f__curves.json"
VM = 10.0


def panel(coins, lo: str, hi: str) -> dict:
    cols = {}
    for c in coins:
        k = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{c}USDT.parquet")
        k.index = pd.to_datetime(k.t, unit="ms", utc=True)
        k = k[(k.index >= pd.Timestamp(lo, tz="UTC") - pd.Timedelta("2D")) & (k.index < pd.Timestamp(hi, tz="UTC") + pd.Timedelta("1D"))]
        cols[c] = k.asfreq("1min")
    f = lambda col: pd.DataFrame({c: k[col] for c, k in cols.items()}).astype("float64")
    return {"close": f("c"), "high": f("h"), "low": f("l"), "volume": f("qv"), "tb": f("tbqv")}


def events(p: dict, lo: str | None = None, hi: str | None = None) -> pd.DataFrame:
    out = []
    idx = p["close"].index
    for coin in p["close"].columns:
        c = p["close"][coin].ffill().to_numpy()
        h = p["high"][coin].fillna(p["close"][coin].ffill()).to_numpy()
        l = p["low"][coin].fillna(p["close"][coin].ffill()).to_numpy()
        v = p["volume"][coin].fillna(0).to_numpy()
        rg = (h - l) / c
        vmed = pd.Series(v).rolling(1440, min_periods=720).median().shift(1).to_numpy()
        rmed = pd.Series(rg).rolling(1440, min_periods=720).median().shift(1).to_numpy()
        lmin = pd.Series(l).rolling(60).min().shift(1).to_numpy()
        hmax = pd.Series(h).rolling(60).max().shift(1).to_numpy()
        prior = np.full(len(c), np.nan)
        prior[61:] = c[60:-1] / c[:-61] - 1          # return over the 60 min before bar q (c[q-1] / c[q-61])
        with np.errstate(invalid="ignore", divide="ignore"):
            vm = v / vmed
            rr = rg / rmed
        n = len(c)
        dn = (vm >= VM) & (l <= lmin) & (prior < 0)
        up = (vm >= VM) & (h >= hmax) & (prior > 0)
        cand = np.flatnonzero((dn | up) & np.isfinite(rr) & (np.arange(n) + 243 < n))
        last = -10**9
        for q in cand:
            if q - last < 30:
                continue
            last = q
            s = 1 if dn[q] else -1                    # fade side: long after a down effort bar
            conf = bool((s * (c[q + 1] - c[q]) > 0) and v[q + 1] < 0.5 * v[q])
            row = {"time": idx[q + 1], "coin": coin, "side": s, "vm": vm[q], "rr": rr[q], "conf": conf,
                   "body": s * (c[q] / c[q - 1] - 1) / rmed[q] if rmed[q] > 0 else np.nan}
            for H in (15, 60, 240):
                row[f"f{H}"] = s * (c[q + 1 + H] / c[q + 1] - 1)        # plain, entry close q+1
                row[f"g{H}"] = s * (c[q + 2 + H] / c[q + 2] - 1)        # confirmed, entry close q+2
            row["gross"] = row["f60"]
            out.append(row)
    e = pd.DataFrame(out)
    if len(e) and lo:
        e = e[(e.time >= pd.Timestamp(lo, tz="UTC")) & (e.time < pd.Timestamp(hi, tz="UTC"))]
    return e.reset_index(drop=True) if len(e) else pd.DataFrame(columns=["time", "coin", "side", "gross"])


def build(coins=None, lo: str = "2021-01-01", hi: str = "2024-01-01", out: Path = TAB) -> pd.DataFrame:
    e = pd.concat([events(panel([c], lo, hi), lo, hi) for c in (coins or L.COINS10)], ignore_index=True)
    e["vb"] = pd.qcut(e.vm.rank(method="first"), 4, labels=False)
    e.to_parquet(out)
    print(len(e), e.groupby(["side"]).size().to_dict(), "conf share", round(e.conf.mean(), 3))
    return e


def _s(g: pd.DataFrame, col: str, base: pd.DataFrame | None = None, reps: int = 400) -> dict:
    x = g.assign(gross=g[col])[["time", "coin", "side", "gross"]]
    b = base.assign(gross=base[col])[["time", "coin", "side", "gross"]] if base is not None else None
    return L.stats(x, b, reps=reps)


def curves() -> None:
    e = pd.read_parquet(TAB)
    res = {"n": int(len(e))}
    for side, sname in ((1, "long_at_low"), (-1, "short_at_high")):
        x = e[e.side == side]
        x = x.assign(b=pd.qcut(x.rr.rank(method="first"), 10, labels=False))
        res[sname] = {}
        for col in ("f15", "f60", "f240"):
            cv = []
            for b, g in x.groupby("b"):
                s = _s(g, col)
                cv.append({"b": int(b), "rr_lo": round(float(g.rr.min()), 2), "rr_hi": round(float(g.rr.max()), 2), "n": s["n"], "mean_bp": s["mean_bp"], "ci95_bp": s["ci95_bp"]})
            means = [c["mean_bp"] for c in cv]
            rho = float(pd.Series(means).corr(pd.Series(range(10)), method="spearman"))
            res[sname][col] = {"curve": cv, "spearman": rho}
            print(f"{sname:14s} {col} n={len(x)} rho {rho:+.2f} | " + " ".join(f"{m:+.0f}" for m in means))
        # small rr (his bar) vs high-effort-with-result baseline, plain and confirmed
        lo_rr = x[x.b <= 1].assign(m=lambda d: d.vb)
        pool = x[x.b >= 5].assign(m=lambda d: d.vb)
        base = L.matched(lo_rr, pool, k=3)
        for col in ("f60", "g60", "f240", "g240"):
            ev = lo_rr if col[0] == "f" else lo_rr[lo_rr.conf]
            s = _s(ev, col, base, reps=1000)
            res[sname][f"lowrr_vs_base_{col}"] = {k: s[k] for k in ("n", "mean_bp", "ci95_bp", "p", "mde80_bp", "base_bp", "vs_base_bp", "p_vs_base") if k in s}
            print(f"  low-rr {'conf' if col[0]=='g' else 'plain'} {col}: n={s['n']} {s['mean_bp']:+.1f} vs base {s.get('base_bp')} p_vs {s.get('p_vs_base')} mde {s['mde80_bp']}")
        c2 = x.groupby("conf")
        for k, g in c2:
            s = _s(g, "g60" if k else "f60")
            res[sname][f"conf_{k}"] = {"n": s["n"], "mean_bp": s["mean_bp"], "ci95_bp": s["ci95_bp"]}
            print(f"  confirmation={k}: n={s['n']} 60-min {s['mean_bp']:+.1f} {s['ci95_bp']}")
    OUT.write_text(json.dumps(res, indent=1, default=float))


def checks() -> None:
    p = panel(["BTC", "SOL"], "2022-01-01", "2022-07-01")
    fn = lambda q: events(q)
    res = {"null": L.null_check(fn, p, n=20), "causal": L.check_causal(fn, p, "2022-04-01")}
    (ROOT / "research/is3/T5f__checks.json").write_text(json.dumps(res, default=float))


if __name__ == "__main__":
    {"build": build, "curves": curves, "checks": checks}[sys.argv[1]]()
