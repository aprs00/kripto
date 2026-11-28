"""InSilico pass 3, ASR: short-alt factor's next-30-d return by trailing-30-d alt-minus-BTC state. a: HL blend legs; b: cached bnall listing_short + lowvol.
python -m research.studies.is3_asr a | b <bnall pickle>"""
import json, pickle, sys, inspect
import numpy as np, pandas as pd
from kripto import backtest as bt, data, strategies as S
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY

form = sys.argv[1]
OUT = "research/is3/asr_%s.json" % form


def state(p):
    c = p["close"]; r = c.pct_change(fill_method=None)
    u = S.universe(p, 30)
    alt = r.where(u).drop(columns=["BTC"]).mean(1)
    a30 = (1 + alt.fillna(0)).rolling(30).apply(np.prod, raw=True) - 1
    b30 = c["BTC"] / c["BTC"].shift(30) - 1
    return a30 - b30


def table(fac, st, edges, yrs):
    fwd = (1 + fac).rolling(30).apply(np.prod, raw=True).shift(-30) - 1
    d = pd.DataFrame({"st": st, "fwd": fwd}).dropna()
    d["q"] = np.searchsorted(edges, d.st.to_numpy()) + 1
    o = {"pooled": {int(q): [int(len(g)), round(float(g.fwd.mean()), 4), round(float(g.fwd.median()), 4), round(float((g.fwd < -0.05).mean()), 3)] for q, g in d.groupby("q")}}
    for y in yrs:
        g0 = d[d.index.year == y]
        o[str(y)] = {int(q): [int(len(g)), round(float(g.fwd.mean()), 4)] for q, g in g0.groupby("q")}
    o["spearman"] = round(float(d.st.corr(d.fwd, method="spearman")), 3)
    return o


if form == "a":
    from research.studies.is3_prl import legs
    p = data.load_panel("hl", "1d")
    fin, _, _ = legs(p)
    slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
    fac = bt.run((fin["listing_short"] + fin["lowvol"]).fillna(0.0), p["close"], p.get("funding"), slip, band=0.005).returns
    fac = fac.loc[pd.Timestamp("2023-03-01", tz="UTC"):]
    st = state(p).reindex(fac.index)
    edges = st.dropna().quantile([.2, .4, .6, .8]).tolist()
    out = {"edges": edges, **table(fac, st, edges, (2023, 2024, 2025, 2026))}
else:
    p = pickle.load(open(sys.argv[2], "rb"))
    slip = bt.slippage_model(p["volume"], 1)
    w = 0.0
    for n in ("listing_short", "lowvol"):
        tv = inspect.signature(REGISTRY[n]).parameters["target_vol"].default
        w = w + S._ffill_targets(REGISTRY[n](p)).reindex(columns=p["close"].columns, fill_value=0.0).fillna(0.0) * (0.20 / tv) / 2
    fac = bt.run(w, p["close"], p.get("funding"), slip, band=0.005).returns.loc[pd.Timestamp("2020-03-01", tz="UTC"):]
    st = state(p).reindex(fac.index)
    edges = json.load(open("research/is3/asr_a.json"))["edges"]
    out = {"edges_frozen_from_hl": edges, **table(fac, st, edges, range(2020, 2027))}
for k, v in out.items():
    print(k, v, flush=True)
json.dump(out, open(OUT, "w"), indent=1)
