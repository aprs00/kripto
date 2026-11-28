"""InSilico pass 3, PRL: HL main book (blend listing_short+lowvol+tsmom) per-leg costs and partial rebalancing on the slow legs only.
python -m research.studies.is3_prl a|b|c"""
from __future__ import annotations

import inspect
import json
import sys

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto import strategies as S
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY
from research.studies.is3_prb import partial, summary

LEGS = ("listing_short", "lowvol", "tsmom")


def legs(panel):
    cols = panel["close"].columns
    raw = {}
    for n in LEGS:
        tv = inspect.signature(REGISTRY[n]).parameters["target_vol"].default
        raw[n] = S._ffill_targets(REGISTRY[n](panel)).reindex(columns=cols, fill_value=0.0) * (0.20 / tv) / len(LEGS)
    tot = sum(raw.values())
    final = S.scheduled(tot, panel, 1, 0.25, 3.0, None)
    ref = REGISTRY["blend"](panel, components={n: {} for n in LEGS})
    a, b = tot.abs().sum(1), final.fillna(0).abs().sum(1)
    s = (b / a.replace(0, np.nan)).fillna(0.0)
    fin = {n: w.fillna(0.0).mul(s, axis=0) for n, w in raw.items()}
    err = float((sum(fin.values()) - ref.fillna(0)).abs().max().max())
    return fin, ref, err


if __name__ == "__main__":
    form = sys.argv[1] if len(sys.argv) > 1 else "a"
    p = data.load_panel("hl", "1d")
    slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
    fin, ref, err = legs(p)
    print("leg decomposition max |err| vs blend:", err, flush=True)
    out = {"decomp_err": err}
    run = lambda w: bt.run(w, p["close"], p.get("funding"), slip, band=0.005)
    yrs = (2023, 2024, 2025, 2026)
    if form == "a":
        book = run(ref)
        out["book"] = {y: summary(book, f"{y}-01-01", f"{y+1}-01-01") for y in yrs}
        for n, w in fin.items():
            r = run(w)
            out[n] = {y: summary(r, f"{y}-01-01", f"{y+1}-01-01") for y in yrs}
        for y in yrs:
            print(y, "book cost %.3f" % out["book"][y]["costs_ann"], {n: (round(out[n][y]["costs_ann"], 3), round(out[n][y]["turnover_ann"], 1),
                  round(out[n][y]["ann"] + out[n][y]["costs_ann"], 3)) for n in LEGS}, flush=True)
    else:
        win = {"b": [("2023-01-01", "2024-01-01"), ("2024-01-01", "2025-01-01"), ("2023-01-01", "2025-01-01")],
               "c": [("2025-01-01", "2026-01-01"), ("2026-01-01", "2027-01-01"), ("2025-01-01", "2027-01-01")]}[form]
        books = {"lam1": ref.fillna(0.0), "whole33": partial(ref, 0.33),
                 "slow33": fin["listing_short"] + partial(fin["lowvol"] + fin["tsmom"], 0.33)}
        for k, w in books.items():
            r = run(w)
            out[k] = {f"{lo[:4]}-{hi[:4]}": summary(r, lo, hi) for lo, hi in win}
            print(k, {a: (round(v["sr"], 3), round(v["costs_ann"], 4), round(v["sr_pre_cost"], 3)) for a, v in out[k].items()}, flush=True)
    json.dump(out, open(f"research/is3/prl_{form}.json", "w"), indent=1, default=str)
