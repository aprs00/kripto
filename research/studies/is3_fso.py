"""InSilico pass 3, FSO: fspread_hold@pair held pairs vs the HL main blend's long legs; aggregate funding of both books (each $1,000). Descriptive.
python -m research.studies.is3_fso"""
import json
import numpy as np, pandas as pd
from kripto import data, strategies as S
from research.studies.is3_prl import legs

pp = data.load_panel("pair", "1d")
cfg = json.load(open("config/strategies.json"))["fspread_hold@pair"]["params"]
wp = S._ffill_targets(S.REGISTRY["fspread_hold"](pp, **cfg)).fillna(0.0).shift(1).fillna(0.0)
h = data.load_panel("hl", "1d")
_, ref, _ = legs(h)
wh = ref.fillna(0.0).shift(1).fillna(0.0)
idx = wp.index.intersection(wh.index)
idx = idx[idx >= pd.Timestamp("2023-06-01", tz="UTC")]
wp, wh = wp.loc[idx], wh.loc[idx]
fp = pp["funding"].reindex(index=idx, columns=wp.columns).fillna(0.0)
fh = h["funding"].reindex(index=idx, columns=wh.columns).fillna(0.0)
hl_cols = [c for c in wp.columns if c.endswith("@hl")]
coin = {c: c[:-3] for c in hl_cols}
held = wp[hl_cols].rename(columns=coin)
out = {"a": {}, "b": {}}
days_any = (held.abs().sum(1) > 0)
out["a"]["days_any_pair"] = round(float(days_any.mean()), 3)
share = held.abs().sum() / held.abs().sum().sum()
out["a"]["top_coins_by_gross"] = {k: round(float(v), 3) for k, v in share.sort_values(ascending=False).head(10).items()}
out["a"]["hl_side_sign_share_short"] = round(float((held < 0).sum().sum() / max((held != 0).sum().sum(), 1)), 3)
for c in ("BTC", "ETH"):
    out["a"][f"days_{c}"] = round(float((held.get(c, pd.Series(0, idx)) != 0).mean()), 3)
# overlap with HL book longs: pair's HL-leg short in a coin the HL book is long (same day)
common = [c for c in held.columns if c in wh.columns]
L = wh[common].clip(lower=0)
ovl = np.minimum(L, (-held[common]).clip(lower=0))
out["a"]["overlap_gross_share_of_hl_longs"] = round(float(ovl.sum(1).sum() / max(wh.clip(lower=0).sum(1).sum(), 1e-12)), 4)
# b: funding P&L of each book on its own equity, and of the sum (two $1,000 books)
fund_hl = (-wh * fh).sum(1)
fund_pair = (-wp * fp).sum(1)
for y in sorted(set(idx.year)):
    m = idx.year == y
    out["b"][str(y)] = {"hl_book_funding_ann": round(float(fund_hl[m].mean() * 365), 4), "pair_book_funding_ann": round(float(fund_pair[m].mean() * 365), 4),
                        "offset_in_same_coins_ann": round(float(((ovl * fh[common]).sum(1))[m].mean() * 365), 4),
                        "hl_btc_long_funding_ann": round(float((-wh["BTC"].clip(lower=0) * fh["BTC"])[m].mean() * 365), 4)}
for k, v in out.items():
    print(k, v, flush=True)
json.dump(out, open("research/is3/fso_ab.json", "w"), indent=1)
