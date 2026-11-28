"""InSilico pass 3, HFX: HL main blend's long legs funded on Binance instead of HL (cached bnall pickle for BN funding/close). Descriptive.
python -m research.studies.is3_hfx data/is3/fc1c_bnall_1d.pkl"""
import json, pickle, sys
import numpy as np, pandas as pd
from kripto import data
from research.studies.is3_prl import legs

b = pickle.load(open(sys.argv[1], "rb"))
h = data.load_panel("hl", "1d")
fin, ref, _ = legs(h)
end = b["close"].index[-1]
W = ref.fillna(0.0).shift(1).fillna(0.0).loc[:end]            # held through bar t, whole book
hf = h["funding"].reindex(index=W.index, columns=W.columns)
bf = b["funding"].reindex(index=W.index, columns=W.columns)
hr = h["close"].reindex(columns=W.columns).pct_change(fill_method=None).reindex(W.index)
br = b["close"].reindex(columns=W.columns).pct_change(fill_method=None).reindex(W.index)
yrs = (2023, 2024, 2025, 2026)
out = {}
# a: BTC
x = W["BTC"]
both = hf["BTC"].notna() & bf["BTC"].notna()
out["btc"] = {}
for y in yrs:
    ix = (W.index.year == y) & both
    out["btc"][str(y)] = {"days": int(ix.sum()), "hl_fund_ann": round(float(hf["BTC"][ix].mean() * 365), 4), "bn_fund_ann": round(float(bf["BTC"][ix].mean() * 365), 4),
                          "held_w_mean": round(float(x[ix].mean()), 3), "long_share": round(float((x[ix] > 0).mean()), 3),
                          "book_saving_ann": round(float((x[ix] * (hf["BTC"][ix] - bf["BTC"][ix])).mean() * 365), 4),
                          "ret_diff_sd_bp": round(float((hr["BTC"][ix] - br["BTC"][ix]).std() * 1e4), 1)}
print("btc", out["btc"], flush=True)
# b: every held cell with a BN twin, split long/short and BTC vs alts; saving = what moving that side to BN would change in funding (+ = HL costs more)
tw = bf.notna() & hf.notna()
out["legs"] = {}
for side, m in (("long", W > 0), ("short", W < 0)):
    for part in ("alts",):
        cols = [c for c in W.columns if c != "BTC"]
        xm = W[cols].where(m[cols], 0.0)
        tot_f = (-xm * hf[cols].fillna(0)).sum(1)                       # funding P&L on HL (all held)
        twin = xm.where(tw[cols], 0.0)
        sav = (twin * (hf[cols] - bf[cols]).fillna(0)).sum(1)          # + = cheaper on BN
        o = {}
        for y in yrs:
            ix = W.index.year == y
            o[str(y)] = {"hl_funding_ann": round(float(tot_f[ix].mean() * 365), 4), "twin_share_of_gross": round(float(twin.abs().sum(1)[ix].sum() / max(xm.abs().sum(1)[ix].sum(), 1e-12)), 3),
                         "book_saving_ann": round(float(sav[ix].mean() * 365), 4)}
        out["legs"][f"{side}_{part}"] = o
        print(side, part, o, flush=True)
json.dump(out, open("research/is3/hfx_ab.json", "w"), indent=1)
