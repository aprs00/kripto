"""InSilico pass 3, L3S: backtest slippage model vs the live paper fills' L2 book walks. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_l3s a    # per-fill walk slip vs model, by venue / ADV tier / size -> research/is3/l3s_a.json (+ l3s_fills.parquet in data/is3)
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto import paper as P

OUT = data.DATA / "is3"


def venue(book, coin):
    if coin.endswith("@hl"):
        return "hl", coin[:-3]
    if coin.endswith("@bn"):
        return "bn", coin[:-3]
    if "@bn" in book or book.endswith("main_bn"):
        return "bn", coin
    return "hl", coin


def fills_table():
    s = P.Store()
    f = pd.DataFrame(s.q("select ts, book, coin, size, px, mid, fee, slip_bps, reason from fills"), columns="ts book coin size px mid fee slip reason".split())
    f["ts"] = pd.to_datetime(f["ts"], utc=True, format="mixed")
    f = f[~f.reason.str.startswith("ladder")].copy()
    f["kind"] = np.where(f.reason == "retired", "retired", "rebalance")
    vc = [venue(b, c) for b, c in zip(f.book, f.coin)]
    f["venue"], f["sym"] = [v for v, _ in vc], [c for _, c in vc]
    f["usd"] = f["size"].abs() * f["px"]
    f["walk_bp"] = (f.px - f.mid).abs() / f.mid * 1e4     # recompute from px/mid (slip_bps sign conventions aside)
    f["day"] = f.ts.dt.floor("1D")
    return f


def model_bp(f):
    out = pd.Series(np.nan, f.index)
    adv = pd.Series(np.nan, f.index)
    for v, ds in (("hl", "hl"), ("bn", "bnall")):
        p = data.load_panel(ds, "1d")
        vol = p["volume"]
        cols = {c: c for c in vol.columns}
        if v == "bn":
            cols.update({data.hl_to_bn(c): c for c in vol.columns})
        sm = bt.slippage_model(vol, 1) * 1e4
        dv = vol.rolling(7, min_periods=1).mean()
        m = f.venue == v
        for i in f.index[m]:
            sym = f.at[i, "sym"]
            col = sym if sym in vol.columns else (data.hl_to_bn(sym) if data.hl_to_bn(sym) in vol.columns else None)
            if col is None:
                continue
            d = f.at[i, "day"] - pd.Timedelta(days=1)       # last closed bar before the fill
            if d not in sm.index:
                d = sm.index[sm.index <= d][-1] if (sm.index <= d).any() else None
            if d is None:
                continue
            out[i], adv[i] = sm.at[d, col], dv.at[d, col]
    return out, adv


def summ(g):
    return {"n": int(len(g)), "walk_med": round(float(g.walk_bp.median()), 2), "walk_mean": round(float(g.walk_bp.mean()), 2),
            "walk_p90": round(float(g.walk_bp.quantile(.9)), 2), "model_med": round(float(g.model_bp.median()), 2), "model_mean": round(float(g.model_bp.mean()), 2),
            "ratio_med_model_over_walk": round(float((g.model_bp / g.walk_bp.clip(lower=0.05)).median()), 2),
            "usd_weighted_walk": round(float((g.walk_bp * g.usd).sum() / g.usd.sum()), 2), "usd_weighted_model": round(float((g.model_bp * g.usd).sum() / g.usd.sum()), 2),
            "usd_med": round(float(g.usd.median()), 1)}


def run_a():
    f = fills_table()
    f["model_bp"], f["adv"] = model_bp(f)
    print("fills", len(f), "with model", int(f.model_bp.notna().sum()))
    f = f[f.model_bp.notna()].copy()
    f["tier"] = pd.cut(f.adv, [0, 20e6, 100e6, 1e9, 1e13], labels=["<20M", "20-100M", "100M-1B", ">1B"])
    f["size_b"] = pd.cut(f.usd, [0, 25, 100, 300, 1e9], labels=["<25", "25-100", "100-300", ">300"])
    OUT.mkdir(exist_ok=True)
    f.drop(columns=["ts"]).assign(ts=f.ts.astype(str)).to_parquet(OUT / "l3s_fills.parquet")
    out = {"window": [str(f.ts.min()), str(f.ts.max())], "all": {}, "by_tier": {}, "by_size": {}, "retired": {}}
    for v, g in f.groupby("venue"):
        r = g[g.kind == "rebalance"]
        out["all"][v] = summ(r)
        out["retired"][v] = summ(g[g.kind == "retired"]) if (g.kind == "retired").sum() > 5 else None
        out["by_tier"][v] = {str(t): summ(x) for t, x in r.groupby("tier", observed=True) if len(x) >= 10}
        out["by_size"][v] = {str(t): summ(x) for t, x in r.groupby("size_b", observed=True) if len(x) >= 10}
    print(json.dumps(out, indent=1))
    json.dump(out, open("research/is3/l3s_a.json", "w"), indent=1)




def run_b():
    """log(walk) on log(usd/ADV) per venue, day-block bootstrap of the slope; and the zero-size intercept (half-spread proxy)."""
    f = pd.read_parquet(OUT / "l3s_fills.parquet")
    f = f[(f.kind == "rebalance") & (f.walk_bp > 0.01) & (f.adv > 0)].copy()
    f["x"], f["y"], f["xa"] = np.log(f.usd / f.adv), np.log(f.walk_bp), np.log(f.adv)
    rng = np.random.default_rng(7)
    out = {}
    for v, g in f.groupby("venue"):
        X = np.column_stack([np.ones(len(g)), g.x - g.xa * 0, g.xa])   # walk ~ size share + liquidity separately
        X = np.column_stack([np.ones(len(g)), np.log(g.usd), g.xa])
        beta = np.linalg.lstsq(X, g.y, rcond=None)[0]
        days = g.day.unique()
        bs = []
        for _ in range(300):
            pick = rng.choice(days, len(days))
            idx = np.concatenate([np.flatnonzero(g.day.to_numpy() == d) for d in pick])
            bs.append(np.linalg.lstsq(X[idx], g.y.to_numpy()[idx], rcond=None)[0])
        bs = np.array(bs)
        q = lambda j: [round(float(np.quantile(bs[:, j], .025)), 3), round(float(np.quantile(bs[:, j], .975)), 3)]
        # within-coin size slope: demean by coin
        gd = g.assign(yd=g.y - g.groupby("sym").y.transform("mean"), ud=np.log(g.usd) - g.groupby("sym").usd.transform(lambda s: np.log(s).mean()))
        within = float(np.polyfit(gd.ud, gd.yd, 1)[0])
        out[v] = {"n": int(len(g)), "slope_log_usd": round(float(beta[1]), 3), "ci": q(1), "slope_log_adv": round(float(beta[2]), 3), "ci_adv": q(2),
                  "within_coin_size_slope": round(within, 3),
                  "model_implied_adv_slope": -0.5, "model_implied_size_slope": 0.0}
    print(json.dumps(out, indent=1))
    json.dump(out, open("research/is3/l3s_b.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": run_a, "b": run_b}[sys.argv[1]]()
