"""InSilico pass 3, HFY: main_bn (approx .5 flow@bn + .5 blend carry_trend/carry/xsmom) short legs held on HL instead of BN (cached bnall + HL panel). Descriptive.
python -m research.studies.is3_hfy data/is3/fc1c_bnall_1d.pkl"""
import json, pickle, sys
import numpy as np, pandas as pd
from kripto import backtest as bt, data, strategies as S
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY

b = pickle.load(open(sys.argv[1], "rb"))
legs = {"flow": S._ffill_targets(REGISTRY["flow"](b, lookback=3, cap=0.05)).fillna(0.0) * 0.5,
        "carry_blend": REGISTRY["blend"](b, components={"carry_trend": {}, "carry": {}, "xsmom": {}}).fillna(0.0) * 0.5}
h = data.load_panel("hl", "1d")
lo = pd.Timestamp("2023-05-12", tz="UTC")
idx = b["close"].index[b["close"].index >= lo]
hf = h["funding"].reindex(index=idx)
bslip = bt.slippage_model(b["volume"], 1).reindex(idx)
hslip = bt.slippage_model(h["volume"], 1).reindex(idx)
out = {}
for n, W in legs.items():
    wh = W.reindex(idx).shift(1).fillna(0.0)
    cols = [c for c in wh.columns if c in hf.columns and c != "BTC"]
    bf = b["funding"].reindex(index=idx, columns=cols)
    hfc = hf[cols]
    tw = bf.notna() & hfc.notna()
    trd = (W.reindex(idx)[cols] - W.reindex(idx)[cols].shift(1)).abs()
    o = {}
    for side, m in (("short", wh[cols] < 0), ("long", wh[cols] > 0)):
        x = wh[cols].where(m & tw, 0.0)
        sav = (-x * (hfc - bf).fillna(0)).sum(1)         # P&L_HL - P&L_BN = -x(hf - bf): + = better on HL (sign fixed after a first run had it flipped)
        tm = trd.where(m & tw, 0.0)
        extra = (tm * (hslip[cols].fillna(25e-4) - bslip[cols].fillna(25e-4) + (bt.TAKER_FEE - 5e-4))).sum(1)   # HL fee 4.5 vs BN 5 bp
        for y in (2023, 2024, 2025, 2026):
            ix = idx.year == y
            allg = wh[cols].where(m, 0).abs().sum(1)[ix].sum() + wh.drop(columns=cols, errors="ignore").where(wh.drop(columns=cols, errors="ignore") < 0 if side == "short" else wh.drop(columns=cols, errors="ignore") > 0, 0).abs().sum(1)[ix].sum()
            o.setdefault(side, {})[str(y)] = {"twin_share": round(float(x.abs().sum(1)[ix].sum() / max(allg, 1e-12)), 3),
                                              "funding_saving_ann": round(float(sav[ix].mean() * 365), 4), "extra_cost_ann": round(float(extra[ix].mean() * 365), 4),
                                              "net_saving_ann": round(float((sav - extra)[ix].mean() * 365), 4)}
    out[n] = o
    print(n, {s: {y: (v["twin_share"], v["funding_saving_ann"], v["extra_cost_ann"], v["net_saving_ann"]) for y, v in d.items()} for s, d in o.items()}, flush=True)
json.dump(out, open("research/is3/hfy_ab.json", "w"), indent=1)
