"""Passive (maker) execution model with a taker fallback (backlog T9, 2026-11-10).

Policy, identical in research and (later) live: at the decision close P0 of bar t, post a limit order at P0 for the
rebalance trade. It counts as FILLED at P0 (maker fee) only if, within the next `horizon_h` hourly bars, the price
trades THROUGH the limit by `through` (buy: some hourly low <= P0*(1-through); sell: some high >= P0*(1+through)).
Trade-through instead of touch means price priority alone guarantees the fill, whatever our queue position.
Otherwise the order is cancelled after `horizon_h` hours and the trade crosses as taker at that hour's close, paying
the price drift since P0 plus the usual taker fee + slippage. Adverse selection is in the model: limit buys fill when
the price falls, and a momentum book's buys into a rising market do not fill and pay the drift instead.

Output matrices are on the DAILY (or 4h) panel index: row t = the trade decided at the close of bar t.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MAKER_FEE = {"hl": 0.00015, "bn": 0.00020}


def maker_fills(hourly: dict[str, pd.DataFrame], index: pd.DatetimeIndex, horizon_h: int = 4,
                through: float = 5e-4) -> dict[str, pd.DataFrame]:
    """hourly = {"close","high","low"} on an hourly index (bar open times). index = the coarser panel's bar open times.
    Returns fill_buy / fill_sell (1.0, 0.0, NaN where hourly data is missing) and drift = close_H / P0 - 1."""
    c, h, l = (hourly[k].sort_index() for k in ("close", "high", "low"))
    full = pd.date_range(c.index.min(), c.index.max(), freq="1h")
    c, h, l = c.reindex(full), h.reindex(full), l.reindex(full)
    H = horizon_h
    # forward window (k+1 .. k+H): reverse, rolling, reverse back, then shift by one
    fmin = l[::-1].rolling(H, min_periods=H).min()[::-1].shift(-1)
    fmax = h[::-1].rolling(H, min_periods=H).max()[::-1].shift(-1)
    cH = c.shift(-H)
    bar = pd.Series(index).diff().median()
    dec = index + bar - pd.Timedelta(hours=1)          # last hourly bar inside panel bar t (its close = close[t])
    p0 = c.reindex(dec)
    fmin, fmax, cH = fmin.reindex(dec), fmax.reindex(dec), cH.reindex(dec)
    ok = p0.notna() & fmin.notna() & fmax.notna() & cH.notna()
    fb = (fmin <= p0 * (1 - through)).astype(float).where(ok)
    fs = (fmax >= p0 * (1 + through)).astype(float).where(ok)
    drift = (cH / p0 - 1).where(ok)
    out = {"fill_buy": fb, "fill_sell": fs, "drift": drift}
    for k in out:
        out[k].index = index
    return out
