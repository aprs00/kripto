"""InSilico pass 3, HSQ: SQZ's off_low squeeze state on HL listing_short held coin-days (descriptive replication, frozen bnall 2021-23 edges).
python -m research.studies.is3_hsq data/is3/fc1c_bnall_1d.pkl"""
import json, pickle, sys
import numpy as np, pandas as pd
from kripto import data
from research.studies.is3_sqz import frame

b = pickle.load(open(sys.argv[1], "rb"))
fb = frame(b)
ex = fb[(fb.time >= "2021-01-01") & (fb.time < "2024-01-01")].dropna(subset=["off_low"])
edges = ex.off_low.quantile([.2, .4, .6, .8]).tolist()
print("bnall 2021-23 off_low edges", [round(x, 3) for x in edges], "n", len(ex), flush=True)
bt_ = (b["volume"].fillna(0) > 0) & b["close"].notna()
bfirst = bt_.idxmax().where(bt_.any())
del b
h = data.load_panel("hl", "1d")
df = frame(h).dropna(subset=["off_low"])
first = ((h["volume"].fillna(0) > 0) & h["close"].notna()).idxmax()
def grp(coin):
    d0, bd = first[coin], bfirst.get(coin)
    prior = (d0 - bd).days if isinstance(bd, pd.Timestamp) and bd < d0 else -1
    return "fresh" if prior < 0 else ("bn_lt60" if prior < 60 else "bn_ge60")
df["group"] = df.coin.map(grp)
df["q"] = np.searchsorted(edges, df.off_low.to_numpy()) + 1
def tab(x):
    return {int(q): {"n": int(len(g)), "coins": int(g.coin.nunique()), "mean": round(float(g.fwd7.mean()), 4), "median": round(float(g.fwd7.median()), 4),
                     "p_loss20": round(float((g.fwd7 < -0.2).mean()), 3)} for q, g in x.groupby("q")}
out = {"edges": edges, "n": int(len(df)), "pooled": tab(df), "by_year": {int(y): tab(g) for y, g in df.groupby(df.time.dt.year)},
       "by_group": {k: tab(g) for k, g in df.groupby("group")}, "group_q5_share": {k: round(float((g.q == 5).mean()), 3) for k, g in df.groupby("group")},
       "group_n": df.groupby("group").coin.nunique().to_dict()}
# event-clustered check: share of q5 coin-days per coin, and P(loss>20) top vs bottom-3 with coin-level bootstrap
top, bot = df[df.q == 5], df[df.q <= 3]
rng = np.random.default_rng(0); coins = df.coin.unique(); diffs = []
for _ in range(2000):
    s = rng.choice(coins, len(coins)); d = pd.concat([df[df.coin == c] for c in s[:0]]) if False else None
    m = df.coin.isin(s)  # approximate (no duplicates): coin subsample
    t_, b_ = df[m & (df.q == 5)], df[m & (df.q <= 3)]
    if len(t_) and len(b_):
        diffs.append((t_.fwd7 < -0.2).mean() - (b_.fwd7 < -0.2).mean())
out["top_vs_bot3"] = {"p_top": round(float((top.fwd7 < -0.2).mean()), 3), "p_bot3": round(float((bot.fwd7 < -0.2).mean()), 3),
                      "coin_boot_p_le0": round(float(np.mean(np.array(diffs) <= 0)), 3)}
for k in ("pooled", "by_year", "by_group", "group_q5_share", "top_vs_bot3"):
    print(k, out[k], flush=True)
json.dump(out, open("research/is3/hsq_ab.json", "w"), indent=1, default=str)
