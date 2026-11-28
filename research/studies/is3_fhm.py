"""InSilico pass 3, FHM: flow (Binance taker flow, lb 3, cap .05) on HL prices (hlx) at taker vs a fee-only maker placebo; HL 1h real fill model. Descriptive.
    PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_fhm a|b   -> research/is3/fhm_<form>.json"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto import strategies as S
from kripto.strategies import REGISTRY
from research.studies.is3_t9d import sim

warnings.filterwarnings("ignore")
EV = data.DATA.parent / "research" / "is3"
TK, MK = 4.5e-4, 1.5e-4


def setup():
    p = data.load_panel("hlx", "1d")
    w = S._ffill_targets(REGISTRY["flow"](p, lookback=3, cap=0.05)).fillna(0.0)
    w = w.loc[:, w.abs().sum() > 0]
    cols, idx = w.columns, w.index
    px = p["close"].reindex(columns=cols).to_numpy(float)
    fnd = p["funding"].reindex(index=idx, columns=cols).to_numpy(float)
    slip = (bt.slippage_model(p["volume"], 1) * 0.5).reindex(index=idx, columns=cols).to_numpy(float)
    drift = p["close"].reindex(columns=cols).shift(-1).to_numpy(float) / px - 1
    return p, w, cols, idx, px, fnd, slip, drift


def yrs(res, ys=(2023, 2024, 2025, 2026), start="2023-03-01"):
    sr = lambda x: round(float(x.mean() / x.std() * np.sqrt(365)), 2) if x.std() > 0 else None
    r = res["r"].loc[start:]
    return {"all": [round(float(r.mean() * 365 * 100), 1), sr(r)], **{y: [round(float(r.loc[str(y)].mean() * 365 * 100), 1), sr(r.loc[str(y)])] for y in ys}}


def form_a():
    p, w, cols, idx, px, fnd, slip, drift = setup()
    W = w.to_numpy(float)
    tk = sim(W, px, fnd, slip, px * 0, px * 0, drift, "taker", taker=TK).set_index(idx)
    rng = np.random.default_rng(3)
    pl = []
    for _ in range(10):
        m = np.where(np.isfinite(px), (rng.random(px.shape) < 0.90).astype(float), np.nan)
        pl.append(sim(W, px, fnd, slip, m, m, drift, "skip", maker=MK, taker=TK).set_index(idx))
    plr = pd.concat([x["r"] for x in pl], axis=1).mean(axis=1).to_frame("r")
    # HL main book (blend listing_short+lowvol+tsmom, PRB2 slow legs not needed for a correlation) daily returns on HL 1d
    hp = data.load_panel("hl", "1d")
    book = bt.run(REGISTRY["blend"](hp, components={"listing_short": {}, "lowvol": {}, "tsmom": {}}), hp["close"], hp["funding"], bt.slippage_model(hp["volume"], 1)).returns
    j = pd.concat([plr["r"], book], axis=1, keys=["f", "b"]).dropna().loc["2023-03-01":]
    out = {"taker": yrs(tk), "maker_placebo_mean_of_10": yrs(plr), "cost_taker_pct_yr": round(float(tk["c"].loc["2023-03-01":].mean() * 365 * 100), 1),
           "turnover_yr": round(float(tk["to"].loc["2023-03-01":].mean() * 365), 0), "corr_with_hl_main_book": round(float(j["f"].corr(j["b"])), 3)}
    print(json.dumps(out, indent=1)); json.dump(out, open(EV / "fhm_a.json", "w"), indent=1)


def form_b(ks=(0, 10), q=3):
    p, w, cols, idx, px, fnd, slip, drift = setup()
    W = w.to_numpy(float)
    h1 = data.load_panel("hl", "1h")
    hl_cols = [c for c in cols]
    D = idx + pd.Timedelta(days=1)
    lo = h1["low"].rolling(24, min_periods=24).min().shift(-23)
    hi = h1["high"].rolling(24, min_periods=24).max().shift(-23)
    mn = lo.reindex(columns=hl_cols).reindex(D).to_numpy(float) / px
    mx = hi.reindex(columns=hl_cols).reindex(D).to_numpy(float) / px
    win = ("2026-04-15", "2026-11-26")
    g = lambda res: round(float(res.set_index(idx).loc[win[0]:win[1]]["r"].mean() * 365 * 100), 2)
    base = g(sim(W, px, fnd, slip, mn * 0, mn * 0, drift, "taker", taker=TK))
    cov = float(np.isfinite(mn[(idx >= win[0]) & (idx <= win[1])]).mean())
    out = {"taker": base, "hourly_cell_coverage": round(cov, 3)}
    rng = np.random.default_rng(9)
    for k in ks:
        th = (k + q) * 1e-4
        fb = np.where(np.isfinite(mn), (mn < 1 - th).astype(float), np.nan); fs = np.where(np.isfinite(mx), (mx > 1 + th).astype(float), np.nan)
        real = g(sim(W, px, fnd, slip, fb, fs, drift, "skip", maker=MK - k * 1e-4, taker=TK))
        cw = (idx >= win[0]) & (idx <= win[1])
        share = float(np.nanmean(np.concatenate([fb[cw][np.isfinite(fb[cw])], fs[cw][np.isfinite(fs[cw])]])))
        pl = np.mean([g(sim(W, px, fnd, slip, m, m, drift, "skip", maker=MK, taker=TK))
                      for m in [np.where(np.isfinite(mn), (rng.random(mn.shape) < share).astype(float), np.nan) for _ in range(5)]])
        out[f"k{k}"] = {"fill_share": round(share, 3), "real_minus_taker": round(real - base, 2), "placebo_minus_taker": round(float(pl) - base, 2), "real_minus_placebo": round(real - float(pl), 2)}
        print(k, out[f"k{k}"], flush=True)
    print(out); json.dump(out, open(EV / "fhm_b.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": form_a, "b": form_b}[sys.argv[1]]()
