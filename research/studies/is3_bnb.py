"""InSilico pass 3, BNB: main_bn = 0.5 flow@bn + 0.5 blend_nested@bn on bnall 1d. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_bnb ab   # mix vs legs by year, attribution, price/funding/costs, BTC worst/best weeks -> research/is3/bnb_ab.json
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

sr = lambda x: round(float(x.mean() / x.std() * np.sqrt(365)), 2) if len(x) > 20 and x.std() > 0 else None


def run_ab():
    p = data.load_panel("bnall", "1d")
    c = p["close"]
    slip = bt.slippage_model(p["volume"], 1)
    run = lambda w: bt.run(w, c, p["funding"], slip, band=default_band())
    wf = S.REGISTRY["flow"](p, lookback=3, cap=0.05)
    wb = S.REGISTRY["blend"](p, components={"carry_trend": {}, "carry": {}, "xsmom": {}})
    ff, fb = wf.ffill().fillna(0.0), wb.ffill().fillna(0.0).reindex(columns=wf.columns, fill_value=0.0)
    legs = {"flow": run(ff * 0.578), "blend_nested": run(fb * 0.578)}         # 0.5 x main_scale 1.156: each leg's share of the mix
    mix = run((ff + fb) * 0.578)
    lo = pd.Timestamp("2021-01-01", tz="UTC")
    R = {k: v.returns.loc[lo:] for k, v in legs.items()}
    rm = mix.returns.loc[lo:]
    out = {"mix_sr": sr(rm), "by_year": {}}
    for y in sorted(set(rm.index.year)):
        yy = str(y)
        d = {"mix": {"sr": sr(rm.loc[yy]), "net": round(float(rm.loc[yy].sum()), 4)}}
        for k, v in legs.items():
            d[k] = {"sr_alone": sr(R[k].loc[yy]), "net_contrib": round(float(R[k].loc[yy].sum()), 4), "funding": round(float(v.funding.loc[yy].sum()), 4),
                    "costs": round(float(v.costs.loc[yy].sum()), 4), "turnover": round(float(v.turnover.loc[yy].sum()), 1)}
            d[k]["price"] = round(d[k]["net_contrib"] - d[k]["funding"] + d[k]["costs"], 4)
        d["corr_legs"] = round(float(R["flow"].loc[yy].corr(R["blend_nested"].loc[yy])), 2)
        out["by_year"][y] = d
    s24 = {k: float(R[k].loc["2024":].sum()) for k in R}
    out["share_2024_26"] = {k: round(v / sum(s24.values()), 2) for k, v in s24.items()}
    wk = (1 + c["BTC"].pct_change().loc[lo:]).resample("W").prod() - 1
    W = {k: (1 + x).resample("W").prod() - 1 for k, x in {**R, "mix": rm}.items()}
    worst, best = wk.nsmallest(20).index, wk.nlargest(20).index
    out["btc_worst20_weeks"] = {"btc": round(float(wk[worst].mean()), 4), **{k: round(float(v[worst].mean()), 4) for k, v in W.items()}}
    out["btc_best20_weeks"] = {"btc": round(float(wk[best].mean()), 4), **{k: round(float(v[best].mean()), 4) for k, v in W.items()}}
    out["2025-10-10"] = {k: round(float(x.get(pd.Timestamp("2025-10-10", tz="UTC"), np.nan)), 4) for k, x in {**R, "mix": rm}.items()}
    print(json.dumps(out, indent=1))
    json.dump(out, open("research/is3/bnb_ab.json", "w"), indent=1)




def run_c():
    p = data.load_panel("bnall", "1d")
    c = p["close"]
    out = {"panel_end": str(c.index[-1].date())}
    pool = list(S.NESTED_POOL) + ["flow"]
    rets = {}
    for name in pool:
        try:
            _, r = S._component_returns(p, name)
        except Exception as e:
            out.setdefault("errors", {})[name] = repr(e)[:120]
            continue
        rets[name] = r
    for d in ("2026-11-03", str(c.index[-1].date())):
        i = c.index.get_loc(pd.Timestamp(d, tz="UTC"))
        cur = {}
        for name, r in rets.items():
            ri = r.iloc[: i + 1]
            inv = ri.ne(0).to_numpy()
            if not inv.any():
                continue
            ri = ri.iloc[int(inv.argmax()):]
            if len(ri) < 240 or ri.std() == 0:
                continue
            cur[name] = round(float(ri.mean() / ri.std() * np.sqrt(365)), 2)
        out[d] = dict(sorted(cur.items(), key=lambda x: -x[1]))
        print(d, out[d], flush=True)
    json.dump(out, open("research/is3/bnb_c.json", "w"), indent=1)


if __name__ == "__main__":
    {"ab": run_ab, "c": run_c}[sys.argv[1]]()
