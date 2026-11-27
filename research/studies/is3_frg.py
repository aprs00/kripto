"""InSilico pass 3, FRG: market funding state (month m) vs the carry books' income and return in month m+1. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_frg ab   # -> research/is3/frg_ab.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto import strategies as S
from kripto.research import default_band


def run_ab():
    p = data.load_panel("bnall", "1d")
    c = p["close"]
    slip = bt.slippage_model(p["volume"], 1)
    run = lambda w: bt.run(w, c, p["funding"], slip, band=default_band())
    f7 = p["funding"].rolling(7, min_periods=3).mean()
    top = S.universe(p, 100)
    st = pd.DataFrame({"med": f7.where(top).median(axis=1), "p90": f7.where(top).quantile(.9, axis=1),
                       "share_hot": (f7.abs() > 0.001).where(top).mean(axis=1)})
    st_m = st.resample("ME").last()                  # state known at the month's last close
    books = {"carry": run(S.REGISTRY["carry"](p)), "carry_trend": run(S.REGISTRY["carry_trend"](p))}
    wf = S.REGISTRY["flow"](p, lookback=3, cap=0.05).ffill().fillna(0.0)
    wb = S.REGISTRY["blend"](p, components={"carry_trend": {}, "carry": {}, "xsmom": {}}).ffill().fillna(0.0).reindex(columns=wf.columns, fill_value=0.0)
    books["main_bn"] = run((wf + wb) * 0.578)
    del p
    pp = data.load_panel("pair", "1d")
    books["pair"] = bt.run(S.REGISTRY["fspread_hold"](pp, lookback=14, enter=0.1) * 0.5, pp["close"], pp["funding"], bt.slippage_model(pp["volume"], 1), band=default_band())
    out = {"n_months": {}, "corr_state_vs_next": {}, "ar1": {}, "terciles_next_month": {}}
    for k, r in books.items():
        inc = r.funding.resample("ME").sum()
        net = r.returns.resample("ME").sum()
        lo = r.gross[r.gross > 0].index.min()
        df = pd.DataFrame({"inc_next": inc.shift(-1), "net_next": net.shift(-1), "inc": inc, **{f"s_{x}": st_m[x] for x in st_m}}).loc[lo:].dropna()
        df = df.loc["2021":]
        out["n_months"][k] = int(len(df))
        out["corr_state_vs_next"][k] = {f"{s}->{y}": round(float(df[s].corr(df[y], method="spearman")), 2) for s in ("s_med", "s_p90", "s_share_hot") for y in ("inc_next", "net_next")}
        out["ar1"][k] = {"income": round(float(df.inc.corr(df.inc_next, method="spearman")), 2)}
        df["t"] = pd.qcut(df.s_med.rank(method="first"), 3, labels=["low", "mid", "high"])
        out["terciles_next_month"][k] = {str(t): {"inc_pct": round(float(g.inc_next.mean() * 100), 2), "net_pct": round(float(g.net_next.mean() * 100), 2), "n": int(len(g))} for t, g in df.groupby("t", observed=True)}
        print(k, out["n_months"][k], out["corr_state_vs_next"][k], out["ar1"][k], out["terciles_next_month"][k], flush=True)
    out["state_now"] = {k: round(float(v), 5) for k, v in st.iloc[-1].items()}
    out["state_pctile_now_vs_2021_26"] = {k: round(float((st[k].loc["2021":] < st[k].iloc[-1]).mean()), 2) for k in st}
    print(out["state_now"], out["state_pctile_now_vs_2021_26"])
    json.dump(out, open("research/is3/frg_ab.json", "w"), indent=1)


if __name__ == "__main__":
    {"ab": run_ab}[sys.argv[1]]()
