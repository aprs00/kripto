"""InSilico pass 3, SMP b: the pair book (fspread_hold lookback 14 enter .1, alloc .5) at $200 on the pair dataset: share of pairs whose BOTH legs clear their minimum
(HL $10, BN symbol MIN_NOTIONAL), one-legged gross under per-leg truncation (the old engine), deployed share under whole-pair truncation and under round-up-both-legs. Descriptive.
  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_smp  -> research/is3/smp_b.json"""
import json
import numpy as np
import pandas as pd
from kripto import backtest as bt, data, research as R
from kripto.strategies import REGISTRY

EQ = 200.0
p = data.load_panel("pair", "1d")
w = REGISTRY["fspread_hold"](p, lookback=14, enter=0.1).ffill().fillna(0.0) * 0.5
cols = w.columns
m = R.small_minima(cols, "pair").reindex(cols).to_numpy()
ok = (w.abs() * EQ >= m) | (w == 0)
base = pd.Index([c.split("@")[0] for c in cols])
legtrunc = w.where(ok, 0.0)                                   # old engine: each leg on its own
okp = ok.T.groupby(base).all().T                               # both legs of a coin clear
whole = w.where(okp.reindex(columns=base).set_axis(cols, axis=1).to_numpy(), 0.0)
mx = pd.Series(m, cols).groupby(base).max()                    # round-up: both legs to the larger minimum when the leg is >= half of it
need = mx.reindex(base).to_numpy() / EQ
a = w.abs()
rnd = np.sign(w) * np.where(a >= need, a, np.where(a >= need / 2, need, 0.0))
rnd = pd.DataFrame(rnd, w.index, cols)
held_pairs = (w != 0).T.groupby(base).any().T.sum(axis=1)
g0 = w.abs().sum(axis=1)
one_leg = (legtrunc != 0).T.groupby(base).sum().T == 1
one_leg_gross = legtrunc.abs().where(one_leg.reindex(columns=base).set_axis(cols, axis=1).to_numpy(), 0.0).sum(axis=1)
S = slice("2023-01-01", None)
yr = lambda s: {int(y): round(float(v.mean()), 2) for y, v in s.loc[S].groupby(s.loc[S].index.year)}
slip = bt.slippage_model(p["volume"], 1)


def stat(x):
    r = bt.run(x, p["close"], p.get("funding"), slip, band=5.0 / EQ).returns.loc[S]
    return {"sr": round(float(r.mean() / r.std() * np.sqrt(365)), 2) if r.std() > 0 else None, "ann%": round(float(r.mean() * 365 * 100), 2)}


inv = g0 > 0
out = {"pairs_held_mean_by_year": yr(held_pairs.where(inv)), "share_pairs_both_legs_clear_by_year": yr((okp & (w != 0).T.groupby(base).any().T).sum(axis=1).where(inv) / held_pairs.where(inv)),
       "one_legged_share_of_gross_old_engine_by_year": yr((one_leg_gross / g0).where(inv)),
       "deployed_whole_pairs_by_year": yr((whole.abs().sum(axis=1) / g0).where(inv)), "deployed_roundup_by_year": yr((rnd.abs().sum(axis=1) / g0).where(inv)),
       "usd1000": stat(w), "usd200_old_leg_trunc": stat(legtrunc), "usd200_whole_pairs": stat(whole), "usd200_roundup_both": stat(rnd)}
print(json.dumps(out, indent=1)); json.dump(out, open("research/is3/smp_b.json", "w"), indent=1)
