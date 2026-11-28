"""X1F: fspread_hold@pair live funding vs research prints and vs the backtest's funding per unit gross. Descriptive, NOT registered.
PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_x1f -> research/is3/x1f_ab.json"""
import json
import numpy as np, pandas as pd
from kripto import backtest as bt, data, paper as P, strategies as S
from kripto.research import bars_per_day, default_band
from research.studies.is3_x1v import live_positions

BOOK = "shadow:fspread_hold@pair"
store = P.Store()
f = pd.DataFrame(store.q("select ts, coin, amount, rate from funding where book=?", BOOK), columns=["ts", "coin", "amount", "rate"])
f["ts"] = pd.to_datetime(f["ts"], utc=True, format="mixed"); f["hour"] = f["ts"].dt.floor("1h"); f["venue"] = f.coin.str[-2:]; f["c"] = f.coin.str[:-3]
f["notional"] = -f.amount / f.rate.replace(0, np.nan)
out = {"rows": len(f), "first": str(f.ts.min()), "last": str(f.ts.max())}


def prints(c, venue):
    if venue == "hl":
        x = pd.read_parquet(f"data/hl/funding/{c}.parquet")
    else:
        fp = f"data/bn/funding_all/{data.hl_to_bn(c)}USDT.parquet"
        try:
            x = pd.read_parquet(fp)
        except FileNotFoundError:
            return pd.Series(dtype=float)
    return x.assign(h=pd.to_datetime(x.time, unit="ms", utc=True).dt.floor("1h")).groupby("h").fundingRate.last()


# a: live rate vs research print for the same coin/hour (research ends 11-21 for BN; HL files = live's own source)
rows = []
for (c, v), g in f.groupby(["c", "venue"]):
    pr = prints(c, v)
    m = g.hour.map(pr)
    rows.append(pd.DataFrame({"venue": v, "c": c, "hour": g.hour, "live": g.rate, "res": m.values}))
A = pd.concat(rows); A = A[A.hour < pd.Timestamp("2026-11-22", tz="UTC")]
a = {}
for v, g in A.groupby("venue"):
    mt = g.dropna(subset=["res"])
    a[v] = {"live_prints": len(g), "matched": len(mt), "share_matched": round(len(mt) / max(len(g), 1), 3),
            "median_abs_diff_bp": round(float((mt.live - mt.res).abs().median() * 1e4), 4), "max_abs_diff_bp": round(float((mt.live - mt.res).abs().max() * 1e4), 3),
            "unmatched_coins": sorted(set(g[g.res.isna()].c))}
out["a_prints"] = a
# known answer: one row by hand
r0 = f.iloc[len(f) // 2]
pos = store.q("select coalesce(sum(size),0) from fills where book=? and coin=? and ts < ?", BOOK, r0.coin, r0.ts.isoformat())[0][0]
out["a_hand_row"] = {"coin": r0.coin, "ts": str(r0.ts), "rate": r0.rate, "amount": r0.amount, "implied_notional": round(float(r0.notional), 2), "size_before": pos,
                     "implied_px": round(float(r0.notional / pos), 6) if pos else None}
print(json.dumps(out, default=str), flush=True)
# b1: replay live positions on research DAILY funding (pair panel) vs live funding per day; b2: per unit gross vs the backtest's own book
p = data.load_panel("pair", "1d"); c = p["close"]; fu = p["funding"]
f["day"] = f.ts.dt.floor("1D")
live_day = f.groupby("day").amount.sum()
pos = live_positions(store, BOOK)
days = [d for d in live_day.index if d in fu.index]
rep = pd.Series({d: float(-sum(pos.loc[d, k] * c.loc[d - pd.Timedelta(days=1), k] * fu.loc[d, k] for k in pos.columns
                               if k in fu.columns and np.isfinite(fu.loc[d, k]) and pos.loc[d, k] != 0))
                 for d in days if d in pos.index})  # held during day d = after its 00:12 rebalance
gross_live = pd.Series({d: float((pos.loc[d].abs() * c.loc[d - pd.Timedelta(days=1)].reindex(pos.columns)).sum()) for d in rep.index})
w = S.REGISTRY["fspread_hold"](p, lookback=14, enter=0.1)
res = bt.run(w, c, fu, bt.slippage_model(p["volume"], bars_per_day(c.index)), band=default_band())
bt_gross = res.weights.abs().sum(axis=1)   # held during the bar that pays funding[t]
b = pd.DataFrame({"live": live_day.reindex(rep.index), "replay": rep, "gross_live": gross_live,
                  "live_per_gross_bp": live_day.reindex(rep.index) / gross_live * 1e4,
                  "bt_per_gross_bp": (res.funding.reindex(rep.index) / bt_gross.reindex(rep.index)) * 1e4})
print(b.round(3).to_string(), flush=True)
out["b"] = {"days": len(b), "live_sum": round(float(b.live.sum()), 3), "replay_sum": round(float(b.replay.sum()), 3), "ratio_live_over_replay": round(float(b.live.sum() / b.replay.sum()), 3),
            "corr_daily": round(float(b.live.corr(b.replay)), 3), "mean_live_per_gross_bp": round(float(b.live_per_gross_bp.mean()), 3),
            "mean_bt_per_gross_bp": round(float(b.bt_per_gross_bp.mean()), 3),
            "bt_per_gross_bp_2026": round(float((res.funding / bt_gross).loc["2026"].replace([np.inf, -np.inf], np.nan).mean() * 1e4), 3),
            "sd_diff_live_minus_bt_per_gross_bp": round(float((b.live_per_gross_bp - b.bt_per_gross_bp).std()), 3),
            "daily": b.round(4).reset_index().astype(str).to_dict("records")}
print({k: v for k, v in out["b"].items() if k != "daily"})
json.dump(out, open("research/is3/x1f_ab.json", "w"), indent=1, default=str)
