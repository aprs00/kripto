"""HBM a: share of gross the Binance main-book components hold in coins with a NaN 20-d beta (hedged at the 1.0 fill). Cached bnall panel."""
import json, pickle, sys
import numpy as np, pandas as pd
from kripto import strategies as S
from kripto.strategies import REGISTRY
p = pickle.load(open(sys.argv[1], "rb"))
beta = S.beta_to(p)
nan = beta.isna()
out = {}
for nm, kw in (("flow", {"lookback": 3, "cap": 0.05}), ("carry", {}), ("carry_trend", {}), ("xsmom", {})):
    w = REGISTRY[nm](p, **kw).fillna(0.0)
    w = w.drop(columns="BTC", errors="ignore")
    g = w.abs()
    sh = (g.where(nan.reindex(index=g.index, columns=g.columns, fill_value=False), 0).sum(1) / g.sum(1).replace(0, np.nan))
    out[nm] = {int(y): round(float(s.mean()), 4) for y, s in sh.groupby(sh.index.year)}
    print(nm, out[nm], flush=True)
json.dump(out, open("research/is3/hbm_a.json", "w"), indent=1)
