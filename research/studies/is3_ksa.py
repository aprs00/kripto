"""InSilico pass 3, KSA: per-venue-account drawdowns of main@pair (fspread_hold x .5) and transfer rules. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_ksa abc   # -> research/is3/ksa_abc.json
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


def accounts():
    p = data.load_panel("pair", "1d")
    c = p["close"]
    w = (S.REGISTRY["fspread_hold"](p, lookback=14, enter=0.1) * 0.5)
    res = bt.run(w, c, p["funding"], bt.slippage_model(p["volume"], 1), band=default_band())
    wl = res.weights.fillna(0.0)
    ret = (c / c.shift(1) - 1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    fund = p["funding"].reindex(index=c.index, columns=c.columns).fillna(0.0)
    out = {}
    for v in ("hl", "bn"):
        cols = [x for x in c.columns if x.endswith("@" + v)]
        pnl = (wl[cols] * ret[cols]).sum(axis=1) - (wl[cols] * fund[cols]).sum(axis=1)
        dw = res.weights[cols].fillna(0.0).diff().abs().sum(axis=1)
        tot_dw = res.weights.fillna(0.0).diff().abs().sum(axis=1).replace(0, np.nan)
        cost = (res.costs * (dw / tot_dw)).fillna(0.0)
        out[v] = ((pnl - cost) / 0.5).loc["2023-05-26":]        # per unit of the account's capital (half the book)
    return pd.DataFrame(out)


def p_dd(x, horizon, levels, n=4000, block=30, seed=3):
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(horizon / block))
    hits = np.zeros(len(levels))
    for _ in range(n):
        st = rng.integers(0, len(x) - block, nb)
        path = np.concatenate([x[s:s + block] for s in st])[:horizon]
        eq = np.cumprod(1 + path)
        dd = (eq / np.maximum.accumulate(np.maximum(eq, 1.0)) - 1).min()
        hits += np.array([dd <= -l for l in levels])
    return [round(float(h / n), 3) for h in hits]


def simulate(a, rule):
    """Two accounts start at .5 each; daily returns per account capital; transfers back to 50/50 by rule. Returns worst account DD and transfers/yr."""
    eh, eb, peak_h, peak_b, worst, nt = 0.5, 0.5, 0.5, 0.5, 0.0, 0
    for i, (rh, rb) in enumerate(a[["hl", "bn"]].to_numpy()):
        tot = eh + eb
        eh, eb = eh + 0.5 * tot * rh, eb + 0.5 * tot * rb      # legs sized on the book's total equity (half each)
        do = (rule == "weekly" and i % 7 == 6) or (rule == "monthly" and i % 30 == 29) or (rule == "ratio70" and min(eh, eb) < 0.7 * max(eh, eb))
        if do:
            eh = eb = (eh + eb) / 2
            nt += 1
        peak_h, peak_b = max(peak_h, eh), max(peak_b, eb)
        worst = min(worst, eh / peak_h - 1, eb / peak_b - 1)
    return round(worst, 3), round(nt / (len(a) / 365), 1)


def run_abc():
    a = accounts()
    out = {"days": int(len(a)), "worst_day": {k: round(float(a[k].min()), 3) for k in a}, "worst_7d": {k: round(float(a[k].rolling(7).sum().min()), 3) for k in a},
           "corr_accounts": round(float(a.hl.corr(a.bn)), 2)}
    lv = (0.25, 0.35, 0.5)
    for k in a:
        out[f"{k}_p_dd_1y"] = dict(zip([str(l) for l in lv], p_dd(a[k].to_numpy(), 365, lv)))
        out[f"{k}_p_dd_2y"] = dict(zip([str(l) for l in lv], p_dd(a[k].to_numpy(), 730, lv)))
    out["transfer_rules"] = {r: dict(zip(["worst_account_dd", "transfers_per_yr"], simulate(a, r))) for r in ("none", "monthly", "weekly", "ratio70")}
    print(json.dumps(out, indent=1))
    json.dump(out, open("research/is3/ksa_abc.json", "w"), indent=1)


if __name__ == "__main__":
    {"abc": run_abc}[sys.argv[1]]()
