"""InSilico second pass, liquidation fade split by open interest (research/insilico_pass2.md section 3, L1). Descriptive.

  nice -n 19 .venv/bin/python -m research.studies.is2_liq download [explore|rep]   # 5-min open interest -> data/bn/metrics/
  nice -n 19 .venv/bin/python -m research.studies.is2_liq explore

The author's reason for the bounce is FORCED selling: liquidations sweep the book and destroy open interest; a news dump is
sold by people opening shorts, which creates it. The first-pass trigger could not tell the two apart. Here every first-pass
trigger (kripto.events.lshock, long side, e=1.0, z=4 so there are enough events to split) is labelled with the change in
open interest across the dump: OI at the first 5-minute stamp AFTER the entry minus OI 30 minutes before it (`after`: needs
a live OI poll at entry, which Binance serves in real time) and, strictly causal, the last stamp at or before the entry
(`causal`). Source: data.binance.vision daily `metrics` files (public, ~12 kB per coin-day, 2020-09 onward).
"""
from __future__ import annotations

import io
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests

from kripto import data
from kripto import events as ev

DIR = data.DATA / "bn" / "metrics"
URL = "https://data.binance.vision/data/futures/um/daily/metrics/{s}/{s}-metrics-{d}.zip"
REP = "DOT BCH TRX ATOM ETC XLM FIL NEAR UNI AAVE MATIC ARB OP APT SUI INJ SAND MANA AXS FTM".split()
SETS = {"explore": (data.MINUTE_COINS, "2021-01-01", "2023-12-31"), "rep": (REP, "2021-01-01", "2026-10-31"),
        "test10_late": (data.MINUTE_COINS, "2024-01-01", "2026-10-31")}


def download(which: str):
    coins, start, end = SETS[which]
    DIR.mkdir(parents=True, exist_ok=True)
    days = [str(d.date()) for d in pd.date_range(start, end, freq="1D")]
    s = requests.Session()

    def one(args):
        sym, day = args
        for _ in range(4):
            try:
                r = s.get(URL.format(s=sym, d=day), timeout=30)
                if r.status_code == 404:
                    return None
                if r.ok:
                    z = zipfile.ZipFile(io.BytesIO(r.content))
                    df = pd.read_csv(z.open(z.namelist()[0]))
                    return df[["create_time", "sum_open_interest", "sum_open_interest_value"]]
            except Exception:
                pass
        return None
    for coin in coins:
        f = DIR / f"{coin}USDT.parquet"
        have = pd.read_parquet(f) if f.exists() else None
        got = set(pd.to_datetime(have["t"]).dt.strftime("%Y-%m-%d")) if have is not None else set()
        todo = [(coin + "USDT", d) for d in days if d not in got]
        with ThreadPoolExecutor(8) as ex:
            parts = [x for x in ex.map(one, todo) if x is not None]
        if parts:
            df = pd.concat(parts)
            df = pd.DataFrame({"t": pd.to_datetime(df["create_time"], utc=True), "oi": df["sum_open_interest"].astype(float),
                               "oiv": df["sum_open_interest_value"].astype(float)})
            if have is not None:
                df = pd.concat([have, df])
            df.drop_duplicates("t").sort_values("t").reset_index(drop=True).to_parquet(f)
        print(f"[metrics] {coin}: {0 if not f.exists() else len(pd.read_parquet(f, columns=['t']))} rows (+{len(parts)} days)", flush=True)


def tstat(x) -> float:
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


def tday(net: pd.Series, day: pd.Series) -> float:
    return tstat(net.groupby(day.values).sum())


def label(which: str, z=4.0, halves=None) -> pd.DataFrame:
    coins, start, end = SETS[which]
    out = []
    for group in (halves or [coins]):
        P = data.load_bn_minute_panel(group, start=start)
        P = {k: v[v.index <= end + " 23:59"] for k, v in P.items()}
        res = ev.lshock(P, z=z, m=5, e=1.0)
        t = res.trades
        if not len(t):
            continue
        t = t.assign(coin=[P["close"].columns[i] for i in t.coin], net=t.gross - t.cost, day=t.time.dt.floor("D"))
        d_after, d_causal = [], []
        for coin, g in t.groupby("coin"):
            f = DIR / f"{coin}USDT.parquet"
            if not f.exists():
                d_after += [(i, np.nan) for i in g.index]
                d_causal += [(i, np.nan) for i in g.index]
                continue
            m = pd.read_parquet(f).set_index("t")["oi"]
            m = m[~m.index.duplicated()].sort_index()
            for i, tm in zip(g.index, g.time):
                tm = tm + pd.Timedelta(minutes=1)                     # entry = close of the signal minute
                base = m.asof(tm - pd.Timedelta(minutes=30))
                nxt = m[m.index >= tm]
                a = nxt.iloc[0] if len(nxt) and (nxt.index[0] - tm) <= pd.Timedelta(minutes=6) else np.nan
                d_after.append((i, a / base - 1 if base and np.isfinite(base) else np.nan))
                d_causal.append((i, m.asof(tm) / base - 1 if base and np.isfinite(base) else np.nan))
        t["doi"] = pd.Series(dict(d_after))
        t["doi_causal"] = pd.Series(dict(d_causal))
        t["n_day"] = t.groupby("day").coin.transform("size")
        out.append(t)
        del P
    return pd.concat(out)


def table(t: pd.DataFrame, title: str):
    print(title)

    def row(name, g):
        if len(g) < 5:
            print(f"   {name:46s} n={len(g)}")
            return
        print(f"   {name:46s} n={len(g):5d} win={float((g.net > 0).mean()):5.1%} net={g.net.mean() * 1e4:+7.1f} bp "
              f"median={g.net.median() * 1e4:+6.1f} t/trade={tstat(g.net):+5.2f} t/day={tday(g.net, g.day):+5.2f} days={g.day.nunique()}")
    row("all triggers", t)
    row("open interest missing", t[t.doi.isna()])
    for col in ("doi", "doi_causal"):
        x = t.dropna(subset=[col])
        print(f"  by {col} (change in open interest across the dump):")
        row("  fell by more than 2%", x[x[col] < -0.02])
        row("  fell 0.5% to 2%", x[(x[col] >= -0.02) & (x[col] < -0.005)])
        row("  flat (-0.5% to +0.5%)", x[x[col].abs() <= 0.005])
        row("  rose by more than 0.5%", x[x[col] > 0.005])
    x = t.dropna(subset=["doi"])
    print("  the question: does falling open interest rescue the days with only one or two triggers?")
    row("  1-2 triggers that day, OI fell > 0.5%", x[(x.n_day <= 2) & (x.doi < -0.005)])
    row("  1-2 triggers that day, OI did not fall", x[(x.n_day <= 2) & (x.doi >= -0.005)])
    row("  5+ triggers that day, OI fell > 0.5%", x[(x.n_day >= 5) & (x.doi < -0.005)])
    row("  5+ triggers that day, OI did not fall", x[(x.n_day >= 5) & (x.doi >= -0.005)])
    f = x[x.doi < -0.005]
    if len(f) > 10:
        d = f.groupby("day").net.sum().sort_values(ascending=False)
        print(f"  OI fell > 0.5%: top-3 days = {d.head(3).sum() / d.sum():.0%} of P&L; without them net "
              f"{f[~f.day.isin(d.head(3).index)].net.mean() * 1e4:+.1f} bp (t/day {tday(f[~f.day.isin(d.head(3).index)].net, f[~f.day.isin(d.head(3).index)].day):+.2f})")
        print("  by year (n, net bp):", {int(y): (len(g), round(float(g.net.mean() * 1e4), 1)) for y, g in f.groupby(f.time.dt.year)})


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "download":
        download(sys.argv[2] if len(sys.argv) > 2 else "explore")
    else:
        which = cmd
        halves = [REP[:10], REP[10:]] if which == "rep" else None
        for z in (4.0, 6.0):
            table(label(which, z=z, halves=halves), f"== {which}: lshock triggers z={z:g}, m=5, e=1.0, long, net of costs")
