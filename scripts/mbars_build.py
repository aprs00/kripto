"""Binance USDT-M aggTrades (public archive) -> micro move bars per day (kripto/mbars.py). Resumable, newest progress kept.

  nice -n 19 .venv/bin/python -m scripts.mbars_build BTCUSDT ETHUSDT SOLUSDT --start 2021-01-01 --end 2023-12-31 --workers 2

A day's trades are held in RAM once (~25 B per trade; the busiest BTC days are ~8 M trades), then dropped: nothing raw is kept.
Run on the server as a transient unit: RuntimeMaxSec=2700, MemoryMax=1500M (rule 4); start it again to continue.
"""
from __future__ import annotations

import argparse
import io
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
import pyarrow.csv as pacsv
import requests

from kripto import mbars
from scripts.aggtrades import COLS, URL


def one(args) -> tuple[str, str, int]:
    sym, day = args
    out = mbars.DIR / sym / f"{day}.npz"
    if out.exists():
        return sym, day, 0
    b = None
    for attempt in range(5):
        try:
            r = requests.get(URL.format(s=sym, d=day), timeout=120)
            if r.status_code == 404:
                return sym, day, -1
            if r.ok:
                b = r.content
                break
        except requests.RequestException:
            pass
        time.sleep(3 * (attempt + 1))
    if b is None:
        return sym, day, -2
    z = zipfile.ZipFile(io.BytesIO(b))
    with z.open(z.namelist()[0]) as f:
        head = f.read(1).isalpha()
    P, Q, T, M = [], [], [], []
    with z.open(z.namelist()[0]) as f:
        rd = pacsv.open_csv(f, read_options=pacsv.ReadOptions(column_names=COLS, skip_rows=1 if head else 0, block_size=8 << 20),
                            convert_options=pacsv.ConvertOptions(include_columns=["price", "quantity", "transact_time", "is_buyer_maker"]))
        for t in rd:
            P.append(t["price"].to_numpy()), Q.append(t["quantity"].to_numpy().astype(np.float32))
            T.append(t["transact_time"].to_numpy()), M.append(t["is_buyer_maker"].to_numpy(zero_copy_only=False))
    if not P:
        return sym, day, -3
    ts = np.concatenate(T)
    if len(ts) and ts[0] > 1e14:              # microseconds in some archive months
        ts = ts // 1000
    p = np.concatenate(P)
    if (np.diff(ts) < 0).any():
        o = np.argsort(ts, kind="stable")
        p, ts, Q, M = p[o], ts[o], [np.concatenate(Q)[o]], [np.concatenate(M)[o]]
    x = mbars.micro(p, np.concatenate(Q), ts, np.concatenate(M))
    for k in ("o", "h", "l", "c"):
        x[k] = x[k].astype(np.float64)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, **x)
    tmp.rename(out)
    return sym, day, len(p)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--start", default="2021-01-01")
    ap.add_argument("--end", default="2023-12-31")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    for sym in a.symbols:
        days = [str(d.date()) for d in pd.date_range(a.start, a.end, freq="1D")]
        t0, miss, rows, done = time.time(), 0, 0, 0
        with ProcessPoolExecutor(a.workers) as ex:
            for _, day, k in ex.map(one, [(sym, d) for d in days], chunksize=2):
                done, miss, rows = done + 1, miss + (k < 0), rows + max(k, 0)
                if done % 100 == 0:
                    print(f"[mbars] {sym} {done}/{len(days)} ({day}), {miss} missing, {rows/1e6:.0f}M trades, {time.time()-t0:.0f}s", flush=True)
        print(f"[mbars] {sym} done {len(days)} days, {miss} missing, {time.time()-t0:.0f}s", flush=True)
