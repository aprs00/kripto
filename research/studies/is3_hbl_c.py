"""HBL c (pre-registered HBL_c): coins without a 20-d beta hedged at 1.35 instead of 1.0; HL 2025-26, ONE run."""
import json, numpy as np, pandas as pd
from kripto import data, strategies as S
from kripto.strategies import REGISTRY
from research.studies.is3_hbl import split
p = data.load_panel("hl", "1d")
btc = p["close"]["BTC"].pct_change(fill_method=None)
orig = S.beta_to
out = {}
for yb in (1.0, 1.35):
    S.beta_to = (lambda panel, *a, _yb=yb, **k: orig(panel, *a, **k).fillna(_yb))
    for nm, fn in (("listing_short", lambda: REGISTRY["listing_short"](p)),
                   ("blend", lambda: REGISTRY["blend"](p, components={"listing_short": {}, "lowvol": {}, "tsmom": {}}))):
        S._COMP_CACHE.clear() if hasattr(S, "_COMP_CACHE") else None
        d, _ = split(p, fn())
        o = {}
        for lab, lo, hi in (("2025", "2025-01-01", "2026-01-01"), ("2026", "2026-01-01", "2027-01-01"), ("2025-26", "2025-01-01", "2027-01-01")):
            g = d.loc[(d.index >= pd.Timestamp(lo, tz="UTC")) & (d.index < pd.Timestamp(hi, tz="UTC")), "net"]
            b = btc.reindex(g.index)
            o[lab] = {"sr": round(float(g.mean() / g.std() * np.sqrt(365)), 3), "ann": round(float(g.mean() * 365), 4), "corr_btc": round(float(g.corr(b)), 3),
                      "worst10": round(float(g.nsmallest(10).mean()), 4), "btc_down5_mean": round(float(g[b < -0.05].mean()), 4), "btc_up5_mean": round(float(g[b > 0.05].mean()), 4)}
        out[f"{nm}_yb{yb}"] = o
        print(nm, yb, o, flush=True)
S.beta_to = orig
json.dump(out, open("research/is3/hbl_c.json", "w"), indent=1)
