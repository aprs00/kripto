"""N3 c / i / j on COINS10 Binance 1-min klines, explore 2021-2023.
c  change of character: taker delta negative for 6 bars in a row, then positive for 6 bars in a row (1h, 4h) -> long 6 bars, vs same
   coin at the same trailing-14-bar return decile (matched); mirror -> short.
i  'higher-timeframe trend as a filter is false' (tg:196): 1h momentum (sign of the 24-h return) held 6 h, split by agreement with the
   20-day trend sign; the claim predicts no difference.
j  last minutes painted: |return of minutes 55-60| >= 1.5 x its 30-day sd, on below-median 5-min volume of that hour, against the taker
   delta of minutes 0-55 -> fade over the next 60 min; placebo = the same at minutes 25-30.

    nice -n 19 .venv/bin/python -m research.studies.is3_n3m     -> research/is3/N3m__explore.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
LO, HI = "2021-01-01", "2024-01-01"
COLS = ["time", "coin", "side", "gross"]


def main() -> dict:
    C, I, J = [], [], []
    for coin in L.COINS10:
        k = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet", columns=["t", "c", "qv", "tbqv"])
        k.index = pd.to_datetime(k.t, unit="ms", utc=True)
        k = k[(k.index >= "2020-11-01") & (k.index < "2024-01-10")]
        for tf in ("1h", "4h"):
            c = k.c.resample(tf).last().ffill(); d = (2 * k.tbqv - k.qv).resample(tf).sum()
            neg = (d < 0).astype(int); pos = (d > 0).astype(int)
            n6 = neg.rolling(6).sum().shift(6) == 6; p6 = pos.rolling(6).sum() == 6
            m6 = pos.rolling(6).sum().shift(6) == 6; q6 = neg.rolling(6).sum() == 6
            f6 = c.shift(-6) / c - 1; r14 = c / c.shift(14) - 1
            df = pd.DataFrame({"time": c.index, "coin": coin, "tf": tf, "f6": f6.to_numpy(), "ret14": r14.to_numpy(),
                               "up": (n6 & p6).to_numpy(), "dn": (m6 & q6).to_numpy()})
            C.append(df[(df.time >= LO) & (df.time < HI)].dropna(subset=["f6", "ret14"]))
        # i
        h = k.c.resample("1h").last().ffill()
        dd = k.c.resample("1D").last().ffill()
        tr = np.sign(dd / dd.shift(20) - 1).shift(1).reindex(h.index, method="ffill")
        mom = np.sign(h / h.shift(24) - 1)
        f6 = h.shift(-6) / h - 1
        x = pd.DataFrame({"time": h.index, "coin": coin, "side": mom.to_numpy(), "agree": (mom == tr).to_numpy(), "gross": (mom * f6).to_numpy()})
        x = x[(x.time >= LO) & (x.time < HI) & (x.side != 0)].dropna()
        I.append(x.iloc[::6])                                   # one decision per 6 h (non-overlapping)
        # j
        b5 = pd.DataFrame({"c": k.c.resample("5min").last().ffill(), "v": k.qv.resample("5min").sum(), "d": (2 * k.tbqv - k.qv).resample("5min").sum()})
        r5 = b5.c.pct_change(fill_method=None)
        sd = r5.rolling(8640, min_periods=2000).std().shift(1)
        hour = b5.index.floor("h")
        vmed = b5.v.groupby(hour).transform("median")
        minute = b5.index.minute
        cv = b5.c.to_numpy()
        for slot, tag in ((55, "last5"), (25, "placebo_25_30")):
            idx = np.flatnonzero((minute == slot) & (np.abs(r5) >= 1.5 * sd).to_numpy() & (b5.v < vmed).to_numpy())
            for i_ in idx:
                if i_ < 12 or i_ + 13 >= len(cv):
                    continue
                dprior = b5.d.iloc[i_ - 11:i_].sum() if slot == 55 else b5.d.iloc[i_ - 5:i_].sum()
                push = np.sign(r5.iloc[i_])
                if np.sign(dprior) == push or dprior == 0:
                    continue
                t = b5.index[i_]
                if not (pd.Timestamp(LO, tz="UTC") <= t < pd.Timestamp(HI, tz="UTC")):
                    continue
                J.append({"time": t, "coin": coin, "side": -int(push), "tag": tag, "gross": -push * (cv[i_ + 12] / cv[i_] - 1)})
    res = {}
    c = pd.concat(C, ignore_index=True)
    for tf in ("1h", "4h"):
        x = c[c.tf == tf].copy()
        x["m"] = (x.groupby("coin").ret14.rank(pct=True) * 9.999).astype(int)
        for col, side in (("up", 1), ("dn", -1)):
            e, pool = x[x[col]], x[~x[col]]
            base = L.matched(e, pool, k=3)
            s = L.stats(e.assign(side=side, gross=e.f6 * side)[COLS], base.assign(side=side, gross=base.f6 * side)[COLS], reps=500)
            res[f"c_{tf}_{col}"] = {"n": s["n"], "mean_bp": s["mean_bp"], "matched_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
    i = pd.concat(I, ignore_index=True)
    s = L.stats(i[i.agree][COLS], i[~i.agree][COLS], reps=500)
    res["i_1h_momentum_agree_vs_disagree_daily_trend"] = {"n_agree": s["n"], "agree_bp": s["mean_bp"], "n_disagree": int((~i.agree).sum()), "disagree_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
    s0 = L.stats(i[COLS], reps=500)
    res["i_1h_momentum_unsplit"] = {"n": s0["n"], "mean_bp": s0["mean_bp"], "p": s0["p"]}
    j = pd.DataFrame(J)
    s = L.stats(j[j.tag == "last5"][COLS], j[j.tag != "last5"][COLS], reps=1000)
    res["j_painted_last5_fade_60m"] = {"n": s["n"], "mean_bp": s["mean_bp"], "placebo_bp": s["base_bp"], "n_placebo": int((j.tag != "last5").sum()), "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
    for k_, v_ in res.items():
        print(k_, v_)
    (ROOT / "research/is3/N3m__explore.json").write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    main()
