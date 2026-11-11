"""Trade-size ("TSize") buckets of taker flow, built from Binance aggTrades (public archive, data.binance.vision).

Source of the idea: research/insilico_rules.md (rules R1-R4). Exocharts' TSize splits market orders into 7 size groups and
reads a bar where EVERY group has the same delta sign as an anomaly. Here a trade's size is its USD notional and the groups
are made from 12 fixed bins (EDGES), so any bucket scheme at these edges can be rebuilt without touching the raw trades again.

Storage (scripts/aggtrades.py): data/bn/tsize/<SYMBOL>.npz with `days` (D,) datetime64[D], `buy`, `sell` (D, 288, 12) float32
= taker-buy / taker-sell notional per 5-minute bar and size bin, `n` (D, 288, 12) uint32 = number of aggregated trades.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

EDGES = np.array([1e3, 3e3, 1e4, 2e4, 3e4, 6e4, 1.1e5, 1.5e5, 2.5e5, 5e5, 1e6])   # USD; bin i = [EDGES[i-1], EDGES[i])
NBINS = len(EDGES) + 1
BARS = 288                                    # 5-minute bars per day
BAR_MS = 300_000
# bucket schemes = lists of (first bin, last bin) inclusive
SCHEMES = {
    # the author's ladder (BitMEX XBTUSD 2021: 31k / 57k / 111k / 155k / 250k / 255k+; Jan 2022: 12k ... 301k)
    "author7": [(0, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9), (10, 11)],
    "fine12": [(i, i) for i in range(NBINS)],
    # two-way split used by the mousetrap rule: "broad market" vs large lots
    "small_large": [(0, 4), (6, 11)],
}
DIR = Path(__file__).resolve().parent.parent / "data" / "bn" / "tsize"


def bucket_trades(price: np.ndarray, qty: np.ndarray, t_ms: np.ndarray, buyer_is_maker: np.ndarray,
                  day_start_ms: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """One day's aggTrades -> (buy, sell, n), each (288, 12). A trade is a taker BUY when the buyer is not the maker."""
    ntl = price.astype(np.float64) * qty.astype(np.float64)
    b = np.searchsorted(EDGES, ntl, side="right")
    bar = ((t_ms.astype(np.int64) - day_start_ms) // BAR_MS)
    ok = (bar >= 0) & (bar < BARS)
    key = (bar * NBINS + b)[ok]
    ntl, sell_side = ntl[ok], buyer_is_maker.astype(bool)[ok]
    size = BARS * NBINS
    buy = np.bincount(key[~sell_side], weights=ntl[~sell_side], minlength=size)
    sell = np.bincount(key[sell_side], weights=ntl[sell_side], minlength=size)
    n = np.bincount(key, minlength=size)
    shape = (BARS, NBINS)
    return buy.reshape(shape).astype(np.float32), sell.reshape(shape).astype(np.float32), n.reshape(shape).astype(np.uint32)


def group(x: np.ndarray, scheme: str) -> np.ndarray:
    """Sum the last axis (12 bins) into the scheme's buckets."""
    return np.stack([x[..., a:b + 1].sum(axis=-1) for a, b in SCHEMES[scheme]], axis=-1)


def one_voiced(delta: np.ndarray, volume: np.ndarray, min_share: float = 0.01) -> np.ndarray:
    """-1 where every populated bucket has negative delta, +1 where every one is positive, else 0.
    delta, volume: (..., k buckets). A bucket counts only if it holds >= min_share of the bar's volume (an empty top
    bucket on a thin coin must not veto the signal) and at least 2 buckets must count."""
    tot = volume.sum(axis=-1, keepdims=True)
    live = volume >= min_share * np.where(tot > 0, tot, np.inf)
    enough = live.sum(axis=-1) >= 2
    neg = (np.where(live, delta < 0, True)).all(axis=-1) & enough
    pos = (np.where(live, delta > 0, True)).all(axis=-1) & enough
    return pos.astype(np.int8) - neg.astype(np.int8)


def load(symbol: str) -> dict | None:
    p = DIR / f"{symbol}.npz"
    if not p.exists():
        return None
    z = np.load(p)
    return {k: z[k] for k in ("days", "buy", "sell", "n")}


def frames(symbol: str, scheme: str, every: str = "1D") -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """(delta, volume) per bucket of `scheme` on a UTC index: every="1D" (one row per day) or "5min"."""
    z = load(symbol)
    if z is None:
        return None
    buy, sell = group(z["buy"].astype(np.float64), scheme), group(z["sell"].astype(np.float64), scheme)
    days = pd.DatetimeIndex(z["days"]).tz_localize("UTC")
    if every == "1D":
        buy, sell, idx = buy.sum(axis=1), sell.sum(axis=1), days
    else:
        k = buy.shape[-1]
        buy, sell = buy.reshape(-1, k), sell.reshape(-1, k)
        idx = (days.repeat(BARS) + pd.to_timedelta(np.tile(np.arange(BARS) * 5, len(days)), unit="min"))
    return pd.DataFrame(buy - sell, idx), pd.DataFrame(buy + sell, idx)
