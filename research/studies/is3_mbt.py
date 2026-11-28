"""InSilico pass 3, MBT: main_bn live turnover vs its replay since 11-18, per day and per coin. Descriptive.
  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_mbt  -> research/is3/mbt_ab.json"""
import json
import numpy as np
import pandas as pd
from kripto import paper as P
from scripts import live_vs_backtest as L

SINCE = pd.Timestamp("2026-11-18", tz="UTC")
cfg, risk = P.load_cfg(); c = L._db()
live_e = {n: s for n, s in cfg.items() if P.venue_of(s) == "bn" and s.get("status") in ("incubation", "active") and s.get("alloc", 0) > 0}
coins = L.live_universe(c, "bn"); pn = L._panel("bn", coins)
sb = pd.Timestamp(pd.read_sql("select bar from rebalances where book='main_bn' order by bar limit 1", c).iloc[0, 0])
w = L.main_targets([(s["alloc"], L.entry_targets(n, s, "bn", pn, sb)) for n, s in live_e.items()], float(risk["main_scale"]["main_bn"]))
res, panel = L.run_replay(w, pn, "bn", sb, risk, 1000.0)
eq = L.daily_live(c, "main_bn")
f = pd.read_sql("select ts, coin, size, px, reason from fills where book='main_bn'", c)
f["ts"] = pd.to_datetime(f["ts"], utc=True, format="ISO8601"); f = f[f.ts >= SINCE]
f["coin"] = f["coin"].str.replace("@bn", "", regex=False)
f["ntl"] = (f["size"] * f["px"]).abs() / float(eq.mean())
live_day = f.groupby(f.ts.dt.floor("D"))["ntl"].sum()
H = res.weights.diff().abs()   # turnover per bar (weights held DURING a bar: change at the start of bar t = trade at the close of t-1)
to = res.turnover[res.turnover.index >= SINCE - pd.Timedelta(hours=4)]
bt_day = to.groupby((to.index + pd.Timedelta(hours=4)).floor("D")).sum()
days = sorted(set(live_day.index) | set(bt_day.index))
per_day = pd.DataFrame({"live": live_day.reindex(days).fillna(0), "replay": bt_day.reindex(days).fillna(0)}).round(3)
# per coin over the period
tgt = res.target
dT = tgt.ffill().fillna(0).diff().abs()
dT = dT[dT.index >= SINCE]
bt_coin = dT.sum().sort_values(ascending=False)
live_coin = f.groupby("coin")["ntl"].sum().sort_values(ascending=False)
cmp_ = pd.DataFrame({"replay": bt_coin, "live": live_coin}).fillna(0).round(3)
cmp_["gap"] = cmp_.replay - cmp_.live
reb = pd.read_sql("select bar from rebalances where book='main_bn' order by bar", c)
out = {"turn_live": round(float(live_day.sum()), 2), "turn_replay": round(float(bt_day[bt_day.index >= SINCE].sum()), 2),
       "split_11_26": {"before": [round(float(live_day[live_day.index < "2026-11-26"].sum()), 2), round(float(bt_day[(bt_day.index >= SINCE) & (bt_day.index < "2026-11-26")].sum()), 2)],
                       "from": [round(float(live_day[live_day.index >= "2026-11-26"].sum()), 2), round(float(bt_day[bt_day.index >= "2026-11-26"].sum()), 2)]},
       "per_day": per_day.reset_index().astype(str).values.tolist(),
       "top_gap_coins": cmp_.sort_values("gap", ascending=False).head(12).reset_index().astype(str).values.tolist(),
       "replay_only_coins": [k for k in cmp_.index if cmp_.loc[k, "live"] == 0 and cmp_.loc[k, "replay"] > 0.01],
       "live_only_coins": [k for k in cmp_.index if cmp_.loc[k, "replay"] == 0 and cmp_.loc[k, "live"] > 0.01],
       "rebalance_bars_since": [str(x) for x in reb.bar if pd.Timestamp(x) >= SINCE]}
print(json.dumps(out, indent=1)); json.dump(out, open("research/is3/mbt_ab.json", "w"), indent=1)
