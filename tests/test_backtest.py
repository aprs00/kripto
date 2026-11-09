import numpy as np
import pandas as pd
import pytest

from kripto import backtest as bt
from kripto import strategies as st


def _panel(T=24 * 200, N=4, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=T, freq="4h", tz="UTC")
    r = rng.normal(0, 0.01, (T, N))
    close = pd.DataFrame(100 * np.exp(np.cumsum(r, 0)), idx, ["BTC", "A", "B", "C"])
    vol = pd.DataFrame(1e7, idx, close.columns)
    fund = pd.DataFrame(1e-5, idx, close.columns)
    tb = vol * pd.DataFrame(rng.uniform(0.3, 0.7, (T, N)), idx, close.columns)  # taker-bought share
    return {"close": close, "volume": vol, "funding": fund, "high": close, "low": close, "taker_buy": tb}


def test_constant_long_matches_buy_and_hold_without_costs():
    p = _panel()
    w = pd.DataFrame(0.0, p["close"].index, p["close"].columns)
    w["BTC"] = 1.0
    res = bt.run(w, p["close"], fee=0.0)
    bh = p["close"]["BTC"].iloc[-1] / p["close"]["BTC"].iloc[0]
    assert res.equity.iloc[-1] == pytest.approx(bh, rel=1e-9)


def test_fee_charged_once_on_entry():
    p = _panel()
    w = pd.DataFrame(np.nan, p["close"].index, p["close"].columns)
    w.iloc[0] = [1.0, 0, 0, 0]
    res = bt.run(w, p["close"], fee=0.001)
    assert res.costs.sum() == pytest.approx(0.001)


def test_long_pays_positive_funding():
    p = _panel()
    flat = pd.DataFrame(100.0, p["close"].index, p["close"].columns)
    w = pd.DataFrame(0.0, flat.index, flat.columns)
    w["A"] = 1.0
    res = bt.run(w, flat, p["funding"], fee=0.0)
    assert res.funding.iloc[5] == pytest.approx(-1e-5)
    w["A"] = -1.0
    res = bt.run(w, flat, p["funding"], fee=0.0)
    assert res.funding.iloc[5] == pytest.approx(1e-5)


def test_no_lookahead_perfect_foresight_signal_is_not_rewarded():
    """A weight equal to the NEXT bar's return sign must earn ~0 if shifted correctly;
    a weight built from the CURRENT bar's return (known at close) must not equal foresight."""
    p = _panel()
    r = p["close"].pct_change()
    cheat = np.sign(r.shift(-1)).fillna(0)       # uses the future
    honest = np.sign(r).fillna(0)                # uses the present
    eq_cheat = bt.run(cheat, p["close"], fee=0).equity.iloc[-1]
    r_honest = bt.run(honest / 4, p["close"], fee=0).returns
    tstat = r_honest.mean() / r_honest.std() * np.sqrt(len(r_honest))
    assert eq_cheat > 50          # the engine does reward foresight if you feed it the future...
    assert abs(tstat) < 3         # ...and a signal from the present earns nothing on a random walk


@pytest.mark.parametrize("name", list(st.REGISTRY))
def test_strategies_do_not_use_future_data(name):
    """Weights at time t must be identical whether or not data after t exists."""
    p = _panel(T=6 * 150)
    cut = 6 * 120
    full = st.REGISTRY[name](p)
    trunc = st.REGISTRY[name]({k: v.iloc[:cut] for k, v in p.items()})
    a, b = full.iloc[:cut].fillna(0), trunc.fillna(0)
    pd.testing.assert_frame_equal(a, b, check_exact=False, atol=1e-10)
