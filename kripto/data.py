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
        since_ms = int(pd.Timestamp(since, tz="UTC").timestamp() * 1000)
        start = int(old["time"].max()) + 1 if old is not None and len(old) else since_ms
        rows = hl.funding_history(coin, start)
        # backfill a missing head (e.g. the live trader only fetched the last 30 days)
        if old is not None and len(old) and int(old["time"].min()) > since_ms + 2 * 86_400_000:
            rows = hl.funding_history(coin, since_ms, int(old["time"].min()) - 1) + rows
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
    vol = pd.DataFrame(vols).reindex(full)
    # HL candles before a coin's listing are zero-volume oracle prices (e.g. BTC 1d from 2020-08 while HL
    # trading began 2023-02). Not tradable -> mask everything before the first bar with volume > 0.
    close = close.where((vol.fillna(0) > 0).cummax())
    panel = {"close": close,
             "volume": vol,
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
    end = pd.Timestamp.now("UTC").tz_localize(None).to_period("M") - 1
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
    closes, vols, highs, lows, funds, tbs = {}, {}, {}, {}, {}, {}
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


# --------------------------------------------------------------------------- Binance FULL universe (incl. delisted)
# The hand-picked 82-coin BN set is survivor-biased (2026-11-09). This is the unbiased alternative: every USDT
# perp that ever existed in the public archive, daily bars. Dataset name in research: "bnall" (1d only).
BN_S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"


def _bn_s3_list(prefix: str) -> tuple[list[str], list[str]]:
    """(common prefixes, keys) under prefix, following pagination."""
    import re
    prefixes, keys, marker = [], [], ""
    while True:
        b = _bn_get(f"{BN_S3}?delimiter=/&prefix={prefix}&marker={marker}")
        if b is None:
            break
        x = b.decode()
        prefixes += re.findall(r"<CommonPrefixes><Prefix>([^<]+)</Prefix>", x)
        keys += re.findall(r"<Key>([^<]+)</Key>", x)
        if "<IsTruncated>true</IsTruncated>" not in x:
            break
        nm = re.search(r"<NextMarker>([^<]+)</NextMarker>", x)
        marker = nm.group(1) if nm else (keys[-1] if keys else prefixes[-1])
    return prefixes, keys


def bn_all_symbols() -> list[str]:
    pre, _ = _bn_s3_list("data/futures/um/monthly/klines/")
    syms = [p.rstrip("/").split("/")[-1] for p in pre]
    return sorted(s for s in syms if s.endswith("USDT") and "_" not in s)


def bn_download_all_daily(symbols: list[str] | None = None, workers: int = 16, log=print):
    """Daily klines + funding for every USDT perp (incl. delisted). Incremental: skips months already stored."""
    kd, fd = DATA / "bn" / "klines_1d_all", DATA / "bn" / "funding_all"
    kd.mkdir(parents=True, exist_ok=True)
    fd.mkdir(parents=True, exist_ok=True)
    symbols = symbols or bn_all_symbols()
    log(f"[bn all] {len(symbols)} symbols")

    def fetch(kind: str, sym: str, path: Path, tcol: str, cols: list[int], names: list[str]):
        sub = f"{sym}/1d/" if kind == "klines" else f"{sym}/"
        _, keys = _bn_s3_list(f"data/futures/um/monthly/{kind}/{sub}")
        keys = [k for k in keys if k.endswith(".zip")]
        have = pd.read_parquet(path) if path.exists() else None
        if have is not None and not set(names) <= set(have.columns):
            have = None  # schema grew (e.g. taker buy volume added 2026-11-09) -> refetch this symbol fully
        if have is not None and len(have):
            last = pd.to_datetime(have[tcol].max(), unit="ms").strftime("%Y-%m")
            keys = [k for k in keys if k[-11:-4] >= last]
        parts = []
        for k in keys:
            b = _bn_get(f"https://data.binance.vision/{k}")
            if b:
                df = _read_zip_csv(b).iloc[:, cols]
                df.columns = names
                parts.append(df)
        if parts:
            d = pd.concat(([have] if have is not None else []) + parts)
            d = d.apply(pd.to_numeric, errors="coerce").dropna(subset=[tcol])
            d[tcol] = d[tcol].astype("int64")
            d = d.drop_duplicates(tcol, keep="last").sort_values(tcol).reset_index(drop=True)
            tmp = path.with_suffix(".tmp")
            d.to_parquet(tmp)
            tmp.replace(path)  # atomic: an interrupted run never leaves a corrupt file
        return len(parts)

    def one(sym):
        nk = fetch("klines", sym, kd / f"{sym}.parquet", "t", [0, 1, 2, 3, 4, 5, 7, 10],
                   ["t", "o", "h", "l", "c", "v", "qv", "tbqv"])  # col 10 = taker buy quote volume
        nf = fetch("fundingRate", sym, fd / f"{sym}.parquet", "time", [0, 2], ["time", "fundingRate"])
        return sym, nk, nf

    with ThreadPoolExecutor(workers) as ex:
        for i, (s, nk, nf) in enumerate(ex.map(one, symbols)):
            if i % 50 == 0:
                log(f"[bn all] {i+1}/{len(symbols)} {s} klines+{nk} funding+{nf}")


def load_bn_all_panel(symbols: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Daily panel over the full (survivorship-free) Binance USDT-perp universe (or only `symbols`)."""
    closes, vols, highs, lows, funds, tbs = {}, {}, {}, {}, {}, {}
    for f in sorted((DATA / "bn" / "klines_1d_all").glob("*.parquet")):
        sym = f.stem
        if symbols and sym not in symbols:
            continue
        coin = sym.removesuffix("USDT")
        df = pd.read_parquet(f)
        t = df["t"].where(df["t"] < 1e14, df["t"] // 1000)
        df.index = pd.to_datetime(t, unit="ms", utc=True).dt.floor("1D")
        df = df[~df.index.duplicated()]
        closes[coin], vols[coin], highs[coin], lows[coin] = df["c"], df["qv"], df["h"], df["l"]
        if "tbqv" in df:
            tbs[coin] = df["tbqv"]
        fp = DATA / "bn" / "funding_all" / f"{sym}.parquet"
        if fp.exists():
            fr = pd.read_parquet(fp)
            ts = pd.to_datetime(fr["time"] - 1, unit="ms", utc=True).dt.floor("1D")
            funds[coin] = fr.groupby(ts)["fundingRate"].sum()
    close = pd.DataFrame(closes).sort_index()
    idx = pd.date_range(close.index.min(), close.index.max(), freq="1D")
    close = close.reindex(idx)
    vol = pd.DataFrame(vols).reindex(idx)
    close = close.where(vol > 0)
    return {"close": close, "volume": vol.where(vol > 0),
            "high": pd.DataFrame(highs).reindex(idx), "low": pd.DataFrame(lows).reindex(idx),
            "funding": pd.DataFrame(funds).reindex(index=idx, columns=close.columns),
            **({"taker_buy": pd.DataFrame(tbs).reindex(index=idx, columns=close.columns).where(vol > 0)} if tbs else {})}


# --------------------------------------------------------------------------- cross-venue panels (daily)
def hl_to_bn(coin: str) -> str:
    """Binance name of a Hyperliquid coin: HL quotes some small-price coins per 1000 with a `k` prefix (kPEPE = 1000PEPE)."""
    return "1000" + coin[1:] if coin.startswith("k") and coin[1:2].isupper() else coin


def _same_asset(a: pd.DataFrame, b: pd.DataFrame, tol: float = 0.05) -> pd.DataFrame:
    """Point-in-time check that two venues' tickers are the same asset: trailing median |log price ratio| < tol."""
    return np.log(a / b).abs().rolling(30, min_periods=10).median() < tol


def load_hl_bnflow_panel() -> dict[str, pd.DataFrame]:
    """Dataset "hlx": the Hyperliquid daily panel (prices, volume, funding = what we would trade) plus Binance taker flow
    for the same coins (`taker_buy`, `flow_volume`). HL candles carry no taker split, and the deepest perp venue leads
    price discovery (library: alexander-heck-2020), so this is how a flow signal gets tested on HL prices."""
    hl, bn = load_hl_panel("1d"), load_bn_all_panel()
    idx, coins = hl["close"].index, list(hl["close"].columns)
    both = [c for c in coins if hl_to_bn(c) in bn["close"].columns]

    def pick(k):
        return bn[k][[hl_to_bn(c) for c in both]].set_axis(both, axis=1).reindex(index=idx, columns=coins)
    ok = _same_asset(hl["close"], pick("close"))
    hl["taker_buy"], hl["flow_volume"] = pick("taker_buy").where(ok), pick("volume").where(ok)
    return hl


def load_pair_panel() -> dict[str, pd.DataFrame]:
    """Dataset "pair": one daily panel holding BOTH venues, columns `<COIN>@hl` and `<COIN>@bn`, for coins listed on both
    with funding history on both. Lets the backtest hold a coin long on one venue and short on the other (each leg with
    its own price, volume-scaled slippage and funding). The engine charges the HL taker fee on every leg (Binance is 0.5 bp more)."""
    hl, bn = load_hl_panel("1d"), load_bn_all_panel()
    idx = hl["close"].index.intersection(bn["close"].index)
    coins = [c for c in hl["close"].columns if hl_to_bn(c) in bn["close"].columns
             and hl["funding"][c].notna().any() and bn["funding"][hl_to_bn(c)].notna().any()]
    out = {}
    for k in ("close", "volume", "funding"):
        a = hl[k][coins].reindex(idx).add_suffix("@hl")
        b = bn[k][[hl_to_bn(c) for c in coins]].reindex(idx).set_axis([c + "@bn" for c in coins], axis=1)
        out[k] = pd.concat([a, b], axis=1)
    return out


# --------------------------------------------------------------------------- intraday + trade-size panels (2026-11-11)
MINUTE_COINS = "BTC ETH SOL XRP DOGE BNB ADA AVAX LINK LTC".split()
TSIZE_COINS = "BTC ETH SOL".split()


def load_bn_minute_panel(coins: list[str] | None = None, start: str = "2021-01-01", rule: str | None = None) -> dict[str, pd.DataFrame]:
    """Dataset "bnm": Binance 1-minute bars (data/bn/klines_1m, scripts/minute_study.download) as float32 frames
    close/high/low/volume on a gap-free index. rule="5min" resamples. A missing minute repeats the last close (no trade).
    Filled column by column into preallocated arrays: 10 coins x 5.8 years is 0.5 GB, and pandas copies would triple it."""
    files = [(c, DATA / "bn" / "klines_1m" / f"{c}USDT.parquet") for c in coins or MINUTE_COINS]
    files = [(c, f) for c, f in files if f.exists()]
    step = pd.Timedelta(rule or "1min")
    t0 = pd.Timestamp(start, tz="UTC")

    def read(f, columns):
        df = pd.read_parquet(f, columns=columns)
        t = df["t"].where(df["t"] < 1e14, df["t"] // 1000)
        df.index = pd.to_datetime(t, unit="ms", utc=True)
        return df
    t1 = max(read(f, ["t"]).index.max() for _, f in files)      # pass 1: only the time column, to size the arrays
    idx = pd.date_range(t0, t1.floor(step), freq=step)
    arr = {k: np.full((len(idx), len(files)), np.nan, dtype=np.float32) for k in ("c", "h", "l", "qv")}
    for j, (coin, f) in enumerate(files):                        # pass 2: one coin in memory at a time
        df = read(f, ["t", "h", "l", "c", "qv"])
        df = df[~df.index.duplicated()].sort_index()
        df = df[df.index >= t0]
        if rule:
            r = df.resample(rule)
            df = pd.DataFrame({"h": r["h"].max(), "l": r["l"].min(), "c": r["c"].last(), "qv": r["qv"].sum()}).dropna(subset=["c"])
        pos = np.asarray((df.index - t0) // step, dtype=np.int64)
        for k in arr:
            arr[k][pos, j] = df[k].to_numpy(dtype=np.float32)
        del df
    cols = [c for c, _ in files]
    close = pd.DataFrame(arr["c"], idx, cols, copy=False).ffill()
    gap = np.isnan(arr["h"])
    arr["h"][gap], arr["l"][gap], arr["qv"][gap] = close.to_numpy()[gap], close.to_numpy()[gap], 0.0
    return {"close": close, "high": pd.DataFrame(arr["h"], idx, cols, copy=False),
            "low": pd.DataFrame(arr["l"], idx, cols, copy=False), "volume": pd.DataFrame(arr["qv"], idx, cols, copy=False)}


def load_bn_tsize_panel(interval: str = "1d", coins: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Dataset "bnts": coins with trade-size buckets from aggTrades (kripto/tsize.py; scripts/aggtrades.py builds them).
    1d: the daily Binance panel plus `ts_delta` / `ts_vol` = taker delta / volume per size bin, columns (coin, bin 0..11).
    5m: 5-minute bars plus `d_small` (trades < 30k USD) and `d_large` (>= 60k USD) taker delta per bar."""
    from . import tsize
    coins = [c for c in (coins or TSIZE_COINS) if (tsize.DIR / f"{c}USDT.npz").exists()]
    if interval == "1d":
        p = load_bn_all_panel([c + "USDT" for c in coins])
        d, v = {}, {}
        for c in coins:
            dd, vv = tsize.frames(c + "USDT", "fine12", "1D")
            for b in dd.columns:
                d[(c, b)], v[(c, b)] = dd[b], vv[b]
        p["ts_delta"] = pd.DataFrame(d).reindex(p["close"].index)
        p["ts_vol"] = pd.DataFrame(v).reindex(p["close"].index)
        first = p["ts_vol"].dropna(how="all").index[0]
        return {k: x[x.index >= first] for k, x in p.items()}
    assert interval == "5m", "bnts is 1d or 5m"
    p = load_bn_minute_panel(coins, rule="5min")
    ds, dl = {}, {}
    for c in coins:
        dd, _ = tsize.frames(c + "USDT", "small_large", "5min")
        ds[c], dl[c] = dd[0], dd[1]
    p["d_small"] = pd.DataFrame(ds).reindex(p["close"].index).astype("float32")
    p["d_large"] = pd.DataFrame(dl).reindex(p["close"].index).astype("float32")
    return p


def load_panel(ds: str, interval: str = "4h") -> dict[str, pd.DataFrame]:
    """Research datasets by name: hl, bn (hand-picked 82, survivor-biased), bnall / hlx / pair (daily only),
    bnts (trade-size buckets, 1d or 5m), bnm (1-minute bars, 10 coins)."""
    if ds == "bnts":
        return load_bn_tsize_panel(interval)
    if ds == "bnm":
        assert interval == "1m", "bnm is 1-minute data: use --interval 1m"
        return load_bn_minute_panel()
    if ds in ("bnall", "hlx", "pair"):
        assert interval == "1d", f"{ds} is daily: use --interval 1d"
        return {"bnall": load_bn_all_panel, "hlx": load_hl_bnflow_panel, "pair": load_pair_panel}[ds]()
    return load_hl_panel(interval) if ds == "hl" else load_bn_panel(interval)
