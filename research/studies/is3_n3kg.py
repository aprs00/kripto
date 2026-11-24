"""N3 k / g on COINS10 1h and 4h bars (Binance 1-min klines), explore 2021-2023; baseline = same coin, matched bin, same side.
k  impulse with non-overlapping bars (wa 18.10.19(1)): 3 bars in a row each with low > the previous bar's midpoint and close > the
   previous high (mirror for down) -> ride: long at the close; outcomes: fixed 6 bars, and exit at the first bar whose low falls below
   the leg's midpoint (max 24 bars). Dose = efficiency ratio over the 3 bars' 6-bar window (quintiles). Matched bin = trailing 14-bar return decile.
g  change of character (wa 18.10.28(1)): after >= 4 new 20-bar highs within the last 8 bars, the first down bar whose body is larger than
   every down body of those 8 bars, on volume >= 2x the 24-bar median -> short 6 bars; baseline = down bars of the same body-size quintile
   (body / close) without the run.

    nice -n 19 .venv/bin/python -m research.studies.is3_n3kg    -> research/is3/N3kg__explore.json
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
    K, KP, G = [], [], []
    for coin in L.COINS10:
        m = pd.read_parquet(ROOT / "data/bn/klines_1m" / f"{coin}USDT.parquet", columns=["t", "h", "l", "c", "qv"])
        m.index = pd.to_datetime(m.t, unit="ms", utc=True)
        m = m[(m.index >= "2020-11-01") & (m.index < "2024-01-10")]
        for tf in ("1h", "4h"):
            c = m.c.resample(tf).last().ffill(); h = m.h.resample(tf).max(); l = m.l.resample(tf).min(); v = m.qv.resample(tf).sum()
            o = c.shift(1)
            mid = (h + l) / 2
            upb = (l > mid.shift(1)) & (c > h.shift(1)); dnb = (h < mid.shift(1)) & (c < l.shift(1))
            imp_up = upb & upb.shift(1, fill_value=False) & upb.shift(2, fill_value=False)
            imp_dn = dnb & dnb.shift(1, fill_value=False) & dnb.shift(2, fill_value=False)
            er = (c - c.shift(6)).abs() / c.diff().abs().rolling(6).sum()
            r14 = c / c.shift(14) - 1
            f6 = c.shift(-6) / c - 1
            cv, hv, lv = c.to_numpy(), h.to_numpy(), l.to_numpy()
            for mask, side in ((imp_up, 1), (imp_dn, -1)):
                for t in np.flatnonzero(mask.to_numpy()):
                    if t < 20 or t + 25 >= len(cv) or not (LO <= str(c.index[t]) < HI):
                        continue
                    legmid = (cv[t] + cv[t - 3]) / 2
                    ex = t + 24
                    for j in range(t + 1, t + 25):
                        if (side > 0 and lv[j] < legmid) or (side < 0 and hv[j] > legmid):
                            ex = j; break
                    K.append({"time": c.index[t], "coin": coin, "tf": tf, "side": side, "er": er.iloc[t], "ret14": r14.iloc[t],
                              "f6": side * f6.iloc[t], "exit_rule": side * (cv[ex] / cv[t] - 1), "hold": ex - t, "ev": True})
            # pool for k: all bars
            pool = pd.DataFrame({"time": c.index, "coin": coin, "tf": tf, "ret14": r14.to_numpy(), "f6raw": f6.to_numpy(), "ev": False})
            KP.append(pool[(pool.time >= LO) & (pool.time < HI)].dropna().iloc[::3])
            # g
            hi20 = h.shift(1).rolling(20).max()
            newhi = (h > hi20).astype(int)
            run = newhi.rolling(8).sum().shift(1) >= 4
            body = (o - c) / c                                   # positive for a down bar
            maxdn = body.clip(lower=0).rolling(8).max().shift(1)
            vol_ok = v >= 2 * v.rolling(24).median().shift(1)
            choch = run & (body > 0) & (body > maxdn) & vol_ok
            plain = (~run) & (body > 0)
            g = pd.DataFrame({"time": c.index, "coin": coin, "tf": tf, "body": body.to_numpy(), "f6": (-f6).to_numpy(), "ev": choch.to_numpy(), "pl": plain.to_numpy()})
            G.append(g[(g.time >= LO) & (g.time < HI)].dropna())
    res = {}
    k = pd.concat([pd.DataFrame(K)] + KP, ignore_index=True)
    for tf in ("1h", "4h"):
        x = k[k.tf == tf].copy()
        x["m"] = (x.groupby("coin").ret14.rank(pct=True) * 9.999).astype(int)
        for side in (1, -1):
            e = x[x.ev.astype(bool) & (x.side == side)]
            pool = x[~x.ev.astype(bool)].assign(f6=lambda d: d.f6raw * side)
            if len(e) < 20:
                res[f"k_{tf}_{side}"] = {"n": int(len(e))}; continue
            base = L.matched(e, pool, k=3)
            s = L.stats(e.assign(gross=e.f6)[COLS], base.assign(side=side, gross=base.f6)[COLS], reps=500)
            q = pd.qcut(e.er.rank(method="first"), 3, labels=False)
            res[f"k_{tf}_{'up' if side > 0 else 'dn'}"] = {"n": s["n"], "fixed6_bp": s["mean_bp"], "matched_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"],
                                                          "exit_rule_bp": round(float(e.exit_rule.mean() * 1e4), 1), "exit_rule_mean_hold": round(float(e.hold.mean()), 1),
                                                          "fixed6_by_er_tercile_bp": [round(float(e[q == i].f6.mean() * 1e4), 1) for i in range(3)]}
    g = pd.concat(G, ignore_index=True)
    for tf in ("1h", "4h"):
        x = g[g.tf == tf].copy()
        edges = np.quantile(x[x.pl | x.ev].body, [0, .2, .4, .6, .8, 1]); edges[0] -= 1; edges[-1] += 1
        x["m"] = pd.cut(x.body, edges, labels=False)
        e, pool = x[x.ev].assign(side=-1), x[x.pl].assign(side=-1)
        base = L.matched(e, pool, k=3)
        s = L.stats(e.assign(gross=e.f6)[COLS], base.assign(gross=base.f6)[COLS], reps=500)
        res[f"g_{tf}_choch_short"] = {"n": s["n"], "mean_bp": s["mean_bp"], "same_body_no_run_bp": s["base_bp"], "diff_bp": s["vs_base_bp"], "p": s["p_vs_base"], "mde_bp": s["mde80_bp"]}
    for k_, v_ in res.items():
        print(k_, v_)
    (ROOT / "research/is3/N3kg__explore.json").write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    main()
