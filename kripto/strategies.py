"""Signal -> target-weight functions. Every strategy has signature f(panel, **params) -> weights DataFrame.

Rows that are all-NaN mean "don't rebalance on this bar". Weights are fractions of equity (signed).
All signals use only data up to and including bar t (they are traded at close[t]).
Add new strategies by decorating with @register; the research loop and paper trader discover them here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

REGISTRY: dict[str, callable] = {}


def register(fn):
    REGISTRY[fn.__name__] = fn
    return fn


# --------------------------------------------------------------------------- helpers
def bars_per_day(idx: pd.DatetimeIndex) -> int:
    return int(round(pd.Timedelta(days=1) / pd.Series(idx).diff().median()))


def returns(panel) -> pd.DataFrame:
    return panel["close"].pct_change(fill_method=None)


def universe(panel, top_n: int = 30, min_days: int = 30, vol_days: int = 30) -> pd.DataFrame:
    """Point-in-time liquid universe: top_n by trailing USD volume, with >= min_days of history."""
    c, v = panel["close"], panel["volume"]
    bpd = bars_per_day(c.index)
    dv = v.rolling(bpd * vol_days, min_periods=bpd * 7).mean()
    age = c.notna().cumsum()
    ok = (age >= bpd * min_days) & c.notna() & (dv > 0)
    rank = dv.where(ok).rank(axis=1, ascending=False)
    return (rank <= top_n) & ok


def ann_vol(panel, halflife_days: float = 20) -> pd.DataFrame:
    r = returns(panel)
    bpd = bars_per_day(r.index)
    return r.ewm(halflife=halflife_days * bpd, min_periods=bpd * 10).std() * np.sqrt(365 * bpd)


def xs_demean_rank(score: pd.DataFrame, mask: pd.DataFrame) -> pd.DataFrame:
    s = score.where(mask)
    rk = s.rank(axis=1, pct=True)
    rk = rk.sub(rk.mean(axis=1), axis=0)
    return rk.div(rk.abs().sum(axis=1), axis=0)  # dollar neutral, gross = 1


def rebalance_rows(w: pd.DataFrame, every: int, offset: int = 0) -> pd.DataFrame:
    """Keep rows on a calendar grid anchored at the epoch (so backtest and live agree on which bars
    rebalance regardless of where the data window starts). `every` is in bars."""
    # unit-agnostic: pandas>=3 indexes may be datetime64[us]; asi8 is then NOT nanoseconds (bug fixed 2026-11-09)
    bar = pd.Series(w.index).diff().median()
    epoch = pd.Timestamp(0, tz=w.index.tz)
    n = np.asarray((w.index - epoch) // bar, dtype=np.int64)
    k = (n - offset) % every == 0
    return w.where(np.broadcast_to(k[:, None], w.shape), np.nan)


def vol_target(w: pd.DataFrame, panel, target: float, lookback_days: int = 60,
               max_gross: float = 3.0) -> pd.DataFrame:
    """Scale each rebalance row so ex-ante portfolio vol (trailing covariance) == target."""
    r = returns(panel).fillna(0.0)
    bpd = bars_per_day(r.index)
    lb = lookback_days * bpd
    out = w.copy()
    R = r.to_numpy()
    Wn = w.to_numpy()
    for i in range(len(w)):
        row = Wn[i]
        if not np.isfinite(row).any():
            continue
        row = np.nan_to_num(row)
        nz = np.flatnonzero(row)
        if len(nz) == 0 or i < bpd * 20:
            out.iloc[i] = 0.0 if i < bpd * 20 else row
            continue
        sub = R[max(0, i - lb + 1): i + 1][:, nz]
        cov = np.cov(sub, rowvar=False) * 365 * bpd
        pv = float(np.sqrt(max(row[nz] @ np.atleast_2d(cov) @ row[nz], 1e-12)))
        scaled = row * (target / pv)
        g = np.abs(scaled).sum()
        if g > max_gross:
            scaled *= max_gross / g
        out.iloc[i] = scaled
    return out


def beta_to(panel, ref: str = "BTC", days: int = 60) -> pd.DataFrame:
    r = returns(panel)
    bpd = bars_per_day(r.index)
    m = r[ref]
    cov = r.rolling(days * bpd, min_periods=bpd * 20).cov(m)
    var = m.rolling(days * bpd, min_periods=bpd * 20).var()
    return cov.div(var, axis=0)


def hedge_beta(w: pd.DataFrame, beta: pd.DataFrame, ref: str = "BTC") -> pd.DataFrame:
    rows = w.notna().any(axis=1)
    b = (w.fillna(0) * beta.fillna(1.0)).sum(axis=1)
    out = w.copy()
    out.loc[rows, ref] = out.loc[rows, ref].fillna(0) - b[rows]
    return out


# --------------------------------------------------------------------------- strategies
@register
def tsmom(panel, lookbacks=(7, 14, 28, 56), top_n=20, target_vol=0.30, every_days=1,
          long_only=False, max_gross=2.0):
    """Time-series trend: per-asset blended vol-normalised trailing return, risk-weighted."""
    c = panel["close"]
    bpd = bars_per_day(c.index)
    vol = ann_vol(panel)
    mask = universe(panel, top_n)
    sig = 0
    for L in lookbacks:
        lr = np.log(c / c.shift(L * bpd))
        z = lr / (vol * np.sqrt(L / 365))
        sig = sig + np.tanh(z)
    sig = sig / len(lookbacks)
    if long_only:
        sig = sig.clip(lower=0)
    raw = (sig / vol).where(mask)
    raw = raw.div(raw.abs().sum(axis=1).replace(0, np.nan), axis=0)
    w = rebalance_rows(raw.fillna(0).where(mask.any(axis=1), np.nan), every_days * bpd)
    return vol_target(w, panel, target_vol, max_gross=max_gross)


@register
def xsmom(panel, lookback=28, skip=1, top_n=30, target_vol=0.25, every_days=3, beta_neutral=True):
    """Cross-sectional momentum (dollar & beta neutral)."""
    c = panel["close"]
    bpd = bars_per_day(c.index)
    score = np.log(c.shift(skip * bpd) / c.shift((lookback + skip) * bpd)) / ann_vol(panel)
    w = xs_demean_rank(score, universe(panel, top_n))
    if beta_neutral:
        w = hedge_beta(w, beta_to(panel))
    w = rebalance_rows(w, every_days * bpd)
    return vol_target(w, panel, target_vol)


@register
def xsrev(panel, lookback=3, top_n=30, target_vol=0.25, every_days=1, beta_neutral=True):
    """Cross-sectional short-term reversal."""
    c = panel["close"]
    bpd = bars_per_day(c.index)
    score = -np.log(c / c.shift(lookback * bpd)) / ann_vol(panel)
    w = xs_demean_rank(score, universe(panel, top_n))
    if beta_neutral:
        w = hedge_beta(w, beta_to(panel))
    w = rebalance_rows(w, every_days * bpd)
    return vol_target(w, panel, target_vol)


@register
def carry(panel, lookback=7, top_n=30, target_vol=0.20, every_days=1, beta_neutral=True):
    """Funding carry: short the assets whose longs pay the most funding, long those that receive.
    Dollar (and optionally beta) neutral so the PnL is funding spread + residual returns."""
    c = panel["close"]
    bpd = bars_per_day(c.index)
    f = panel["funding"].rolling(lookback * bpd, min_periods=bpd).mean()
    mask = universe(panel, top_n) & f.notna()
    w = xs_demean_rank(-f, mask)
    if beta_neutral:
        w = hedge_beta(w, beta_to(panel))
    w = rebalance_rows(w, every_days * bpd)
    return vol_target(w, panel, target_vol)


@register
def lowvol(panel, top_n=30, target_vol=0.20, every_days=7, vol_days=30):
    """Betting-against-volatility: long low-vol, short high-vol, beta hedged to BTC."""
    c = panel["close"]
    bpd = bars_per_day(c.index)
    v = returns(panel).rolling(vol_days * bpd, min_periods=bpd * 10).std()
    w = xs_demean_rank(-v, universe(panel, top_n))
    w = hedge_beta(w, beta_to(panel))
    w = rebalance_rows(w, every_days * bpd)
    return vol_target(w, panel, target_vol)


@register
def funding_contra(panel, fast=1, slow=14, top_n=20, target_vol=0.20, every_days=1, beta_neutral=True):
    """Crowding reversal: assets whose funding just spiked vs their own history (crowded longs)
    are shorted, those whose funding collapsed are bought. Cross-sectional, dollar neutral."""
    c = panel["close"]
    bpd = bars_per_day(c.index)
    f = panel["funding"]
    fz = (f.rolling(fast * bpd, min_periods=1).mean() - f.rolling(slow * bpd, min_periods=bpd * 3).mean()) \
        / f.rolling(slow * bpd, min_periods=bpd * 3).std()
    mask = universe(panel, top_n) & fz.notna()
    w = xs_demean_rank(-fz, mask)
    if beta_neutral:
        w = hedge_beta(w, beta_to(panel))
    w = rebalance_rows(w, every_days * bpd)
    return vol_target(w, panel, target_vol)
