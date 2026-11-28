"""InSilico pass 3, T9D: would post-only orders fill PRB2's slow-leg daily gaps? Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_t9d a|b|c     # -> data/is3/t9d_<form>.json

Legs: is3_prl.legs on BN-82 1d (HL main book's legs, built on Binance where 1h history is long), slow legs tsmom + lowvol at lam .33 (PRB2).
Order at decision D = daily bar open + 1 d (bt.run trades w[t] at close[t]): dw = slow[t] - slow[t-1] per coin (per leg and netted 'net').
Resting post-only limit at L = close[t] * (1 -/+ off) (buy -/sell +). Filled within h hours only if a 1h bar opening in [D, D+h) TRADES THROUGH L
(buy: low < L; sell: high > L). No queue credit, no partial fills. Weight = |dw| (fraction of book).
Samples: explore = decisions in 2021-2023 (form a/b/c); confirm 2024-26 only if c saves >= 1 %/yr (not run here).
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data
from research.studies.is3_prb import partial
from research.studies.is3_prl import legs

OUT = data.DATA / "is3"
EV = data.DATA.parent / "research" / "is3"   # evidence JSONs (tracked)
HS = (1, 4, 24)
OFFS = (0.0, 2e-4)
LAM = 0.33


def orders(start="2021-01-01", end="2024-01-01"):
    d = data.load_panel("bn", "1d")
    fin, _, err = legs(d)
    assert err < 1e-9, err
    slow = {n: partial(fin[n], LAM) for n in ("tsmom", "lowvol")}
    slow["net"] = slow["tsmom"] + slow["lowvol"]
    out = {}
    for n, w in slow.items():
        dw = w.diff().fillna(0.0)
        s = dw.stack()
        s = s[s.abs() > 1e-6]
        df = s.rename("dw").reset_index()
        df.columns = ["t", "coin", "dw"]
        df["D"] = df["t"] + pd.Timedelta(days=1)
        df = df[(df["D"] >= start) & (df["D"] < end)]
        df["L0"] = [d["close"].at[t, c] for t, c in zip(df["t"], df["coin"])]
        out[n] = df.reset_index(drop=True)
    return out, d


def fills(df, h1):
    """flags fill_<off>_<h>, plus signed returns from L0 to the close at D+24h and D+48h."""
    hi, lo, cl = h1["high"], h1["low"], h1["close"]
    idx = hi.index
    pos = idx.get_indexer(df["D"])
    assert (pos >= 0).all()
    ci = hi.columns.get_indexer(df["coin"])
    H, Lo, C = hi.to_numpy(), lo.to_numpy(), cl.to_numpy()
    side = np.sign(df["dw"].to_numpy())
    L0 = df["L0"].to_numpy()
    # known answer: the 1h close of the bar before D equals the daily close used as L0
    prev_close = C[pos - 1, ci]
    agree = float(np.nanmax(np.abs(prev_close / L0 - 1)))
    res = {}
    for off in OFFS:
        L = L0 * (1 - side * off)
        first = np.full(len(df), np.inf)
        for k in range(24):
            hk, lk = H[pos + k, ci], Lo[pos + k, ci]
            hit = np.where(side > 0, lk < L, hk > L)
            first = np.where(hit & ~np.isfinite(first), k + 1, first)
        for h in HS:
            res[f"f{int(off*1e4)}_{h}"] = first <= h
        res[f"first{int(off*1e4)}"] = first
    for hh in (24, 48):
        p = C[np.minimum(pos + hh - 1, len(C) - 1), ci]
        res[f"r{hh}"] = side * (p / L0 - 1)
    return pd.DataFrame(res, index=df.index), agree


def form_a():
    od, _ = orders()
    h1 = data.load_panel("bn", "1h")
    out = {}
    for n, df in od.items():
        f, agree = fills(df, h1)
        df = pd.concat([df, f], axis=1)
        df.to_parquet(OUT / f"t9d_orders_{n}.parquet")
        w = df["dw"].abs()
        row = {"n_orders": int(len(df)), "turnover_ann": float(w.sum() / 3), "L0_vs_1h_close_maxdiff": agree}
        for side, m in (("all", slice(None)), ("buy", df["dw"] > 0), ("sell", df["dw"] < 0)):
            sub, ww = df[m], w[m]
            row[side] = {k: round(float((ww * sub[k]).sum() / ww.sum()), 3) for k in f.columns if k.startswith("f")}
        row["by_year_f0_24"] = {int(y): round(float((w[g.index] * g["f0_24"]).sum() / w[g.index].sum()), 3)
                                for y, g in df.groupby(df["D"].dt.year)}
        out[n] = row
        print(n, json.dumps(row), flush=True)
    json.dump(out, open(EV / "t9d_a.json", "w"), indent=1)


QS = (0, 5, 10, 20)          # queue stress: a fill needs a trade-through of q bp beyond the limit
TAKER, MAKER = 5e-4, 2e-4    # Binance VIP0


def first_hit(df, h1, q):
    hi, lo = h1["high"].to_numpy(), h1["low"].to_numpy()
    pos = h1["high"].index.get_indexer(df["D"]); ci = h1["high"].columns.get_indexer(df["coin"])
    side = np.sign(df["dw"].to_numpy()); L = df["L0"].to_numpy() * (1 - side * q * 1e-4)
    first = np.full(len(df), np.inf)
    for k in range(24):
        hit = np.where(side > 0, lo[pos + k, ci] < L, hi[pos + k, ci] > L)
        first = np.where(hit & ~np.isfinite(first), k + 1, first)
    return first


def dayboot(v, w, day, reps=2000, seed=7):
    g = pd.DataFrame({"vw": v * w, "w": w, "d": day}).groupby("d")[["vw", "w"]].sum()
    a, b = g["vw"].to_numpy(), g["w"].to_numpy()
    rng = np.random.default_rng(seed); i = rng.integers(0, len(a), (reps, len(a)))
    bs = a[i].sum(1) / b[i].sum(1)
    return float(a.sum() / b.sum()), [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))]


def form_b():
    from kripto import backtest as bt
    d = data.load_panel("bn", "1d")
    slip = bt.slippage_model(d["volume"], 1)
    h1 = data.load_panel("bn", "1h")
    out = {}
    for n in ("net", "tsmom", "lowvol"):
        df = pd.read_parquet(OUT / f"t9d_orders_{n}.parquet")
        df = df[np.isfinite(df["r24"])]
        w = df["dw"].abs().to_numpy()
        sl = np.array([slip.at[t, c] for t, c in zip(df["t"], df["coin"])])
        sl = np.where(np.isfinite(sl), sl, 25e-4)
        r24 = df["r24"].to_numpy(); day = df["D"].dt.normalize().to_numpy()
        row = {"slip_bp_wmean": round(float((w * sl).sum() / w.sum() * 1e4), 2),
               "r24_all_bp": round(float((w * r24).sum() / w.sum() * 1e4), 1)}
        for q in QS:
            fh = first_hit(df, h1, q)
            f = fh <= 24
            m_f, ci_f = dayboot(r24[f], w[f], day[f])
            m_u, ci_u = dayboot(r24[~f], w[~f], day[~f]) if (~f).sum() > 30 else (float("nan"), None)
            save = np.where(f, TAKER + sl - MAKER, -r24)        # chase unfilled at D+24h as taker
            s_m, s_ci = dayboot(save, w, day)
            yr = {int(y): round(float((w[m] * save[m]).sum() / w[m].sum() * 1e4), 2)
                  for y in (2021, 2022, 2023) for m in [pd.DatetimeIndex(df["D"]).year == y]}
            row[f"q{q}"] = {"fill24": round(float(w[f].sum() / w.sum()), 3), "fill1h": round(float(w[fh <= 1].sum() / w.sum()), 3),
                            "r24_filled_bp": round(m_f * 1e4, 1), "r24_unfilled_bp": round(m_u * 1e4, 1),
                            "r24_unfilled_ci_bp": None if ci_u is None else [round(x * 1e4, 1) for x in ci_u],
                            "save_bp_per_unit": round(s_m * 1e4, 2), "save_ci_bp": [round(x * 1e4, 2) for x in s_ci],
                            "save_pct_yr": round(s_m * w.sum() / 3 * 100, 2), "save_bp_by_year": yr}
        out[n] = row
        print(n, json.dumps(row), flush=True)
    json.dump(out, open(EV / "t9d_b.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": form_a, "b": form_b}[sys.argv[1]]()
