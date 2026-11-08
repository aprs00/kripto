"""Performance statistics incl. Probabilistic & Deflated Sharpe (Bailey & Lopez de Prado)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

EULER = 0.5772156649


def periods_per_year(idx: pd.DatetimeIndex) -> float:
    dt = pd.Series(idx).diff().median()
    return pd.Timedelta(days=365) / dt


def sharpe(r: pd.Series, ppy: float) -> float:
    r = r.dropna()
    s = r.std()
    return float(r.mean() / s * np.sqrt(ppy)) if s > 0 else 0.0


def max_drawdown(r: pd.Series) -> float:
    eq = (1 + r.fillna(0)).cumprod()
    return float((eq / eq.cummax() - 1).min())


def psr(r: pd.Series, sr_benchmark: float = 0.0) -> float:
    """Probability that the true per-period Sharpe exceeds sr_benchmark (per-period units)."""
    r = r.dropna()
    n = len(r)
    if n < 30 or r.std() == 0:
        return 0.0
    sr = r.mean() / r.std()
    sk, ku = stats.skew(r), stats.kurtosis(r, fisher=False)
    den = np.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4 * sr ** 2))
    return float(stats.norm.cdf((sr - sr_benchmark) * np.sqrt(n - 1) / den))


def expected_max_sr(n_trials: int, sr_var: float) -> float:
    """Expected max of n_trials Sharpe estimates under the null (per-period units)."""
    if n_trials <= 1:
        return 0.0
    z1 = stats.norm.ppf(1 - 1 / n_trials)
    z2 = stats.norm.ppf(1 - 1 / (n_trials * np.e))
    return float(np.sqrt(sr_var) * ((1 - EULER) * z1 + EULER * z2))


def dsr(r: pd.Series, n_trials: int, sr_var: float | None = None) -> float:
    """Deflated Sharpe: PSR against the Sharpe you'd expect from the best of n_trials pure-noise strategies.
    sr_var defaults to the sampling variance of a per-period Sharpe estimate (1/n)."""
    r = r.dropna()
    if sr_var is None:
        sr_var = 1.0 / max(len(r), 1)
    return psr(r, expected_max_sr(n_trials, sr_var))


def summary(r: pd.Series, gross: pd.Series | None = None, turnover: pd.Series | None = None,
            costs: pd.Series | None = None, funding: pd.Series | None = None, n_trials: int = 1) -> dict:
    r = r.dropna()
    if len(r) < 2:
        return {}
    ppy = periods_per_year(r.index)
    yrs = len(r) / ppy
    eq = (1 + r).cumprod()
    cagr = eq.iloc[-1] ** (1 / yrs) - 1 if eq.iloc[-1] > 0 else -1.0
    vol = r.std() * np.sqrt(ppy)
    downside = r[r < 0].std() * np.sqrt(ppy)
    mdd = max_drawdown(r)
    out = {
        "start": str(r.index[0].date()), "end": str(r.index[-1].date()), "years": round(yrs, 2),
        "cagr": round(float(cagr), 4), "vol": round(float(vol), 4),
        "sharpe": round(sharpe(r, ppy), 3),
        "sortino": round(float(r.mean() * ppy / downside), 3) if downside > 0 else None,
        "max_dd": round(mdd, 4),
        "calmar": round(float(cagr / -mdd), 3) if mdd < 0 else None,
        "psr0": round(psr(r), 4),
        "dsr": round(dsr(r, n_trials), 4),
        "n_trials": n_trials,
        "pos_months": round(float((r.resample("30D").sum() > 0).mean()), 3),
    }
    if gross is not None:
        out["avg_gross"] = round(float(gross.mean()), 3)
    if turnover is not None:
        out["turnover_yr"] = round(float(turnover.sum() / yrs), 1)
    if costs is not None:
        out["cost_yr"] = round(float(costs.sum() / yrs), 4)
    if funding is not None:
        out["funding_yr"] = round(float(funding.sum() / yrs), 4)
    return out
