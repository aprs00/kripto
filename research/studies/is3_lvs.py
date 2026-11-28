"""InSilico pass 3, LVS: HL lowvol leg (as held in the main-book blend, is3_prl.legs) split by side.
a: per side (long = low-vol alts + BTC hedge, short = high-vol alts) price, funding, approx costs by year; corr of each side's daily P&L to BTC and an alt index.
b: high-vol short candidates' next-30-d simple return by trailing-30-d return quintile (explore 2023-24; 2025-26 shown separately, descriptive).
python -m research.studies.is3_lvs a|b"""
import json, sys
import numpy as np, pandas as pd
from kripto import backtest as bt, data
from kripto.research import bars_per_day
from research.studies.is3_prl import legs

p = data.load_panel("hl", "1d")
fin, ref, err = legs(p)
w = fin["lowvol"].fillna(0.0)
close = p["close"].reindex(index=w.index, columns=w.columns)
r = close.pct_change(fill_method=None).fillna(0.0)
f = p["funding"].reindex(index=w.index, columns=w.columns).fillna(0.0)
slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index)).reindex(index=w.index, columns=w.columns).fillna(25e-4)
form = sys.argv[1] if len(sys.argv) > 1 else "a"
out = {"decomp_err": err}
yrs = (2023, 2024, 2025, 2026)
if form == "a":
    wh = w.shift(1).fillna(0.0)                          # held through bar t
    tr = (w - w.shift(1).fillna(0.0)).abs()              # traded at close t (drift ignored: approximation)
    cst = tr * (bt.TAKER_FEE + slip)
    alts = [c for c in w.columns if c != "BTC"]
    altidx = r[alts].where(close[alts].notna()).mean(1)  # equal-weight HL alt index (all listed)
    for side in ("long", "short"):
        m = (wh > 0) if side == "long" else (wh < 0)
        x = wh.where(m, 0.0)
        mc = (w > 0) | (w.shift(1) > 0) if side == "long" else (w < 0) | (w.shift(1) < 0)
        price, fund, cost = (x * r).sum(1), (-x * f).sum(1), cst.where(mc, 0.0).sum(1)
        pnl = price + fund - cost
        o = {}
        for y in yrs:
            ix = pnl.index.year == y
            o[str(y)] = {"price": round(float(price[ix].mean() * 365), 4), "funding": round(float(fund[ix].mean() * 365), 4),
                         "cost": round(float(cost[ix].mean() * 365), 4), "net": round(float(pnl[ix].mean() * 365), 4),
                         "gross_exp": round(float(x[ix].abs().sum(1).mean()), 3), "btc_w": round(float(x.loc[ix, "BTC"].mean()), 3),
                         "corr_btc": round(float(pnl[ix].corr(r.loc[ix, "BTC"])), 3), "corr_alt": round(float(pnl[ix].corr(altidx[ix])), 3)}
        out[side] = o
        print(side, {y: (v["price"], v["funding"], v["cost"], v["net"], v["corr_btc"], v["corr_alt"]) for y, v in o.items()}, flush=True)
    tot = (wh * r).sum(1) + (-wh * f).sum(1) - cst.sum(1)
    out["leg_net"] = {str(y): round(float(tot[tot.index.year == y].mean() * 365), 4) for y in yrs}
    out["leg_corr_btc"] = {str(y): round(float(tot[tot.index.year == y].corr(r.loc[tot.index.year == y, "BTC"])), 3) for y in yrs}
    print("leg net", out["leg_net"], "corr btc", out["leg_corr_btc"])
else:
    # short candidates = coins the leg is short at a rebalance (weekly target change days); state = trailing 30-d simple return
    fwd = close.shift(-30) / close - 1.0
    past = close / close.shift(30) - 1.0
    reb = w.index[(w.diff().abs().sum(1) > 1e-9)]
    rows = []
    for t in reb:
        s = w.loc[t]
        for c in s.index[s < 0]:
            if c == "BTC" or pd.isna(fwd.at[t, c]) or pd.isna(past.at[t, c]):
                continue
            rows.append((t, c, float(past.at[t, c]), float(fwd.at[t, c]), float(fwd.at[t, "BTC"]) if not pd.isna(fwd.at[t, "BTC"]) else np.nan, float(-s[c])))
    e = pd.DataFrame(rows, columns=["t", "coin", "past30", "fwd30", "btc30", "wt"])
    e["ex"] = e["fwd30"] - e["btc30"]
    exp = e[e.t < pd.Timestamp("2025-01-01", tz="UTC")]
    edges = exp["past30"].quantile([.2, .4, .6, .8]).tolist()
    out["edges_explore"] = edges
    for name, d in (("2023-24", exp), ("2025-26", e[e.t >= pd.Timestamp("2025-01-01", tz="UTC")])):
        q = np.searchsorted(edges, d["past30"].to_numpy())
        g = {}
        for k in range(5):
            dd = d[q == k]
            if len(dd) == 0:
                continue
            g[f"q{k+1}"] = {"n": int(len(dd)), "dates": int(dd.t.nunique()), "mean_fwd": round(float(dd.fwd30.mean()), 4), "median_fwd": round(float(dd.fwd30.median()), 4),
                            "mean_ex_btc": round(float(dd.ex.mean()), 4), "p_up20": round(float((dd.fwd30 > 0.2).mean()), 3),
                            "t_date_cl": round(float(dd.groupby("t").ex.mean().mean() / (dd.groupby("t").ex.mean().std() / np.sqrt(dd.t.nunique()))), 2) if dd.t.nunique() > 2 else None}
        out[name] = g
        print(name, {k: (v["n"], v["mean_fwd"], v["median_fwd"], v["mean_ex_btc"], v["p_up20"], v["t_date_cl"]) for k, v in g.items()}, flush=True)
    # overlapping 30-d windows on weekly rebalances: date-clustered t is optimistic (overlap ~4x); quoted as such
json.dump(out, open(f"research/is3/lvs_{form}.json", "w"), indent=1, default=str)
