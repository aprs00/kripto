"""T2b (daily family): which features are extreme on ALL of InSilico's capitulation days (M4e examples, T2a), vs every
other BTC day and vs the down days of similar size?  Descriptive, n = 4 examples (+1 stay-out contrast day).

Features per UTC day (BTCUSDT perp, 1-min klines + kripto.tsize author7 buckets):
  ret, ret_z (ret / 30-d std of daily returns, prior days only), range_atr (h-l over 20-d mean range), qv_z / n_z
  (log volume / trade count vs prior 30 d), taker (taker-buy share of quote volume), avg_trade (qv / n vs prior 30 d, log),
  dd5 / dd20 / dd90 (close vs prior 5/20/90-d high), clv (close location in the day's range, 0 = low), peak_min
  (largest 1-min volume / day volume), tsz_neg (number of author7 buckets with negative delta, 0..7), tsz_min / tsz_large
  (smallest bucket delta/volume share; delta share of the two largest buckets).
Output: percentile of each example among all days (2021-02..2026-10) and among down days with ret <= -3 %; features in the
top or bottom 15 % on all four examples are printed.

    nice -n 19 .venv/bin/python -m research.studies.is3_t2b    -> research/is3/T2b__daily.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from kripto import tsize

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "is3" / "T2b__daily.json"
EXAMPLES = ["2021-07-20", "2021-11-26", "2021-12-13", "2022-01-07"]
CONTRAST = ["2021-09-21"]          # his 'not a bottom, issa fart' day


def daily() -> pd.DataFrame:
    return daily_sym("BTCUSDT")


def daily_sym(sym: str, end: str | None = None) -> pd.DataFrame:
    """Daily features of one perp; `end` (exclusive day) truncates the input, for the causality check."""
    k = pq.read_table(ROOT / "data/bn/klines_1m" / f"{sym}.parquet", columns=["t", "h", "l", "c", "qv", "n", "tbqv"]).to_pandas()
    k.index = pd.to_datetime(k.t, unit="ms", utc=True)
    if end:
        k = k[k.index < pd.Timestamp(end, tz="UTC")]
    d = k.resample("1D").agg({"h": "max", "l": "min", "c": "last", "qv": "sum", "n": "sum", "tbqv": "sum"})
    d["peak_min"] = k.qv.resample("1D").max() / d.qv
    prev = d.shift(1)
    d["ret"] = d.c / prev.c - 1
    sd = d.ret.shift(1).rolling(30).std()
    d["ret_z"] = d.ret / sd
    rng = (d.h - d.l)
    d["range_atr"] = rng / rng.shift(1).rolling(20).mean()
    for col, name in (("qv", "qv_z"), ("n", "n_z")):
        lg = np.log(d[col].where(d[col] > 0))
        d[name] = (lg - lg.shift(1).rolling(30).mean()) / lg.shift(1).rolling(30).std()
    d["taker"] = d.tbqv / d.qv
    at = np.log(d.qv / d.n)
    d["avg_trade"] = at - at.shift(1).rolling(30).mean()
    for w in (5, 20, 90):
        d[f"dd{w}"] = d.c / d.h.shift(1).rolling(w).max() - 1
    d["clv"] = (d.c - d.l) / rng
    fr = tsize.frames(sym, "author7", "1D")
    if fr is not None:
        dl, vol = fr
        dl.index = pd.to_datetime(dl.index, utc=True)
        vol.index = dl.index
        share = dl / vol.replace(0, np.nan)
        d["tsz_neg"] = (dl < 0).sum(axis=1).reindex(d.index)
        d["tsz_min"] = share.min(axis=1).reindex(d.index)
        d["tsz_large"] = (dl.iloc[:, -2:].sum(axis=1) / vol.iloc[:, -2:].sum(axis=1)).reindex(d.index)
        if end:   # TSize days after the cut must not leak in
            d.loc[d.index >= pd.Timestamp(end, tz="UTC"), ["tsz_neg", "tsz_min", "tsz_large"]] = np.nan
    return d


FEATS = ["ret", "ret_z", "range_atr", "qv_z", "n_z", "taker", "avg_trade", "dd5", "dd20", "dd90", "clv", "peak_min",
         "tsz_neg", "tsz_min", "tsz_large"]


def main() -> None:
    d = daily().loc["2021-02-01":"2026-10-31"]
    down = d[d.ret <= -0.03]
    res = {"n_days": int(len(d)), "n_down3": int(len(down)), "examples": {}, "contrast": {}}
    for grp, days in (("examples", EXAMPLES), ("contrast", CONTRAST)):
        for day in days:
            row = d.loc[day]
            res[grp][day] = {f: {"value": float(row[f]),
                                 "pct_all": float((d[f] < row[f]).mean()),
                                 "pct_down3": float((down[f] < row[f]).mean())} for f in FEATS if f in d and np.isfinite(row[f])}
    tab = pd.DataFrame({day: {f: v["pct_down3"] for f, v in res["examples"][day].items()} for day in EXAMPLES})
    tab["contrast_0921"] = pd.Series({f: v["pct_down3"] for f, v in res["contrast"]["2021-09-21"].items()})
    common = [f for f in tab.index if (tab.loc[f, EXAMPLES] >= 0.85).all() or (tab.loc[f, EXAMPLES] <= 0.15).all()]
    res["extreme_in_all_4_vs_down3"] = common
    tab_all = pd.DataFrame({day: {f: v["pct_all"] for f, v in res["examples"][day].items()} for day in EXAMPLES})
    res["extreme_in_all_4_vs_all"] = [f for f in tab_all.index if (tab_all.loc[f] >= 0.85).all() or (tab_all.loc[f] <= 0.15).all()]
    OUT.write_text(json.dumps(res, indent=1))
    vals = pd.DataFrame({day: {f: v["value"] for f, v in res["examples"][day].items()} for day in EXAMPLES})
    with pd.option_context("display.width", 200, "display.float_format", "{:.3f}".format):
        print("values\n", vals.to_string())
        print(f"\npercentile among down days (ret <= -3 pct, n={len(down)})\n", tab.to_string())
    print("\nextreme in all 4 vs down days:", common)
    print("extreme in all 4 vs all days:", res["extreme_in_all_4_vs_all"])


if __name__ == "__main__":
    main()
