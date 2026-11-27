"""InSilico pass 3, L6V: range / HAR vol forecasts (library N6). Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_l6v a    # forecast accuracy of next-7-d realized vol, bnall 1d, top-100 point-in-time, 2021-23 -> research/is3/l6v_a.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data
from research.studies import is3_lib as L

H = 7


def run_a():
    p = data.load_panel("bnall", "1d")
    c, h, l, v = p["close"], p["high"], p["low"], p["volume"]
    r = np.log(c / c.shift(1))
    pk = (np.log(h / l) ** 2) / (4 * np.log(2))                       # Parkinson daily variance
    pk = pk.where(np.isfinite(pk) & (pk > 0))
    top = v.rolling(30, min_periods=10).mean().rank(axis=1, ascending=False) <= 100
    liq = v.rolling(30, min_periods=10).mean().where(top).rank(axis=1, ascending=False)
    # target: realized variance over t+1..t+7 (daily close-to-close, mean of r^2)
    fut = (r ** 2).rolling(H, min_periods=H).mean().shift(-H)
    F = {"cc20": (r ** 2).rolling(20, min_periods=15).mean(), "cc60": (r ** 2).rolling(60, min_periods=40).mean(),
         "ewm20": (r ** 2).ewm(halflife=20, min_periods=15).mean(), "pk20": pk.rolling(20, min_periods=15).mean(), "pk5": pk.rolling(5, min_periods=4).mean()}
    # HAR on Parkinson (log space), pooled fit on 2021-22, liquid top-100 cells only
    lw = {"d": np.log(pk), "w": np.log(pk.rolling(5, min_periods=4).mean()), "m": np.log(pk.rolling(22, min_periods=15).mean())}
    y = np.log(fut)
    mask = top & np.isfinite(y)
    def stack(df):
        return df.where(mask).stack()
    X = pd.concat({k: stack(x) for k, x in lw.items()}, axis=1).join(stack(y).rename("y"), how="inner").dropna()
    tr = X[X.index.get_level_values(0) < pd.Timestamp("2023-01-01", tz="UTC")]
    tr = tr[tr.index.get_level_values(0) >= pd.Timestamp("2021-01-01", tz="UTC")]
    A = np.column_stack([np.ones(len(tr)), tr.d, tr.w, tr.m])
    beta = np.linalg.lstsq(A, tr.y.to_numpy(), rcond=None)[0]
    resid_var = float(np.var(tr.y.to_numpy() - A @ beta))
    har = np.exp(beta[0] + beta[1] * lw["d"] + beta[2] * lw["w"] + beta[3] * lw["m"] + resid_var / 2)
    F["har_pk"] = har
    print("HAR beta (const, d, w, m):", beta.round(3), "resid var", round(resid_var, 3), flush=True)
    # constant scale per estimator fitted on 2021-22 (median ratio), applied to 2023
    out = {"har_beta": beta.round(4).tolist()}
    rows = []
    for nm, f in F.items():
        d = pd.concat({"f": f.where(mask).stack(), "y": fut.where(mask).stack(), "liq": liq.where(mask).stack()}, axis=1).dropna()
        d = d[(d.f > 0) & (d.y > 0)]
        t = d.index.get_level_values(0)
        fit = d[(t >= pd.Timestamp("2021-01-01", tz="UTC")) & (t < pd.Timestamp("2023-01-01", tz="UTC"))]
        k = float(np.exp(np.median(np.log(fit.y / fit.f))))
        for scaled in (False, True):
            for yr in (2021, 2022, 2023):
                g = d[t.year == yr]
                ff = g.f * (k if scaled else 1.0)
                q = g.y / ff
                ql = q - np.log(q) - 1
                le = np.abs(0.5 * np.log(ff / g.y))
                for tl, gg in ((0, g.liq <= 33), (1, (g.liq > 33) & (g.liq <= 66)), (2, g.liq > 66), (-1, g.liq > 0)):
                    rows.append({"est": nm, "scaled": scaled, "k": round(k, 3), "year": yr, "liq": tl, "n": int(gg.sum()),
                                 "qlike": float(ql[gg].mean()), "qlike_med": float(ql[gg].median()), "abs_log_vol_err": float(le[gg].mean())})
    T = pd.DataFrame(rows)
    piv = T[T.liq == -1].pivot_table(index=["est", "scaled"], columns="year", values="qlike").round(4)
    print(piv.to_string(), flush=True)
    piv2 = T[(T.year == 2023) & T.scaled].pivot_table(index="est", columns="liq", values="qlike").round(4)
    print("2023 scaled, by liquidity tercile (0 = most liquid, -1 = all):\n" + piv2.to_string(), flush=True)
    out["table"] = T.round(5).to_dict("records")
    (L.OUT / "l6v_a.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    {"a": run_a}[sys.argv[1]]()
