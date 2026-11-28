"""InSilico pass 3, T9F: post-only execution for flow@bn (and blend_nested@bn's components) on bnall 1d with fills from bn100 1h high/low. Descriptive, NOT registered.

  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_t9f ab      # -> research/is3/t9f_ab.json

Fill rule as T9D: a post-only order at the decision close L0 = close[t] fills within 24 h only if a 1h bar opening in [D, D+24h) trades THROUGH L0 by q bp
(buy: low < L0 (1 - q); sell: high > L0 (1 + q)), D = t + 1 d. Coins without bn100 hourly data: taker (counted). Policies via is3_t9d.sim.
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto import strategies as S
from kripto.data import BN100_DIR
from kripto.strategies import REGISTRY
from research.studies.is3_t9d import MAKER, TAKER, sim

warnings.filterwarnings("ignore")
EV = data.DATA.parent / "research" / "is3"
BOOKS = {"flow": ("flow", {"lookback": 3, "cap": 0.05}), "carry_trend": ("carry_trend", {}), "carry": ("carry", {}), "xsmom": ("xsmom", {})}


def hl24(cols, idx):
    """min low / max high over the 24 hourly bars opening in [t+1d, t+2d) for each daily label t, aligned to (idx, cols)."""
    D = idx + pd.Timedelta(days=1)
    mn = np.full((len(idx), len(cols)), np.nan); mx = mn.copy()
    for j, coin in enumerate(cols):
        f = BN100_DIR / f"{coin}USDT.parquet"
        if not f.exists():
            continue
        df = pd.read_parquet(f, columns=["t", "h", "l"])
        t = df["t"].where(df["t"] < 1e14, df["t"] // 1000)
        df.index = pd.to_datetime(t, unit="ms", utc=True)
        df = df[~df.index.duplicated()].sort_index()
        df = df.reindex(pd.date_range(df.index[0], df.index[-1], freq="1h"))
        lo = df["l"].rolling(24, min_periods=24).min().shift(-23)
        hi = df["h"].rolling(24, min_periods=24).max().shift(-23)
        mn[:, j] = lo.reindex(D).to_numpy(); mx[:, j] = hi.reindex(D).to_numpy()
    return mn, mx


def form_ab():
    p = data.load_panel("bnall", "1d")
    sl_all = bt.slippage_model(p["volume"], 1)
    out = {}
    for name, (fn, kw) in BOOKS.items():
        w = S._ffill_targets(REGISTRY[fn](p, **kw)).fillna(0.0)
        w = w.loc[:, w.abs().sum() > 0]
        cols, idx = w.columns, w.index
        px = p["close"].reindex(columns=cols).to_numpy(float)
        fnd = p["funding"].reindex(index=idx, columns=cols).to_numpy(float)
        slip = sl_all.reindex(index=idx, columns=cols).to_numpy(float)
        mn, mx = hl24(cols, idx)
        mn, mx = mn / px, mx / px
        drift = p["close"].reindex(columns=cols).shift(-1).to_numpy(float) / px - 1
        W = w.to_numpy(float)
        dW = np.abs(np.diff(np.vstack([np.zeros(len(cols)), W]), axis=0))
        ex = (idx >= "2021-01-01") & (idx < "2024-01-01")
        cov = float(np.nansum(dW[ex] * np.isfinite(mn[ex])) / dW[ex].sum())
        ref = bt.run(w, p["close"].reindex(columns=cols), p["funding"].reindex(columns=cols), sl_all.reindex(columns=cols), fee=TAKER)
        chk = float(np.abs(sim(W, px, fnd, slip, mn * 0, mn * 0, drift, "taker")["r"].to_numpy() - ref.returns.to_numpy()).max())
        row = {"hourly_coverage_of_turnover_2021_23": round(cov, 3), "taker_vs_btrun_maxdiff": chk}
        # (a) fill rates and runaways, explore, per unit traded
        sign = np.sign(np.diff(np.vstack([np.zeros(len(cols)), W]), axis=0))
        for q in (0, 5, 10):
            fb, fs = mn < 1 - q * 1e-4, mx > 1 + q * 1e-4
            filled = np.where(sign > 0, fb, fs) & np.isfinite(mn)
            have = np.isfinite(mn) & np.isfinite(drift) & (dW > 0) & ex[:, None]
            sd = sign * np.nan_to_num(drift)
            wf, wu = dW * (have & filled), dW * (have & ~filled)
            row[f"a_q{q}"] = {"fill24": round(float(wf.sum() / (wf.sum() + wu.sum())), 3),
                              "r24_filled_bp": round(float((wf * sd).sum() / wf.sum() * 1e4), 1),
                              "r24_unfilled_bp": round(float((wu * sd).sum() / max(wu.sum(), 1e-12) * 1e4), 1)}
        # (b) policies
        E = pd.DataFrame(dW, idx, cols).rolling(20, min_periods=5).mean().shift(1).to_numpy()
        for q in (0, 5, 10):
            fb = np.where(np.isfinite(mn), (mn < 1 - q * 1e-4).astype(float), np.nan)
            fs = np.where(np.isfinite(mx), (mx > 1 + q * 1e-4).astype(float), np.nan)
            for mode in ("taker", "skip", "env", "chase"):
                if mode == "taker" and q:
                    continue
                res = sim(W, px, fnd, slip, fb, fs, drift, mode, E).set_index(idx)
                yr = {}
                for y in (2021, 2022, 2023, "all"):
                    g = res.loc["2021":"2023"] if y == "all" else res.loc[str(y)]
                    yr[y] = [round(float(g["r"].mean() * 365 * 100), 2), round(float(g["r"].mean() / g["r"].std() * np.sqrt(365)), 2), round(float(g["c"].mean() * 365 * 100), 2)]
                row[f"b_{mode}_q{q}"] = yr
        out[name] = row
        print(name, json.dumps(row), flush=True)
    json.dump(out, open(EV / "t9f_ab.json", "w"), indent=1)


def form_b2(names=("flow", "carry_trend", "carry", "xsmom")):
    """'post k bp beyond the close' policy: a buy rests at L0 (1 - k), fills only on a trade-through of k + q bp (q = extra queue/latency stress), and is
    filled AT L0 (1 - k): price improvement k on the filled part = maker fee minus k in sim. k = 0 / 2 / 5 / 10, q = 0 / 3. Explore 2021-23."""
    p = data.load_panel("bnall", "1d")
    sl_all = bt.slippage_model(p["volume"], 1)
    out = {}
    for name in names:
        fn, kw = BOOKS[name]
        w = S._ffill_targets(REGISTRY[fn](p, **kw)).fillna(0.0)
        w = w.loc[:, w.abs().sum() > 0]
        cols, idx = w.columns, w.index
        px = p["close"].reindex(columns=cols).to_numpy(float)
        fnd = p["funding"].reindex(index=idx, columns=cols).to_numpy(float)
        slip = sl_all.reindex(index=idx, columns=cols).to_numpy(float)
        mn, mx = hl24(cols, idx); mn, mx = mn / px, mx / px
        drift = p["close"].reindex(columns=cols).shift(-1).to_numpy(float) / px - 1
        W = w.to_numpy(float)
        dW = np.abs(np.diff(np.vstack([np.zeros(len(cols)), W]), axis=0))
        E = pd.DataFrame(dW, idx, cols).rolling(20, min_periods=5).mean().shift(1).to_numpy()
        yrs = lambda res: {y: round(float((res.loc["2021":"2023"] if y == "all" else res.loc[str(y)])["r"].mean() * 365 * 100), 2) for y in (2021, 2022, 2023, "all")}
        row = {"taker": yrs(sim(W, px, fnd, slip, mn * 0, mn * 0, drift, "taker").set_index(idx))}
        for k in (0, 2, 5, 10):
            for q in (0, 3):
                th = (k + q) * 1e-4
                fb = np.where(np.isfinite(mn), (mn < 1 - th).astype(float), np.nan); fs = np.where(np.isfinite(mx), (mx > 1 + th).astype(float), np.nan)
                for mode in ("skip", "env"):
                    row[f"{mode}_k{k}_q{q}"] = yrs(sim(W, px, fnd, slip, fb, fs, drift, mode, E, maker=MAKER - k * 1e-4).set_index(idx))
        out[name] = row
        print(name, json.dumps(row), flush=True)
    json.dump(out, open(EV / "t9f_b2.json", "w"), indent=1)


if __name__ == "__main__":
    {"ab": form_ab, "b2": form_b2}[sys.argv[1]]()
