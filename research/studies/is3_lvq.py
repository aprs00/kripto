"""InSilico pass 3, LVQ: HL lowvol (as held in the blend) by side x liquidity tier (top-30 volume rank), and 2025 short-side breadth.
python -m research.studies.is3_lvq"""
import json
import numpy as np, pandas as pd
from kripto import backtest as bt, data, strategies as S
from kripto.research import bars_per_day
from research.studies.is3_prl import legs

p = data.load_panel("hl", "1d")
fin, ref, err = legs(p)
w = fin["lowvol"].fillna(0.0)
cols = w.columns
r = p["close"].reindex(columns=cols).pct_change(fill_method=None).reindex(w.index).fillna(0.0)
f = p["funding"].reindex(index=w.index, columns=cols).fillna(0.0)
sl = bt.slippage_model(p["volume"], bars_per_day(p["close"].index)).reindex(index=w.index, columns=cols).fillna(25e-4)
dv = p["volume"].reindex(columns=cols).rolling(30, min_periods=7).mean()
rank = dv.where(S.universe(p, 30).reindex(columns=cols, fill_value=False)).rank(axis=1, ascending=False).reindex(w.index)
tier = pd.DataFrame(np.select([rank <= 10, rank <= 20, rank <= 30], [1, 2, 3], 0), index=w.index, columns=cols)
wh, th = w.shift(1).fillna(0.0), tier.shift(1).fillna(0)
tr = (w - wh).abs()
price, fund, cost = wh * r, -wh * f, tr * (bt.TAKER_FEE + sl)
out = {"decomp_err": err, "a": {}}
alts = [c for c in cols if c != "BTC"]
for side in ("long", "short"):
    sm = (wh > 0) if side == "long" else (wh < 0)
    for k in (1, 2, 3):
        m = sm & (th == k)
        m["BTC"] = False                                   # BTC hedge reported separately (LVS)
        o = {}
        for y in (2023, 2024, 2025, 2026):
            ix = w.index.year == y
            pr, fu = (float(x.loc[ix].where(m.loc[ix], 0).sum(1).mean() * 365) for x in (price, fund))
            co = float(cost.loc[ix].where(m.loc[ix] | (sm & (tier == k)).loc[ix], 0).sum(1).mean() * 365)
            o[str(y)] = {"gross": round(float(wh.abs().loc[ix].where(m.loc[ix], 0).sum(1).mean()), 3), "price": round(pr, 4), "funding": round(fu, 4),
                         "cost": round(co, 4), "net": round(pr + fu - co, 4), "coins": int((m.loc[ix].any()).sum())}
        out["a"][f"{side}_t{k}"] = o
        print(side, k, {y: (v["gross"], v["price"], v["net"], v["coins"]) for y, v in o.items()}, flush=True)
# b: 2025 short-side breadth
ix = w.index.year == 2025
per = price.loc[ix].where((wh < 0).loc[ix], 0)[alts].sum() * 365 / ix.sum()
per = per[per != 0].sort_values(ascending=False)
tot = float(per.sum())
out["b"] = {"total_short_price_2025": round(tot, 4), "n_coins": int(len(per)), "top5": {k: round(float(v), 4) for k, v in per.head(5).items()},
            "top5_share": round(float(per.head(5).sum() / tot), 3), "top10_share": round(float(per.head(10).sum() / tot), 3),
            "bottom5": {k: round(float(v), 4) for k, v in per.tail(5).items()}, "share_positive": round(float((per > 0).mean()), 3)}
print(out["b"], flush=True)
json.dump(out, open("research/is3/lvq_ab.json", "w"), indent=1)
