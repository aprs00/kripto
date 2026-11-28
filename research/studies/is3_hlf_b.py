"""HLF b: HL listing_short hedged with ETH instead of BTC (beta to ETH, hedge leg ETH), explore 2023-24: funding of the hedge leg, corr to BTC, SR."""
import json
import numpy as np, pandas as pd
from kripto import backtest as bt, data, strategies as S
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY
from research.studies.is3_hbl import split
p = data.load_panel("hl", "1d")
btc = p["close"]["BTC"].pct_change(fill_method=None)
ob, oh = S.beta_to, S.hedge_beta
out = {}
for ref in ("BTC", "ETH"):
    S.beta_to = (lambda panel, ref_=ref, days=60: ob(panel, ref=ref_, days=days))
    S.hedge_beta = (lambda w, beta, ref_=ref: oh(w, beta, ref=ref_))
    w = REGISTRY["listing_short"](p)
    S.beta_to, S.hedge_beta = ob, oh
    slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
    res = bt.run(w, p["close"], p.get("funding"), slip, band=0.005)
    W = res.weights.reindex(columns=p["close"].columns).fillna(0.0)
    f = p["funding"].reindex(index=W.index, columns=W.columns).fillna(0.0)
    o = {}
    for y in (2023, 2024):
        ix = W.index.year == y
        g = res.returns[ix]
        o[str(y)] = {"sr": round(float(g.mean() / g.std() * np.sqrt(365)), 3), "ann": round(float(g.mean() * 365), 4),
                     "hedge_funding": round(float((-W[ref] * f[ref])[ix].mean() * 365), 4), "corr_btc": round(float(g.corr(btc[ix])), 3),
                     "costs": round(float(res.costs[ix].mean() * 365), 4), "worst10": round(float(g.nsmallest(10).mean()), 4)}
    out[ref] = o
    print(ref, o, flush=True)
json.dump(out, open("research/is3/hlf_b.json", "w"), indent=1)
