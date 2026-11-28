"""InSilico pass 3, VTS: every vol_target() scalar held until it moves > thr (hysteresis), vs daily. python -m research.studies.is3_vts a|c <bnall pickle>
(a = explore: turnover removed + net SR/vol per year; c = held-out, pre-registered)"""
import json, pickle, sys
import numpy as np, pandas as pd
from kripto import backtest as bt, data, strategies as S
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY
from research.studies.is3_prb import summary

_orig = S.vol_target
THR = {"v": 0.0}


def vt(w, panel, target, lookback_days=60, max_gross=3.0):
    out = _orig(w, panel, target, lookback_days=lookback_days, max_gross=max_gross)
    if THR["v"] <= 0:
        return out
    a = np.abs(np.nan_to_num(w.to_numpy())).sum(1)
    b = np.abs(np.nan_to_num(out.to_numpy())).sum(1)
    s = np.where(a > 0, b / np.where(a > 0, a, 1), np.nan)
    held, h = np.full(len(s), np.nan), np.nan
    for i, x in enumerate(s):
        if np.isfinite(x) and x > 0:
            if not np.isfinite(h) or abs(x / h - 1) > THR["v"]:
                h = x
            held[i] = h
    # rows with weights keep the held scalar (max_gross cap: held scalar never exceeds today's capped one by > thr)
    f = np.where(np.isfinite(held) & (s > 0), held / np.where(s > 0, s, 1), 1.0)
    return out.mul(f, axis=0)


S.vol_target = vt

BOOKS = {"blend_hl": ("hl", lambda p: REGISTRY["blend"](p, components={"listing_short": {}, "lowvol": {}, "tsmom": {}})),
         "blend_bn": ("bn", lambda p: REGISTRY["blend"](p, components={"carry_trend": {}, "carry": {}, "xsmom": {}})),
         "flow_bn": ("bn", lambda p: REGISTRY["flow"](p, lookback=3, cap=0.05))}

if __name__ == "__main__":
    form, pk = sys.argv[1], sys.argv[2]
    pan = {"hl": data.load_panel("hl", "1d"), "bn": pickle.load(open(pk, "rb"))}
    yrs = {"a": {"hl": (2023, 2024), "bn": (2021, 2022, 2023)}, "c": {"hl": (2025, 2026), "bn": (2024, 2025, 2026)}}[form]
    out = {}
    for nm, (v, fn) in BOOKS.items():
        p = pan[v]
        slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
        for thr in (0.0, 0.10):
            THR["v"] = thr
            S._COMP_CACHE.clear()
            r = bt.run(fn(p), p["close"], p.get("funding"), slip, band=0.005)
            o = {}
            for y in yrs[v]:
                o[str(y)] = summary(r, f"{y}-01-01", f"{y+1}-01-01")
                g = r.returns[r.returns.index.year == y]
                o[str(y)]["realised_vol"] = float(g.std() * np.sqrt(365))
            out[f"{nm}_thr{thr}"] = o
            print(nm, thr, {y: (round(x["sr"], 3), round(x["costs_ann"], 4), round(x["turnover_ann"], 1), round(x["realised_vol"], 3)) for y, x in o.items()}, flush=True)
    THR["v"] = 0.0
    json.dump(out, open(f"research/is3/vts_{form}.json", "w"), indent=1)
