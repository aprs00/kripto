"""F0: filter harness. Does a signal improve a book that already works? (design.md §4 filters; research/insilico_pass3.md §2 row 11)

A filter is a boolean mask (True = allowed) over coin-days (DataFrame like the panel) or days (Series). Applied to a book's target
weights: blocked cells get weight 0 (side=+1 / -1 blocks only longs / only shorts). The book is re-run through kripto.backtest
with its own slippage model and funding, so costs of the extra trading the filter causes are paid.

The question is never "did it cut the drawdown" (any mask that cuts exposure does that) but "did it beat masks that cut the same
exposure at random": 200 random masks with the same on-share AND persistence (each coin's mask circularly shifted by a random
offset, so its on-share and run lengths are identical), the real filter's ΔSharpe percentile among them, plus a paired day-block
bootstrap of the daily return difference. Explore = <= 2023, confirm = 2024-25 (L.SAMPLES); weights are causal, so one run, then cut.

    from research.studies import is3_filter as F
    w, panel, slip = F.book("flow", "bnall", {"lookback": 3, "cap": 0.05})
    F.judge("F1b", w, panel, slip, mask, "explore", side=-1)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto.research import bars_per_day, default_band
from kripto.strategies import REGISTRY
from research.studies import is3_lib as L


def book(name: str, ds: str, params: dict, interval: str = "1d") -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    panel = data.load_panel(ds, interval)
    w = REGISTRY[name](panel, **params)
    slip = bt.slippage_model(panel["volume"], bars_per_day(panel["close"].index))
    return w, panel, slip


def apply(w: pd.DataFrame, mask, side: int | None = None) -> pd.DataFrame:
    m = mask.reindex(index=w.index, columns=w.columns).fillna(True).astype(bool) if isinstance(mask, pd.DataFrame) \
        else pd.DataFrame(np.repeat(mask.reindex(w.index).fillna(True).astype(bool).to_numpy()[:, None], w.shape[1], 1), w.index, w.columns)
    if side is None:
        return w.where(m, 0.0)
    hit = (np.sign(w) == side) & ~m
    return w.mask(hit, 0.0)


def noadd(w: pd.DataFrame, mask, side: int | None = None) -> pd.DataFrame:
    """A DELAY, not an exit (F2): on blocked cells a position may not be opened or increased on `side` (None = both sides); it keeps the
    previous bar's (already filtered) weight on that side or shrinks toward 0. Unblocked cells take the book's target."""
    W = w.fillna(0.0).to_numpy(dtype=float).copy()
    if isinstance(mask, pd.DataFrame):
        M = mask.reindex(index=w.index, columns=w.columns).fillna(True).astype(bool).to_numpy()
    else:
        M = np.repeat(mask.reindex(w.index).fillna(True).astype(bool).to_numpy()[:, None], w.shape[1], 1)
    rows = np.where(~M.all(axis=1))[0]
    for t in rows:
        if t == 0:
            continue
        prev, cur, b = W[t - 1], W[t], ~M[t]
        if side in (None, -1):
            lim = np.minimum(prev, 0.0)
            hit = b & (cur < lim)
            cur[hit] = lim[hit]
        if side in (None, 1):
            lim = np.maximum(prev, 0.0)
            hit = b & (cur > lim)
            cur[hit] = lim[hit]
    return pd.DataFrame(W, w.index, w.columns)


def scale(w: pd.DataFrame, mask, side=None, k: float = 0.0) -> pd.DataFrame:
    """blocked rows/cells scaled by k (k=0 = flat)."""
    m = mask.reindex(index=w.index, columns=w.columns).fillna(True).astype(bool) if isinstance(mask, pd.DataFrame) \
        else pd.DataFrame(np.repeat(mask.reindex(w.index).fillna(True).astype(bool).to_numpy()[:, None], w.shape[1], 1), w.index, w.columns)
    return w.where(m, w * k)


def run(w: pd.DataFrame, panel: dict, slip: pd.DataFrame | None, band: float | None = None) -> pd.Series:
    res = bt.run(w, panel["close"], panel.get("funding"), slip, band=default_band() if band is None else band)
    return res.returns


def stats(r: pd.Series) -> dict:
    r = r.dropna()
    sd = r.std()
    eq = (1 + r).cumprod()
    return {"sr": float(r.mean() / sd * np.sqrt(365)) if sd > 0 else 0.0, "ann": float(r.mean() * 365),
            "mdd": float((eq / eq.cummax() - 1).min()), "days": int(len(r))}


def random_masks(mask, n: int, seed: int = 0):
    """Same on-share and run lengths per coin: circular shift of each column (of the day series) by a random offset."""
    rng = np.random.default_rng(seed)
    if isinstance(mask, pd.Series):
        a = mask.to_numpy()
        for _ in range(n):
            yield pd.Series(np.roll(a, rng.integers(1, len(a))), mask.index)
        return
    A = mask.to_numpy()
    T = A.shape[0]
    for _ in range(n):
        off = rng.integers(1, T, size=A.shape[1])
        idx = (np.arange(T)[:, None] - off[None, :]) % T
        yield pd.DataFrame(np.take_along_axis(A, idx, 0), mask.index, mask.columns)


def cut(r: pd.Series, sample: str) -> pd.Series:
    lo, hi = (pd.Timestamp(x, tz=r.index.tz) if r.index.tz is not None else pd.Timestamp(x) for x in L.SAMPLES[sample])
    return r[(r.index >= lo) & (r.index < hi)]


def boot_diff(d: pd.Series, reps: int = 2000, block: int = 20, seed: int = 7) -> float:
    """two-sided p of mean(d) != 0, circular block bootstrap of days."""
    a = d.dropna().to_numpy()
    if len(a) < 2 * block:
        return float("nan")
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(len(a) / block))
    m = np.empty(reps)
    for i in range(reps):
        st = rng.integers(0, len(a), nb)
        ix = ((st[:, None] + np.arange(block)[None, :]) % len(a)).ravel()[:len(a)]
        m[i] = a[ix].mean()
    m -= m.mean()
    return float((1 + np.sum(np.abs(m) >= abs(a.mean()))) / (reps + 1))


def judge(name: str, w: pd.DataFrame, panel: dict, slip, mask, sample: str, side: int | None = None, n_random: int = 200,
          seed: int = 0, note: str = "", tf=None) -> dict:
    """Base book vs filtered book on `sample`; percentile of ΔSR among n_random same-share same-persistence masks.
    Confirm / vault samples follow the L.card rules: pre-registered and committed first, one run per name and sample.
    tf(w, mask, side) -> filtered weights (default `apply` = exit blocked cells; `noadd` = delay; random masks get the same tf)."""
    tf = tf or apply
    if sample != "explore":
        if name not in L.committed_prereg():
            raise SystemExit(f"{name}: pre-register (L.prereg) and COMMIT before touching {sample}")
        if (L.OUT / f"{name}__{sample}.json").exists():
            raise SystemExit(f"{name}: {sample} was already used")
    base = cut(run(w, panel, slip), sample)
    filt = cut(run(tf(w, mask, side), panel, slip), sample)
    sb, sf = stats(base), stats(filt)
    rnd = []
    for mk in random_masks(mask, n_random, seed):
        sr = stats(cut(run(tf(w, mk, side), panel, slip), sample))
        rnd.append((sr["sr"] - sb["sr"], sr["mdd"] - sb["mdd"]))
    rnd = np.array(rnd) if rnd else np.zeros((0, 2))
    dsr, dmdd = sf["sr"] - sb["sr"], sf["mdd"] - sb["mdd"]
    m = mask if isinstance(mask, pd.Series) else mask.reindex(index=w.index, columns=w.columns)
    on = float(np.nanmean(m.to_numpy(dtype=float)))
    out = {"name": name, "sample": sample, "side": side, "on_share": round(on, 3), "base": sb, "filtered": sf, "dSR": round(dsr, 3), "dMDD": round(dmdd, 4),
           "p_daily_diff": boot_diff(filt - base), "n_random": len(rnd),
           "pct_dSR_vs_random": float((rnd[:, 0] < dsr).mean()) if len(rnd) else None,
           "random_dSR_q05_q50_q95": [round(float(np.quantile(rnd[:, 0], q)), 3) for q in (0.05, 0.5, 0.95)] if len(rnd) else None,
           "pct_dMDD_vs_random": float((rnd[:, 1] < dmdd).mean()) if len(rnd) else None, "note": note}
    out["passes"] = bool(out["pct_dSR_vs_random"] is not None and out["pct_dSR_vs_random"] >= 0.95 and dsr > 0)
    L.OUT.mkdir(parents=True, exist_ok=True)
    import json
    (L.OUT / f"{name}__{sample}.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    print(f"[{name} {sample}] on {on:.0%} | SR {sb['sr']:.2f} -> {sf['sr']:.2f} (dSR {dsr:+.2f}, pct vs random {out['pct_dSR_vs_random']}, random q05/50/95 "
          f"{out['random_dSR_q05_q50_q95']}) | mdd {sb['mdd']:.1%} -> {sf['mdd']:.1%} | p(daily diff) {out['p_daily_diff']:.3f} | passes={out['passes']} {note}")
    return out
