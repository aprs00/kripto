"""Known-answer tests for the passive-execution model (T9)."""
import numpy as np
import pandas as pd
import pytest

from kripto import backtest as bt
from kripto.execution import maker_fills


def _hourly(path_after):
    """3 days of hourly bars at 100; the hours after day 0's close follow `path_after` (close=high=low)."""
    idx = pd.date_range("2025-01-01", periods=72, freq="1h", tz="UTC")
    c = pd.Series(100.0, idx)
    c.iloc[24:24 + len(path_after)] = path_after
    df = lambda s: pd.DataFrame({"A": s})
    return {"close": df(c), "high": df(c), "low": df(c)}


def test_buy_fills_on_trade_through_and_sell_does_not():
    daily = pd.date_range("2025-01-01", periods=3, freq="1D", tz="UTC")
    m = maker_fills(_hourly([100.0, 99.9, 99.0, 100.5]), daily, horizon_h=4, through=5e-4)
    # decision = close of the 2025-01-01 bar (hour 23 = 100); next 4 hours dip to 99.0 then 100.5
    assert m["fill_buy"].iloc[0, 0] == 1.0
    assert m["fill_sell"].iloc[0, 0] == 1.0            # 100.5 >= 100.05: the sell would fill too
    m = maker_fills(_hourly([100.01, 100.02, 100.03, 100.04]), daily, horizon_h=4, through=5e-4)
    assert m["fill_buy"].iloc[0, 0] == 0.0 and m["fill_sell"].iloc[0, 0] == 0.0   # never trades through either side
    assert m["drift"].iloc[0, 0] == pytest.approx(0.0004)
    m = maker_fills(_hourly([100.0, 99.0]), daily, horizon_h=1, through=5e-4)
    assert m["fill_buy"].iloc[0, 0] == 0.0             # the dip comes in hour 2, after a 1-hour horizon
    assert np.isnan(m["fill_buy"].iloc[-1, 0])         # no hourly bars after the last close


def test_backtest_charges_maker_fee_when_filled_and_drift_plus_taker_when_not():
    idx = pd.date_range("2025-01-01", periods=4, freq="1D", tz="UTC")
    close = pd.DataFrame({"A": [100.0, 100, 100, 100]}, idx)
    w = pd.DataFrame({"A": [1.0, np.nan, -1.0, np.nan]}, idx)     # buy 1.0 on day 0, sell 2.0 on day 2
    one = lambda v: pd.DataFrame({"A": [v] * 4}, idx)
    mk = {"fill_buy": one(1.0), "fill_sell": one(0.0), "drift": one(-0.01), "fee": 0.00015}
    r = bt.run(w, close, cost=0.0, fee=0.00045, maker=mk)
    assert r.costs.iloc[0] == pytest.approx(0.00015)                       # filled buy: maker fee
    assert r.costs.iloc[2] == pytest.approx(2 * (0.01 + 0.00045), rel=1e-3)  # unfilled sell after a 1% drop: sells 1% lower + taker
    r0 = bt.run(w, close, cost=0.0, fee=0.00045)
    assert r0.costs.iloc[0] == pytest.approx(0.00045)                      # default: taker everywhere
