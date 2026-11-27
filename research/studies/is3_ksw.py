"""InSilico pass 3, KSW: the -25 % kill switch, false-alarm rate vs power, per main book. Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_ksw ab   # block bootstrap of each main book's daily returns: P(kill) real / zero / negative edge -> research/is3/ksw_ab.json
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

KILL = 0.25


def book_returns():
    out = {}
    p = data.load_panel("hl", "1d")
    w = S.REGISTRY["blend"](p, components={"listing_short": {}, "lowvol": {}, "tsmom": {}}) * 0.871
    r = bt.run(w, p["close"], p["funding"], bt.slippage_model(p["volume"], 1), band=default_band())
    out["main (HL)"] = r.returns[r.gross > 0]
    del p
    p = data.load_panel("bnall", "1d")
    wf = S.REGISTRY["flow"](p, lookback=3, cap=0.05).ffill().fillna(0.0)
    wb = S.REGISTRY["blend"](p, components={"carry_trend": {}, "carry": {}, "xsmom": {}}).ffill().fillna(0.0)
    w = (0.5 * wf + 0.5 * wb.reindex(columns=wf.columns, fill_value=0.0)) * 1.156
    r = bt.run(w, p["close"], p["funding"], bt.slippage_model(p["volume"], 1), band=default_band())
    out["main_bn"] = r.returns[r.gross > 0]
    del p
    p = data.load_panel("pair", "1d")
    w = S.REGISTRY["fspread_hold"](p, lookback=14, enter=0.1) * 0.5
    r = bt.run(w, p["close"], p["funding"], bt.slippage_model(p["volume"], 1), band=default_band())
    out["main@pair"] = r.returns[r.gross > 0].loc["2023-05-15":]
    return out


def p_kill(r, horizon, n=4000, block=30, seed=5):
    x = r.to_numpy()
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(horizon / block))
    hits, t_kill = 0, []
    for _ in range(n):
        st = rng.integers(0, len(x) - block, nb)
        path = np.concatenate([x[s:s + block] for s in st])[:horizon]
        eq = np.cumprod(1 + path)
        dd = eq / np.maximum.accumulate(np.maximum(eq, 1.0)) - 1
        k = np.flatnonzero(dd <= -KILL)
        if len(k):
            hits += 1
            t_kill.append(int(k[0]))
    return round(hits / n, 3), (int(np.median(t_kill)) if t_kill else None)


def run_ab():
    out = {}
    for name, r in book_returns().items():
        r = r.dropna()
        sd = r.std()
        o = {"start": str(r.index[0].date()), "days": int(len(r)), "sr": round(float(r.mean() / sd * np.sqrt(365)), 2), "vol": round(float(sd * np.sqrt(365)), 3),
             "hist_mdd": round(float(((1 + r).cumprod() / (1 + r).cumprod().cummax() - 1).min()), 3)}
        for lab, rr in (("real", r), ("zero", r - r.mean()), ("neg05", r - r.mean() - 0.5 * sd / np.sqrt(365))):
            for h in (365, 730):
                pk, tk = p_kill(rr, h)
                o[f"{lab}_{h}d"] = {"p_kill": pk, "median_day": tk}
        # the design §4 alternative: share of 60-d windows with SR < 0 under the real edge (how often demotion would fire on a good book)
        roll = r.rolling(60).mean() / r.rolling(60).std()
        o["share_60d_sr_below0_real"] = round(float((roll < 0).mean()), 2)
        out[name] = o
        print(name, o, flush=True)
    json.dump(out, open("research/is3/ksw_ab.json", "w"), indent=1)


if __name__ == "__main__":
    {"ab": run_ab}[sys.argv[1]]()
