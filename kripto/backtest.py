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
    dv = volume.rolling(bars_per_day * 7, min_periods=bars_per_day).mean() * bars_per_day
    bps = (3.0 * np.sqrt(50e6 / dv.clip(lower=1e4))).clip(1.5, 25.0)
    return bps / 1e4


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
    other cells pay the taker cost. cost_mult scales fees/slippage, not the drift (a price fact, not an estimate)."""
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
            cost_t = float(np.clip(dw, 0, None) @ np.where(np.isfinite(cb[t]), cb[t], 0.0)
                           + np.clip(-dw, 0, None) @ np.where(np.isfinite(cs[t]), cs[t], 0.0))
            w = w + dw
            out_to[t] = np.abs(dw).sum()
            w = w / (1.0 - cost_t) if cost_t < 1 else w
        out_c[t] = cost_t
        out_r[t] = (1.0 + tot) * (1.0 - cost_t) - 1.0
    S = lambda a: pd.Series(a, idx)
    return BTResult(S(out_r), S(out_g), S(out_to), S(out_c), S(out_f), pd.DataFrame(held, idx, cols))
