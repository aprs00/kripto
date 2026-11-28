"""FLXF: FLX2 precheck on bnall 1d. a = flow@bn (lookback 3, cap .05) P&L by position funding side (trailing 7-d mean funding, known at the decision);
b = FROZEN variant (iii): flow score residualised cross-sectionally on trailing 7-d mean funding; c = descriptive: keep only positions on the funding-paying side.
Not registered (descriptive). PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_flxf -> research/is3/flxf_abc.json"""
import json
import numpy as np, pandas as pd
from kripto import backtest as bt, data
from kripto.strategies import (REGISTRY, universe, xs_demean_rank, short_guard, hedge_beta, beta_to, alt_cap, scheduled, bars_per_day)

S = slice("2021-01-01", "2026-10-31")
p = data.load_panel("bnall", "1d")
slip = bt.slippage_model(p["volume"], 1)
cols = p["close"].columns
fund = p["funding"].reindex(columns=cols)
f7 = fund.rolling(7, min_periods=3).mean()          # trailing, includes day t (known at t's close, when the target is set)


def flow_x(panel, lookback=3, top_n=30, target_vol=0.25, cap=0.05, mode=None):
    """kripto.strategies.flow (sign +1, beta_neutral, short_filter none) with an optional funding step. mode None = production."""
    c, v, tb = panel["close"], panel["volume"], panel["taker_buy"]
    n = lookback * bars_per_day(c.index)
    fv = panel.get("flow_volume", v)
    imb = (2 * tb - fv).rolling(n, min_periods=n).sum() / fv.rolling(n, min_periods=n).sum()
    mask = universe(panel, top_n) & imb.notna()
    score = imb.where(mask)
    if mode == "resid_f7":
        fx = f7.where(mask)
        sc, fc = score.sub(score.mean(axis=1), axis=0), fx.sub(fx.mean(axis=1), axis=0).fillna(0.0)
        b = (sc * fc).sum(axis=1) / (fc * fc).sum(axis=1).replace(0, np.nan)
        score = sc.sub(fc.mul(b.fillna(0.0), axis=0))
    w = short_guard(xs_demean_rank(score, mask), panel, mask, "none")
    if mode == "paying_only":     # long only where trailing funding >= 0 (longs pay), short only where < 0
        w = w.where(((w > 0) & (f7 >= 0)) | ((w < 0) & (f7 < 0)), 0.0)
    w = hedge_beta(w, beta_to(panel))
    return alt_cap(scheduled(w, panel, 1, target_vol), cap)


def run(w):
    w = w.ffill().fillna(0.0).reindex(columns=cols, fill_value=0.0)
    return bt.run(w, p["close"], p["funding"], slip, fee=5e-4)


def decomp(res):
    H = res.weights.loc[S]; r = p["close"].pct_change().reindex(H.index).fillna(0.0); f = fund.reindex(H.index).fillna(0.0)
    side = f7.shift(1).reindex(H.index)    # funding known when the held position was set (target at t-1's close)
    recv = ((H > 0) & (side < 0)) | ((H < 0) & (side >= 0))
    out = {}
    for nm, m in (("receiving", recv), ("paying", ~recv & (H != 0))):
        pr = (H * r).where(m, 0.0).sum(axis=1); fd = (-H * f).where(m, 0.0).sum(axis=1)
        out[nm] = {"gross_share": round(float(H.abs().where(m, 0.0).sum().sum() / H.abs().sum().sum()), 3),
                   "price_pct_yr": {int(y): round(float(v.mean() * 365 * 100), 1) for y, v in pr.groupby(pr.index.year)},
                   "funding_pct_yr": {int(y): round(float(v.mean() * 365 * 100), 1) for y, v in fd.groupby(fd.index.year)}}
    # known answer: the two halves' funding sum to the backtest's own funding series
    tot_f = (-H * f).sum(axis=1)
    out["check_funding_maxdiff"] = float((tot_f - res.funding.loc[S]).abs().max())
    return out


def summ(res, ref=None):
    r = res.returns.loc[S]; fd = res.funding.loc[S]; c = res.costs.loc[S]; pr = r - fd + c
    sr = lambda x: round(float(x.mean() / x.std() * np.sqrt(365)), 2)
    o = {"sr": sr(r), "ann%": round(float(r.mean() * 365 * 100), 1), "vol%": round(float(r.std() * np.sqrt(365) * 100), 1),
         "turn_yr": round(float(res.turnover.loc[S].mean() * 365), 1), "cost%": round(float(c.mean() * 365 * 100), 1),
         "by_year": {int(y): {"sr": sr(r[r.index.year == y]), "price%": round(float(pr[pr.index.year == y].mean() * 365 * 100), 1),
                              "funding%": round(float(fd[fd.index.year == y].mean() * 365 * 100), 1)} for y in sorted(set(r.index.year))}}
    if ref is not None:
        o["corr_blend"] = round(float(r.corr(ref)), 3)
        o["corr_blend_by_year"] = {int(y): round(float(r[r.index.year == y].corr(ref[ref.index.year == y])), 2) for y in sorted(set(r.index.year))}
    return o


if __name__ == "__main__":
    import sys
    w0 = flow_x(p)
    wp = REGISTRY["flow"](p, lookback=3, cap=0.05)
    ka = float((w0.fillna(0) - wp.reindex_like(w0).fillna(0)).abs().max().max())
    print("known answer vs production flow, max |dw| =", ka, flush=True)
    assert ka < 1e-12
    blend = run(REGISTRY["blend"](p, components={"carry_trend": {}, "carry": {}, "xsmom": {}})).returns.loc[S]
    r0 = run(w0)
    out = {"known_answer_maxdw": ka, "a": {"flow": summ(r0, blend), "decomp": decomp(r0)}}
    print(json.dumps(out["a"]), flush=True)
    if "a" not in sys.argv[1:]:
        rb = run(flow_x(p, mode="resid_f7")); out["b"] = {"resid_f7": summ(rb, blend), "corr_flow": round(float(rb.returns.loc[S].corr(r0.returns.loc[S])), 3)}
        print(json.dumps(out["b"]), flush=True)
        rc = run(flow_x(p, mode="paying_only")); out["c"] = {"paying_only": summ(rc, blend), "corr_flow": round(float(rc.returns.loc[S].corr(r0.returns.loc[S])), 3)}
        print(json.dumps(out["c"]), flush=True)
    json.dump(out, open("research/is3/flxf_abc.json", "w"), indent=1)
