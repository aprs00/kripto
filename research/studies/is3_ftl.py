"""InSilico pass 3, FTL: HL nested pool strategies: standalone net SR by year and corr with the short-alt factor (listing_short + lowvol) and tsmom. Descriptive.
python -m research.studies.is3_ftl"""
import json
import numpy as np, pandas as pd
from kripto import data, strategies as S

p = data.load_panel("hl", "1d")
R = {}
for n in S.NESTED_POOL:
    try:
        R[n] = S._component_returns(p, n)[1]
    except KeyError:
        continue
R = pd.DataFrame(R)
R = R.loc[pd.Timestamp("2023-01-01", tz="UTC"):]
fac = R["listing_short"] + R["lowvol"]
out = {}
for n in R.columns:
    x = R[n]
    o = {}
    for y in (2023, 2024, 2025, 2026):
        xi = x[x.index.year == y]; inv = xi[xi != 0]
        o[str(y)] = {"sr": round(float(xi.mean() / xi.std() * np.sqrt(365)), 2) if xi.std() > 0 else None, "ann": round(float(xi.mean() * 365), 3),
                     "active_days": int(len(inv)), "worst10_share": round(float(xi.nsmallest(10).sum() / max(abs(xi.sum()), 1e-9)), 2) if xi.sum() != 0 else None}
    m = (x != 0) & (fac != 0)
    out[n] = {"years": o, "corr_shortalt": round(float(x[m].corr(fac[m])), 2), "corr_tsmom": round(float(x[(x != 0) & (R.tsmom != 0)].corr(R.tsmom[(x != 0) & (R.tsmom != 0)])), 2),
              "pos_years": int(sum(1 for v in o.values() if v["sr"] is not None and v["sr"] > 0))}
    print(f"{n:15s}", {y: v["sr"] for y, v in o.items()}, "corr_sa", out[n]["corr_shortalt"], "corr_ts", out[n]["corr_tsmom"], "pos", out[n]["pos_years"], flush=True)
json.dump(out, open("research/is3/ftl_a.json", "w"), indent=1)
