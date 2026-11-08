"""Data download + panel loading.

Storage (gitignored):  data/hl/candles_{iv}/{COIN}.parquet, data/hl/funding/{COIN}.parquet,
                       data/bn/klines_1h/{SYM}.parquet,    data/bn/funding/{SYM}.parquet
Panels are wide DataFrames: index = UTC bar open time, columns = coin.
Convention: bar t covers [t, t+bar). ret[t] = close[t]/close[t-1]-1 is earned by the position
held through bar t (decided at close of t-1). funding[t] = sum of hourly rates paid during bar t.
"""
from __future__ import annotations

import io
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .hl import HL, INTERVAL_MS

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def _now_ms() -> int:
    return int(time.time() * 1000)


# --------------------------------------------------------------------------- Hyperliquid
def hl_update_candles(coins: list[str], interval: str = "4h", hl: HL | None = None, log=print):
    hl = hl or HL()
    d = DATA / "hl" / f"candles_{interval}"
    d.mkdir(parents=True, exist_ok=True)
    for i, coin in enumerate(coins):
        p = d / f"{coin}.parquet"
        old = pd.read_parquet(p) if p.exists() else None
        start = int(old["t"].max()) - INTERVAL_MS[interval] * 2 if old is not None and len(old) else 0
        if start == 0:
            start = _now_ms() - INTERVAL_MS[interval] * 5200
        rows = hl.candles(coin, interval, start, _now_ms())
        if not rows:
            continue
        df = pd.DataFrame(rows)[["t", "o", "h", "l", "c", "v", "n"]]
        for c in "ohlcv":
            df[c] = df[c].astype(float)
        df["t"] = df["t"].astype("int64")
        if old is not None:
            df = pd.concat([old, df]).drop_duplicates("t", keep="last")
        df.sort_values("t").reset_index(drop=True).to_parquet(p)
        if i % 20 == 0:
            log(f"[hl candles {interval}] {i+1}/{len(coins)} {coin} rows={len(df)}")


def hl_update_funding(coins: list[str], since: str = "2023-05-01", hl: HL | None = None, log=print):
    hl = hl or HL()
    d = DATA / "hl" / "funding"
    d.mkdir(parents=True, exist_ok=True)
    for i, coin in enumerate(coins):
        p = d / f"{coin}.parquet"
        old = pd.read_parquet(p) if p.exists() else None
        start = int(old["time"].max()) + 1 if old is not None and len(old) else int(pd.Timestamp(since, tz="UTC").timestamp() * 1000)
        rows = hl.funding_history(coin, start)
        if rows:
            df = pd.DataFrame(rows)[["time", "fundingRate", "premium"]]
            df["fundingRate"] = df["fundingRate"].astype(float)
            df["premium"] = df["premium"].astype(float)
            df["time"] = df["time"].astype("int64")
            if old is not None:
                df = pd.concat([old, df]).drop_duplicates("time", keep="last")
            df.sort_values("time").reset_index(drop=True).to_parquet(p)
        log(f"[hl funding] {i+1}/{len(coins)} {coin} +{len(rows)}")


def hl_universe(hl: HL | None = None, min_day_ntl: float = 0.0) -> pd.DataFrame:
    hl = hl or HL()
    df = pd.DataFrame(hl.meta_and_ctxs())
    df["dayNtlVlm"] = df["dayNtlVlm"].astype(float)
    df["isDelisted"] = df.get("isDelisted", False).fillna(False).astype(bool)
    return df[df["dayNtlVlm"] >= min_day_ntl].sort_values("dayNtlVlm", ascending=False)


def load_hl_panel(interval: str = "4h", coins: list[str] | None = None) -> dict[str, pd.DataFrame]:
    d = DATA / "hl" / f"candles_{interval}"
    files = sorted(d.glob("*.parquet"))
    closes, vols, highs, lows = {}, {}, {}, {}
    for f in files:
        c = f.stem
        if coins and c not in coins:
            continue
        df = pd.read_parquet(f)
        idx = pd.to_datetime(df["t"], unit="ms", utc=True)
        closes[c] = pd.Series(df["c"].values, idx)
        vols[c] = pd.Series((df["v"] * df["c"]).values, idx)
        highs[c] = pd.Series(df["h"].values, idx)
        lows[c] = pd.Series(df["l"].values, idx)
    close = pd.DataFrame(closes).sort_index()
    bar = pd.Timedelta(milliseconds=INTERVAL_MS[interval])
    full = pd.date_range(close.index.min(), close.index.max(), freq=bar)
    close = close.reindex(full)
    panel = {"close": close,
             "volume": pd.DataFrame(vols).reindex(full),
             "high": pd.DataFrame(highs).reindex(full),
             "low": pd.DataFrame(lows).reindex(full)}
    panel["funding"] = _hl_funding_panel(full, bar, list(close.columns))
    return panel


def _hl_funding_panel(index: pd.DatetimeIndex, bar: pd.Timedelta, coins: list[str]) -> pd.DataFrame:
    out = {}
    for c in coins:
        p = DATA / "hl" / "funding" / f"{c}.parquet"
        if not p.exists():
            continue
        f = pd.read_parquet(p)
        # a funding print at time tau is paid by positions held during the hour ending at tau
        ts = pd.to_datetime(f["time"] - 1, unit="ms", utc=True).dt.floor(bar)
        out[c] = f.groupby(ts)["fundingRate"].sum()
    return pd.DataFrame(out).reindex(index=index, columns=coins)


# --------------------------------------------------------------------------- Binance (public archive)
BN_BASE = "https://data.binance.vision/data/futures/um/monthly"


def _bn_get(url: str) -> bytes | None:
    for _ in range(4):
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 404:
                return None
            if r.ok:
                return r.content
        except requests.RequestException:
            pass
        time.sleep(2)
    return None


def _read_zip_csv(b: bytes) -> pd.DataFrame:
    z = zipfile.ZipFile(io.BytesIO(b))
    raw = z.read(z.namelist()[0]).decode()
    first = raw.split("\n", 1)[0]
    header = 0 if any(ch.isalpha() for ch in first) else None
    return pd.read_csv(io.StringIO(raw), header=header)


def _months(start: str) -> list[str]:
    end = pd.Timestamp.utcnow().tz_localize(None).to_period("M") - 1
    return [str(p) for p in pd.period_range(pd.Period(start, "M"), end, freq="M")]


def bn_download(symbols: list[str], start: str = "2020-01", workers: int = 16, log=print):
    kd, fd = DATA / "bn" / "klines_1h", DATA / "bn" / "funding"
    kd.mkdir(parents=True, exist_ok=True)
    fd.mkdir(parents=True, exist_ok=True)

    def one(sym: str):
        months = _months(start)
        kp, fp = kd / f"{sym}.parquet", fd / f"{sym}.parquet"
        have_k = pd.read_parquet(kp) if kp.exists() else None
        have_f = pd.read_parquet(fp) if fp.exists() else None
        if have_k is not None:
            last = pd.to_datetime(have_k["t"].max(), unit="ms").to_period("M")
            months_k = [m for m in months if pd.Period(m, "M") >= last]
        else:
            months_k = months
        if have_f is not None:
            last = pd.to_datetime(have_f["time"].max(), unit="ms").to_period("M")
            months_f = [m for m in months if pd.Period(m, "M") >= last]
        else:
            months_f = months
        ks, fs = [], []
        for m in months_k:
            b = _bn_get(f"{BN_BASE}/klines/{sym}/1h/{sym}-1h-{m}.zip")
            if b:
                df = _read_zip_csv(b).iloc[:, :8]
                df.columns = ["t", "o", "h", "l", "c", "v", "T", "qv"]
                ks.append(df[["t", "o", "h", "l", "c", "v", "qv"]])
        for m in months_f:
            b = _bn_get(f"{BN_BASE}/fundingRate/{sym}/{sym}-fundingRate-{m}.zip")
            if b:
                df = _read_zip_csv(b).iloc[:, [0, 2]]
                df.columns = ["time", "fundingRate"]
                fs.append(df)
        if ks:
            k = pd.concat(([have_k] if have_k is not None else []) + ks).astype(float)
            k["t"] = k["t"].astype("int64")
            k = k.drop_duplicates("t", keep="last").sort_values("t").reset_index(drop=True)
            k.to_parquet(kp)
        if fs:
            f = pd.concat(([have_f] if have_f is not None else []) + fs)
            f["time"] = f["time"].astype("int64")
            f["fundingRate"] = f["fundingRate"].astype(float)
            f = f.drop_duplicates("time", keep="last").sort_values("time").reset_index(drop=True)
            f.to_parquet(fp)
        return sym, len(ks), len(fs)

    with ThreadPoolExecutor(workers) as ex:
        for sym, nk, nf in ex.map(one, symbols):
            log(f"[bn] {sym} klines_months={nk} funding_months={nf}")


def load_bn_panel(interval: str = "4h", symbols: list[str] | None = None) -> dict[str, pd.DataFrame]:
    rule = {"1h": "1h", "4h": "4h", "1d": "1D"}[interval]
    closes, vols, highs, lows, funds = {}, {}, {}, {}, {}
    for f in sorted((DATA / "bn" / "klines_1h").glob("*.parquet")):
        sym = f.stem
        if symbols and sym not in symbols:
            continue
        coin = sym.removesuffix("USDT")
        df = pd.read_parquet(f)
        # some archive months use microsecond timestamps
        t = df["t"].where(df["t"] < 1e14, df["t"] // 1000)
        df.index = pd.to_datetime(t, unit="ms", utc=True)
        df = df[~df.index.duplicated()]
        r = df.resample(rule)
        closes[coin] = r["c"].last()
        vols[coin] = r["qv"].sum()
        highs[coin] = r["h"].max()
        lows[coin] = r["l"].min()
        fp = DATA / "bn" / "funding" / f"{sym}.parquet"
        if fp.exists():
            fr = pd.read_parquet(fp)
            ts = pd.to_datetime(fr["time"] - 1, unit="ms", utc=True).dt.floor(rule)
            funds[coin] = fr.groupby(ts)["fundingRate"].sum()
    close = pd.DataFrame(closes).sort_index()
    idx = close.index
    vol = pd.DataFrame(vols).reindex(idx)
    close = close.where(vol > 0)
    return {"close": close, "volume": vol.where(vol > 0),
            "high": pd.DataFrame(highs).reindex(idx), "low": pd.DataFrame(lows).reindex(idx),
            "funding": pd.DataFrame(funds).reindex(index=idx, columns=close.columns)}


BN_SYMBOLS = """BTC ETH BNB SOL XRP DOGE ADA AVAX LINK DOT LTC BCH TRX ATOM ETC XLM FIL NEAR UNI AAVE
MATIC ARB OP APT SUI INJ SAND MANA AXS FTM EOS XTZ ALGO THETA ICP CRV SNX COMP MKR LDO RUNE DYDX
GALA CHZ ENJ 1INCH SUSHI YFI ZEC XMR KAVA ZIL EGLD HBAR VET GRT FLOW NEO WAVES DASH IOTA ONE KSM
CELO RSR BAL ALPHA LRC STORJ SKL OCEAN ANKR BAND HYPE TIA SEI WLD PEPE WIF ENA JUP TAO ORDI""".split()
BN_SYMBOLS = [s + "USDT" for s in BN_SYMBOLS]
