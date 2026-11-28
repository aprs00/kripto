"""InSilico pass 3, HFZ: HL blend split into a shorts account (HL funding) and a longs account (BN funding, cached bnall); per-account swings and transfers.
python -m research.studies.is3_hfz data/is3/fc1c_bnall_1d.pkl"""
import json, pickle, sys
import numpy as np, pandas as pd
from kripto import data
from research.studies.is3_prl import legs

b = pickle.load(open(sys.argv[1], "rb"))
h = data.load_panel("hl", "1d")
_, ref, _ = legs(h)
end = b["close"].index[-1]
W = ref.fillna(0.0).shift(1).fillna(0.0).loc[pd.Timestamp("2023-05-12", tz="UTC"):end]
r = h["close"].pct_change(fill_method=None).reindex(index=W.index, columns=W.columns).fillna(0.0)
hf = h["funding"].reindex(index=W.index, columns=W.columns).fillna(0.0)
bf = b["funding"].reindex(index=W.index, columns=W.columns)
bf = bf.fillna(hf)                                     # no BN twin -> that long stays at HL funding (stated)
S, L = W.clip(upper=0), W.clip(lower=0)
pnl_s = (S * r - S * hf).sum(1)                         # fraction of total equity
pnl_l = (L * r - L * bf).sum(1)
gs, gl = S.abs().sum(1), L.sum(1)
tgt_s = (gs / (gs + gl).replace(0, np.nan)).fillna(0.5).clip(0.2, 0.8)   # margin share pro rata to gross, floor/cap .2/.8 (stated)
E, es, el = 1.0, 0.5, 0.5
rows, transfers = [], []
for t in W.index:
    ds, dl = E * pnl_s[t], E * pnl_l[t]
    rb = pnl_s[t] + pnl_l[t]                          # book return on total equity
    rs, rl = ds / es, dl / el
    es, el = es + ds, el + dl
    E = es + el
    ts = tgt_s[t]
    dev = max(abs(es / E - ts) / ts, abs(el / E - (1 - ts)) / (1 - ts))
    tr = 0.0
    if dev > 0.25:
        tr = abs(es - ts * E) / E
        es, el = ts * E, (1 - ts) * E
        transfers.append((t, tr))
    rows.append((t, rs, rl, rb, tr))
A = pd.DataFrame(rows, columns=["t", "acct_s", "acct_l", "book", "transfer"]).set_index("t")
book = A.book                                          # book return (fraction of total equity at t-1, since E is total)
out = {}
for k in ("acct_s", "acct_l"):
    x7 = (1 + A[k]).rolling(7).apply(np.prod, raw=True) - 1
    out[k] = {"vol_ann": round(float(A[k].std() * np.sqrt(365)), 3), "worst_7d": round(float(x7.min()), 3), "p01_7d": round(float(x7.quantile(.01)), 3),
              "p05_7d": round(float(x7.quantile(.05)), 3), "n_7d_below_-25": int((x7 < -0.25).sum())}
b7 = (1 + book).rolling(7).apply(np.prod, raw=True) - 1
out["book"] = {"vol_ann": round(float(book.std() * np.sqrt(365)), 3), "worst_7d": round(float(b7.min()), 3), "p01_7d": round(float(b7.quantile(.01)), 3)}
T = pd.Series([x for _, x in transfers], index=[t for t, _ in transfers])
out["transfers"] = {"n": int(len(T)), "per_year": {str(y): int((T.index.year == y).sum()) for y in (2023, 2024, 2025, 2026)},
                    "median_size_of_book": round(float(T.median()), 3) if len(T) else None, "max_size_of_book": round(float(T.max()), 3) if len(T) else None}
for k, v in out.items():
    print(k, v, flush=True)
json.dump(out, open("research/is3/hfz_ab.json", "w"), indent=1)
