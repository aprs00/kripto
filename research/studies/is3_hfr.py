"""InSilico pass 3, HFR: HL main blend monthly funding P&L vs the HL market funding state. Descriptive."""
import json
import numpy as np, pandas as pd
from kripto import backtest as bt, data, strategies as S
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY
p = data.load_panel("hl", "1d")
w = REGISTRY["blend"](p, components={"listing_short": {}, "lowvol": {}, "tsmom": {}})
slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
res = bt.run(w, p["close"], p.get("funding"), slip, band=0.005)
fd = res.funding[res.funding.index >= pd.Timestamp("2023-04-01", tz="UTC")]
m = fd.groupby(fd.index.to_period("M")).sum()
top = S.universe(p, 20)
mf = p["funding"].where(top).median(axis=1) * 365
mf = mf[mf.index >= pd.Timestamp("2023-04-01", tz="UTC")]
st = mf.groupby(mf.index.to_period("M")).mean()
df = pd.DataFrame({"drag": m, "state": st}).dropna()
df = df.iloc[:-1] if df.index[-1] == pd.Timestamp.utcnow().to_period("M") else df   # current month partial: state only
out = {"n_months": int(len(df)), "drag_mean_month": float(df.drag.mean()), "ar1_drag": float(df.drag.autocorr(1)), "ar1_state": float(df.state.autocorr(1)),
       "rank_corr_state_m_drag_m1": float(df.state.iloc[:-1].reset_index(drop=True).corr(df.drag.iloc[1:].reset_index(drop=True), method="spearman")),
       "rank_corr_same_month": float(df.state.corr(df.drag, method="spearman"))}
now = st.iloc[-1]
out["state_now_ann"] = float(now); out["state_now_pct"] = float((st.iloc[:-1] < now).mean())
nxt = pd.DataFrame({"s": df.state.iloc[:-1].values, "d": df.drag.iloc[1:].values})
nxt["t"] = pd.qcut(nxt.s, 3, labels=["low", "mid", "high"])
out["next_drag_by_state_tercile"] = {str(k): float(v) for k, v in nxt.groupby("t", observed=True).d.mean().items()}
out["tercile_edges_ann"] = [float(x) for x in nxt.s.quantile([1 / 3, 2 / 3])]
print(json.dumps(out, indent=0), flush=True)
json.dump(out, open("research/is3/hfr_abc.json", "w"), indent=1)
