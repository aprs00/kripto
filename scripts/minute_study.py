"""Event study of intraday ideas from the library on 1-minute Binance bars (spec: research/batches/2026-11-10-minute-study.json).

  nice -n 19 .venv/bin/python -m scripts.minute_study            # downloads what is missing, prints the table,
                                                                 # writes research/minute_study.json
Descriptive only: conditional forward returns, no portfolio, no costs applied (the cost bar is printed next to the table).
Data: data/bn/klines_1m/<SYMBOL>.parquet from the public archive data.binance.vision (gitignored)."""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from kripto import data

ROOT = Path(__file__).resolve().parent.parent
DIR = data.DATA / "bn" / "klines_1m"
COINS = "BTC ETH SOL XRP DOGE BNB ADA AVAX LINK SUI HYPE 1000PEPE WIF ENA TAO WLD TIA SEI NEAR LTC".split()
MONTHS = ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]
SPLIT = "2026-08-01"
HORIZONS = (1, 5, 15, 60)
COST_BP = 12.0


def download(coins=COINS, months=MONTHS, log=print):
    DIR.mkdir(parents=True, exist_ok=True)

    def one(coin):
        p = DIR / f"{coin}USDT.parquet"
        have = pd.read_parquet(p) if p.exists() else None
        got = set(pd.to_datetime(have["t"], unit="ms").dt.strftime("%Y-%m")) if have is not None else set()
        parts = [have] if have is not None else []
        for m in months:
            if m in got:
                continue
            b = data._bn_get(f"{data.BN_BASE}/klines/{coin}USDT/1m/{coin}USDT-1m-{m}.zip")
            if b:
                df = data._read_zip_csv(b).iloc[:, [0, 2, 3, 4, 7, 8, 10]]
                df.columns = ["t", "h", "l", "c", "qv", "n", "tbqv"]
                parts.append(df.apply(pd.to_numeric, errors="coerce").dropna())
        if len(parts) > (1 if have is not None else 0):
            d = pd.concat(parts).drop_duplicates("t", keep="last").sort_values("t").reset_index(drop=True)
            d["t"] = d["t"].astype("int64")
            d.to_parquet(p)
        return coin, 0 if not p.exists() else len(pd.read_parquet(p, columns=["t"]))
    with ThreadPoolExecutor(6) as ex:
        for coin, n in ex.map(one, coins):
            log(f"[1m] {coin}: {n} bars")


def panel(coins=COINS) -> dict[str, pd.DataFrame]:
    out = {k: {} for k in ("c", "h", "l", "qv", "tbqv")}
    for coin in coins:
        p = DIR / f"{coin}USDT.parquet"
        if not p.exists():
            continue
        df = pd.read_parquet(p)
        t = df["t"].where(df["t"] < 1e14, df["t"] // 1000)
        df.index = pd.to_datetime(t, unit="ms", utc=True)
        df = df[~df.index.duplicated()]
        for k in out:
            out[k][coin] = df[k]
    return {k: pd.DataFrame(v).sort_index() for k, v in out.items()}


def zscore(x: pd.DataFrame | pd.Series, window: int):
    m = x.rolling(window, min_periods=window // 4).mean()
    s = x.rolling(window, min_periods=window // 4).std()
    return (x - m.shift(1)) / s.shift(1)          # compared with the PAST distribution only


def study(P: dict) -> list[dict]:
    C, H, L, V, TB = P["c"], P["h"], P["l"], P["qv"], P["tbqv"]
    lc = np.log(C)
    r1 = lc.diff()
    fwd = {h: lc.shift(-h) - lc for h in HORIZONS}
    day, week = 1440, 10080
    sig: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}       # name -> (event mask, direction)

    for k in (5, 15, 60):
        imb = (2 * TB - V).rolling(k).sum() / V.rolling(k).sum()
        z = zscore(imb, week)
        rk = lc - lc.shift(k)
        ev = z.abs() > 3
        sig[f"A flow continuation, {k}-min imbalance"] = (ev, np.sign(z))
        sig[f"B absorption (flow extreme, price did not follow), {k}-min"] = (ev & (np.sign(rk) != np.sign(z)), np.sign(z))
    hi, lo = H.shift(1).rolling(240).max(), L.shift(1).rolling(240).min()
    up_fail, dn_fail = (H > hi) & (C < hi), (L < lo) & (C > lo)
    sig["C sweep of the 4h high/low that closes back inside (fade)"] = (up_fail | dn_fail, dn_fail.astype(float) - up_fail.astype(float))
    up_ok, dn_ok = C > hi, C < lo
    sig["C close beyond the 4h high/low (follow)"] = (up_ok | dn_ok, up_ok.astype(float) - dn_ok.astype(float))
    alts = [c for c in C.columns if c != "BTC"]
    for k in (1, 5):
        zb = zscore(lc["BTC"] - lc["BTC"].shift(k), day)
        ev = pd.DataFrame(np.broadcast_to((zb.abs() > 4).to_numpy()[:, None], (len(C), len(alts))), C.index, alts)
        dr = pd.DataFrame(np.broadcast_to(np.sign(zb).to_numpy()[:, None], (len(C), len(alts))), C.index, alts)
        sig[f"D alts after a 4-sigma BTC move over {k} min (follow BTC)"] = (ev, dr)
    r15 = lc - lc.shift(15)
    breadth = (r15 > 0).sum(axis=1) / r15.notna().sum(axis=1)
    mz = zscore(r15.mean(axis=1), day)
    ev = ((breadth >= 0.9) & (mz > 3)) | ((breadth <= 0.1) & (mz < -3))
    sig["E breadth extreme, 90% of coins one way over 15 min (follow)"] = (
        pd.DataFrame(np.broadcast_to(ev.to_numpy()[:, None], C.shape), C.index, C.columns),
        pd.DataFrame(np.broadcast_to(np.sign(mz).to_numpy()[:, None], C.shape), C.index, C.columns))
    z1 = zscore(r1, day)
    sig["F volume spike 10x with a 3-sigma minute (follow)"] = ((V > 10 * V.rolling(day).mean().shift(1)) & (z1.abs() > 3), np.sign(r1))
    z5 = zscore(lc - lc.shift(5), day)
    sig["G 4-sigma move over 5 min (fade)"] = (z5.abs() > 4, -np.sign(z5))

    rows = []
    for name, (ev, dr) in sig.items():
        ev = ev.reindex(columns=C.columns, fill_value=False).fillna(False)
        dr = dr.reindex(columns=C.columns).fillna(0.0)
        row = {"signal": name, "events_per_day": round(float(ev.sum().sum() / (len(C) / day)), 1)}
        for half, sel in (("h1", C.index < SPLIT), ("h2", C.index >= SPLIT)):
            for h in HORIZONS:
                x = (fwd[h] * dr).where(ev)[sel]
                daily = x.stack().groupby(level=0).mean().resample("1D").mean().dropna() * 1e4
                mean = float(x.stack().mean() * 1e4) if x.notna().any().any() else float("nan")
                t = float(daily.mean() / daily.std() * np.sqrt(len(daily))) if len(daily) > 5 and daily.std() > 0 else float("nan")
                row[f"{half}_{h}m_bp"], row[f"{half}_{h}m_t"] = round(mean, 1), round(t, 1)
        rows.append(row)
    mkt = r1.mean(axis=1)
    hourly = mkt.groupby([mkt.index.floor("1h")]).sum() * 1e4
    by = hourly.groupby(hourly.index.hour)
    seas = pd.DataFrame({"bp": by.mean(), "t": by.mean() / by.std() * np.sqrt(by.count())}).round(1)
    rows.append({"signal": "H hour-of-day (UTC) market return, bp per hour", "hours": {int(k): [float(v.bp), float(v.t)] for k, v in seas.iterrows()}})
    return rows


if __name__ == "__main__":
    if "--no-download" not in sys.argv:
        download()
    P = panel()
    print(f"panel: {P['c'].shape[1]} coins, {len(P['c'])} minutes, {P['c'].index[0]} to {P['c'].index[-1]}")
    rows = study(P)
    (ROOT / "research" / "minute_study.json").write_text(json.dumps({"cost_bp": COST_BP, "rows": rows}, indent=1))
    print(f"signed forward return in bp (t on daily means) | first half May-Jul / second half Aug-Oct | cost of a round trip ~{COST_BP:.0f} bp")
    for r in rows[:-1]:
        print(f"\n{r['signal']}  [{r['events_per_day']} events/day]")
        for h in HORIZONS:
            print(f"   +{h:>2d} min: {r[f'h1_{h}m_bp']:+7.1f} (t {r[f'h1_{h}m_t']:+5.1f})   /   {r[f'h2_{h}m_bp']:+7.1f} (t {r[f'h2_{h}m_t']:+5.1f})")
    hrs = rows[-1]["hours"]
    print("\nH hour-of-day (UTC), bp per hour (t): " + "  ".join(f"{k:02d}h {v[0]:+.1f}({v[1]:+.1f})" for k, v in hrs.items()))
