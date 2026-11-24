"""N2 data: Binance SPOT 1h klines with taker-buy volume from the public archive (data.binance.vision/data/spot, the same host the
futures archives come from; unauthenticated market data, <= 1 request/s). Coins = the 30 perps with the highest mean quote volume
in bnall 2021-2023 (clean universe, no 1000x names). Resumable: one parquet per symbol, months already present are skipped.

    systemd-run --user --unit is3-n2 -p Nice=19 -p MemoryMax=800M -p RuntimeMaxSec=2700 --working-directory=$HOME/kripto \
        .venv/bin/python -m research.studies.is3_n2_download
"""
from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

from kripto import data

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/bn/spot_1h"
URL = "https://data.binance.vision/data/spot/monthly/klines/{s}/1h/{s}-1h-{m}.zip"
COLS = ["t", "o", "h", "l", "c", "v", "ct", "qv", "n", "tbv", "tbqv", "x"]


def coins(n: int = 30) -> list[str]:
    p = data.load_panel("bnall", "1d")
    v = p["volume"].loc["2021-01-01":"2023-12-31"].mean().sort_values(ascending=False)
    return [c for c in v.index if not c.startswith("1000")][:n]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    months = [m.strftime("%Y-%m") for m in pd.period_range("2021-01", "2025-12", freq="M")]
    for coin in coins():
        sym = f"{coin}USDT"
        f = OUT / f"{sym}.parquet"
        old = pd.read_parquet(f) if f.exists() else pd.DataFrame(columns=["t"])
        have = set(pd.to_datetime(old.t, unit="ms", utc=True).dt.strftime("%Y-%m")) if len(old) else set()
        parts = [old] if len(old) else []
        for m in months:
            if m in have:
                continue
            time.sleep(1.0)
            try:
                r = requests.get(URL.format(s=sym, m=m), timeout=60)
            except requests.RequestException:
                continue
            if r.status_code != 200:
                continue
            z = zipfile.ZipFile(io.BytesIO(r.content))
            d = pd.read_csv(z.open(z.namelist()[0]), header=None)
            if not str(d.iloc[0, 0]).isdigit():
                d = d.iloc[1:]
            d.columns = COLS
            d = d[["t", "h", "l", "c", "qv", "n", "tbqv"]].astype(float)
            d.loc[d.t > 1e14, "t"] = d.t // 1000          # the spot archive switched to microseconds in 2025
            d["t"] = d.t.astype("int64")
            parts.append(d)
        if parts:
            pd.concat(parts, ignore_index=True).drop_duplicates("t").sort_values("t").to_parquet(f)
        print(sym, "done", flush=True)


if __name__ == "__main__":
    main()
