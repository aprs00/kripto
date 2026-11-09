"""Decompose a config: yearly returns, funding vs price vs cost, 2x cost stress, correlation to BTC.
  python -m scripts.inspect_strategy tsmom bn '{"every_days":3}' [4h|1d]"""
import json, sys
import numpy as np, pandas as pd
from kripto import data, metrics as mx
from kripto.research import evaluate

name, ds = sys.argv[1], sys.argv[2]
params = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
iv = sys.argv[4] if len(sys.argv) > 4 else "4h"   # optional 4th arg: bar interval (4h|1d)
p = data.load_panel(ds, "1d" if ds in ("bnall", "hlx", "pair") else iv)
ref = "BTC" if "BTC" in p["close"] else "BTC@bn"   # two-venue panel names its columns <COIN>@<venue>
res, s = evaluate(name, p, params, ds)
res2, s2 = evaluate(name, p, params, ds, cost_mult=2.0)
r = res.returns[res.gross.cumsum() > 0]
yr = pd.DataFrame({"ret": r.groupby(r.index.year).apply(lambda x: (1 + x).prod() - 1),
                   "sharpe": r.groupby(r.index.year).apply(lambda x: mx.sharpe(x, mx.periods_per_year(r.index))),
                   "funding": res.funding.reindex(r.index).groupby(r.index.year).sum(),
                   "costs": -res.costs.reindex(r.index).groupby(r.index.year).sum(),
                   "gross": res.gross.reindex(r.index).groupby(r.index.year).mean()}).round(3)
btc = p["close"][ref].pct_change(fill_method=None).reindex(r.index)
print(json.dumps({k: s[k] for k in ("sharpe", "cagr", "max_dd", "turnover_yr", "cost_yr", "funding_yr", "avg_gross")}))
print("2x costs:", {k: s2[k] for k in ("sharpe", "cagr", "max_dd")})
print("corr to BTC:", round(r.corr(btc), 3), " | price-only sharpe:",
      round(mx.sharpe(r - res.funding.reindex(r.index) + res.costs.reindex(r.index), mx.periods_per_year(r.index)), 2))
print(yr.to_string())
# Artifact checks (added 2026-11-09 after listing_short on bnall looked great only because the 5% band kept the many
# small shorts from opening, leaving a net-long BTC hedge): (a) same config at a tiny band, (b) P&L of the BTC leg vs the rest.
res3, s3 = evaluate(name, p, params, ds, band=0.005)
rets = p["close"].pct_change(fill_method=None).fillna(0).reindex(r.index)
W = res.weights.reindex(r.index)
ppy = mx.periods_per_year(r.index)
legb = W[ref] * rets[ref] if ref in W else pd.Series(0.0, r.index)
lego = (W.drop(columns=ref, errors="ignore") * rets.drop(columns=ref, errors="ignore")).sum(axis=1)
print(f"band 0.005: sharpe={s3['sharpe']} cost_yr={s3['cost_yr']} | BTC-leg ann={legb.mean() * ppy:.3f} "
      f"other-legs ann={lego.mean() * ppy:.3f} (SR {mx.sharpe(lego, ppy):.2f}) | names ever held="
      f"{int((W.abs() > 0).any().sum())}")
print("  WARN: |corr BTC| > 0.3 or BTC leg > other legs => result may be beta/band artifact, not the signal")
