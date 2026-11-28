"""InSilico pass 3, SMD: $200-able versions of the main books. a = HL top-N vol-matched then $10 minimum; b = round-to-minimum (>= half the minimum -> AT the minimum)
on HL and BN mixes, vol rescaled down only. Full-sample vol scaling (descriptive, small look-ahead). Not registered.
  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_smd a|b  -> research/is3/smd_a.json, smd_b.json"""
import json
import sys

import numpy as np
import pandas as pd

from kripto import backtest as bt, data, paper as P, research as R
from kripto.strategies import REGISTRY

_, risk = P.load_cfg()
EQ = 200.0
BAND_USD = {"hl": 10.0, "bn": 5.0}
VEN = ["hl"]   # venue of the book being run (sets the trade band: HL $10, Binance $5)


def hl_book():
    p = data.load_panel("hl", "1d")
    w = REGISTRY["blend"](p, components={"listing_short": {}, "lowvol": {}, "tsmom": {}}, slow_lam=0.33).ffill().fillna(0.0) * float(risk["main_scale"]["main"])
    return p, w.clip(-risk["max_asset_weight"], risk["max_asset_weight"]), R.small_minima(p["close"].columns, "hl"), slice("2023-01-01", None)


def bn_book():
    p = data.load_panel("bnall", "1d")
    cols = p["close"].columns
    wf = REGISTRY["flow"](p, lookback=3, cap=0.05).ffill().fillna(0.0).reindex(columns=cols, fill_value=0.0)
    wb = REGISTRY["blend"](p, components={"carry_trend": {}, "carry": {}, "xsmom": {}}).ffill().fillna(0.0).reindex(columns=cols, fill_value=0.0)
    w = ((wf + wb) * 0.5 * float(risk["main_scale"]["main_bn"])).clip(-risk["max_asset_weight"], risk["max_asset_weight"])
    return p, w, R.small_minima(cols, "bnall"), slice("2021-01-01", "2026-10-31")


def run(p, w, eq, S):
    res = bt.run(w, p["close"], p["funding"], bt.slippage_model(p["volume"], 1), band=BAND_USD[VEN[0]] / eq)
    return res, res.returns.loc[S]


def stats(p, w, eq, S, ref_gross=None):
    res, r = run(p, w, eq, S)
    sr = lambda y: round(float(y.mean() / y.std() * np.sqrt(365)), 2) if y.std() > 0 else None
    g = res.weights.loc[S].abs().sum(axis=1)
    out = {"sr": sr(r), "ann%": round(float(r.mean() * 365 * 100), 1), "vol%": round(float(r.std() * np.sqrt(365) * 100), 1), "gross": round(float(g.mean()), 3),
           "names": round(float((res.weights.loc[S] != 0).sum(axis=1).mean()), 1), "years": {int(y): sr(v) for y, v in r.groupby(r.index.year)}}
    if ref_gross is not None:
        sh = (g / ref_gross.reindex(g.index)).replace([np.inf, -np.inf], np.nan)
        out["deployed_by_year"] = {int(y): round(float(v.mean()), 2) for y, v in sh.groupby(sh.index.year)}
    return out


def trunc(w, mins):
    return w.where((w.abs() * EQ >= mins.reindex(w.columns).to_numpy()) | (w == 0), 0.0)


def topn(w, n):
    rk = w.abs().rank(axis=1, ascending=False, method="first")
    return w.where(rk <= n, 0.0)


def form_a():
    p, w, mins, S = hl_book()
    base_res, br = run(p, w, 1000.0, S)
    vol0 = float(br.std()); g0 = base_res.weights.abs().sum(axis=1)
    out = {"usd1000": stats(p, w, 1000.0, S), "usd200_trunc": stats(p, trunc(w, mins), EQ, S, g0)}
    for n in (3, 5, 8, 12):
        k = topn(w, n); _, rk = run(p, k, 1000.0, S)
        k = k * vol0 / float(rk.std())
        out[n] = stats(p, trunc(k, mins), EQ, S, g0)
        print(n, out[n], flush=True)
    print(json.dumps(out)); json.dump(out, open("research/is3/smd_a.json", "w"), indent=1)


def roundmin(w, mins):
    m = mins.reindex(w.columns).to_numpy() / EQ
    a = w.abs()
    return np.sign(w) * np.where(a >= m, a, np.where(a >= m / 2, m, 0.0))


def form_b():
    out = {}
    for tag, fn in (("hl", hl_book), ("bn", bn_book)):
        VEN[0] = tag
        p, w, mins, S = fn()
        base_res, br = run(p, w, 1000.0, S)
        vol0 = float(br.std()); g0 = base_res.weights.abs().sum(axis=1)
        rm = pd.DataFrame(roundmin(w, mins), w.index, w.columns)
        _, rr = run(p, rm, EQ, S)
        f = min(1.0, vol0 / float(rr.std()))
        rm2 = pd.DataFrame(roundmin(rm * f, mins), w.index, w.columns) if f < 1 else rm   # scaling down can push names under the minimum again: re-round once
        out[tag] = {"usd1000": stats(p, w, 1000.0, S), "usd200_trunc": stats(p, trunc(w, mins), EQ, S, g0),
                    "usd200_roundmin": stats(p, rm, EQ, S, g0), "vol_scale": round(f, 3), "usd200_roundmin_volcapped": stats(p, rm2, EQ, S, g0)}
        print(tag, json.dumps(out[tag]), flush=True)
    json.dump(out, open("research/is3/smd_b.json", "w"), indent=1)



def tracking():
    """daily-return correlation of each $200 form with the $1,000 book (does the deployed gross follow the same bets?), by year."""
    out = {}
    for tag, fn in (("hl", hl_book), ("bn", bn_book)):
        VEN[0] = tag
        p, w, mins, S = fn()
        _, r0 = run(p, w, 1000.0, S)
        forms = {"trunc": trunc(w, mins), "roundmin": pd.DataFrame(roundmin(w, mins), w.index, w.columns)}
        out[tag] = {}
        for k, x in forms.items():
            _, r = run(p, x, EQ, S)
            out[tag][k] = {"corr": round(float(r.corr(r0)), 2), "by_year": {int(y): round(float(r[r.index.year == y].corr(r0[r0.index.year == y])), 2) for y in sorted(set(r.index.year))}}
    print(json.dumps(out)); json.dump(out, open("research/is3/smd_track.json", "w"), indent=1)



def hysteresis(w, mins, enter=0.5, leave=0.25):
    """round-to-min with hysteresis: a name enters at >= enter x minimum (placed at the minimum), stays while >= leave x minimum, else 0."""
    m = mins.reindex(w.columns).to_numpy() / EQ
    W = w.to_numpy(); out = np.zeros_like(W); held = np.zeros(W.shape[1], bool)
    for t in range(W.shape[0]):
        a = np.abs(np.nan_to_num(W[t]))
        held = np.where(held, a >= leave * m, a >= enter * m)
        out[t] = np.where(held, np.sign(np.nan_to_num(W[t])) * np.maximum(a, m), 0.0)
    return pd.DataFrame(out, w.index, w.columns)


def churn():
    out = {}
    for tag, fn in (("hl", hl_book), ("bn", bn_book)):
        VEN[0] = tag
        p, w, mins, S = fn()
        m = mins.reindex(w.columns).to_numpy() / EQ
        forms = {"usd1000": (w, 1000.0), "trunc": (trunc(w, mins), EQ), "roundmin": (pd.DataFrame(roundmin(w, mins), w.index, w.columns), EQ),
                 "hyst_50_25": (hysteresis(w, mins), EQ)}
        out[tag] = {}
        for k, (x, eq) in forms.items():
            res, r = run(p, x, eq, S)
            yrs = len(r) / 365
            gross_ret = float((r + res.costs.loc[S]).mean() * 365)
            H = res.weights.loc[S].to_numpy(); dH = np.abs(np.diff(H, axis=0))
            cross = ((H[1:] == 0) != (H[:-1] == 0))                      # a name enters or leaves
            out[tag][k] = {"sr": round(float(r.mean() / r.std() * np.sqrt(365)), 2), "turn_yr": round(float(res.turnover.loc[S].sum() / yrs), 1),
                           "cost_pct_yr": round(float(res.costs.loc[S].sum() / yrs * 100), 2), "gross_ret_pct_yr": round(gross_ret * 100, 1),
                           "cost_share_of_gross": round(float(res.costs.loc[S].sum() / yrs) / gross_ret, 2) if gross_ret > 0 else None,
                           "crossing_share_of_turnover": round(float(dH[cross].sum() / dH.sum()), 2) if dH.sum() > 0 else None}
        print(tag, json.dumps(out[tag]), flush=True)
    json.dump(out, open("research/is3/smy_b.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": form_a, "b": form_b, "t": tracking, "churn": churn}[sys.argv[1]]()
