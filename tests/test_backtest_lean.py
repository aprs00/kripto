"""bt.run computes returns/costs/funding row by row since 2026-11-19 (memory: bn100). Reference = the previous full-array
implementation, copied verbatim; results must agree to 1e-12 (only dot-product rounding differs) for float64 and float32 inputs."""
import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto.backtest import BTResult, TAKER_FEE


def ref_run(weights: pd.DataFrame, close: pd.DataFrame, funding: pd.DataFrame | None = None,
        cost: pd.DataFrame | float | None = None, band: float = 0.0, fee: float = TAKER_FEE,
        cost_mult: float = 1.0, rebalance_every: int = 1, maker: dict | None = None) -> BTResult:
    """maker = execution.maker_fills(...) output + {"fee": maker fee}: trades on (t, asset) cells with hourly data use the
    passive policy (filled at the decision price for the maker fee, else drift since the decision + taker cost);
    other cells pay the taker cost. maker["skip_unfilled"]=True: post-only, an unfilled trade is not done (no drift paid,
    the position stays where it was until the next rebalance). cost_mult scales fees/slippage, not the drift (a price fact, not an estimate)."""
    idx, cols = close.index, close.columns
    W = weights.reindex(index=idx, columns=cols).to_numpy(dtype=float)
    px = close.to_numpy(dtype=float)
    ret = np.zeros_like(px)
    ret[1:] = px[1:] / px[:-1] - 1.0
    ret[~np.isfinite(ret)] = 0.0
    fnd = np.zeros_like(px) if funding is None else np.nan_to_num(
        funding.reindex(index=idx, columns=cols).to_numpy(dtype=float))
    if cost is None:
        c = np.full_like(px, fee)
    elif isinstance(cost, (int, float)):
        c = np.full_like(px, fee + cost)
    else:
        c = fee + cost.reindex(index=idx, columns=cols).to_numpy(dtype=float)
        c = np.where(np.isfinite(c), c, fee + 25e-4)
    c = c * cost_mult
    tradable = np.isfinite(px)
    if maker is not None:
        M = {k: maker[k].reindex(index=idx, columns=cols).to_numpy(dtype=float) for k in ("fill_buy", "fill_sell", "drift")}
        mf = maker["fee"] * cost_mult
        have = np.isfinite(M["fill_buy"]) & np.isfinite(M["drift"])
        cb = np.where(have, np.where(M["fill_buy"] == 1, mf, M["drift"] + c), c)
        cs = np.where(have, np.where(M["fill_sell"] == 1, mf, -M["drift"] + c), c)
        skip = bool(maker.get("skip_unfilled", False))   # post-only: an unfilled order is dropped, retried next rebalance
        nobuy = have & (M["fill_buy"] != 1)
        nosell = have & (M["fill_sell"] != 1)
    else:
        cb = cs = c

    T, N = px.shape
    w = np.zeros(N)
    out_r, out_g, out_to, out_c, out_f = (np.zeros(T) for _ in range(5))
    held = np.zeros((T, N))
    for t in range(T):
        # 1) hold through bar t
        held[t] = w
        r = ret[t]
        pr = float(w @ r)
        fp = -float(w @ fnd[t])
        tot = pr + fp
        out_g[t] = np.abs(w).sum()
        out_f[t] = fp
        denom = 1.0 + tot
        if denom <= 0:  # wiped out
            out_r[t] = -1.0
            out_r[t + 1:] = 0.0
            break
        w = w * (1.0 + r) / denom
        # 2) rebalance at close of t
        cost_t = 0.0
        tgt = W[t]
        if t % rebalance_every == 0 and np.isfinite(tgt).any():
            tgt = np.where(np.isfinite(tgt) & tradable[t], tgt, 0.0)
            # can't trade an asset without a price: keep whatever we hold
            tgt = np.where(tradable[t], tgt, w)
            dw = tgt - w
            if band > 0:
                small = (np.abs(dw) < band) & (tgt != 0)
                dw = np.where(small, 0.0, dw)
            if maker is not None and skip:
                dw = np.where(((dw > 0) & nobuy[t]) | ((dw < 0) & nosell[t]), 0.0, dw)
            cost_t = float(np.clip(dw, 0, None) @ np.where(np.isfinite(cb[t]), cb[t], 0.0)
                           + np.clip(-dw, 0, None) @ np.where(np.isfinite(cs[t]), cs[t], 0.0))
            w = w + dw
            out_to[t] = np.abs(dw).sum()
            w = w / (1.0 - cost_t) if cost_t < 1 else w
        out_c[t] = cost_t
        out_r[t] = (1.0 + tot) * (1.0 - cost_t) - 1.0
    S = lambda a: pd.Series(a, idx)
    return BTResult(S(out_r), S(out_g), S(out_to), S(out_c), S(out_f), pd.DataFrame(held, idx, cols))


def _case(seed, dtype):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=300, freq="1D", tz="UTC")
    cols = list("ABCDEF")
    px = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.03, (300, 6)), axis=0)), idx, cols)
    px.iloc[:40, 4] = np.nan                     # late listing
    px.iloc[200:, 5] = np.nan                    # delisting
    vol = pd.DataFrame(rng.uniform(1e5, 1e8, (300, 6)), idx, cols).where(px.notna())
    fnd = pd.DataFrame(rng.normal(0, 3e-4, (300, 6)), idx, cols)
    fnd.iloc[::7, 2] = np.nan
    w = pd.DataFrame(rng.normal(0, 0.2, (300, 6)), idx, cols).where(rng.uniform(size=(300, 6)) > 0.3)
    return w, px.astype(dtype), fnd.astype(dtype), bt.slippage_model(vol.astype(dtype), 1)


def test_rowwise_equals_reference():
    for seed in range(3):
        for dtype in ("float64", "float32"):
            w, px, fnd, slip = _case(seed, dtype)
            for args, kw in (((fnd, slip), {}), ((fnd, slip), {"band": 0.02, "cost_mult": 2.0}), ((None, 0.001), {}), ((), {})):
                a, b = ref_run(w, px, *args, **kw), bt.run(w, px, *args, **kw)
                # float32 (lean) panels: float32 cost frame and float32 reporting weights -> ~1e-10 on returns, ~1e-7 on weights
                tol = 1e-12 if dtype == "float64" else 1e-9
                for f in ("returns", "gross", "turnover", "costs", "funding"):
                    np.testing.assert_allclose(getattr(b, f).to_numpy(), getattr(a, f).to_numpy(), rtol=0, atol=tol)
                np.testing.assert_allclose(b.weights.to_numpy(float), a.weights.to_numpy(), rtol=0, atol=1e-12 if dtype == "float64" else 1e-6)
