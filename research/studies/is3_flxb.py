"""FLXB a: known answer, kripto.strategies.flow(fund_resid=True) == research/studies/is3_flxf resid_f7 on bnall 1d (and default == production)."""
import json
from research.studies import is3_flxf as X
from kripto.strategies import REGISTRY
a = X.flow_x(X.p, mode="resid_f7").fillna(0); b = REGISTRY["flow"](X.p, lookback=3, cap=0.05, fund_resid=True).reindex_like(a).fillna(0)
d = REGISTRY["flow"](X.p, lookback=3, cap=0.05).reindex_like(a).fillna(0) - X.flow_x(X.p).fillna(0)
out = {"maxdw_fund_resid": float((a - b).abs().max().max()), "maxdw_default": float(d.abs().max().max())}
print(out); json.dump(out, open("research/is3/flxb_a.json", "w"))
