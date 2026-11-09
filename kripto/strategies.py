"""Signal -> target-weight functions. Every strategy has signature f(panel, **params) -> weights DataFrame.

Rows that are all-NaN mean "don't rebalance on this bar". Weights are fractions of equity (signed).
All signals use only data up to and including bar t (they are traded at close[t]).
Add new strategies by decorating with @register; the research loop and paper trader discover them here.
"""
from __future__ import annotations

import inspect

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
def trend_signal(panel, lookbacks=(7, 14, 28, 56)) -> pd.DataFrame:
    """Blended tanh of vol-normalised trailing log returns, in [-1, 1]."""
    c = panel["close"]
    bpd = bars_per_day(c.index)
    vol = ann_vol(panel)
    sig = 0
    for L in lookbacks:
        lr = np.log(c / c.shift(L * bpd))
        z = lr / (vol * np.sqrt(L / 365))
        sig = sig + np.tanh(z)
    return sig / len(lookbacks)


def dollar_volume(panel, days: int = 7) -> pd.DataFrame:
    """Trailing mean daily USD volume."""
    bpd = bars_per_day(panel["close"].index)
    return panel["volume"].rolling(days * bpd, min_periods=bpd).mean() * bpd


@register
def tsmom(panel, lookbacks=(7, 14, 28, 56), top_n=20, target_vol=0.30, every_days=1,
          long_only=False, max_gross=2.0, smooth_days=0.0, min_dv=0.0):
    """Time-series trend: per-asset blended vol-normalised trailing return, risk-weighted.
    smooth_days: EMA half-life on the signal (turnover reduction); min_dv: min trailing $ daily volume."""
    c = panel["close"]
    bpd = bars_per_day(c.index)
    vol = ann_vol(panel)
    mask = universe(panel, top_n)
    if min_dv > 0:
        mask = mask & (dollar_volume(panel) >= min_dv)
    sig = trend_signal(panel, lookbacks)
    if smooth_days > 0:
        sig = sig.ewm(halflife=smooth_days * bpd, min_periods=1).mean().where(c.notna())
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


@register
def carry_trend(panel, lookback=7, top_n=30, target_vol=0.20, every_days=1, lookbacks=(14, 28, 56),
                beta_neutral=True):
    """Trend-conditioned carry (T1d): earn funding only where price trend agrees. Short names with
    above-median funding AND a negative trend; long names with below-median funding AND a positive trend.
    Rationale: on HL the highest-funding names are momentum squeezes; only fade crowding once trend turns."""
    c = panel["close"]
    bpd = bars_per_day(c.index)
    f = panel["funding"].rolling(lookback * bpd, min_periods=bpd).mean()
    mask = universe(panel, top_n) & f.notna()
    fr = f.where(mask).rank(axis=1, pct=True)
    tr = trend_signal(panel, lookbacks)
    short = (fr > 0.5) & (tr < 0)
    long_ = (fr <= 0.5) & (tr > 0)
    raw = (long_.astype(float) - short.astype(float)) * (0.5 + (fr - 0.5).abs())  # stronger carry -> bigger
    raw = raw.where(mask, 0.0)
    raw = raw.div(raw.abs().sum(axis=1).replace(0, np.nan), axis=0)
    w = raw.fillna(0.0).where(mask.any(axis=1), np.nan)  # no agreeing names -> flat
    if beta_neutral:
        w = hedge_beta(w, beta_to(panel))
    w = rebalance_rows(w, every_days * bpd)
    return vol_target(w, panel, target_vol)


@register
def listing_short(panel, skip_days=1, hold_days=60, min_dv=1e6, target_vol=0.20, every_days=1,
                  max_gross=1.5, beta_neutral=True):
    """New-listing decay (T2): short perps from skip_days to skip_days+hold_days after their first traded
    bar (volume > 0), equal weight, BTC-beta hedged. Coins already trading in the first 30 days of the
    panel are not listing events (data start != listing). Rationale: post-listing supply overhang
    (airdrops, unlocks, early holders selling to late retail longs)."""
    c, v = panel["close"], panel["volume"]
    bpd = bars_per_day(c.index)
    traded = (v.fillna(0) > 0) & c.notna()
    started = traded.cummax()
    age = started.cumsum()  # 1 on the first traded bar
    any_t = traded.any(axis=1)
    if not any_t.any():
        return pd.DataFrame(np.nan, c.index, c.columns)
    t_cut = any_t.idxmax() + pd.Timedelta(days=30)
    pre = started.loc[started.index < t_cut].any()
    elig = (age > skip_days * bpd) & (age <= (skip_days + hold_days) * bpd) & c.notna()
    elig = elig & (dollar_volume(panel) >= min_dv)
    elig = elig.loc[:, ~pre]
    elig = elig.reindex(columns=c.columns, fill_value=False)
    elig = elig & pd.DataFrame(np.broadcast_to((c.index >= t_cut)[:, None], c.shape), c.index, c.columns)
    raw = -elig.astype(float)
    n = elig.sum(axis=1).replace(0, np.nan)
    raw = raw.div(n, axis=0).fillna(0.0)
    if beta_neutral:
        raw = hedge_beta(raw, beta_to(panel))
    w = rebalance_rows(raw, every_days * bpd)
    return vol_target(w, panel, target_vol, max_gross=max_gross)


@register
def xsmom_k(panel, lookback=28, skip=1, k=4, top_n=30, target_vol=0.25, every_days=3, beta_neutral=True):
    """Small-account cross-sectional momentum (T11): long the top-k / short the bottom-k names by
    vol-normalised trailing return (within the top_n liquid universe), equal weight, BTC-beta hedged.
    Few, large positions so every leg clears the $10 min order at $200 equity (k <= 5 per side)."""
    c = panel["close"]
    bpd = bars_per_day(c.index)
    mask = universe(panel, top_n)
    score = (np.log(c.shift(skip * bpd) / c.shift((lookback + skip) * bpd)) / ann_vol(panel)).where(mask)
    n = score.notna().sum(axis=1)
    hi = score.rank(axis=1, ascending=False, method="first") <= k
    lo = score.rank(axis=1, ascending=True, method="first") <= k
    raw = (hi.astype(float) - lo.astype(float)) / (2.0 * k)
    raw = raw.where(n >= 2 * k, 0.0)
    w = raw.where(mask.any(axis=1), np.nan)
    if beta_neutral:
        w = hedge_beta(w, beta_to(panel))
    w = rebalance_rows(w, every_days * bpd)
    return vol_target(w, panel, target_vol)


def _ffill_targets(w: pd.DataFrame) -> pd.DataFrame:
    """Held target weights between a component's rebalances (rows of all-NaN = 'no rebalance')."""
    rows = w.notna().any(axis=1)
    return w[rows].fillna(0.0).reindex(w.index).ffill().fillna(0.0)


BLEND_COMPONENTS = {  # fixed before testing (T4, 2026-11-09): the candidates' default/current params
    "tsmom": {"lookbacks": (7, 14, 28, 56), "every_days": 1, "top_n": 12, "target_vol": 0.3},
    "xsmom_k": {"lookback": 28, "every_days": 3, "k": 4},
    "listing_short": {"skip_days": 1, "hold_days": 60, "min_dv": 1e6},
}


@register
def blend(panel, target_vol=0.25, every_days=1, unit_vol=0.20, max_gross=3.0, components=None):
    """Equal-risk blend of the candidate strategies (T4). Each component's (held) target weights are
    rescaled from its own vol target to unit_vol, summed with equal weight 1/n, and the sum is
    vol-targeted to target_vol on a daily grid. One pre-registered rule; no weight search."""
    comps = components or BLEND_COMPONENTS
    bpd = bars_per_day(panel["close"].index)
    tot = 0.0
    for name, p in comps.items():
        tv = p.get("target_vol", inspect.signature(REGISTRY[name]).parameters["target_vol"].default)
        wi = _ffill_targets(REGISTRY[name](panel, **p)) * (unit_vol / tv)
        tot = tot + wi.reindex(columns=panel["close"].columns, fill_value=0.0)
    w = rebalance_rows(tot / len(comps), every_days * bpd)
    return vol_target(w, panel, target_vol, max_gross=max_gross)
