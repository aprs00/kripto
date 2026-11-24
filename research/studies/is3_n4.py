"""N4 lead-lag (R32, R33; wa 18.10.49, tg:114-116), explore 2021-2023, Binance 1-min klines of every coin on the server.
a  5-min returns: equal-weight thin (bottom volume tercile) and thick (top tercile, excl. BTC) baskets; corr(BTC[t], thin[t-k]) vs
   corr(thin[t], BTC[t-k]) for k = 1..12 bars; sign trade: BTC next 5 min signed by the thin basket's last 5 min, vs the reverse.
b  daily: correlation of 5-min alt-basket and BTC returns within the day; z vs its 30-day mean; next-day BTC |return| and return by
   quintile; thin-minus-BTC daily return -> next-day BTC return.
c  1-min tail asymmetry: counts of moves <= -k and >= +k x 24-h sigma (k = 5 / 8 / 12) per coin-year, down/up ratio.

    nice -n 19 .venv/bin/python -m research.studies.is3_n4      -> research/is3/N4__explore.json
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from research.studies import is3_lib as L

ROOT = Path(__file__).resolve().parents[2]
LO, HI = "2021-01-01", "2024-01-01"


def main() -> dict:
    files = sorted(glob.glob(str(ROOT / "data/bn/klines_1m/*USDT.parquet")))
    R5, VOL, TAIL = {}, {}, []
    for f in files:
        coin = os.path.basename(f)[:-12]
        k = pd.read_parquet(f, columns=["t", "c", "qv"])
        k.index = pd.to_datetime(k.t, unit="ms", utc=True)
        k = k[(k.index >= LO) & (k.index < HI)]
        if len(k) < 200_000:
            continue
        c5 = k.c.resample("5min").last()
        R5[coin] = c5.pct_change(fill_method=None).astype("float32")
        VOL[coin] = float(k.qv.mean())
        r1 = np.log(k.c).diff()
        sig = r1.rolling(1440, min_periods=720).std().shift(1)
        z = (r1 / sig).dropna()
        for y, g in z.groupby(z.index.year):
            row = {"coin": coin, "year": int(y)}
            for kk in (5, 8, 12):
                row[f"dn{kk}"] = int((g <= -kk).sum()); row[f"up{kk}"] = int((g >= kk).sum())
            TAIL.append(row)
    R = pd.DataFrame(R5)
    v = pd.Series(VOL).drop("BTC")
    q = pd.qcut(v.rank(method="first"), 3, labels=["thin", "mid", "thick"])
    thin = R[q[q == "thin"].index].mean(axis=1); thick = R[q[q == "thick"].index].mean(axis=1); btc = R["BTC"]
    res = {"n_coins": int(len(R.columns)), "thin_coins": int((q == "thin").sum())}
    cc = {}
    for kk in range(1, 13):
        cc[kk] = {"thin_leads_btc": round(float(btc.corr(thin.shift(kk))), 4), "btc_leads_thin": round(float(thin.corr(btc.shift(kk))), 4),
                  "thick_leads_btc": round(float(btc.corr(thick.shift(kk))), 4), "btc_leads_thick": round(float(thick.corr(btc.shift(kk))), 4)}
    res["a_crosscorr_by_lag_5min"] = cc
    print("lag1", cc[1], "lag2", cc[2])
    df = pd.DataFrame({"time": btc.index, "coin": "BTC", "s_thin": np.sign(thin.to_numpy()), "s_btc": np.sign(btc.to_numpy()),
                       "btc_next": btc.shift(-1).to_numpy(), "thin_next": thin.shift(-1).to_numpy()}).dropna()
    a1 = df.assign(side=df.s_thin, gross=df.s_thin * df.btc_next)
    a2 = df.assign(side=df.s_btc, gross=df.s_btc * df.thin_next)
    s1, s2 = L.stats(a1[["time", "coin", "side", "gross"]], reps=300), L.stats(a2[["time", "coin", "side", "gross"]], reps=300)
    res["a_sign_trade_5min"] = {"btc_next_signed_by_thin_bp": s1["mean_bp"], "p": s1["p"], "thin_next_signed_by_btc_bp": s2["mean_bp"], "p2": s2["p"]}
    print(res["a_sign_trade_5min"])
    # b
    alts = R.drop(columns="BTC").mean(axis=1)
    day = R.index.floor("D")
    corr = pd.DataFrame({"a": alts, "b": btc}).groupby(day).apply(lambda g: g.a.corr(g.b))
    bd = (1 + btc).groupby(day).prod() - 1
    td = (1 + thin).groupby(day).prod() - 1
    zc = (corr - corr.rolling(30).mean().shift(1)) / corr.rolling(30).std().shift(1)
    x = pd.DataFrame({"zc": zc, "nb": bd.shift(-1), "div": td - bd}).dropna()
    qq = pd.qcut(x.zc.rank(method="first"), 5, labels=False)
    res["b_next_day_btc_abs_by_corr_drop_quintile_bp"] = [round(float(x[qq == i].nb.abs().mean() * 1e4), 1) for i in range(5)]
    res["b_next_day_btc_ret_by_corr_drop_quintile_bp"] = [round(float(x[qq == i].nb.mean() * 1e4), 1) for i in range(5)]
    ev = pd.DataFrame({"time": x.index, "coin": "BTC", "side": np.sign(x["div"]).to_numpy(), "gross": (np.sign(x["div"]) * x.nb).to_numpy()})
    s = L.stats(ev, reps=1000)
    res["b_divergence_sign_trade_next_day"] = {"days": s["n"], "mean_bp": s["mean_bp"], "ci95_bp": s["ci95_bp"], "p": s["p"], "mde_bp": s["mde80_bp"]}
    print(res["b_next_day_btc_abs_by_corr_drop_quintile_bp"], res["b_next_day_btc_ret_by_corr_drop_quintile_bp"], res["b_divergence_sign_trade_next_day"])
    t = pd.DataFrame(TAIL)
    agg = t.groupby("year")[[c for c in t.columns if c[:2] in ("dn", "up")]].sum()
    res["c_tail_counts_by_year"] = {int(y): {f"k{kk}": {"down": int(r[f"dn{kk}"]), "up": int(r[f"up{kk}"]), "ratio": round(r[f"dn{kk}"] / max(r[f"up{kk}"], 1), 2)} for kk in (5, 8, 12)} for y, r in agg.iterrows()}
    share = (t.dn8 > t.up8).groupby(t.year).mean()
    res["c_share_of_coins_with_more_down_than_up_8sigma"] = {int(y): round(float(v_), 3) for y, v_ in share.items()}
    print(res["c_tail_counts_by_year"], res["c_share_of_coins_with_more_down_than_up_8sigma"])
    (ROOT / "research/is3/N4__explore.json").write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    main()
