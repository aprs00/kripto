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


def form_k(names=("flow", "carry_trend"), ks=(10, 20, 30, 50, 100), q=3):
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
        dWs = np.diff(np.vstack([np.zeros(len(cols)), W]), axis=0); dW = np.abs(dWs); sign = np.sign(dWs)
        E = pd.DataFrame(dW, idx, cols).rolling(20, min_periods=5).mean().shift(1).to_numpy()
        ex = ((idx >= "2021-01-01") & (idx < "2024-01-01"))[:, None]
        yrs = lambda res: {y: round(float((res.loc["2021":"2023"] if y == "all" else res.loc[str(y)])["r"].mean() * 365 * 100), 2) for y in (2021, 2022, 2023, "all")}
        base = yrs(sim(W, px, fnd, slip, mn * 0, mn * 0, drift, "taker").set_index(idx))
        row = {"taker": base}
        for k in ks:
            th = (k + q) * 1e-4
            fb = np.where(np.isfinite(mn), (mn < 1 - th).astype(float), np.nan); fs = np.where(np.isfinite(mx), (mx > 1 + th).astype(float), np.nan)
            filled = np.where(sign > 0, fb == 1, fs == 1); have = np.isfinite(mn) & (dW > 0) & ex
            row[f"k{k}"] = {"fill24": round(float((dW * (have & filled)).sum() / (dW * have).sum()), 3)}
            for mode in ("skip", "env"):
                r = yrs(sim(W, px, fnd, slip, fb, fs, drift, mode, E, maker=MAKER - k * 1e-4).set_index(idx))
                row[f"k{k}"][mode] = {y: round(r[y] - base[y], 2) for y in r}
        out[name] = row
        print(name, json.dumps(row), flush=True)
    json.dump(out, open(EV / "t9k_a.json", "w"), indent=1)


def form_kp(name="flow", ks=(10, 50, 100), q=3, reps=10):
    """matched placebo for form_k: random fill masks with the real fill share (per k, explore), (i) with the price improvement k, (ii) without (maker fee only)."""
    p = data.load_panel("bnall", "1d")
    sl_all = bt.slippage_model(p["volume"], 1)
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
    yrs = lambda res: {y: round(float((res.loc["2021":"2023"] if y == "all" else res.loc[str(y)])["r"].mean() * 365 * 100), 2) for y in (2021, 2022, 2023, "all")}
    base = yrs(sim(W, px, fnd, slip, mn * 0, mn * 0, drift, "taker").set_index(idx))
    rng = np.random.default_rng(11)
    out = {"taker": base}
    for k in ks:
        th = (k + q) * 1e-4
        fb = np.where(np.isfinite(mn), (mn < 1 - th).astype(float), np.nan); fs = np.where(np.isfinite(mx), (mx > 1 + th).astype(float), np.nan)
        real = yrs(sim(W, px, fnd, slip, fb, fs, drift, "skip", maker=MAKER - k * 1e-4).set_index(idx))
        share = float(np.nanmean(np.concatenate([fb[np.isfinite(fb)], fs[np.isfinite(fs)]])))
        pi, pn = [], []
        for _ in range(reps):
            m = np.where(np.isfinite(mn), (rng.random(mn.shape) < share).astype(float), np.nan)
            pi.append(yrs(sim(W, px, fnd, slip, m, m, drift, "skip", maker=MAKER - k * 1e-4).set_index(idx)))
            pn.append(yrs(sim(W, px, fnd, slip, m, m, drift, "skip", maker=MAKER).set_index(idx)))
        avg = lambda L: {y: round(float(np.mean([d[y] for d in L])), 2) for y in L[0]}
        out[f"k{k}"] = {"fill_share": round(share, 3), "real_minus_taker": {y: round(real[y] - base[y], 2) for y in real},
                        "placebo_improve_minus_taker": {y: round(avg(pi)[y] - base[y], 2) for y in real},
                        "placebo_noimprove_minus_taker": {y: round(avg(pn)[y] - base[y], 2) for y in real},
                        "selection_value_real_minus_placebo": {y: round(real[y] - avg(pi)[y], 2) for y in real}}
        print(k, json.dumps(out[f"k{k}"]), flush=True)
    json.dump(out, open(EV / f"t9k_placebo_{name}.json", "w"), indent=1)


def form_conf():
    """T9C: one run of the pre-registered T9C_flow_k50 / T9C_carry_trend_k20 on 2024-01-01..2026-10-31."""
    from research.studies import is3_lib as L
    pr = L.committed_prereg()
    p = data.load_panel("bnall", "1d")
    sl_all = bt.slippage_model(p["volume"], 1)
    out = {}
    for name, key in (("flow", "T9C_flow_k50"), ("carry_trend", "T9C_carry_trend_k20")):
        assert key in pr, key
        k, q = pr[key]["params"]["k_bp"], pr[key]["params"]["q_bp"]
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
        ys = (2024, 2025, 2026)
        g = lambda res: {**{y: float(res.loc[str(y)].loc[:"2026-10-31"]["r"].mean() * 365 * 100) for y in ys},
                         "all": float(res.loc["2024-01-01":"2026-10-31"]["r"].mean() * 365 * 100)}
        base = g(sim(W, px, fnd, slip, mn * 0, mn * 0, drift, "taker").set_index(idx))
        th = (k + q) * 1e-4
        fb = np.where(np.isfinite(mn), (mn < 1 - th).astype(float), np.nan); fs = np.where(np.isfinite(mx), (mx > 1 + th).astype(float), np.nan)
        res = sim(W, px, fnd, slip, fb, fs, drift, "skip", maker=MAKER - k * 1e-4).set_index(idx)
        real = g(res)
        cw = (idx >= "2024-01-01") & (idx <= "2026-10-31")
        share = float(np.nanmean(np.concatenate([fb[cw][np.isfinite(fb[cw])], fs[cw][np.isfinite(fs[cw])]])))
        rng = np.random.default_rng(13)
        pl = [g(sim(W, px, fnd, slip, m, m, drift, "skip").set_index(idx))
              for m in [np.where(np.isfinite(mn), (rng.random(mn.shape) < share).astype(float), np.nan) for _ in range(10)]]
        plm = {y: float(np.mean([d[y] for d in pl])) for y in base}
        d_t = {y: round(real[y] - base[y], 2) for y in base}; d_p = {y: round(real[y] - plm[y], 2) for y in base}
        rr = res.loc["2024-01-01":"2026-10-31"]["r"]
        verdict = all(d_t[y] >= 1.0 for y in ys) and d_p["all"] >= 0
        out[key] = {"taker_ann_pct": {y: round(v, 2) for y, v in base.items()}, "real_minus_taker": d_t, "real_minus_fee_placebo": d_p,
                    "fill_share": round(share, 3), "sr_real": round(float(rr.mean() / rr.std() * np.sqrt(365)), 2), "PASS": bool(verdict)}
        print(key, json.dumps(out[key]), flush=True)
    json.dump(out, open(EV / "t9c_confirm.json", "w"), indent=1)


if __name__ == "__main__":
    {"ab": form_ab, "b2": form_b2, "k": form_k, "kp": form_kp, "conf": form_conf}[sys.argv[1]]()
