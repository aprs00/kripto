"""InSilico second pass, T5: the trade-size capitulation rule on the author's KIND of venue and in his era. Descriptive.

  nice -n 19 .venv/bin/python -m research.studies.is2_bybit download      # -> data/bybit/tsize/BTCUSD/<day>.npz (laptop)
  nice -n 19 .venv/bin/python -m research.studies.is2_bybit study

Bybit inverse BTCUSD, 2019-10..2022-12, from Bybit's public trade archive (public.bybit.com/trading, free, ~4-90 MB/day).
BitMEX XBTUSD, the venue of his charts, has closed its public archive (403); Bybit inverse is the other venue he names as
"cleaner flow". Fills with the same timestamp and side are one taker ORDER (a 1,000-contract sell printed as 58 + 942 is one
order), which is closer to his tool than per-print sizes. Same 12 USD bins as kripto/tsize.py (inverse contract: size is USD).
Price for forward returns: Binance BTCUSDT daily close (same underlying). No confirmation sample: this asks whether the
rule was ever true where and when he saw it.
"""
from __future__ import annotations

import io
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
import requests

from kripto import data, tsize

DIR = data.DATA / "bybit" / "tsize" / "BTCUSD"
URL = "https://public.bybit.com/trading/BTCUSD/BTCUSD{d}.csv.gz"


def one(day: str) -> tuple[str, int]:
    out = DIR / f"{day}.npz"
    if out.exists():
        return day, 0
    b = None
    for _ in range(4):
        try:
            r = requests.get(URL.format(d=day), timeout=120)
            if r.status_code == 404:
                return day, -1
            if r.ok:
                b = r.content
                break
        except requests.RequestException:
            pass
    if b is None:
        return day, -2
    df = pd.read_csv(io.BytesIO(b), compression="gzip", usecols=["timestamp", "side", "size"])
    g = df.groupby(["timestamp", "side"], sort=False)["size"].sum().reset_index()      # one row per taker order
    d0 = int(pd.Timestamp(day, tz="UTC").timestamp() * 1000)
    buy, sell, n = tsize.bucket_trades(np.ones(len(g)), g["size"].to_numpy(float), (g["timestamp"].to_numpy(float) * 1000).astype(np.int64),
                                       (g["side"] == "Sell").to_numpy(), d0)
    DIR.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, buy=buy.sum(axis=0), sell=sell.sum(axis=0), n=n.sum(axis=0))
    tmp.rename(out)
    return day, len(g)


def download(start="2019-10-01", end="2022-12-31", workers=4):
    days = [str(d.date()) for d in pd.date_range(start, end, freq="1D")]
    done = miss = 0
    with ProcessPoolExecutor(workers) as ex:
        for _, k in ex.map(one, days, chunksize=4):
            done += 1
            miss += k < 0
            if done % 200 == 0:
                print(f"[bybit] {done}/{len(days)} days, {miss} missing", flush=True)
    print(f"[bybit] finished: {done} days, {miss} missing", flush=True)


def tstat(x) -> float:
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


def welch(a, b) -> float:
    a, b = pd.Series(a).dropna(), pd.Series(b).dropna()
    return float((a.mean() - b.mean()) / np.sqrt(a.var() / len(a) + b.var() / len(b))) if len(a) > 2 and len(b) > 2 else float("nan")


def study(start="2019-10-01", end="2022-12-31"):
    files = sorted(p for p in DIR.glob("*.npz") if ".tmp" not in p.name and start <= p.stem <= end)
    days = pd.DatetimeIndex([p.stem for p in files]).tz_localize("UTC")
    buy = np.stack([np.load(p)["buy"] for p in files]).astype(float)
    sell = np.stack([np.load(p)["sell"] for p in files]).astype(float)
    c = data.load_bn_all_panel(["BTCUSDT"])["close"]["BTC"].reindex(days)
    r = np.log(c / c.shift(1))
    sig = r.rolling(30, min_periods=15).std().shift(1)
    print(f"Bybit inverse BTCUSD {days[0].date()}..{days[-1].date()}, {len(days)} days; taker orders merged by timestamp; forward returns in bp")
    share = (buy + sell).sum(axis=0) / (buy + sell).sum()
    print("  volume share by bin (<1k,1-3k,3-10k,10-20k,20-30k,30-60k,60-110k,110-150k,150-250k,250-500k,0.5-1M,>1M):", np.round(share, 3).tolist())
    for scheme in ("author7", "fine12"):
        d, v = tsize.group(buy - sell, scheme), tsize.group(buy + sell, scheme)
        sign = pd.Series(tsize.one_voiced(d, v, 0.01), days)
        x = pd.DataFrame(np.where(v > 0, d / np.where(v > 0, v, 1), np.nan), days)
        z = (x - x.rolling(90, min_periods=45).mean().shift(1)) / x.rolling(90, min_periods=45).std().shift(1)
        live = pd.DataFrame(v / v.sum(axis=1, keepdims=True) >= 0.01, days)
        abn_neg = (z.where(live).max(axis=1) < -1) & (live.sum(axis=1) >= 2)
        abn_pos = (z.where(live).min(axis=1) > 1) & (live.sum(axis=1) >= 2)
        dn = (r / sig) <= -1.5
        print(f"[{scheme}] days all-negative {int((sign == -1).sum())}, all-positive {int((sign == 1).sum())}, abnormal all-negative {int(abn_neg.sum())}, big down days {int(dn.sum())}")
        for h in (1, 3, 5):
            f = np.log(c.shift(-h) / c)
            base = f.dropna()

            def row(name, m, ref=None):
                a = f[m].dropna()
                b = f[ref].dropna() if ref is not None else base
                print(f"   +{h}d {name:52s} n={len(a):4d} mean={a.mean() * 1e4:+7.1f} (t {tstat(a):+.1f}) vs {b.mean() * 1e4:+7.1f} diff t {welch(a, b):+.1f}")
            row("author's rule: every bucket net negative", sign == -1)
            row("  ... to 2021-06 (before his posts)", (sign == -1) & (days < "2021-07-01"))
            row("  ... 2021-07 onward (when he posted it)", (sign == -1) & (days >= "2021-07-01"))
            row("every bucket net positive", sign == 1)
            row("every bucket ABNORMALLY negative (z<-1)", abn_neg)
            row("big down day & every bucket negative vs other big down", dn & (sign == -1), dn & (sign != -1))
            row("big down day & abnormally negative vs other big down", dn & abn_neg, dn & ~abn_neg)
            row("every bucket abnormally positive", abn_pos)


if __name__ == "__main__":
    download() if sys.argv[1] == "download" else study(*sys.argv[2:4])
