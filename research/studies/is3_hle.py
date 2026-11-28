"""InSilico pass 3, HLE a/b: HL listing_short events split by prior Binance trading history (cached bnall first-trade dates). Descriptive."""
import json, pickle, sys
import numpy as np, pandas as pd
from kripto import data, strategies as S

h = data.load_panel("hl", "1d")
b = pickle.load(open(sys.argv[1], "rb"))
c, v = h["close"], h["volume"]
traded = (v.fillna(0) > 0) & c.notna()
first = traded.idxmax().where(traded.any())
t_cut = traded.any(axis=1).idxmax() + pd.Timedelta(days=30)
dv = S.dollar_volume(h)
bt_ = ((b["volume"].fillna(0) > 0) & b["close"].notna())
bfirst = bt_.idxmax().where(bt_.any())
f = h["funding"].reindex_like(c).fillna(0.0) if "funding" in h else 0 * c
r = c.pct_change(fill_method=None)
rb = r["BTC"]
ev = []
for coin, d0 in first.dropna().items():
    if coin == "BTC" or d0 < t_cut:
        continue
    i0 = c.index.get_loc(d0)
    win = c.index[i0 + 2: i0 + 62]          # held d2..d61 (return of bars after the d1 close)
    if len(win) < 10 or not (dv[coin].iloc[i0 + 1: i0 + 8] >= 1e6).any():
        continue
    rr = (-(r[coin].reindex(win).fillna(0)) + rb.reindex(win).fillna(0) + f[coin].reindex(win).fillna(0))
    bd = bfirst.get(coin)
    prior = (d0 - bd).days if isinstance(bd, pd.Timestamp) and bd < d0 else -1
    grp = "fresh" if prior < 0 else ("bn_lt60" if prior < 60 else "bn_ge60")
    ev.append({"coin": coin, "d0": str(d0.date()), "year": d0.year, "prior_bn_days": prior, "group": grp, "ret": float((1 + rr).prod() - 1), "n_days": len(win)})
E = pd.DataFrame(ev)
out = {"events": ev, "counts": E.groupby(["year", "group"]).size().unstack(fill_value=0).to_dict()}
summ = {}
for (g), x in E.groupby("group"):
    summ[g] = {"n": int(len(x)), "mean": round(float(x.ret.mean()), 4), "median": round(float(x.ret.median()), 4), "win": round(float((x.ret > 0).mean()), 3),
               "t": round(float(x.ret.mean() / (x.ret.std() / np.sqrt(len(x)))), 2) if len(x) > 2 else None,
               "worst3": [round(float(z), 3) for z in x.ret.nsmallest(3)],
               "by_year": {int(y): [int(len(z)), round(float(z.ret.mean()), 3), round(float(z.ret.median()), 3)] for y, z in x.groupby("year")}}
out["summary"] = summ
print(pd.DataFrame(out["counts"]), flush=True)
for g, s in summ.items():
    print(g, s, flush=True)
json.dump(out, open("research/is3/hle_ab.json", "w"), indent=1, default=str)
