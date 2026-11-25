"""C1 cost calibration (assumptions rows 1 and 20): live paper fills vs the backtest's slippage model.

Per live fill (shadow/main books on HL and Binance; pair and ladder books excluded):
  live_slip  = fills.slip_bps (fill px vs mid at the fill, signed cost; the depth walk)
  drift      = mid at the fill vs the decision bar's close (research/studies/fill_delay.py), signed cost; 4h-bar runs only
  model      = backtest.slippage_model at the fill: 3 bp * sqrt($50M / trailing 7-day mean USD volume), clipped 1.5..25 bp
Notional-weighted means per venue and per volume bucket, and the ratio live/model. Fees are not part of either side.
  usage: nice -n 19 .venv/bin/python -m scripts.cost_calibration [--since 2026-11-10]
"""
import sqlite3
import sys

import numpy as np
import pandas as pd

from kripto import data, paper as P, venue_bn
from research.studies.fill_delay import closes


def usd_volume(venue: str, coin: str) -> pd.Series | None:
    if venue == "hl":
        f = data.DATA / "hl" / "candles_1d" / f"{coin}.parquet"
        if not f.exists():
            return None
        d = pd.read_parquet(f)
        s = pd.Series((d["v"].astype(float) * d["c"].astype(float)).to_numpy(), pd.to_datetime(d["t"], unit="ms", utc=True))
    else:
        f = data.DATA / "bn" / "klines_1d_all" / f"{coin}USDT.parquet"
        if not f.exists():
            return None
        d = pd.read_parquet(f)
        s = pd.Series(d["qv"].astype(float).to_numpy(), pd.to_datetime(d["t"], unit="ms", utc=True))
    return s[s > 0].sort_index()


def model_bps(dv: float) -> float:
    return float(np.clip(3.0 * np.sqrt(50e6 / max(dv, 1e4)), 1.5, 25.0)) if np.isfinite(dv) else np.nan


def wmean(x, w):
    m = np.isfinite(x) & np.isfinite(w)
    return float(np.average(x[m], weights=w[m])) if m.any() else float("nan")


def main():
    since = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv else "2026-11-01"
    c = sqlite3.connect(f"file:{P.DB}?mode=ro", uri=True)
    f = pd.read_sql("select * from fills where (book like 'shadow:%' or book like 'main%') and book not like '%@pair' "
                    "and book not like '%ladder%'", c)
    f["ts"] = pd.to_datetime(f["ts"], utc=True, format="ISO8601")
    f = f[f["ts"] >= pd.Timestamp(since, tz="UTC")].copy()
    f["venue"] = np.where(f["book"].str.endswith("@bn") | (f["book"] == "main_bn"), "bn", "hl")
    f["ntl"] = (f["size"] * f["px"]).abs()
    vols, refs, dvs = {}, {}, []
    for v, coin, ts in zip(f["venue"], f["coin"], f["ts"]):
        if (v, coin) not in vols:
            vols[v, coin] = usd_volume(v, coin)
        s = vols[v, coin]
        if s is None:
            dvs.append(np.nan)
            continue
        win = s[(s.index < ts.floor("D")) & (s.index >= ts.floor("D") - pd.Timedelta(days=7))]
        dvs.append(win.mean() if len(win) else np.nan)
    f["dv"] = dvs
    f["model"] = [model_bps(x) for x in f["dv"]]
    f["bar"] = f["ts"].dt.floor("4h")
    f["delay_min"] = (f["ts"] - f["bar"]).dt.total_seconds() / 60
    ref = []
    for v, coin, b, dm in zip(f["venue"], f["coin"], f["bar"], f["delay_min"]):
        if dm > 60:
            ref.append(np.nan)
            continue
        if (v, coin) not in refs:
            refs[v, coin] = closes(v, coin)
        s = refs[v, coin]
        ref.append(s.get(b, np.nan) if s is not None else np.nan)
    f["drift"] = np.sign(f["size"]) * (f["mid"] / np.asarray(ref, float) - 1) * 1e4
    print(f"C1 cost calibration | fills since {since}: {len(f)} | days {f['ts'].dt.floor('D').nunique()} | "
          f"{f['ts'].min():%Y-%m-%d} .. {f['ts'].max():%Y-%m-%d}")
    for v, g in f.groupby("venue"):
        n, w = g["ntl"].to_numpy(), g
        ls, md, dr = wmean(g["slip_bps"].to_numpy(), n), wmean(g["model"].to_numpy(), n), wmean(g["drift"].to_numpy(), n)
        print(f"\n{v}: fills {len(g)} notional ${n.sum():,.0f} median order ${np.median(n):.0f} | notional-weighted bp: live slip {ls:.1f}, "
              f"model {md:.1f} (ratio {ls / md:.2f}); drift {dr:+.1f} on {g['drift'].notna().sum()} fills -> live slip+drift {ls + dr:.1f} vs model {md:.1f}")
        g = g.assign(bucket=pd.cut(g["dv"], [0, 5e6, 2e7, 1e8, 5e8, np.inf], labels=["<5M", "5-20M", "20-100M", "100-500M", ">500M"]))
        for b, h in g.groupby("bucket", observed=True):
            hn = h["ntl"].to_numpy()
            print(f"   ADV {b:>8s}: fills {len(h):4d}  live slip {wmean(h['slip_bps'].to_numpy(), hn):5.1f}  model {wmean(h['model'].to_numpy(), hn):5.1f}"
                  f"  p90 live {np.nanpercentile(h['slip_bps'], 90):5.1f}  drift {wmean(h['drift'].to_numpy(), hn):+6.1f}")
        day = g.groupby(g["ts"].dt.floor("D")).apply(lambda x: pd.Series({"slip": wmean(x["slip_bps"].to_numpy(), x["ntl"].to_numpy()),
                                                                          "model": wmean(x["model"].to_numpy(), x["ntl"].to_numpy())}), include_groups=False)
        print("   by day (live/model): " + " ".join(f"{d:%m-%d} {r.slip:.1f}/{r.model:.1f}" for d, r in day.iterrows()))


if __name__ == "__main__":
    main()
