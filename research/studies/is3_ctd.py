"""CTD: carry_trend (default params) decay check on bnall 1d 2021-26: by year SR, gross, funding, price, costs, long/short legs, top-5 coin share; monthly slope HAC t
with xsmom control; rolling 365-d SR. Descriptive, NOT registered. PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_ctd -> research/is3/ctd_abc.json"""
import json
import numpy as np, pandas as pd
from kripto import backtest as bt
from kripto.strategies import REGISTRY
from kripto import data

S = slice("2021-01-01", "2026-10-31")
p = data.load_panel("bnall", "1d")
slip = bt.slippage_model(p["volume"], 1)


def hac_slope(y):   # copy of is3_flx.hac_slope (importing that script runs it)
    y = y.dropna(); x = (y.index - y.index[0]).days.to_numpy() / 365.0
    X = np.c_[np.ones(len(x)), x]; b = np.linalg.lstsq(X, y.to_numpy(), rcond=None)[0]; e = y.to_numpy() - X @ b
    L = 6; S0 = (X * e[:, None]).T @ (X * e[:, None])
    for l in range(1, L + 1):
        w = 1 - l / (L + 1); G = (X[l:] * e[l:, None]).T @ (X[:-l] * e[:-l, None]); S0 += w * (G + G.T)
    XtXi = np.linalg.inv(X.T @ X); V = XtXi @ S0 @ XtXi
    return float(b[1]), float(b[1] / np.sqrt(V[1, 1]))

c = p["close"]; cols = c.columns
ret = (c / c.shift(1) - 1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
fund = p["funding"].reindex(index=c.index, columns=cols).fillna(0.0)
w = REGISTRY["carry_trend"](p).ffill().fillna(0.0).reindex(columns=cols, fill_value=0.0)
res = bt.run(w, c, p["funding"], slip, fee=5e-4)
wl = res.weights.reindex(columns=cols, fill_value=0.0).fillna(0.0)
price = (wl * ret); fpl = -(wl * fund)
out = {"a": {}}
for y, g in res.returns.loc[S].groupby(res.returns.loc[S].index.year):
    ix = g.index; gr = wl.loc[ix].abs().sum(axis=1)
    L, Sh = wl.loc[ix] > 0, wl.loc[ix] < 0
    pc = (price + fpl).loc[ix].sum().sort_values(ascending=False)
    out["a"][int(y)] = {"sr": round(float(g.mean() / g.std() * np.sqrt(365)), 2), "net%": round(float(g.sum() * 100), 1), "gross_lev": round(float(gr.mean()), 2),
                        "price%": round(float(price.loc[ix].sum().sum() * 100), 1), "funding%": round(float(fpl.loc[ix].sum().sum() * 100), 1),
                        "cost%": round(float(res.costs.loc[ix].sum() * 100), 1),
                        "funding_bp_per_unit_gross_day": round(float(fpl.loc[ix].sum(axis=1).sum() / gr.sum() * 1e4), 2),
                        "long_leg%": round(float((price + fpl).loc[ix].where(L, 0).sum().sum() * 100), 1), "short_leg%": round(float((price + fpl).loc[ix].where(Sh, 0).sum().sum() * 100), 1),
                        "top5_share": round(float(pc.head(5).sum() / pc.sum()), 2) if pc.sum() > 0 else None}
    print(y, out["a"][int(y)], flush=True)
m = res.returns.loc[S].resample("ME").sum()
xs = bt.run(REGISTRY["xsmom"](p).ffill().fillna(0.0), c, p["funding"], slip, fee=5e-4).returns.loc[S].resample("ME").sum()
b, t = hac_slope(m); b2, t2 = hac_slope(m - xs)
fm = fpl.loc[S].sum(axis=1).resample("ME").sum(); bf, tf = hac_slope(fm)
r365 = res.returns.loc[S].rolling(365).apply(lambda x: x.mean() / x.std() * np.sqrt(365), raw=True).dropna()
ref = r365.loc[:"2024-12-31"]
out["b"] = {"monthly_slope_pct_per_yr": round(b * 100, 2), "t": round(t, 2), "minus_xsmom_slope": round(b2 * 100, 2), "t_minus_xsmom": round(t2, 2),
            "funding_monthly_slope_pct_per_yr": round(bf * 100, 2), "t_funding": round(tf, 2),
            "rolling365_sr_now": round(float(r365.iloc[-1]), 2), "rolling365_sr_pct_of_2021_24": round(float((ref < r365.iloc[-1]).mean()), 2),
            "rolling365_sr_min_2022": round(float(r365.loc["2022"].min()), 2), "rolling365_sr_min_2025_26": round(float(r365.loc["2025":].min()), 2)}
print(out["b"])
json.dump(out, open("research/is3/ctd_abc.json", "w"), indent=1)
# bug check: where does 2026 funding come from
f26 = fpl.loc["2026"].sum().sort_values(ascending=False)
pr26 = price.loc["2026"].sum()
top = f26.head(8)
out["a_2026_top_funding"] = [{"coin": k, "funding%": round(float(v * 100), 2), "price%": round(float(pr26[k] * 100), 2),
                              "days_held": int((wl.loc["2026", k] != 0).sum()), "mean_w": round(float(wl.loc["2026", k].mean()), 4),
                              "mean_rate_bp": round(float(fund.loc["2026", k][wl.loc["2026", k] != 0].mean() * 1e4), 2),
                              "median_dv_musd": round(float((c[k] * p["volume"][k]).loc["2026"][wl.loc["2026", k] != 0].median() / 1e6), 2)} for k, v in top.items()]
for r in out["a_2026_top_funding"]: print(r)
print("funding 2026 total %", round(float(f26.sum() * 100), 1), "top8", round(float(top.sum() * 100), 1))
json.dump(out, open("research/is3/ctd_abc.json", "w"), indent=1)
