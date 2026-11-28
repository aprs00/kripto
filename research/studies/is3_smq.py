"""InSilico pass 3, SMQ: main_bn's mix at $1,000 / $200 (band only = today's small_acct) / $200 with per-symbol minimum orders, bnall 1d, taker 5 bp.
Constant account size (re-funded), so the minimum binds alike every year. Descriptive, not registered.
  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_smq   -> research/is3/smq_abc.json"""
import json

import numpy as np
import pandas as pd

from kripto import backtest as bt, data, paper as P, venue_bn as V
from kripto.strategies import REGISTRY

S, SCALE = slice("2021-01-01", "2026-10-31"), 0.5 * 1.156   # alloc .5 per leg x main_scale (= is3_mbl .578)
_, risk = P.load_cfg()
p = data.load_panel("bnall", "1d")
cols = p["close"].columns
mins_now = pd.Series({k: v["min_notional"] for k, v in V.symbol_filters(None, max_age_h=1e9).items()}).reindex(cols).fillna(5.0)
mins_stress = mins_now.copy(); mins_stress[[c for c in ("BTC", "ETH") if c in cols]] = [50.0, 20.0][:sum(c in cols for c in ("BTC", "ETH"))]
wf = REGISTRY["flow"](p, lookback=3, cap=0.05).ffill().fillna(0.0)
wb = REGISTRY["blend"](p, components={"carry_trend": {}, "carry": {}, "xsmom": {}}).ffill().fillna(0.0).reindex(columns=cols, fill_value=0.0)
wf = wf.reindex(columns=cols, fill_value=0.0)
slip = bt.slippage_model(p["volume"], 1)


def risked(w):
    w = w.clip(-risk["max_asset_weight"], risk["max_asset_weight"])
    g = w.abs().sum(axis=1); f = (risk["max_gross"] / g).where(g > risk["max_gross"], 1.0)
    return w.mul(f, axis=0)


def trunc(w, eq, mins):
    return w.where(w.abs() * eq >= mins.to_numpy(), 0.0)


def topn(w, n):
    r = w.abs().rank(axis=1, ascending=False, method="first")
    k = w.where(r <= n, 0.0)
    g0, g1 = w.abs().sum(axis=1), k.abs().sum(axis=1)
    return k.mul((g0 / g1).where(g1 > 0, 0.0), axis=0).clip(-risk["max_asset_weight"] * 4, risk["max_asset_weight"] * 4)


def stats(w, eq):
    res = bt.run(w, p["close"], p["funding"], slip, band=5.0 / eq, fee=5e-4)
    r = res.returns.loc[S]
    sr = lambda x: round(float(x.mean() / x.std() * np.sqrt(365)), 2) if x.std() > 0 else None
    return {"sr": sr(r), "ann%": round(float(r.mean() * 365 * 100), 1), "vol%": round(float(r.std() * np.sqrt(365) * 100), 1),
            "gross_held": round(float(res.weights.loc[S].abs().sum(axis=1).mean()), 3), "turn_yr": round(float(res.turnover.loc[S].sum() / 5.83), 1),
            "years": {int(y): sr(x) for y, x in r.groupby(r.index.year)}}


out = {}
for leg, w in (("mix", (wf + wb) * SCALE), ("flow_in_main", wf * SCALE), ("blend_in_main", wb * SCALE)):   # legs at their weight inside main_bn
    w = risked(w)
    out[leg] = {"usd1000": stats(w, 1000.0), "usd200_band": stats(w, 200.0), "usd200_symmin": stats(trunc(w, 200.0, mins_now), 200.0),
                "usd200_symmin_btceth_stress": stats(trunc(w, 200.0, mins_stress), 200.0)}
    print(leg, json.dumps(out[leg]), flush=True)
w = risked((wf + wb) * SCALE)
out["c_topn_200"] = {n: stats(trunc(topn(w, n), 200.0, mins_now), 200.0) for n in (4, 6, 8, 12)}
print("c", json.dumps(out["c_topn_200"]), flush=True)
if __name__ == "__main__":
    json.dump(out, open("research/is3/smq_abc.json", "w"), indent=1)


def form_d():
    """top-N re-scaled to the $1,000 mix's realised vol (full-sample scale: descriptive, a small look-ahead), THEN cut at per-symbol minima."""
    base = stats(w, 1000.0)
    res = {"base_usd1000": {k: base[k] for k in ("sr", "ann%", "vol%", "gross_held")}}
    for n in (4, 6, 8, 12):
        k = topn(w, n)
        v = stats(k, 1000.0)["vol%"]
        k = k * base["vol%"] / v
        t = trunc(k, 200.0, mins_now)
        ga, gt = k.abs().sum(axis=1), t.abs().sum(axis=1)
        sh = (gt / ga.where(ga > 0)).loc["2021":"2026-10"]
        res[n] = {"usd1000_volmatched": stats(k, 1000.0), "usd200_symmin": stats(t, 200.0),
                  "deployed_share_by_year": {int(y): round(float(x.mean()), 2) for y, x in sh.groupby(sh.index.year)}}
        print(n, json.dumps(res[n]), flush=True)
    json.dump(res, open("research/is3/smq_d.json", "w"), indent=1)
