"""InSilico pass 3, ERC: HL main blend legs: correlations / variance shares (a); equal-risk-contribution leg multipliers on trailing 90-d leg returns, monthly (b / conf).
python -m research.studies.is3_erc a|b|conf"""
import json, sys
import numpy as np, pandas as pd
from kripto import backtest as bt, data
from kripto.research import bars_per_day
from research.studies.is3_prl import legs, LEGS
from research.studies.is3_prb import summary

p = data.load_panel("hl", "1d")
fin, ref, err = legs(p)
r = p["close"].pct_change(fill_method=None).fillna(0.0)
f = p["funding"].reindex(index=ref.index, columns=ref.columns).fillna(0.0)
lr = pd.DataFrame({n: (w.fillna(0).shift(1).fillna(0) * (r.reindex(index=w.index, columns=w.columns).fillna(0) - f)).sum(1) for n, w in fin.items()})
form = sys.argv[1] if len(sys.argv) > 1 else "a"
out = {"decomp_err": err}


def erc(S, iters=500):
    n = len(S); x = np.ones(n) / n
    for _ in range(iters):                  # damped fixed point: x_i ∝ 1 / (S x)_i  <=>  x_i (S x)_i equal (ERC, long-only multipliers)
        g = S @ x
        xn = 1 / np.maximum(g, 1e-12); xn /= xn.sum()
        x = 0.5 * x + 0.5 * xn
    return x


if form == "a":
    for y in (2023, 2024, 2025, 2026):
        x = lr[lr.index.year == y]
        C = x.corr().round(3)
        cov = x.cov().to_numpy(); wv = np.ones(3)
        contrib = wv * (cov @ wv) / (wv @ cov @ wv)
        out[str(y)] = {"corr": C.to_dict(), "var_share": dict(zip(LEGS, np.round(contrib, 3))), "leg_vol": dict(zip(LEGS, np.round(x.std().to_numpy() * np.sqrt(365), 3)))}
        print(y, "corr ls-lv %.2f ls-ts %.2f lv-ts %.2f" % (C.loc["listing_short", "lowvol"], C.loc["listing_short", "tsmom"], C.loc["lowvol", "tsmom"]),
              "var share", out[str(y)]["var_share"], "vol", out[str(y)]["leg_vol"], flush=True)
else:
    me = lr.index.to_series().groupby(lr.index.to_period("M")).max()
    mult = pd.DataFrame(np.nan, index=lr.index, columns=LEGS)
    for t in me.iloc[:-1]:
        x = lr.loc[:t].iloc[-90:]
        if len(x) < 60:
            continue
        S = x.cov().to_numpy()
        m = erc(S) * 3                        # equal weights = 1 each
        v_eq, v_m = np.ones(3) @ S @ np.ones(3), m @ S @ m
        m *= np.sqrt(v_eq / v_m)              # same ex-ante book vol as equal weights
        nxt = lr.index[lr.index > t]
        if len(nxt):
            mult.loc[nxt[0]] = m
    mult = mult.ffill().fillna(1.0)
    w_erc = sum(fin[n].fillna(0).mul(mult[n].reindex(fin[n].index).fillna(1.0), axis=0) for n in LEGS)
    slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
    run = lambda w: bt.run(w, p["close"], p.get("funding"), slip, band=0.005)
    win = [("2023-01-01", "2024-01-01"), ("2024-01-01", "2025-01-01"), ("2023-01-01", "2025-01-01")] if form == "b" else \
          [("2025-01-01", "2026-01-01"), ("2026-01-01", "2027-01-01"), ("2025-01-01", "2027-01-01")]
    for k, w in (("equal", ref.fillna(0.0)), ("erc", w_erc)):
        res = run(w)
        out[k] = {f"{lo[:4]}-{hi[:4]}": summary(res, lo, hi) for lo, hi in win}
        print(k, {a: (round(v["sr"], 3), round(v["ann"], 4), round(v["costs_ann"], 4), round(v["mdd"], 3)) for a, v in out[k].items()}, flush=True)
    mm = mult[mult.index < pd.Timestamp(win[0][0][:4] + "-01-01", tz="UTC") + pd.DateOffset(years=2)]
    out["mult_mean"] = {n: round(float(mult[n].loc[win[0][0]:win[-1][1]].mean()), 3) for n in LEGS}
    print("mean multipliers", out["mult_mean"])
json.dump(out, open(f"research/is3/erc_{form}.json", "w"), indent=1, default=str)
