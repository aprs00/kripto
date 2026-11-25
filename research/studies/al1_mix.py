"""AL1 (library N12, maxdama §6; 2026-11-25 research): how should main_bn mix its candidates? Descriptive, nested, no new signal and no
registry line (books run through kripto.backtest directly, like the F0 harness). Component daily net returns on bnall 1d (clean) with the
live configs; every 60 days, weights are refit on the expanding window before that date (>= 240 days of history) and held for 60 days:
  1/N · inverse-vol (trailing 180 d) · min-variance with the covariance shrunk 50% to its diagonal (long-only, sum 1)
Sets: NOW = main_bn today (flow, xsmom, blend); ATOMS = the single strategies (flow, xsmom, xsmom_k, tsmom, listing_short);
RULE = what the fixed M1 rule would admit on the TF1 numbers (flow, xsmom, xsmom_k, tsmom, blend, blend_nested).
Mixing returns ignores netting between books (slightly cost-pessimistic). Reported: OOS SR, ann vol, mdd, by year SR, component correlations.
  usage: nice -n 19 .venv/bin/python -m research.studies.al1_mix
"""
import numpy as np
import pandas as pd

from kripto import backtest as bt, data
from kripto.research import bars_per_day, default_band
from kripto.strategies import REGISTRY

CFG = {"flow": ("flow", {"lookback": 3, "cap": 0.05}), "xsmom": ("xsmom", {"lookback": 28, "every_days": 1, "cap": 0.05}),
       "xsmom_k": ("xsmom_k", {"lookback": 28, "k": 5, "every_days": 3, "cap": 0.05}),
       "tsmom": ("tsmom", {"lookbacks": [14, 28, 56], "every_days": 1, "top_n": 12, "target_vol": 0.3}),
       "listing_short": ("listing_short", {"skip_days": 1, "hold_days": 60, "min_dv": 1e6}),
       "blend": ("blend", {}), "blend_nested": ("blend_nested", {"top": 3})}
SETS = {"NOW": ["flow", "xsmom", "blend"], "ATOMS": ["flow", "xsmom", "xsmom_k", "tsmom", "listing_short"],
        "RULE": ["flow", "xsmom", "xsmom_k", "tsmom", "blend", "blend_nested"]}


def stats(r):
    r = r.dropna()
    eq = (1 + r).cumprod()
    return r.mean() / r.std() * np.sqrt(365), r.std() * np.sqrt(365), (eq / eq.cummax() - 1).min()


def weights(R: pd.DataFrame, how: str) -> np.ndarray:
    n = R.shape[1]
    if how == "1/N":
        return np.full(n, 1 / n)
    if how == "invvol":
        sd = R.iloc[-180:].std().to_numpy()
        v = np.where(sd > 1e-9, 1 / np.maximum(sd, 1e-9), 0.0)          # a book not yet trading (blend_nested before 2021-06) gets 0
        return v / v.sum()
    S = R.cov().to_numpy()
    S = 0.5 * S + 0.5 * np.diag(np.diag(S))
    w = np.linalg.pinv(S) @ np.ones(n)                                 # pinv: a not-yet-trading book has zero variance
    w = np.clip(w, 0, None)
    return w / w.sum() if w.sum() > 0 else np.full(n, 1 / n)


def main():
    p = data.load_panel("bnall", "1d")
    slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
    comp = {}
    for k, (fn, prm) in CFG.items():
        w = REGISTRY[fn](p, **prm)
        comp[k] = bt.run(w, p["close"], p.get("funding"), slip, band=default_band()).returns
    R = pd.DataFrame(comp).fillna(0.0)
    R = R[R.ne(0).any(axis=1).cummax()]
    print(f"AL1 | bnall 1d | {R.index[0]:%Y-%m-%d} .. {R.index[-1]:%Y-%m-%d}")
    print("component full-sample SR: " + ", ".join(f"{k} {stats(R[k])[0]:.2f}" for k in R))
    print("correlations (daily):\n" + R.corr().round(2).to_string())
    for name, cols in SETS.items():
        X = R[cols]
        start = X.index[0] + pd.Timedelta(days=240)
        print(f"\n{name}: {cols}")
        for how in ("1/N", "invvol", "minvar_shrunk"):
            out, wl = [], []
            t = start
            while t < X.index[-1]:
                e = t + pd.Timedelta(days=60)
                w = weights(X[X.index < t], how)
                wl.append(w)
                out.append(X[(X.index >= t) & (X.index < e)] @ w)
                t = e
            r = pd.concat(out)
            sr, vol, mdd = stats(r)
            yrs = " ".join(f"{y}:{stats(g)[0]:+.1f}" for y, g in r.groupby(r.index.year))
            wm = np.mean(wl, axis=0)
            print(f"  {how:14s} OOS SR {sr:.2f} vol {vol:.0%} mdd {mdd:.0%} | {yrs} | mean w " + " ".join(f"{c}={x:.2f}" for c, x in zip(cols, wm)))


if __name__ == "__main__":
    main()
