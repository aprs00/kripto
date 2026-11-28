"""LSH2: listing_short hold 60/90/120 and the P&L of each age tranche (days since listing) of the hold-120 book. bnall explore 2020-23 + HL 2023-26 check.
Not registered (descriptive). PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_lsh2 bnall|hl -> research/is3/lsh2_<ds>.json"""
import json, sys
import numpy as np, pandas as pd
from kripto import backtest as bt, data
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY

ds = sys.argv[1]
p = data.load_panel(ds, "1d")
lo, hi = ("2020-01-01", "2024-01-01") if ds == "bnall" else ("2023-01-01", "2027-01-01")
kw = {"fee": 5e-4} if ds == "bnall" else {"band": 0.005}
c, f = p["close"], p["funding"].reindex_like(p["close"])
slip = bt.slippage_model(p["volume"], bars_per_day(c.index))
L, H = pd.Timestamp(lo, tz="UTC"), pd.Timestamp(hi, tz="UTC")
out = {"dataset": ds, "lo": lo, "hi": hi}
res = {}
for h in (60, 90, 120):
    r = bt.run(REGISTRY["listing_short"](p, skip_days=1, hold_days=h, min_dv=1e6), c, p["funding"], slip, **kw)
    res[h] = r
    x = r.returns[(r.returns.index >= L) & (r.returns.index < H)]
    fd = r.funding.loc[x.index]; cs = r.costs.loc[x.index]
    out[f"hold{h}"] = {"sr": round(float(x.mean() / x.std() * np.sqrt(365)), 2), "ann%": round(float(x.mean() * 365 * 100), 1),
                       "funding%": round(float(fd.mean() * 365 * 100), 1), "cost%": round(float(cs.mean() * 365 * 100), 1),
                       "sr_by_year": {int(y): round(float(v.mean() / v.std() * np.sqrt(365)), 2) for y, v in x.groupby(x.index.year) if v.std() > 0}}
    print(ds, h, json.dumps(out[f"hold{h}"]), flush=True)
# tranches of the hold-120 book by age since the first traded day (volume > 0)
first = (p["volume"] > 0).idxmax().where((p["volume"] > 0).any())
age = pd.DataFrame({k: (c.index - t).days if pd.notna(t) else np.nan for k, t in first.items()}, index=c.index)
Hd = res[120].weights
ret = c.pct_change().fillna(0.0)
ix = Hd.index[(Hd.index >= L) & (Hd.index < H)]
tr = {}
for a0, a1 in ((0, 30), (30, 60), (60, 90), (90, 125)):
    m = (age >= a0) & (age < a1) & (Hd != 0)
    pr = (Hd * ret).where(m, 0.0).loc[ix].sum(axis=1); fu = (-Hd * f.fillna(0.0)).where(m, 0.0).loc[ix].sum(axis=1)
    g = Hd.abs().where(m, 0.0).loc[ix].sum(axis=1)
    ev = (Hd * ret).where(m).loc[ix]
    tr[f"{a0}-{a1}"] = {"gross_share": round(float(g.sum() / Hd.abs().loc[ix].sum().sum()), 3),
                        "price_bp_per_unit_day": round(float(pr.sum() / g.sum() * 1e4), 2) if g.sum() > 0 else None,
                        "funding_bp_per_unit_day": round(float(fu.sum() / g.sum() * 1e4), 2) if g.sum() > 0 else None,
                        "by_year_price_plus_funding_pct": {int(y): round(float(v * 100), 2) for y, v in (pr + fu).groupby((pr + fu).index.year).sum().items()},
                        "worst_1pct_event_day_bp": round(float(np.nanpercentile((ev / Hd.abs().where(m)).loc[ix].to_numpy(), 1) * 1e4), 0) if m.loc[ix].to_numpy().any() else None}
out["tranches_hold120"] = tr
print(json.dumps(tr), flush=True)
json.dump(out, open(f"research/is3/lsh2_{ds}.json", "w"), indent=1)
