"""Binance USDT-M aggTrades (public archive) -> trade-size buckets per 5 minutes (kripto/tsize.py).

  nice -n 19 .venv/bin/python -m scripts.aggtrades BTCUSDT ETHUSDT --start 2020-01-01 --workers 8

Each day's zip (20-110 MB) is downloaded into memory, reduced to a (288, 12) table and dropped: nothing raw is kept.
Per-day results go to data/bn/tsize/<SYMBOL>/<date>.npz (resumable), then one <SYMBOL>.npz. ~0.2 GB RAM per worker.
"""
from __future__ import annotations

import argparse
import io
import sys
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
import pyarrow.csv as pacsv
import requests

from kripto import tsize

URL = "https://data.binance.vision/data/futures/um/daily/aggTrades/{s}/{s}-aggTrades-{d}.zip"
COLS = ["agg_trade_id", "price", "quantity", "first_trade_id", "last_trade_id", "transact_time", "is_buyer_maker"]


def one(args) -> tuple[str, str, int]:
    sym, day = args
    out = tsize.DIR / sym / f"{day}.npz"
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
        head = f.read(1)
    has_header = head.isalpha()
    with z.open(z.namelist()[0]) as f:
        t = pacsv.read_csv(f, read_options=pacsv.ReadOptions(column_names=COLS, skip_rows=1 if has_header else 0),
                           convert_options=pacsv.ConvertOptions(include_columns=["price", "quantity", "transact_time", "is_buyer_maker"]))
    ts = t["transact_time"].to_numpy()
    if len(ts) and ts[0] > 1e14:          # microseconds in some archive months
        ts = ts // 1000
    d0 = int(pd.Timestamp(day, tz="UTC").timestamp() * 1000)
    buy, sell, n = tsize.bucket_trades(t["price"].to_numpy(), t["quantity"].to_numpy(), ts,
                                       t["is_buyer_maker"].to_numpy(zero_copy_only=False), d0)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, buy=buy, sell=sell, n=n)
    tmp.rename(out)
    return sym, day, len(ts)


def consolidate(sym: str) -> int:
    files = sorted(p for p in (tsize.DIR / sym).glob("*.npz") if ".tmp" not in p.name)
    if not files:
        return 0
    days, buy, sell, n = [], [], [], []
    for p in files:
        z = np.load(p)
        days.append(np.datetime64(p.stem, "D"))
        buy.append(z["buy"]), sell.append(z["sell"]), n.append(z["n"])
    np.savez_compressed(tsize.DIR / f"{sym}.npz", days=np.array(days), buy=np.stack(buy), sell=np.stack(sell), n=np.stack(n))
    return len(files)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--start", default="2020-01-01")
    ap.add_argument("--end", default=str((pd.Timestamp.now("UTC") - pd.Timedelta(days=2)).date()))
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    for sym in a.symbols:
        days = [str(d.date()) for d in pd.date_range(a.start, a.end, freq="1D")]
        t0, done, missing, rows = time.time(), 0, 0, 0
        with ProcessPoolExecutor(a.workers) as ex:
            for _, day, k in ex.map(one, [(sym, d) for d in days], chunksize=4):
                done += 1
                missing += k < 0
                rows += max(k, 0)
                if done % 100 == 0:
                    print(f"[agg] {sym} {done}/{len(days)} days, {missing} missing, {rows/1e6:.0f}M trades, {time.time()-t0:.0f}s", flush=True)
        print(f"[agg] {sym} consolidated {consolidate(sym)} days ({missing} missing) in {time.time()-t0:.0f}s", flush=True)
        sys.stdout.flush()
