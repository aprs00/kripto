"""W3B a/b: fade the 12->18 NY 6-h move of BTC and ETH for 24 h (tranches: decisions at 17/18/19 NY, move over the 6 h before), by weekday (Sunday = the claim,
the other six = placebo). Simple returns, funding ignored (+-1 bp/day). Per-day mean over coins and tranches; t over days. notes.md W3B.
    PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_w3b [confirm]"""
import json, sys
import numpy as np
import pandas as pd
from kripto.data import BN100_DIR

COST = 12e-4
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def px(coin):
    df = pd.read_parquet(BN100_DIR / f"{coin}USDT.parquet", columns=["t", "c"])
    t = df["t"].where(df["t"] < 1e14, df["t"] // 1000)
    s = pd.Series(df["c"].to_numpy(), pd.to_datetime(t, unit="ms", utc=True) + pd.Timedelta(hours=1))
    return s[~s.index.duplicated()].sort_index()


def main():
    conf = "confirm" in sys.argv
    lo, hi = ("2024-01-01", "2026-10-31") if conf else ("2020-02-15", "2023-12-31")
    S = {c: px(c) for c in ("BTC", "ETH")}
    hrs = pd.date_range(lo, hi, freq="1h", tz="America/New_York")
    res, rows = {}, []
    for c, s in S.items():
        for h in (17, 18, 19):
            T = hrs[hrs.hour == h].tz_convert("UTC")
            m = s.reindex(T).to_numpy() / s.reindex(T - pd.Timedelta(hours=6)).to_numpy() - 1
            f = s.reindex(T + pd.Timedelta(hours=24)).to_numpy() / s.reindex(T).to_numpy() - 1
            rows.append(pd.DataFrame({"T": T, "day": T.tz_convert("America/New_York").normalize().tz_localize(None), "dow": T.tz_convert("America/New_York").day_of_week,
                                      "coin": c, "m": m, "o": -np.sign(m) * f}))
    e = pd.concat(rows).dropna()
    for thr in (0.005, 0.01, 0.02):
        x = e[e.m.abs() >= thr]
        for k, d in enumerate(DAYS):
            z = x[x.dow == k]
            dm = z.groupby("day")["o"].mean()
            t = float(dm.mean() / dm.std() * np.sqrt(len(dm))) if len(dm) > 3 else np.nan
            yrs = dm.groupby(dm.index.year).mean() * 1e4
            res[f"{d} |m|>={thr:.1%}"] = {"days": int(len(dm)), "mean_bp": round(float(dm.mean() * 1e4), 1), "med_bp": round(float(dm.median() * 1e4), 1),
                                          "t": round(t, 2), "net_bp": round(float((dm.mean() - COST) * 1e4), 1), "mde_bp": round(float(2.8 * dm.std() / np.sqrt(len(dm)) * 1e4), 0),
                                          "years": {int(a): round(float(v), 1) for a, v in yrs.items()}}
            print(f"{d} |m|>={thr:.1%}: {res[f'{d} |m|>={thr:.1%}']}", flush=True)
    json.dump({"study": "research/studies/is3_w3b.py", "window": [lo, hi], "res": res}, open(f"research/is3/w3b_{'confirm' if conf else 'explore'}.json", "w"), indent=1)


if __name__ == "__main__":
    main()
