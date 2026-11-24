"""M0a/b: inventory and reconciliation of the micro move bars (data/bn/mbars) against Binance 1-min klines, per day:
quote volume, taker-buy share, day high and low (relative differences), bars per day by year, share of bars completing in < 1 s.

    nice -n 19 .venv/bin/python -m research.studies.is3_m0b [SYM ...]   -> research/is3/M0b__reconcile.json + research/is3/mbars_bad_days.json (load it in every M-form)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research/is3/M0b__reconcile.json"


def one(sym: str) -> tuple[pd.DataFrame, dict]:
    k = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{sym}.parquet")
    k["d"] = pd.to_datetime(k.t, unit="ms", utc=True).dt.strftime("%Y-%m-%d")
    kd = k.groupby("d").agg(qv=("qv", "sum"), tb=("tbqv", "sum"), h=("h", "max"), l=("l", "min"), mins=("t", "size"))
    rows = []
    for f in sorted((ROOT / "data/bn/mbars" / sym).glob("*.npz")):
        z = np.load(f)
        v = float(z["buy"].sum() + z["sell"].sum())
        rows.append({"d": f.stem, "bars": int(len(z["c"])), "mv": v, "mb": float(z["buy"].sum()), "mh": float(z["h"].max()), "ml": float(z["l"].min()),
                     "fast": float(((z["t1"] - z["t0"]) < 1000).mean()), "trades": int(z["n"].sum())})
    m = pd.DataFrame(rows).set_index("d").join(kd, how="left")
    m["dv"] = m.mv / m.qv - 1
    m["dtk"] = m.mb / m.mv - m.tb / m.qv
    m["dh"] = m.mh / m.h - 1
    m["dl"] = m.ml / m.l - 1
    bad = m[(m.dv.abs() > 1e-3) | (m.dh.abs() > 1e-3) | (m.dl.abs() > 1e-3) | (m.dtk.abs() > 1e-3) | m.qv.isna()]
    yr = m.groupby(m.index.str[:4]).agg(days=("bars", "size"), bars_day=("bars", "median"), fast=("fast", "median"))
    s = {"days": int(len(m)), "first": m.index.min(), "last": m.index.max(), "missing_klines": int(m.qv.isna().sum()),
         "abs_dv_p50_p99_max": [float(m.dv.abs().quantile(q)) for q in (0.5, 0.99, 1.0)],
         "abs_dtaker_p50_p99_max": [float(m.dtk.abs().quantile(q)) for q in (0.5, 0.99, 1.0)],
         "abs_dhigh_max": float(m.dh.abs().max()), "abs_dlow_max": float(m.dl.abs().max()),
         "days_off_0.1pct": int(len(bad)), "worst": bad.assign(score=bad[["dv", "dh", "dl", "dtk"]].abs().max(axis=1)).nlargest(5, "score")[["dv", "dtk", "dh", "dl"]].round(5).reset_index().to_dict("records"),
         "by_year": {y: {"days": int(r.days), "bars_per_day_median": float(r.bars_day), "sub1s_share_median": round(float(r.fast), 4)} for y, r in yr.iterrows()}}
    return m, s


if __name__ == "__main__":
    res = {}
    for sym in sys.argv[1:] or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        _, res[sym] = one(sym)
        print(sym, json.dumps(res[sym], default=str)[:900])
    OUT.write_text(json.dumps(res, indent=1, default=str))
    # days every M-form must drop (volume/taker/high/low off klines by > 0.1%: duplicated archive trades, bad prints, partial archives)
    bad = {}
    for sym in res:
        m, _ = one(sym)
        b = m[(m.dv.abs() > 1e-3) | (m.dh.abs() > 1e-3) | (m.dl.abs() > 1e-3) | (m.dtk.abs() > 1e-3)]
        bad[sym] = {d: {k: round(float(r[k]), 5) for k in ("dv", "dtk", "dh", "dl")} for d, r in b.iterrows()}
    (ROOT / "research/is3/mbars_bad_days.json").write_text(json.dumps(bad, indent=1))
