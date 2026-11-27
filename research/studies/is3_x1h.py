"""InSilico pass 3, X1H: fspread_hold churn (trip table) and a wider exit band. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_x1h a          # trip table 2023-05..2026-11 -> research/is3/x1h_a.json
  nice -n 19 .venv/bin/python -m research.studies.is3_x1h b          # exit-band explore 2023-05-15..2024-12-31 -> research/is3/x1h_b.json
  nice -n 19 .venv/bin/python -m research.studies.is3_x1h c <x>      # ONE run of the frozen pick on 2025-01-01..2026-11-22 -> research/is3/x1h_c.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto import strategies as S
from kripto.research import bars_per_day, default_band
from research.studies import is3_lib as L
from research.studies.is3_x1cp import bn_interval


def fsh(panel, lookback=14, enter=0.1, exit_x=0.0, top_n=20, max_pair=0.10, gross=2.0):
    """Local copy of kripto.strategies.fspread_hold with an exit band: an open pair (sign O) closes when O * s < -exit_x (exit_x = 0: the live rule, sign change)."""
    c, f = panel["close"], panel["funding"]
    hlc = [x for x in c.columns if x.endswith("@hl") and x[:-3] + "@bn" in c.columns]
    bnc = [x[:-3] + "@bn" for x in hlc]
    bpd = bars_per_day(c.index)
    n = lookback * bpd
    on_bn = lambda df: df[bnc].set_axis(hlc, axis=1)
    s = (f[hlc] - on_bn(f)).rolling(n, min_periods=n).mean() * bpd * 365
    same = np.log(c[hlc] / on_bn(c)).abs().rolling(30 * bpd, min_periods=10 * bpd).median() < 0.03
    dv = S.dollar_volume(panel)
    dvm = np.minimum(dv[hlc], on_bn(dv))
    elig = same & s.notna() & c[hlc].notna() & on_bn(c).notna() & (dvm > 0)
    liquid = dvm.where(elig).rank(axis=1, ascending=False) <= 2 * top_n
    can_open = elig & (dvm.where(elig).rank(axis=1, ascending=False) <= top_n)
    Sx, E, Lo, O = s.to_numpy(), (elig & liquid).to_numpy(), can_open.to_numpy(), np.zeros(len(hlc))
    slots = int(round(gross / (2 * max_pair)))
    out = np.zeros((len(c), len(hlc)))
    for t in range(len(c)):
        st_ = Sx[t]
        keep = (O != 0) & E[t] & np.isfinite(st_) & (O * np.nan_to_num(st_) > (-exit_x if exit_x > 0 else 0.0))
        if exit_x == 0.0:
            keep = (O != 0) & E[t] & np.isfinite(st_) & (np.sign(np.nan_to_num(st_)) == O)
        O = np.where(keep, O, 0.0)
        free = slots - int((O != 0).sum())
        if free > 0:
            cand = np.flatnonzero((O == 0) & Lo[t] & np.isfinite(st_) & (np.abs(np.nan_to_num(st_)) > enter))
            cand = cand[np.argsort(-np.abs(st_[cand]))][:free]
            O[cand] = np.sign(st_[cand])
        out[t] = O
    leg = pd.DataFrame(-out * max_pair, c.index, hlc)
    w = pd.DataFrame(0.0, c.index, c.columns)
    w[hlc], w[bnc] = leg, -leg.to_numpy()
    return S.rebalance_rows(w.where(elig.any(axis=1), np.nan), bpd)


def summary(res, lo, hi):
    r = res.returns[(res.returns.index >= lo) & (res.returns.index < hi)]
    yrs = len(r) / 365
    cut = lambda s: s.reindex(r.index).fillna(0.0)
    return {"net_yr": round(float(r.sum() / yrs), 4), "sr": round(float(r.mean() / r.std() * np.sqrt(365)), 2), "cost_yr": round(float(cut(res.costs).sum() / yrs), 4),
            "funding_yr": round(float(cut(res.funding).sum() / yrs), 4), "turnover_yr": round(float(cut(res.turnover).sum() / yrs), 1),
            "gross_mean": round(float(cut(res.gross).mean()), 2), "by_year": {int(y): round(float(x.sum()), 4) for y, x in r.groupby(r.index.year)}}


def run_a():
    p = data.load_panel("pair", "1d")
    c = p["close"]
    w = fsh(p)
    w_reg = S.REGISTRY["fspread_hold"](p, lookback=14, enter=0.1)
    assert np.allclose(w.fillna(0).to_numpy(), w_reg.fillna(0).to_numpy()), "local copy differs from the registered fspread_hold"
    wf = w.ffill().fillna(0.0)
    slip = bt.slippage_model(p["volume"], bars_per_day(c.index))
    res = bt.run(w, c, p["funding"], slip, band=default_band())
    r = (c / c.shift(1) - 1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    wl = wf.shift(1).fillna(0.0)
    price, fund = wl * r, -wl * p["funding"].fillna(0.0)
    dw = wf.diff().abs().fillna(0.0)
    cost = dw.div(dw.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0).mul(res.costs.reindex(c.index).fillna(0.0), axis=0)
    hlc = [x for x in c.columns if x.endswith("@hl") and x[:-3] + "@bn" in c.columns]
    trips = []
    for h in hlc:
        b = h[:-3] + "@bn"
        on = (wf[h] != 0).to_numpy()
        i = 0
        while i < len(on):
            if on[i]:
                j = i
                while j + 1 < len(on) and on[j + 1]:
                    j += 1
                idx = c.index[i:j + 2] if j + 2 <= len(c) else c.index[i:]
                iv = bn_interval(h[:-3], pd.DatetimeIndex([c.index[i]])).iloc[0]
                trips.append({"coin": h[:-3], "start": c.index[i], "days": j - i + 1, "iv": iv,
                              "price": float(price.loc[idx, [h, b]].sum().sum()), "fund": float(fund.loc[idx, [h, b]].sum().sum()),
                              "cost": float(cost.loc[c.index[i]:idx[-1], [h, b]].sum().sum())})
                i = j + 1
            else:
                i += 1
    T = pd.DataFrame(trips)
    T = T[T.start >= pd.Timestamp("2023-05-15", tz="UTC")]
    T["net"] = T.price + T.fund - T.cost
    T["year"] = T.start.dt.year
    T["short"] = T.days < 14
    g = T.groupby(["year", "short"]).agg(n=("net", "size"), days=("days", "median"), fund=("fund", "sum"), price=("price", "sum"), cost=("cost", "sum"), net=("net", "sum")).round(4)
    gi = T.groupby(["year", "iv"]).agg(n=("net", "size"), days=("days", "median"), cost=("cost", "sum"), net=("net", "sum")).round(4)
    print(g.to_string(), "\n", gi.to_string(), flush=True)
    out = {"n_trips": int(len(T)), "by_year_short": {f"{k[0]}_{'lt14' if k[1] else 'ge14'}": v for k, v in g.to_dict("index").items()},
           "by_year_iv": {f"{k[0]}_{k[1]}h": v for k, v in gi.to_dict("index").items()},
           "cost_per_trip_bp_of_equity": round(float(T.cost.mean()) * 1e4, 2), "summary": summary(res, pd.Timestamp("2023-05-15", tz="UTC"), pd.Timestamp("2026-11-22", tz="UTC"))}
    json.dump({"study": "research/studies/is3_x1h.py a", **out}, open(L.OUT / "x1h_a.json", "w"), indent=1, default=str)


def run_b(lo="2023-05-15", hi="2025-01-01", tag="b", xs=(0.0, 0.05, 0.10)):
    p = data.load_panel("pair", "1d")
    c = p["close"]
    slip = bt.slippage_model(p["volume"], bars_per_day(c.index))
    lo, hi = pd.Timestamp(lo, tz="UTC"), pd.Timestamp(hi, tz="UTC")
    out = {}
    for x in xs:
        w = fsh(p, exit_x=x)
        res = bt.run(w, c, p["funding"], slip, band=default_band())
        out[str(x)] = summary(res, lo, hi)
        print(f"exit_x {x}: {out[str(x)]}", flush=True)
    json.dump({"study": f"research/studies/is3_x1h.py {tag}", "window": [str(lo.date()), str(hi.date())], **out}, open(L.OUT / f"x1h_{tag}.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "a":
        run_a()
    elif a[0] == "b":
        run_b()
    elif a[0] == "c":
        if (L.OUT / "x1h_c.json").exists():
            raise SystemExit("c already spent")
        run_b("2025-01-01", "2026-11-22", "c", (0.0, float(a[1])))
    elif a[0] == "d":
        if (L.OUT / "x1h_d.json").exists():
            raise SystemExit("d already spent")
        run_b("2025-01-01", "2026-11-22", "d", (0.0, 0.05, 0.10))
