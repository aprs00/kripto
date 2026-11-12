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


def tranche_mean(w: pd.DataFrame, n: int) -> pd.DataFrame:
    """Staggered tranches. `w` has target rows on the rebalance bars (all-NaN rows elsewhere). On each rebalance row the
    result is the mean of the last `n` rebalance rows' targets = a book split into n equal tranches, each rebalanced
    every n-th row on a different row. A tranche that has not traded yet is flat (so the book ramps in over n rows)."""
    rows = w.notna().any(axis=1)
    d = w[rows].fillna(0.0)
    return (d.rolling(n, min_periods=1).sum() / n).reindex(w.index)


def scheduled(raw: pd.DataFrame, panel, every_days: int, target_vol: float, max_gross: float = 3.0,
              phase: int | None = None) -> pd.DataFrame:
    """Turn fresh per-bar target weights into the traded schedule, then vol-target.
    phase=None (default, what research and live use): a schedule of `every_days` > 1 is run as `every_days` staggered
    tranches rebalanced daily, i.e. the average over every possible start day of the schedule. A single start day is
    a lottery for concentrated books (2026-11-09 review: bnall xsmom_k weekly SR 0.26-1.46 depending on the weekday).
    phase=k: the single schedule that rebalances on days == k (mod every_days); k=0 is the pre-2026-11-10 behaviour.
    Diagnostics only (phase spread in research.robustness)."""
    bpd = bars_per_day(panel["close"].index)
    if phase is not None or every_days <= 1:
        # every_days may be a fraction on intraday bars: 1/6 = every 4 hours, 1/24 = every hour (never finer than one bar)
        w = rebalance_rows(raw, max(1, int(round(every_days * bpd))), offset=int(round((phase or 0) * bpd)))
    else:
        w = tranche_mean(rebalance_rows(raw, bpd), int(round(every_days)))
    return vol_target(w, panel, target_vol, max_gross=max_gross)


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
          long_only=False, max_gross=2.0, smooth_days=0.0, min_dv=0.0, phase=None):
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
    return scheduled(raw.fillna(0).where(mask.any(axis=1), np.nan), panel, every_days, target_vol, max_gross, phase)


@register
def xsmom(panel, lookback=28, skip=1, top_n=30, target_vol=0.25, every_days=3, beta_neutral=True, phase=None):
    """Cross-sectional momentum (dollar & beta neutral)."""
    c = panel["close"]
    bpd = bars_per_day(c.index)
    score = np.log(c.shift(skip * bpd) / c.shift((lookback + skip) * bpd)) / ann_vol(panel)
    w = xs_demean_rank(score, universe(panel, top_n))
    if beta_neutral:
        w = hedge_beta(w, beta_to(panel))
    return scheduled(w, panel, every_days, target_vol, phase=phase)


@register
def xsrev(panel, lookback=3, top_n=30, target_vol=0.25, every_days=1, beta_neutral=True, phase=None):
    """Cross-sectional short-term reversal."""
    c = panel["close"]
    bpd = bars_per_day(c.index)
    score = -np.log(c / c.shift(lookback * bpd)) / ann_vol(panel)
    w = xs_demean_rank(score, universe(panel, top_n))
    if beta_neutral:
        w = hedge_beta(w, beta_to(panel))
    return scheduled(w, panel, every_days, target_vol, phase=phase)


@register
def carry(panel, lookback=7, top_n=30, target_vol=0.20, every_days=1, beta_neutral=True, phase=None):
    """Funding carry: short the assets whose longs pay the most funding, long those that receive.
    Dollar (and optionally beta) neutral so the PnL is funding spread + residual returns."""
    c = panel["close"]
    bpd = bars_per_day(c.index)
    f = panel["funding"].rolling(lookback * bpd, min_periods=bpd).mean()
    mask = universe(panel, top_n) & f.notna()
    w = xs_demean_rank(-f, mask)
    if beta_neutral:
        w = hedge_beta(w, beta_to(panel))
    return scheduled(w, panel, every_days, target_vol, phase=phase)


@register
def lowvol(panel, top_n=30, target_vol=0.20, every_days=7, vol_days=30, phase=None):
    """Betting-against-volatility: long low-vol, short high-vol, beta hedged to BTC."""
    c = panel["close"]
    bpd = bars_per_day(c.index)
    v = returns(panel).rolling(vol_days * bpd, min_periods=bpd * 10).std()
    w = xs_demean_rank(-v, universe(panel, top_n))
    w = hedge_beta(w, beta_to(panel))
    return scheduled(w, panel, every_days, target_vol, phase=phase)


@register
def funding_contra(panel, fast=1, slow=14, top_n=20, target_vol=0.20, every_days=1, beta_neutral=True, phase=None):
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
    return scheduled(w, panel, every_days, target_vol, phase=phase)


@register
def carry_trend(panel, lookback=7, top_n=30, target_vol=0.20, every_days=1, lookbacks=(14, 28, 56),
                beta_neutral=True, phase=None):
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
    return scheduled(w, panel, every_days, target_vol, phase=phase)


@register
def listing_short(panel, skip_days=1, hold_days=60, min_dv=1e6, target_vol=0.20, every_days=1,
                  max_gross=1.5, beta_neutral=True, phase=None):
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
    return scheduled(raw, panel, every_days, target_vol, max_gross, phase)


@register
def xsmom_k(panel, lookback=28, skip=1, k=4, top_n=30, target_vol=0.25, every_days=3, beta_neutral=True, phase=None):
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
    return scheduled(w, panel, every_days, target_vol, phase=phase)


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
def blend(panel, target_vol=0.25, every_days=1, unit_vol=0.20, max_gross=3.0, components=None, phase=None):
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
    return scheduled(tot / len(comps), panel, every_days, target_vol, max_gross, phase)


@register
def resrev(panel, lookback=7, thr=1.5, top_n=30, target_vol=0.20, every_days=1, beta_days=60, phase=None):
    """Residual reversion with an entry threshold (library N5: Pole ch. 3/4/7; Bouchaud et al.: impact is mostly
    transient). New angle vs the dead `xsrev` (raw returns, every name, every bar → fees): remove BTC beta, z-score
    each name's L-day cumulative residual by its own residual vol, and trade only the excess beyond `thr`
    (soft threshold: weight ∝ -(z - sign(z)·thr)), so most names are flat most of the time.
    Who pays: liquidity demanders whose flow pushed the price away from its factor-implied value."""
    c = panel["close"]
    bpd = bars_per_day(c.index)
    r = returns(panel)
    beta = beta_to(panel, days=beta_days)
    e = r.sub(beta.mul(r["BTC"], axis=0))
    rv = e.ewm(halflife=20 * bpd, min_periods=10 * bpd).std()
    z = e.rolling(lookback * bpd, min_periods=lookback * bpd).sum() / (rv * np.sqrt(lookback * bpd))
    mask = universe(panel, top_n) & z.notna()
    mask["BTC"] = False  # BTC is the factor, not a residual bet
    ex = (z.abs() - thr).clip(lower=0) * np.sign(z)
    raw = (-ex).where(mask, 0.0)
    raw = raw.div(raw.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    raw = raw.where(mask.any(axis=1), np.nan)
    w = hedge_beta(raw, beta)
    return scheduled(w, panel, every_days, target_vol, phase=phase)


@register
def flow(panel, lookback=7, sign=1, resid=False, top_n=30, target_vol=0.25, every_days=1, beta_neutral=True, phase=None):
    """Taker-flow imbalance, cross-sectional (library N1/N2: Bouchaud-Farmer-Lillo, Toth et al. on metaorder splitting;
    Valtos/Tradingriot "delta"/absorption). imb = (taker buy - taker sell) / volume over `lookback` days.
    sign=+1: continuation (split metaorders keep coming). sign=-1: reversal (transient impact). resid=True: use only
    the part of imb NOT explained by the same-window return (cross-sectional regression) = "flow without price
    progress", i.e. absorption. Requires panel['taker_buy'] (quote volume bought by takers); Binance only.
    Cross-venue use (dataset "hlx"): prices/universe from HL, taker_buy + flow_volume from Binance for the same coins."""
    if "taker_buy" not in panel:
        raise ValueError("flow needs panel['taker_buy'] (Binance klines col 10)")
    c, v, tb = panel["close"], panel["volume"], panel["taker_buy"]
    bpd = bars_per_day(c.index)
    n = lookback * bpd
    fv = panel.get("flow_volume", v)   # volume on the venue the taker split comes from (differs from `v` cross-venue)
    imb = (2 * tb - fv).rolling(n, min_periods=n).sum() / fv.rolling(n, min_periods=n).sum()
    mask = universe(panel, top_n) & imb.notna()
    score = imb.where(mask)
    if resid:
        ret = np.log(c / c.shift(n)).where(mask)
        sc, rc = score.sub(score.mean(axis=1), axis=0), ret.sub(ret.mean(axis=1), axis=0)
        b = (sc * rc).sum(axis=1) / (rc * rc).sum(axis=1).replace(0, np.nan)
        score = sc.sub(rc.mul(b, axis=0))
    w = xs_demean_rank(sign * score, mask)
    if beta_neutral:
        w = hedge_beta(w, beta_to(panel))
    return scheduled(w, panel, every_days, target_vol, phase=phase)


@register
def fspread(panel, lookback=7, thr=0.10, top_n=30, gross=2.0, max_pair=0.25, every_days=1, phase=None):
    """Cross-venue funding capture (backlog X1). Needs the two-venue panel (dataset "pair": columns <COIN>@hl, <COIN>@bn).
    s = trailing `lookback`-day mean of (HL funding - Binance funding), annualised. Where s > thr, HL longs pay more than
    Binance longs: short the coin on HL and hold it long on Binance (mirror for s < -thr). Price risk cancels (same asset on
    both legs); the book earns the funding difference minus two sets of trading costs and basis noise.
    Weight per pair is proportional to the excess |s| - thr, each leg capped at max_pair of equity; total gross <= `gross`
    (2.0 = one unit long + one unit short). No vol targeting: its volatility is tiny, the binding limit is leverage.
    Who pays: leveraged longs on the venue where they are more crowded (HL retail), and nobody arbitrages it away in thin
    names because it needs margin on two venues and is too small for a fund. NOT modelled: margin sits on two venues with no
    netting, so a large move needs collateral moved between them (or the losing leg is liquidated)."""
    c, f = panel["close"], panel["funding"]
    hlc = [x for x in c.columns if x.endswith("@hl") and x[:-3] + "@bn" in c.columns]
    if not hlc:
        return pd.DataFrame(np.nan, c.index, c.columns)
    bnc = [x[:-3] + "@bn" for x in hlc]
    bpd = bars_per_day(c.index)
    n = lookback * bpd
    on_bn = lambda df: df[bnc].set_axis(hlc, axis=1)
    s = (f[hlc] - on_bn(f)).rolling(n, min_periods=n).mean() * bpd * 365
    same = np.log(c[hlc] / on_bn(c)).abs().rolling(30 * bpd, min_periods=10 * bpd).median() < 0.03
    dv = dollar_volume(panel)
    dvm = np.minimum(dv[hlc], on_bn(dv))                      # a pair is only as liquid as its thinner leg
    elig = same & s.notna() & c[hlc].notna() & on_bn(c).notna() & (dvm > 0)
    liquid = dvm.where(elig).rank(axis=1, ascending=False) <= top_n
    ex = (s.abs() - thr).clip(lower=0).where(elig & liquid, 0.0)
    wt = ex.div(ex.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0) * (gross / 2)
    leg = -np.sign(s).fillna(0.0) * wt.clip(upper=max_pair)    # s > 0: short HL, long Binance
    w = pd.DataFrame(0.0, c.index, c.columns)
    w[hlc], w[bnc] = leg, -leg.to_numpy()
    w = w.where(elig.any(axis=1), np.nan)
    if phase is not None or every_days <= 1:
        return rebalance_rows(w, every_days * bpd, offset=(phase or 0) * bpd)
    return tranche_mean(rebalance_rows(w, bpd), every_days)


# H4 (2026-11-10): component SELECTION nested inside the blend. Pool fixed before testing = every registered strategy that
# runs on plain price/volume/funding panels (flow/fspread need extra columns), each at its function DEFAULT params.
NESTED_POOL = ("tsmom", "xsmom", "xsrev", "carry", "lowvol", "funding_contra", "carry_trend", "listing_short",
               "xsmom_k", "resrev")
_COMP_CACHE: dict = {}


def _component_returns(panel, name: str):
    """(held target weights, net backtest returns) of one pool component at default params. Cached per panel object
    (the cache keeps a reference to panel['close'] so an id is never reused while cached)."""
    from . import backtest as bt
    key = (id(panel["close"]), name)
    hit = _COMP_CACHE.get(key)
    if hit is not None and hit[0] is panel["close"]:
        return hit[1], hit[2]
    w = REGISTRY[name](panel)
    slip = bt.slippage_model(panel["volume"], bars_per_day(panel["close"].index))
    r = bt.run(w, panel["close"], panel.get("funding"), slip, band=0.01).returns
    held = _ffill_targets(w)
    if len(_COMP_CACHE) > 64:
        _COMP_CACHE.clear()
    _COMP_CACHE[key] = (panel["close"], held, r)
    return held, r


def nested_selection(panel, top=3, refit_days=60, min_days=240, unit_vol=0.20, pool=NESTED_POOL):
    """H4 selection rule. Returns (comps, sel, log): comps = {name: rescaled held weights}, sel = per-bar equal weights of the
    chosen components (rows on refit bars, forward-filled), log = [(refit date, {name: expanding Sharpe})] of the choices."""
    c = panel["close"]
    bpd = bars_per_day(c.index)
    comps, rets = {}, {}
    for name in pool:
        try:
            held, r = _component_returns(panel, name)
        except KeyError:            # panel lacks a column this component needs
            continue
        tv = inspect.signature(REGISTRY[name]).parameters["target_vol"].default
        comps[name] = held.reindex(columns=c.columns, fill_value=0.0) * (unit_vol / tv)
        rets[name] = r
    epoch = pd.Timestamp(0, tz=c.index.tz)
    day = np.asarray((c.index - epoch) // pd.Timedelta(days=1), dtype=np.int64)
    refit = np.r_[True, np.diff(day // refit_days) != 0]
    sel = pd.DataFrame(np.nan, c.index, list(comps))
    ann = np.sqrt(365 * bpd)
    log = []
    for i in np.flatnonzero(refit):
        cur = {}
        for name, r in rets.items():
            ri = r.iloc[: i + 1]
            inv = ri.ne(0).to_numpy()
            if not inv.any():
                continue
            ri = ri.iloc[int(inv.argmax()):]
            if len(ri) < min_days * bpd or ri.std() == 0:
                continue
            cur[name] = float(ri.mean() / ri.std() * ann)
        best = [n for n, s in sorted(cur.items(), key=lambda x: -x[1]) if s > 0][:top]
        sel.iloc[i] = 0.0
        if best:
            sel.iloc[i, [sel.columns.get_loc(n) for n in best]] = 1.0 / len(best)
        log.append((c.index[i], {n: round(cur[n], 2) for n in best}))
    return comps, sel.ffill().fillna(0.0), log


@register
def blend_nested(panel, top=3, refit_days=60, min_days=240, target_vol=0.25, unit_vol=0.20, max_gross=3.0,
                 every_days=1, pool=NESTED_POOL, phase=None):
    """Blend whose components are chosen out-of-sample (H4, pre-registered 2026-11-10). Every `refit_days` days (grid
    anchored at the epoch) rank every pool strategy by its expanding net Sharpe on all data up to that bar (needs
    >= min_days of invested history) and hold the equal-risk blend (same rescaling as `blend`) of the `top` best with
    Sharpe > 0 until the next refit. Removes the hindsight in choosing `blend`'s three components.
    Live trades `blend` with the latest choice (`python -m scripts.nested_choice hl`): the live panel is too short."""
    c = panel["close"]
    comps, sel, _ = nested_selection(panel, top, refit_days, min_days, unit_vol, pool)
    tot = pd.DataFrame(0.0, c.index, c.columns)
    for name, w in comps.items():
        tot = tot + w.mul(sel[name], axis=0)
    tot = tot.where(sel.sum(axis=1) > 0, 0.0)
    return scheduled(tot, panel, every_days, target_vol, max_gross, phase)


@register
def fspread_hold(panel, lookback=14, enter=0.20, top_n=20, max_pair=0.10, gross=2.0, phase=None):
    """Funding capture, second angle (X1b, 2026-11-10). X1 `fspread` re-weighted every day in proportion to the spread and
    churned the funding away (turnover 70-410x/yr). Here each pair is a fixed-size position with hysteresis: OPEN when the
    trailing `lookback`-day mean of (HL - Binance funding), annualised, exceeds `enter` in absolute value (short the venue
    whose longs pay more, long the other, each leg `max_pair` of equity); HOLD until that mean changes sign or the pair stops
    being eligible (not the same asset, no price, out of the top_n by thinner-leg volume x 2). At most gross/(2*max_pair)
    pairs open; free slots go to the widest spreads. Same economics as fspread: paid by crowded leveraged longs on one venue."""
    c, f = panel["close"], panel["funding"]
    hlc = [x for x in c.columns if x.endswith("@hl") and x[:-3] + "@bn" in c.columns]
    if not hlc:
        return pd.DataFrame(np.nan, c.index, c.columns)
    bnc = [x[:-3] + "@bn" for x in hlc]
    bpd = bars_per_day(c.index)
    n = lookback * bpd
    on_bn = lambda df: df[bnc].set_axis(hlc, axis=1)
    s = (f[hlc] - on_bn(f)).rolling(n, min_periods=n).mean() * bpd * 365
    same = np.log(c[hlc] / on_bn(c)).abs().rolling(30 * bpd, min_periods=10 * bpd).median() < 0.03
    dv = dollar_volume(panel)
    dvm = np.minimum(dv[hlc], on_bn(dv))
    elig = same & s.notna() & c[hlc].notna() & on_bn(c).notna() & (dvm > 0)
    liquid = dvm.where(elig).rank(axis=1, ascending=False) <= 2 * top_n     # hold through small rank changes
    can_open = elig & (dvm.where(elig).rank(axis=1, ascending=False) <= top_n)
    S, E, L, O = s.to_numpy(), (elig & liquid).to_numpy(), can_open.to_numpy(), np.zeros(len(hlc))
    slots = int(round(gross / (2 * max_pair)))
    out = np.zeros((len(c), len(hlc)))
    for t in range(len(c)):
        st_ = S[t]
        # exits: spread changed sign (or vanished) or pair no longer eligible
        keep = (O != 0) & E[t] & np.isfinite(st_) & (np.sign(np.nan_to_num(st_)) == O)
        O = np.where(keep, O, 0.0)
        free = slots - int((O != 0).sum())
        if free > 0:
            cand = np.flatnonzero((O == 0) & L[t] & np.isfinite(st_) & (np.abs(np.nan_to_num(st_)) > enter))
            cand = cand[np.argsort(-np.abs(st_[cand]))][:free]
            O[cand] = np.sign(st_[cand])
        out[t] = O
    leg = pd.DataFrame(-out * max_pair, c.index, hlc)        # O = +1 (HL longs pay more): short HL, long Binance
    w = pd.DataFrame(0.0, c.index, c.columns)
    w[hlc], w[bnc] = leg, -leg.to_numpy()
    return rebalance_rows(w.where(elig.any(axis=1), np.nan), bpd)


# --------------------------------------------------------------------------- InSilico rules (research/insilico_rules.md)
@register
def tsize_capit(panel, scheme="author7", hold_days=3, min_share=0.01, side="long", weight=None):
    """Daily trade-size capitulation (R1): a closed day on which EVERY trade-size bucket of taker flow is net negative
    -> long that coin for `hold_days` (a new signal restarts the clock). side="short": the mirror the author says does
    not work (all buckets positive -> short), kept as a control. Needs panel["ts_delta"], panel["ts_vol"] with columns
    (coin, bin) (dataset bnts). Fixed weight 1/n_coins per position: no leverage, no vol targeting."""
    from . import tsize
    c = panel["close"]
    if "ts_delta" not in panel:
        return pd.DataFrame(np.nan, c.index, c.columns)
    bpd = bars_per_day(c.index)
    coins = [x for x in c.columns if x in panel["ts_delta"].columns.get_level_values(0)]
    w = pd.DataFrame(0.0, c.index, c.columns)
    unit = weight or 1.0 / max(1, len(coins))
    want = -1 if side == "long" else 1
    for coin in coins:
        d = tsize.group(panel["ts_delta"][coin].to_numpy(dtype=float), scheme)
        v = tsize.group(panel["ts_vol"][coin].to_numpy(dtype=float), scheme)
        sig = pd.Series(tsize.one_voiced(d, v, min_share) == want, c.index) & c[coin].notna()
        act = sig.astype(float).rolling(int(hold_days * bpd), min_periods=1).max() > 0
        w[coin] = np.where(act, -want * unit, 0.0)
    return w


@register
def weekend_revert(panel, thr=0.01, exit="fill", coins=("BTC", "ETH"), weight=0.5):
    """Weekend -> Monday reversion to Friday's price (R21). F = close of the hour ending Friday 17:00 New York (CME
    close). At the close of the hour ending Sunday 18:00 New York (CME reopen): if |P/F - 1| >= thr, hold -sign(gap).
    exit="fill": out at the first hourly close after the hour's range crossed F; always out by Monday 17:00 New York.
    Hourly bars indexed by open time; on other bar sizes the session hours never match and the book stays flat."""
    c = panel["close"]
    w = pd.DataFrame(0.0, c.index, c.columns)
    ny = (c.index + (c.index[1] - c.index[0])).tz_convert("America/New_York")     # bar CLOSE time in New York
    wd, hr, mi = np.asarray(ny.day_of_week), np.asarray(ny.hour), np.asarray(ny.minute)
    fri = np.flatnonzero((wd == 4) & (hr == 17) & (mi == 0))
    sun = np.flatnonzero((wd == 6) & (hr == 18) & (mi == 0))
    mon = np.flatnonzero((wd == 0) & (hr == 17) & (mi == 0))
    for coin in [x for x in coins if x in c.columns]:
        px = c[coin].to_numpy(dtype=float)
        hi = panel["high"][coin].to_numpy(dtype=float) if "high" in panel else px
        lo = panel["low"][coin].to_numpy(dtype=float) if "low" in panel else px
        col = np.zeros(len(px))
        for f in fri:
            s = sun[np.searchsorted(sun, f)] if np.searchsorted(sun, f) < len(sun) else None
            m = mon[np.searchsorted(mon, f)] if np.searchsorted(mon, f) < len(mon) else None
            if s is None or m is None or not (f < s < m) or (m - f) > 100 or not np.isfinite(px[f]) or not np.isfinite(px[s]):
                continue
            g = px[s] / px[f] - 1.0
            if abs(g) < thr:
                continue
            x = m
            if exit == "fill":
                hit = np.flatnonzero((lo[s + 1:m + 1] <= px[f]) & (hi[s + 1:m + 1] >= px[f]))
                if len(hit):
                    x = s + 1 + int(hit[0])
            col[s:x] = -np.sign(g) * weight
        w[coin] = col
    return w
