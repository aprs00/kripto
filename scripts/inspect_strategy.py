"""Decompose a config: yearly returns, funding vs price vs cost, 2x cost stress, correlation to BTC.
  python -m scripts.inspect_strategy tsmom bn '{"every_days":3}' [4h|1d]"""
import json, sys
import numpy as np, pandas as pd
from kripto import data, metrics as mx
from kripto.research import evaluate

name, ds = sys.argv[1], sys.argv[2]
params = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
iv = sys.argv[4] if len(sys.argv) > 4 else "4h"   # optional 4th arg: bar interval (4h|1d)
p = data.load_hl_panel(iv) if ds == "hl" else data.load_bn_panel(iv)
res, s = evaluate(name, p, params, ds)
res2, s2 = evaluate(name, p, params, ds, cost_mult=2.0)
r = res.returns[res.gross.cumsum() > 0]
yr = pd.DataFrame({"ret": r.groupby(r.index.year).apply(lambda x: (1 + x).prod() - 1),
                   "sharpe": r.groupby(r.index.year).apply(lambda x: mx.sharpe(x, mx.periods_per_year(r.index))),
                   "funding": res.funding.reindex(r.index).groupby(r.index.year).sum(),
                   "costs": -res.costs.reindex(r.index).groupby(r.index.year).sum(),
                   "gross": res.gross.reindex(r.index).groupby(r.index.year).mean()}).round(3)
btc = p["close"]["BTC"].pct_change().reindex(r.index)
print(json.dumps({k: s[k] for k in ("sharpe", "cagr", "max_dd", "turnover_yr", "cost_yr", "funding_yr", "avg_gross")}))
print("2x costs:", {k: s2[k] for k in ("sharpe", "cagr", "max_dd")})
print("corr to BTC:", round(r.corr(btc), 3), " | price-only sharpe:",
      round(mx.sharpe(r - res.funding.reindex(r.index) + res.costs.reindex(r.index), mx.periods_per_year(r.index)), 2))
print(yr.to_string())
