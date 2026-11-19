"""Event-ordered portfolio backtest with fees, slippage, funding, weight drift and a no-trade band.

Timing (no lookahead):  target weights W[t] are computed from information available at the CLOSE
of bar t, traded at close[t] (paying costs), then held through bar t+1, earning ret[t+1] and
paying funding[t+1].  Positive funding => longs pay shorts (Hyperliquid convention).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TAKER_FEE = 0.00045   # Hyperliquid base tier taker
MAKER_FEE = 0.00015


def slippage_model(volume: pd.DataFrame, bars_per_day: int) -> pd.DataFrame:
    """Half-spread + impact estimate (fraction) per asset/bar from trailing USD daily volume.
    ~1.5bp for BTC/ETH-like volume, ~25bp cap for illiquid names. Deliberately conservative."""
    dv = volume.rolling(bars_per_day * 7, min_periods=bars_per_day).mean()
    a = dv.to_numpy(dtype=float, copy=True)
    del dv
    # same elementwise arithmetic as (3*sqrt(50e6/(dv*bpd).clip(lower=1e4))).clip(1.5, 25)/1e4, done in place (2026-11-19, bn100 memory)
    a *= bars_per_day
    np.clip(a, 1e4, None, out=a)
    np.divide(50e6, a, out=a)
    np.sqrt(a, out=a)
    a *= 3.0
    np.clip(a, 1.5, 25.0, out=a)
    a /= 1e4
    if all(dt == np.float32 for dt in volume.dtypes):   # lean (float32) panels get a float32 cost frame (bn100); float64 unchanged
        a = a.astype(np.float32)
    return pd.DataFrame(a, volume.index, volume.columns)


@dataclass
class BTResult:
    returns: pd.Series        # per-bar net portfolio returns
    gross: pd.Series          # gross exposure held during bar
    turnover: pd.Series       # traded notional / equity per bar
    costs: pd.Series          # trading cost per bar (fraction of equity)
    funding: pd.Series        # funding pnl per bar (fraction of equity, +=received)
    weights: pd.DataFrame     # held weights during bar

    @property
    def equity(self) -> pd.Series:
        return (1 + self.returns).cumprod()


def run(weights: pd.DataFrame, close: pd.DataFrame, funding: pd.DataFrame | None = None,
        cost: pd.DataFrame | float | None = None, band: float = 0.0, fee: float = TAKER_FEE,
        cost_mult: float = 1.0, rebalance_every: int = 1, maker: dict | None = None) -> BTResult:
    """maker = execution.maker_fills(...) output + {"fee": maker fee}: trades on (t, asset) cells with hourly data use the
    passive policy (filled at the decision price for the maker fee, else drift since the decision + taker cost);
    other cells pay the taker cost. maker["skip_unfilled"]=True: post-only, an unfilled trade is not done (no drift paid,
    the position stays where it was until the next rebalance). cost_mult scales fees/slippage, not the drift (a price fact, not an estimate)."""
    idx, cols = close.index, close.columns
    W = weights.reindex(index=idx, columns=cols).to_numpy()   # native dtype, rows cast to float64 below
    # 2026-11-19: prices, funding and costs stay in their native dtype and are turned into float64 returns/costs ONE ROW at a
    # time inside the loop (same arithmetic, identical results; tests/test_backtest_lean.py). The full-array version held
    # ~7 float64 copies of the panel and could not run the 698-coin hourly bn100 set under the 2 GB job limit.
    px = close.to_numpy()
    tradable = np.isfinite(px)
    fnd = None if funding is None else funding.reindex(index=idx, columns=cols).to_numpy()
    cst = None if (cost is None or isinstance(cost, (int, float))) else cost.reindex(index=idx, columns=cols).to_numpy()

    def ret_row(t):
        if t == 0:
            return np.zeros(px.shape[1])
        r = px[t].astype(float) / px[t - 1].astype(float) - 1.0
        r[~np.isfinite(r)] = 0.0
        return r

    def cost_row(t):
        if cost is None:
            c = np.full(px.shape[1], fee)
        elif cst is None:
            c = np.full(px.shape[1], fee + cost)
        else:
            c = fee + cst[t].astype(float)
            c = np.where(np.isfinite(c), c, fee + 25e-4)
        return c * cost_mult

    if maker is not None:
        c = np.vstack([cost_row(t) for t in range(len(idx))]) if len(idx) else np.zeros(px.shape)
        M = {k: maker[k].reindex(index=idx, columns=cols).to_numpy(dtype=float) for k in ("fill_buy", "fill_sell", "drift")}
        mf = maker["fee"] * cost_mult
        have = np.isfinite(M["fill_buy"]) & np.isfinite(M["drift"])
        cb = np.where(have, np.where(M["fill_buy"] == 1, mf, M["drift"] + c), c)
        cs = np.where(have, np.where(M["fill_sell"] == 1, mf, -M["drift"] + c), c)
        skip = bool(maker.get("skip_unfilled", False))   # post-only: an unfilled order is dropped, retried next rebalance
        nobuy = have & (M["fill_buy"] != 1)
        nosell = have & (M["fill_sell"] != 1)

    T, N = px.shape
    w = np.zeros(N)
    out_r, out_g, out_to, out_c, out_f = (np.zeros(T) for _ in range(5))
    held = np.zeros((T, N), dtype=np.float32 if px.dtype == np.float32 else float)   # lean panels: reporting copy only
    for t in range(T):
        # 1) hold through bar t
        held[t] = w
        r = ret_row(t)
        pr = float(w @ r)
        fp = 0.0 if fnd is None else -float(w @ np.nan_to_num(fnd[t].astype(float)))
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
        tgt = W[t].astype(float)
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
            if maker is not None:
                cbt, cst_ = cb[t], cs[t]
            else:
                cbt = cst_ = cost_row(t)
            cost_t = float(np.clip(dw, 0, None) @ np.where(np.isfinite(cbt), cbt, 0.0)
                           + np.clip(-dw, 0, None) @ np.where(np.isfinite(cst_), cst_, 0.0))
            w = w + dw
            out_to[t] = np.abs(dw).sum()
            w = w / (1.0 - cost_t) if cost_t < 1 else w
        out_c[t] = cost_t
        out_r[t] = (1.0 + tot) * (1.0 - cost_t) - 1.0
    S = lambda a: pd.Series(a, idx)
    return BTResult(S(out_r), S(out_g), S(out_to), S(out_c), S(out_f), pd.DataFrame(held, idx, cols))
