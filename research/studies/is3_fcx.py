"""FCX b: flow@bn (shipped lb 3, cap .05) daily returns regressed on carry and carry_trend (default params) on bnall 1d, by year: beta, alpha %/yr, HAC t.
Descriptive, NOT registered. PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_fcx -> research/is3/fcx_b.json"""
import json
import numpy as np, pandas as pd
from kripto.strategies import REGISTRY
from research.studies import is3_flxf as X


def hac_t(y, Xm, L=10):
    Xm = np.column_stack([np.ones(len(y)), Xm]); b = np.linalg.lstsq(Xm, y, rcond=None)[0]; e = y - Xm @ b
    XtXi = np.linalg.inv(Xm.T @ Xm); u = Xm * e[:, None]; S = u.T @ u
    for l in range(1, L + 1):
        G = u[l:].T @ u[:-l]; S += (1 - l / (L + 1)) * (G + G.T)
    V = XtXi @ S @ XtXi
    return b, b / np.sqrt(np.diag(V))


R = {"flow": X.run(X.flow_x(X.p)).returns}
for k in ("carry", "carry_trend"):
    R[k] = X.run(REGISTRY[k](X.p)).returns
D = pd.DataFrame(R).loc[X.S].dropna()
out = {"corr": D.corr().round(3).to_dict()}
for lab, g in [("all", D)] + [(str(y), x) for y, x in D.groupby(D.index.year)]:
    b, t = hac_t(g.flow.to_numpy(), g[["carry", "carry_trend"]].to_numpy())
    out[lab] = {"days": len(g), "flow_ann%": round(float(g.flow.mean() * 365 * 100), 1), "alpha_ann%": round(float(b[0] * 365 * 100), 1), "t_alpha": round(float(t[0]), 2),
                "beta_carry": round(float(b[1]), 2), "beta_carry_trend": round(float(b[2]), 2), "r2": round(float(1 - np.var(g.flow - np.column_stack([np.ones(len(g)), g[["carry", "carry_trend"]]]) @ b) / np.var(g.flow)), 3),
                "corr_carry": round(float(g.flow.corr(g.carry)), 2), "corr_carry_trend": round(float(g.flow.corr(g.carry_trend)), 2)}
    print(lab, out[lab], flush=True)
json.dump(out, open("research/is3/fcx_b.json", "w"), indent=1)
