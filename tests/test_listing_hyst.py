"""Known answer for listing_short's liquidity hysteresis (T2b(e), 2026-11-19)."""
import numpy as np
import pandas as pd

from kripto import strategies as st


def _panel():
    idx = pd.date_range("2024-01-01", periods=120, freq="1D", tz="UTC")
    c = pd.DataFrame({"OLD": 100.0, "NEW": 50.0}, idx)
    v = pd.DataFrame({"OLD": 5e7, "NEW": np.nan}, idx)
    # NEW lists on day 40; volume 1.2M for 10 days, then 0.7M (below min_dv 1M, above stay 0.5M), then 0.3M
    v.iloc[40:50, 1], v.iloc[50:70, 1], v.iloc[70:, 1] = 1.2e6, 0.7e6, 0.3e6
    c.loc[c.index < idx[40], "NEW"] = np.nan
    rng = np.random.default_rng(0)
    c = c * np.exp(np.cumsum(rng.normal(0, 0.02, c.shape), axis=0))
    return {"close": c, "volume": v}


def _short_days(**kw):
    w = st.REGISTRY["listing_short"](_panel(), beta_neutral=False, hold_days=60, **kw)
    return set(np.flatnonzero(w["NEW"].fillna(0).to_numpy() < 0))


def test_hysteresis_keeps_position_between_thresholds():
    base, hyst = _short_days(), _short_days(stay_mult=0.5)
    assert base and hyst > base                                         # hysteresis holds longer
    assert not any(d >= 56 for d in base)                                # base exits once 7-d dv < 1M (≈ day 53)
    assert any(60 <= d < 70 for d in hyst) and not any(d >= 76 for d in hyst)   # stays at 0.7M, leaves at 0.3M
    assert _short_days(enter_mult=2.0) == set()                          # never reached 2M: never entered
