"""PRBF: power of the PRB2-F forward judge. Backtest daily P&L of the shipped HL main blend (listing_short, lowvol, tsmom) with slow_lam .33 vs lam 1.
a = sd / AC of the daily difference, mean diff by year, HAC MDE (t=2) at 30/60/90 d vs the expected gain; b = cost-clause ratio (slow costs / lam1 costs) over rolling 30/60/90-d windows.
Not registered (descriptive). PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_prbf -> research/is3/prbf_ab.json"""
import json
import numpy as np, pandas as pd
from kripto import backtest as bt, data
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY

p = data.load_panel("hl", "1d")
slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
comps = {"listing_short": {}, "lowvol": {}, "tsmom": {}}
R = {}
for k, lam in (("slow", 0.33), ("lam1", None)):
    w = REGISTRY["blend"](p, components=comps, slow_lam=lam)
    R[k] = bt.run(w, p["close"], p.get("funding"), slip, band=0.005)
S = slice("2023-01-01", None)
rs, rl = R["slow"].returns.loc[S], R["lam1"].returns.loc[S]
cs, cl = R["slow"].costs.loc[S], R["lam1"].costs.loc[S]
d = rs - rl


def hac_var(x, L):                      # Newey-West long-run variance of the mean's numerator
    x = x - x.mean(); n = len(x); v = float((x * x).mean())
    for l in range(1, L + 1):
        v += 2 * (1 - l / (L + 1)) * float((x[l:].to_numpy() * x[:-l].to_numpy()).mean())
    return v


ac = {l: round(float(d.autocorr(l)), 3) for l in (1, 2, 5, 10)}
lrv = hac_var(d, 10)
out = {"days": len(d), "corr_slow_lam1": round(float(rs.corr(rl)), 3),
       "sd_slow_bp": round(float(rs.std() * 1e4), 1), "sd_diff_bp": round(float(d.std() * 1e4), 1), "ac_diff": ac,
       "lrv_ratio": round(lrv / float(d.var()), 2), "mean_diff_bp": round(float(d.mean() * 1e4), 2), "mean_diff_pct_yr": round(float(d.mean() * 365 * 100), 2),
       "t_full_hac": round(float(d.mean() / np.sqrt(lrv / len(d))), 2),
       "by_year": {int(y): {"mean_diff_bp": round(float(v.mean() * 1e4), 2), "sr_slow": round(float(rs[v.index].mean() / rs[v.index].std() * np.sqrt(365)), 2),
                            "sr_lam1": round(float(rl[v.index].mean() / rl[v.index].std() * np.sqrt(365)), 2),
                            "cost_ratio": round(float(cs[v.index].sum() / cl[v.index].sum()), 3)} for y, v in d.groupby(d.index.year)}}
out["mde_bp"] = {n: round(2 * np.sqrt(lrv / n) * 1e4, 2) for n in (30, 60, 90, 180)}
out["mde_over_expected_gain"] = {n: round(out["mde_bp"][n] / out["mean_diff_bp"], 1) for n in (30, 60, 90, 180)} if out["mean_diff_bp"] > 0 else None
# chance the P&L clause (t > -1) fails over an n-day window: rolling windows with naive-HAC t
pf = {}
for n in (30, 60, 90):
    m = d.rolling(n).mean().dropna()
    t = m / np.sqrt(lrv / n)
    pf[n] = {"share_t_le_-1": round(float((t <= -1).mean()), 3), "share_t_ge_2": round(float((t >= 2).mean()), 3)}
out["pnl_clause_windows"] = pf
# b: cost clause
cb = {}
for n in (30, 60, 90):
    ratio = (cs.rolling(n).sum() / cl.rolling(n).sum()).dropna()
    cb[n] = {"p10": round(float(ratio.quantile(.1)), 3), "p50": round(float(ratio.median()), 3), "p90": round(float(ratio.quantile(.9)), 3),
             "max": round(float(ratio.max()), 3), "share_fail_gt_.75": round(float((ratio > 0.75).mean()), 3),
             "share_fail_2026": round(float((ratio[ratio.index.year == 2026] > 0.75).mean()), 3)}
out["cost_clause_windows"] = cb
out["cost_ratio_full"] = round(float(cs.sum() / cl.sum()), 3)
out["costs_pct_yr"] = {"slow": round(float(cs.mean() * 365 * 100), 2), "lam1": round(float(cl.mean() * 365 * 100), 2)}
# known answer: the difference of the two return series equals the difference of their components
assert abs(float((d - (rs - rl)).abs().max())) < 1e-15
print(json.dumps(out, indent=1))
json.dump(out, open("research/is3/prbf_ab.json", "w"), indent=1)
