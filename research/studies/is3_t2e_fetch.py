"""T2e data: 1-min Binance USDT-perp klines 2020-06..2021-01 for BTC ETH LINK LTC from data.binance.vision (public archive,
1 request per second) -> data/is3/k1m_2020/<SYM>.parquet (kept apart from data/bn/klines_1m)."""
import time
from pathlib import Path

import pandas as pd

from kripto import data

OUT = data.DATA / "is3" / "k1m_2020"
MONTHS = ["2020-06", "2020-07", "2020-08", "2020-09", "2020-10", "2020-11", "2020-12", "2021-01"]

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for coin in ("BTC", "ETH", "LINK", "LTC"):
        parts = []
        for m in MONTHS:
            b = data._bn_get(f"{data.BN_BASE}/klines/{coin}USDT/1m/{coin}USDT-1m-{m}.zip")
            time.sleep(1.0)
            if not b:
                print(coin, m, "missing"); continue
            df = data._read_zip_csv(b).iloc[:, [0, 2, 3, 4, 7, 8, 10]]
            df.columns = ["t", "h", "l", "c", "qv", "n", "tbqv"]
            parts.append(df.apply(pd.to_numeric, errors="coerce").dropna())
        d = pd.concat(parts).drop_duplicates("t").sort_values("t").reset_index(drop=True)
        d["t"] = d["t"].astype("int64")
        d.to_parquet(OUT / f"{coin}USDT.parquet")
        print(coin, len(d), pd.to_datetime(d.t.iloc[0], unit="ms"), pd.to_datetime(d.t.iloc[-1], unit="ms"))
