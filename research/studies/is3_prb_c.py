import json, numpy as np, pandas as pd
from kripto import backtest as bt, data
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY
from research.studies.is3_prb import partial, summary
out = {}
p = data.load_panel("bnall", "1d")
slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
books = {"blend_bn": REGISTRY["blend"](p, components={"carry_trend": {}, "carry": {}, "xsmom": {}}),
         "flow_bn": REGISTRY["flow"](p, lookback=3, cap=0.05)}
for nm, w in books.items():
    for lam in (1.0, 0.33):
        res = bt.run(partial(w, lam), p["close"], p.get("funding"), slip, band=0.005)
        out[f"{nm}_{lam}"] = {f"{a}": summary(res, f"{a}-01-01", f"{a+1}-01-01") for a in (2021, 2022, 2023)}
        out[f"{nm}_{lam}"]["2021-23"] = summary(res, "2021-01-01", "2024-01-01")
        print(nm, lam, {k: (round(v["sr"], 2), round(v["costs_ann"], 3), round(v["sr_pre_cost"], 2)) for k, v in out[f"{nm}_{lam}"].items()}, flush=True)
# $200 executability on HL: share of traded cells (|dw| > band) whose notional at $200 is below $10
h = data.load_panel("hl", "1d")
wh = REGISTRY["blend"](h, components={"listing_short": {}, "lowvol": {}, "tsmom": {}})
for lam in (1.0, 0.33):
    d = partial(wh, lam).diff().abs()
    d = d[d.index >= pd.Timestamp("2023-01-01", tz="UTC")].to_numpy().ravel()
    d = d[d > 0.005]
    out[f"hl_small_lam{lam}"] = {"n_trades": int(len(d)), "share_below_10usd_at_200": float((d * 200 < 10).mean()), "share_below_10usd_at_1000": float((d * 1000 < 10).mean())}
    print(lam, out[f"hl_small_lam{lam}"], flush=True)
json.dump(out, open("research/is3/prb_c.json", "w"), indent=1)
