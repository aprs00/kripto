"""InSilico pass 3, HLX: bnall listing events (2023-04+) split by >= 60 d of prior HL trading (frozen from HLE). Descriptive held-out."""
import json, pickle, sys
import numpy as np, pandas as pd
from kripto import data, strategies as S

b = pickle.load(open(sys.argv[1], "rb"))
h = data.load_panel("hl", "1d")
c, v = b["close"], b["volume"]
traded = (v.fillna(0) > 0) & c.notna()
first = traded.idxmax().where(traded.any())
dv = S.dollar_volume(b)
ht = (h["volume"].fillna(0) > 0) & h["close"].notna()
hfirst = ht.idxmax().where(ht.any())
hl_start = ht.any(axis=1).idxmax()
f = b["funding"].reindex_like(c).fillna(0.0)
r = c.pct_change(fill_method=None)
rb = r["BTC"]
ev = []
for coin, d0 in first.dropna().items():
    if coin == "BTC" or d0 < pd.Timestamp("2023-04-01", tz="UTC"):
        continue
    i0 = c.index.get_loc(d0)
    win = c.index[i0 + 2: i0 + 62]
    if len(win) < 10 or not (dv[coin].iloc[i0 + 1: i0 + 8] >= 1e6).any():
        continue
    rr = -(r[coin].reindex(win).fillna(0)) + rb.reindex(win).fillna(0) + f[coin].reindex(win).fillna(0)
    hd = hfirst.get(coin)
    prior = (d0 - hd).days if isinstance(hd, pd.Timestamp) and hd < d0 else -1
    if isinstance(hd, pd.Timestamp) and hd <= hl_start + pd.Timedelta(days=1) and prior >= 0:
        prior = max(prior, 60)  # on HL since HL data start: established
    ev.append({"coin": coin, "d0": str(d0.date()), "year": d0.year, "month": str(d0.to_period("M")), "prior_hl_days": prior,
               "group": "est_hl" if prior >= 60 else "new", "ret": float((1 + rr).prod() - 1)})
E = pd.DataFrame(ev)


def clus_t(x):
    m = x.groupby("month").ret.mean()
    return round(float(m.mean() / (m.std() / np.sqrt(len(m)))), 2) if len(m) > 2 else None


out = {"events": ev, "summary": {}}
for g, x in E.groupby("group"):
    out["summary"][g] = {"n": int(len(x)), "mean": round(float(x.ret.mean()), 4), "median": round(float(x.ret.median()), 4), "win": round(float((x.ret > 0).mean()), 3),
                         "month_t": clus_t(x), "worst3": [round(float(z), 3) for z in x.ret.nsmallest(3)],
                         "by_year": {int(y): [int(len(z)), round(float(z.ret.mean()), 3), round(float(z.ret.median()), 3)] for y, z in x.groupby("year")}}
    print(g, out["summary"][g], flush=True)
s = out["summary"]
out["PASS"] = bool("est_hl" in s and "new" in s and s["est_hl"]["mean"] < s["new"]["mean"] and s["est_hl"]["median"] < s["new"]["median"] and s["est_hl"]["median"] <= 0.05)
print("PASS", out["PASS"])
json.dump(out, open("research/is3/hlx_ab.json", "w"), indent=1, default=str)
