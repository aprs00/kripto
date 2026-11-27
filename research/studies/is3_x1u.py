"""InSilico pass 3, X1U: fspread_hold@pair on the live universe (both venues' top-60) and from a cold start. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_x1u a    # live-universe rule vs research rule, by year -> research/is3/x1u_a.json
  nice -n 19 .venv/bin/python -m research.studies.is3_x1u b    # 20 cold starts vs the continuous path (holdings overlap, P&L over 90 d) -> research/is3/x1u_b.json
  nice -n 19 .venv/bin/python -m research.studies.is3_x1u c    # replay of the live book (live universe + BN funding from 2026-09-13) vs the fills table -> research/is3/x1u_c.json
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
from research.studies.is3_x1h import summary

TOPN = 60


def fsh_u(panel, uni=None, lookback=14, enter=0.1, top_n=20, max_pair=0.10, gross=2.0):
    """Copy of kripto.strategies.fspread_hold (live rule) with an extra point-in-time universe mask (columns = HL coins `X@hl`)."""
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
    if uni is not None:
        # live: the panel holds the top-60 lists + every held leg, so a held pair is never forced out by the lists; new pairs open only inside them,
        # and the top-20 / top-40 ranks are taken within the live panel's coins (approximated: within the lists)
        um = uni.reindex(index=c.index, columns=hlc).fillna(False).astype(bool)
        eu = elig & um
        can_open = eu & (dvm.where(eu).rank(axis=1, ascending=False) <= top_n)
    else:
        can_open = elig & (dvm.where(elig).rank(axis=1, ascending=False) <= top_n)
    Sx, E, Lo, O = s.to_numpy(), (elig & liquid).to_numpy(), can_open.to_numpy(), np.zeros(len(hlc))
    slots = int(round(gross / (2 * max_pair)))
    out = np.zeros((len(c), len(hlc)))
    for t in range(len(c)):
        st_ = Sx[t]
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


def live_universe(p):
    """Proxy of the live lists: coins in the HL top-60 AND the Binance top-60 by the previous day's USD volume, each ranked among ALL that venue's coins."""
    hl = data.load_panel("hl", "1d")["volume"]
    bn = data.load_panel("bnall", "1d")["volume"]
    rh = (hl.shift(1).rank(axis=1, ascending=False) <= TOPN)
    rb = (bn.shift(1).rank(axis=1, ascending=False) <= TOPN)
    hlc = [x for x in p["close"].columns if x.endswith("@hl")]
    idx = p["close"].index
    u = pd.DataFrame(False, idx, hlc)
    for x in hlc:
        h, b = x[:-3], data.hl_to_bn(x[:-3])
        if h in rh.columns and b in rb.columns:
            u[x] = rh[h].reindex(idx).fillna(False).astype(bool) & rb[b].reindex(idx).fillna(False).astype(bool)
    return u


def bt_run(p, w):
    return bt.run(w, p["close"], p["funding"], bt.slippage_model(p["volume"], bars_per_day(p["close"].index)), band=default_band())


def run_a():
    p = data.load_panel("pair", "1d")
    w0 = fsh_u(p)
    assert np.allclose(w0.fillna(0).to_numpy(), S.REGISTRY["fspread_hold"](p, lookback=14, enter=0.1).fillna(0).to_numpy()), "copy differs from the registered rule"
    u = live_universe(p)
    wu = fsh_u(p, u)
    out = {"uni_size_median_by_year": {int(y): float(x.sum(axis=1).median()) for y, x in u.loc["2023-05":].groupby(u.loc["2023-05":].index.year)}}
    for lab, w in (("research", w0), ("live_universe", wu)):
        res = bt_run(p, w)
        out[lab] = {"2023-05..": summary(res, "2023-05-15", "2027-01-01"), "2025..": summary(res, "2025-01-01", "2027-01-01")}
        wf = w.ffill().fillna(0)
        out[lab]["pairs_mean"] = round(float((wf[[c for c in wf.columns if c.endswith('@hl')]] != 0).sum(axis=1).loc["2025":].mean()), 2)
    a, b = w0.ffill().fillna(0), wu.ffill().fillna(0)
    hlc = [c for c in a.columns if c.endswith("@hl")]
    ov = ((a[hlc] != 0) & (b[hlc] != 0)).sum(axis=1) / (a[hlc] != 0).sum(axis=1).replace(0, np.nan)
    out["overlap_share_of_research_pairs_by_year"] = {int(y): round(float(x.mean()), 2) for y, x in ov.loc["2023-06":].groupby(ov.loc["2023-06":].index.year)}
    held = (a[hlc] != 0).loc["2025":].sum()
    outside = (a[hlc] != 0) & ~u.reindex(a.index).fillna(False)
    out["research_pair_days_outside_live_universe_2025_26"] = round(float(outside.loc["2025":].sum().sum() / max(1, held.sum())), 2)
    out["top_outside_coins_2025_26"] = {k[:-3]: int(v) for k, v in outside.loc["2025":].sum().sort_values(ascending=False).head(8).items()}
    print(json.dumps(out, indent=1))
    json.dump(out, open("research/is3/x1u_a.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": run_a}[sys.argv[1]]()
