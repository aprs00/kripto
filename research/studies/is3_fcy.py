"""FCY: flow arm (iii) (FLXF resid_f7) vs carry_trend overlap on bnall 1d 2021-26. a: regression on carry + carry_trend by year (shipped flow and iii);
b: same-coin same-side gross share with carry_trend; c: main_bn mixes (.5 flow + .5 blend, .5 iii + .5 blend, blend) by year. Descriptive, NOT registered.
PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_fcy -> research/is3/fcy_abc.json"""
import json
import numpy as np, pandas as pd
from kripto.strategies import REGISTRY
from research.studies import is3_flxf as X


def hac_t(y, Xm, L=10):
    Xm = np.column_stack([np.ones(len(y)), Xm]); b = np.linalg.lstsq(Xm, y, rcond=None)[0]; e = y - Xm @ b
    XtXi = np.linalg.inv(Xm.T @ Xm); u = Xm * e[:, None]; S = u.T @ u
    for l in range(1, L + 1):
        G = u[l:].T @ u[:-l]; S += (1 - l / (L + 1)) * (G + G.T)
    return b, b / np.sqrt(np.diag(XtXi @ S @ XtXi)), 1 - np.var(e) / np.var(y)


prep = lambda w: w.ffill().fillna(0.0).reindex(columns=X.cols, fill_value=0.0)
W = {"flow": prep(X.flow_x(X.p)), "iii": prep(X.flow_x(X.p, mode="resid_f7")),
     "carry": prep(REGISTRY["carry"](X.p)), "carry_trend": prep(REGISTRY["carry_trend"](X.p)),
     "blend": prep(REGISTRY["blend"](X.p, components={"carry_trend": {}, "carry": {}, "xsmom": {}}))}
R = {k: X.run(w).returns for k, w in W.items()}
R["mix_flow"] = X.run((W["flow"] + W["blend"]) * 0.5).returns
R["mix_iii"] = X.run((W["iii"] + W["blend"]) * 0.5).returns
D = pd.DataFrame(R).loc[X.S].dropna()
out = {"a": {}, "b": {}, "c": {}}
for arm in ("flow", "iii"):
    for lab, g in [("all", D)] + [(str(y), x) for y, x in D.groupby(D.index.year)]:
        b, t, r2 = hac_t(g[arm].to_numpy(), g[["carry", "carry_trend"]].to_numpy())
        out["a"].setdefault(arm, {})[lab] = {"ann%": round(float(g[arm].mean() * 365 * 100), 1), "alpha%": round(float(b[0] * 365 * 100), 1), "t": round(float(t[0]), 2),
                                             "b_carry": round(float(b[1]), 2), "b_ct": round(float(b[2]), 2), "r2": round(float(r2), 3)}
    print("a", arm, out["a"][arm], flush=True)
ix = D.index
for arm in ("flow", "iii"):
    a, ct = W[arm].loc[ix], W["carry_trend"].loc[ix]
    same = (np.sign(a) == np.sign(ct)) & (a != 0) & (ct != 0)
    opp = (np.sign(a) == -np.sign(ct)) & (a != 0) & (ct != 0)
    g = a.abs().sum(axis=1)
    sh = pd.DataFrame({"same": a.abs().where(same, 0).sum(axis=1) / g, "opp": a.abs().where(opp, 0).sum(axis=1) / g,
                       "net_long": a.sum(axis=1), "ct_net_long": ct.sum(axis=1)})
    out["b"][arm] = {str(y): {k: round(float(v), 3) for k, v in x.mean().items()} for y, x in sh.groupby(sh.index.year)}
    print("b", arm, out["b"][arm], flush=True)
sr = lambda x: round(float(x.mean() / x.std() * np.sqrt(365)), 2)
for k in ("blend", "mix_flow", "mix_iii"):
    out["c"][k] = {"all": {"sr": sr(D[k]), "vol%": round(float(D[k].std() * np.sqrt(365) * 100), 1)}, **{str(y): sr(x) for y, x in D[k].groupby(D.index.year)}}
    print("c", k, out["c"][k], flush=True)
for k in ("mix_flow", "mix_iii"):   # share of the mix's variance explained by carry_trend
    out["c"][k]["r2_on_carry_trend_by_year"] = {str(y): round(float(x[k].corr(x["carry_trend"]) ** 2), 3) for y, x in D.groupby(D.index.year)}
out["c"]["blend"]["r2_on_carry_trend_by_year"] = {str(y): round(float(x["blend"].corr(x["carry_trend"]) ** 2), 3) for y, x in D.groupby(D.index.year)}
print({k: out["c"][k]["r2_on_carry_trend_by_year"] for k in ("blend", "mix_flow", "mix_iii")})
json.dump(out, open("research/is3/fcy_abc.json", "w"), indent=1)
