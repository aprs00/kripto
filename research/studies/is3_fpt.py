"""InSilico pass 3, FPT: flow@bn anchors on the TRUE hourly taker split. Descriptive, NOT registered.

  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_fpt dl      # resumable download -> data/is3/k1h_tb/<SYM>.parquet (<= 1 request/s)
  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_fpt check   # known answer: 24 x hourly tbqv == daily tbqv
  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_fpt b       # is3_e2c a + c on the true split -> research/is3/fpt_b.json

Source: the public data.binance.vision monthly 1h kline archives (the same files bn100 is built from; column 10 = taker buy quote volume is kept here).
Coin-months: data/is3/fpt_months.json = every bn100 coin-month in the point-in-time top 40 by 30-d dollar volume (2021-12..2026-10) plus the month before.
"""
from __future__ import annotations

import json
import sys
import time
import warnings

import numpy as np
import pandas as pd

from kripto import data
from kripto.data import BN_BASE, DATA, _bn_get, _read_zip_csv

warnings.filterwarnings("ignore")
OUT = DATA / "is3" / "k1h_tb"
EV = DATA.parent / "research" / "is3"


def dl(max_sec=2500):
    OUT.mkdir(parents=True, exist_ok=True)
    need = json.load(open(DATA / "is3" / "fpt_months.json"))
    t_start = time.time(); n_req = 0; last = 0.0
    for coin, months in sorted(need.items()):
        sym = f"{coin}USDT"
        fp = OUT / f"{sym}.parquet"
        have = pd.read_parquet(fp) if fp.exists() else None
        done = set(have["month"].unique()) if have is not None else set()
        new = []
        for m in months:
            if m in done:
                continue
            if time.time() - t_start > max_sec:
                break
            wait = 1.0 - (time.time() - last)
            if wait > 0:
                time.sleep(wait)
            last = time.time(); n_req += 1
            b = _bn_get(f"{BN_BASE}/klines/{sym}/1h/{sym}-1h-{m}.zip")
            if b:
                df = _read_zip_csv(b).iloc[:, [0, 4, 7, 10]]
                df.columns = ["t", "c", "qv", "tbqv"]
                df = df.apply(pd.to_numeric, errors="coerce")
            else:
                df = pd.DataFrame({"t": [], "c": [], "qv": [], "tbqv": []})
            df["month"] = m
            new.append(df)
        if new:
            k = pd.concat(([have] if have is not None else []) + new)
            k.to_parquet(fp)
        if time.time() - t_start > max_sec:
            break
    left = sum(1 for c, ms in need.items() for m in ms
               if not (OUT / f"{c}USDT.parquet").exists() or m not in set(pd.read_parquet(OUT / f"{c}USDT.parquet", columns=["month"])["month"]))
    print(f"requests {n_req}, coin-months left {left}", flush=True)


def true_hourly():
    """{coin: DataFrame(index = hourly open time UTC, tbqv)}"""
    out = {}
    for fp in sorted(OUT.glob("*.parquet")):
        k = pd.read_parquet(fp)
        if k.empty:
            continue
        t = k["t"].where(k["t"] < 1e14, k["t"] // 1000)
        s = pd.Series(k["tbqv"].to_numpy(float), pd.to_datetime(t, unit="ms", utc=True))
        out[fp.stem.removesuffix("USDT")] = s[~s.index.duplicated()].sort_index()
    return out


def check():
    th = true_hourly()
    res = []
    for coin, s in list(th.items()):
        kd = DATA / "bn" / "klines_1d_all" / f"{coin}USDT.parquet"
        if not kd.exists():
            continue
        k = pd.read_parquet(kd, columns=["t", "tbqv"])
        tt = k["t"].where(k["t"] < 1e14, k["t"] // 1000)
        d = pd.Series(k["tbqv"].to_numpy(float), pd.to_datetime(tt, unit="ms", utc=True))
        g = s.resample("1D").agg(["sum", "count"])
        g = g[g["count"] == 24]["sum"]
        j = pd.concat([g, d[~d.index.duplicated()]], axis=1, keys=["h", "d"]).dropna()
        j = j[j["d"] > 0]
        if len(j):
            res.append((coin, len(j), float((j["h"] / j["d"] - 1).abs().quantile(.99)), float((j["h"] / j["d"] - 1).abs().max())))
    df = pd.DataFrame(res, columns=["coin", "days", "relerr_p99", "relerr_max"])
    out = {"coins": int(len(df)), "coin_days": int(df.days.sum()), "relerr_p99_median": float(df.relerr_p99.median()),
           "share_coins_p99_lt_1e-6": float((df.relerr_p99 < 1e-6).mean()), "worst": df.nlargest(5, "relerr_max").to_dict("records")}
    print(json.dumps(out, indent=1))
    json.dump(out, open(EV / "fpt_check.json", "w"), indent=1)


def form_b():
    from research.studies import is3_e2c as E
    th = true_hourly()
    E.TRUE_HOURLY = th
    E.form_a(tag="fpt_b_a")
    E.form_c(tag="fpt_b_c")


if __name__ == "__main__":
    {"dl": dl, "check": check, "b": form_b}[sys.argv[1]]()
