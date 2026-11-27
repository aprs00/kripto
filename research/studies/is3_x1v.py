"""InSilico pass 3, X1V: why fspread_hold@pair's live price-P&L vol is ~3x the backtest's. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_x1v a    # live ledger vs backtest day by day + replay of LIVE positions on research closes -> research/is3/x1v_a.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto import paper as P
from kripto import strategies as S
from kripto.research import bars_per_day, default_band
from scripts.ledger_decomp import decompose

BOOK = "shadow:fspread_hold@pair"


def live_positions(store, book=BOOK) -> pd.DataFrame:
    """Position per leg after each day's rebalance (fills accumulated to the end of UTC day D), index = day D."""
    f = pd.DataFrame(store.q("select ts, coin, size from fills where book=? order by ts", book), columns=["ts", "coin", "size"])
    f["day"] = pd.to_datetime(f["ts"], utc=True, format="mixed").dt.floor("1D")
    pos = f.pivot_table(index="day", columns="coin", values="size", aggfunc="sum").fillna(0.0).cumsum()
    days = pd.date_range(pos.index.min(), pd.Timestamp.now("UTC").floor("1D"), freq="1D")
    return pos.reindex(days).ffill()


def run_a():
    store = P.Store()
    led = decompose(store, BOOK)
    start = store.q("select start_equity from books where name=?", BOOK)[0][0]
    led.index = led.index.floor("1D")
    pos = live_positions(store)
    p = data.load_panel("pair", "1d")
    c = p["close"]
    # backtest of the registered function on the research panel (its own path-dependent holdings)
    w = S.REGISTRY["fspread_hold"](p, lookback=14, enter=0.1)
    slip = bt.slippage_model(p["volume"], bars_per_day(c.index))
    res = bt.run(w, c, p["funding"], slip, band=default_band())
    wf = w.ffill().fillna(0.0)
    days = [d for d in led.index if d in c.index and (d - pd.Timedelta(days=1)) in c.index]
    rows = []
    for d in days:
        prev = d - pd.Timedelta(days=1)
        # live day D (00:0x D -> 00:0x D+1) ~ research bar D (close at D+1 00:00) minus bar D-1; positions held = after D's 00:12 rebalance
        ps = pos.loc[d] if d in pos.index else pd.Series(dtype=float)
        ps = ps[ps != 0]
        dpx = (c.loc[d] - c.loc[prev])
        miss = [k for k in ps.index if k not in c.columns or not np.isfinite(dpx.get(k, np.nan))]
        rep = float(sum(ps[k] * dpx[k] for k in ps.index if k not in miss))
        bt_hold = sorted(k[:-3] for k in wf.columns if k.endswith("@hl") and wf.loc[d, k] != 0)
        lv_hold = sorted(k[:-3] for k in ps.index if k.endswith("@hl"))
        rows.append({"day": str(d.date()), "live_price": round(float(led.loc[d, "price"]), 2), "replay_live_pos_research_close": round(rep, 2),
                     "bt_ret_bp": round(float(res.returns.get(d, np.nan)) * 1e4, 1), "live_ret_bp": round(float(led.loc[d, "d_eq"]) / start * 1e4, 1),
                     "missing": miss, "live_hold": lv_hold, "bt_hold": bt_hold, "overlap": len(set(lv_hold) & set(bt_hold))})
    df = pd.DataFrame(rows)
    k = np.sqrt(365) / start
    bt_r = res.returns.reindex(pd.to_datetime(df["day"]).dt.tz_localize("UTC"))
    out = {"n_days": len(df), "panel_end": str(c.index[-1].date()),
           "vol_live_price_pct": round(float(df.live_price.std() * k) * 100, 2),
           "vol_replay_live_pos_pct": round(float(df.replay_live_pos_research_close.std() * k) * 100, 2),
           "vol_bt_ret_pct_same_days": round(float(bt_r.std() * np.sqrt(365)) * 100, 2),
           "vol_bt_ret_pct_2026": round(float(res.returns.loc["2026"].std() * np.sqrt(365)) * 100, 2),
           "corr_live_vs_replay": round(float(df.live_price.corr(df.replay_live_pos_research_close)), 3),
           "mean_overlap_pairs": round(float(df.overlap.mean()), 2), "mean_live_pairs": round(float(df.live_hold.str.len().mean()), 2),
           "mean_bt_pairs": round(float(df.bt_hold.str.len().mean()), 2), "days": rows}
    print(df.drop(columns=["live_hold", "bt_hold"]).to_string())
    for r in rows[:1] + rows[-1:]:
        print(r["day"], "live", r["live_hold"], "| bt", r["bt_hold"])
    print({k_: v for k_, v in out.items() if k_ != "days"})
    json.dump(out, open("research/is3/x1v_a.json", "w"), indent=1)
    return out




def run_a2():
    """How unusual are the live days for the backtest itself: rolling 10-day vol of the backtest's daily returns, 2023-05.. ."""
    a = json.load(open("research/is3/x1v_a.json"))
    p = data.load_panel("pair", "1d")
    c = p["close"]
    w = S.REGISTRY["fspread_hold"](p, lookback=14, enter=0.1)
    res = bt.run(w, c, p["funding"], bt.slippage_model(p["volume"], bars_per_day(c.index)), band=default_band())
    r = res.returns.loc["2023-06":]
    rv = r.rolling(10).std() * np.sqrt(365) * 100
    last = float(rv.loc[a["days"][-1]["day"]])
    df = pd.DataFrame(a["days"])
    resid = df.live_price - df.replay_live_pos_research_close
    out = {"bt_vol_by_year_pct": {int(y): round(float(x.std() * np.sqrt(365) * 100), 2) for y, x in r.groupby(r.index.year)},
           "bt_10d_vol_at_live_window_end_pct": round(last, 2), "pctile_of_all_10d_windows": round(float((rv < last).mean()), 3),
           "bt_10d_vol_median_pct": round(float(rv.median()), 2),
           "resid_live_minus_replay_usd_std": round(float(resid.std()), 2), "replay_usd_std": round(float(df.replay_live_pos_research_close.std()), 2)}
    print(out)
    a["a2"] = out
    json.dump(a, open("research/is3/x1v_a.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": run_a, "a2": run_a2}[sys.argv[1]]()
