"""L1T: Binance->HL lead-lag as execution timing for the shipped HL main book's daily trades. Rule (fixed before any run): per trade, L = s x (BN ret - HL ret) over the hour
before the decision (D 22:00 -> 23:00 bar closes); wait 1 h when L < 0, else trade at the decision price. Saving per unit traded = -s x HL ret over the next hour on waited trades.
Explore = 2026-04-15..07-22, held-out = 07-23..10-31. Placebo: same number of waits chosen at random (200 draws). Not registered.
PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_l1t -> research/is3/l1t_abc.json"""
import json
import numpy as np, pandas as pd
from kripto import backtest as bt, data
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY

d = data.load_panel("hl", "1d")
w = REGISTRY["blend"](d, components={"listing_short": {}, "lowvol": {}, "tsmom": {}}, slow_lam=0.33)
res = bt.run(w, d["close"], d.get("funding"), bt.slippage_model(d["volume"], bars_per_day(d["close"].index)), band=0.005)
H = res.weights                                    # held through bar t; trade at t's close = H[t+1] - (drifted H[t]) ~ H[t+1] - H[t]
dW = (H.shift(-1) - H)                             # trade decided at day t's close
hh = data.load_panel("hl", "1h")["close"]; bb = data.load_panel("bn", "1h")["close"]
coins = sorted(set(hh.columns) & set(bb.columns) & set(H.columns))
rows = []
for t in dW.index:
    dec = t + pd.Timedelta(hours=23)                # the 1h bar whose close = day t's close
    prev, nxt = dec - pd.Timedelta(hours=1), dec + pd.Timedelta(hours=1)
    if prev not in hh.index or nxt not in hh.index or prev not in bb.index or dec not in bb.index:
        continue
    for cn in coins:
        x = dW.at[t, cn]
        if not np.isfinite(x) or abs(x) < 0.005:
            continue
        hp, hd, hn = hh.at[prev, cn], hh.at[dec, cn], hh.at[nxt, cn]
        bp_, bd = bb.at[prev, cn], bb.at[dec, cn]
        if not all(np.isfinite([hp, hd, hn, bp_, bd])):
            continue
        s = np.sign(x)
        rows.append({"day": t, "coin": cn, "units": abs(x), "L": s * ((bd / bp_ - 1) - (hd / hp - 1)), "wait_gain": -s * (hn / hd - 1)})
E = pd.DataFrame(rows)
out = {"coins": len(coins), "trades": len(E), "days": int(E["day"].nunique()) if len(E) else 0}


def cl_t(e, col):
    g = e.groupby("day").apply(lambda z: (z[col] * z["units"]).sum() / z["units"].sum())
    return float(g.mean() / (g.std() / np.sqrt(len(g)))) if len(g) > 2 else None


def sample(e, tag):
    o = {"trades": len(e), "days": int(e["day"].nunique())}
    q = pd.qcut(e["L"], 3, labels=["lo", "mid", "hi"])
    o["wait_gain_bp_by_L_tercile"] = {k: round(float((g["wait_gain"] * g["units"]).sum() / g["units"].sum() * 1e4), 2) for k, g in e.groupby(q, observed=True)}
    wait = e["L"] < 0
    sav = (e["wait_gain"] * e["units"] * wait).sum() / e["units"].sum()      # per unit traded (all trades), waited trades contribute their gain
    o["share_waited_units"] = round(float((e["units"] * wait).sum() / e["units"].sum()), 3)
    o["saving_bp_per_unit"] = round(float(sav * 1e4), 2)
    e2 = e.assign(g=e["wait_gain"] * wait)
    gd = e2.groupby("day").apply(lambda z: (z["g"] * z["units"]).sum() / z["units"].sum())
    o["day_t"] = round(float(gd.mean() / (gd.std() / np.sqrt(len(gd)))), 2)
    rng = np.random.default_rng(11); pl = []
    for _ in range(200):
        m = rng.random(len(e)) < wait.mean()
        pl.append((e["wait_gain"] * e["units"] * m).sum() / e["units"].sum())
    pl = np.array(pl) * 1e4
    o["placebo_bp_mean_p95"] = [round(float(pl.mean()), 2), round(float(np.quantile(pl, .95)), 2)]
    o["p_vs_placebo"] = round(float((pl >= o["saving_bp_per_unit"]).mean()), 3)
    o["top3_day_share"] = round(float(gd.nlargest(3).sum() / gd.sum()), 2) if gd.sum() > 0 else None
    return o


ex = E[E["day"] < pd.Timestamp("2026-07-23", tz="UTC")]; ho = E[E["day"] >= pd.Timestamp("2026-07-23", tz="UTC")]
out["explore"] = sample(ex, "explore")
print("explore", json.dumps(out["explore"]), flush=True)
out["turnover_units_per_yr"] = round(float(res.turnover.loc["2023":].mean() * 365), 1)
# hand check: one trade printed
r0 = E.iloc[len(E) // 2]; out["hand_check"] = {k: (str(v) if k in ("day", "coin") else round(float(v), 6)) for k, v in r0.items()}
json.dump(out, open("research/is3/l1t_abc.json", "w"), indent=1, default=str)
E.to_parquet("data/is3/l1t_events.parquet")
