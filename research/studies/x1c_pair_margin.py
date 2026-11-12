"""X1c (2026-11-12): descriptive margin/basis risk of fspread_hold (live params lookback 14, enter 0.1) on the pair dataset.
Per venue account = half the equity; each venue holds only one side per pair. Measures, over the days a pair is held:
worst 1/3/7-day move of a held leg against its venue account, worst daily basis change, and the per-venue account
drawdown if no money is moved between venues for 7 days. No backtest, nothing registered."""
import numpy as np, pandas as pd
from kripto import data, strategies as S
p = data.load_panel("pair", "1d")
w = S.REGISTRY["fspread_hold"](p, lookback=14, enter=0.1).fillna(0.0)
c = p["close"]
r = c.pct_change(fill_method=None).fillna(0.0)
hl = [x for x in w.columns if x.endswith("@hl")]
held = (w[hl].abs() > 0)
print("pair-days held:", int(held.to_numpy().sum()), "from", w.index[held.any(axis=1)][0].date())
# venue account P&L (weights are fractions of TOTAL equity; each venue account holds half) -> x2 for the account
for v in ("hl", "bn"):
    cols = [x for x in w.columns if x.endswith("@" + v)]
    acc = (w[cols].shift(1) * r[cols]).sum(axis=1) * 2
    for k in (1, 3, 7):
        worst = acc.rolling(k).sum().min()
        print(f"{v} account worst {k}-day P&L (no transfers): {worst:+.1%}")
    lev = w[cols].abs().sum(axis=1) * 2
    print(f"{v} account gross leverage: median {lev[lev>0].median():.2f}x max {lev.max():.2f}x")
# worst single leg move against us while held, 1 and 7 days
adv = []
for x in hl:
    b = x[:-3] + "@bn"
    side = np.sign(w[x].shift(1))
    for k in (1, 7):
        mv = (c[x].pct_change(k, fill_method=None) * -side.where(side != 0)).min()   # against the HL leg
        adv.append((k, x[:-3], mv))
a = pd.DataFrame(adv, columns=["k", "coin", "against_hl_leg"])
for k in (1, 7):
    print(f"worst {k}d move against a held HL leg:", a[a.k == k].nsmallest(3, "against_hl_leg").to_dict("records"))
basis = np.log(c[hl] / c[[x[:-3] + "@bn" for x in hl]].set_axis(hl, axis=1))
db = basis.diff().where(held.shift(1, fill_value=False))
print("worst daily basis change while held (bp):", round(float(db.abs().max().max()) * 1e4), "p99:",
      round(float(np.nanpercentile(db.abs().to_numpy(), 99)) * 1e4))
