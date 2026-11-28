"""T9W: the frozen maker-at-the-touch forward ledger, hand-computed on a toy set."""
import numpy as np
import pandas as pd

from scripts.maker_ledger import replay, score


def _bars(lo, hi, close_last):
    idx = pd.date_range("2026-12-01 04:00", periods=8, freq="4h", tz="UTC")
    return pd.DataFrame({"h": hi, "l": lo, "c": [100.0] * 6 + [close_last] * 2}, idx)   # the 24-h window from 04:10 ends with the 04:00 bar (index 6)


def test_filled_buy_and_unfilled_sell_hand_computed():
    ts = pd.Timestamp("2026-12-01 04:10", tz="UTC")
    fills = pd.DataFrame({"ts": [ts, ts], "coin": ["X", "Y"], "size": [1.0, -1.0], "px": [100.0, 100.0], "mid": [100.0, 100.0], "slip_bps": [1.0, 1.0]})
    bars = {"X": _bars(lo=99.9, hi=100.0, close_last=100.0),          # trades 10 bp through a buy at 100 -> filled
            "Y": _bars(lo=99.0, hi=100.02, close_last=99.0)}          # only 2 bp above a sell at 100 -> unfilled; it then falls 1 %
    d = replay(fills, bars).set_index("coin")
    assert np.isclose(d.at["X", "thru_bp"], 10.0) and np.isclose(d.at["Y", "thru_bp"], 2.0)
    assert np.isclose(d.at["Y", "move24"], 100.0)                    # the sell would have earned 100 bp
    s = score(d.reset_index())
    assert s["orders"] == 2 and np.isclose(s["fill_share_notional"], 0.5)
    assert np.isclose(s["net_bp_per_unit"], ((5 - 2 + 1) - (100 - 5 - 1)) / 2)   # (+4 - 94) / 2 = -45


def test_incomplete_window_and_first_bar_rule():
    ts = pd.Timestamp("2026-12-01 04:10", tz="UTC")
    fills = pd.DataFrame({"ts": [ts], "coin": ["X"], "size": [1.0], "px": [100.0], "mid": [100.0], "slip_bps": [0.0]})
    b = _bars(lo=100.0, hi=100.0, close_last=100.0)
    b.loc[pd.Timestamp("2026-12-01 04:00", tz="UTC"), "l"] = 99.0      # the dip is inside the order's own bar
    assert replay(fills, {"X": b}).iloc[0]["thru_bp"] == 0.0         # conservative: not counted
    assert np.isclose(replay(fills, {"X": b}, include_first=True).iloc[0]["thru_bp"], 100.0)
    assert replay(fills, {"X": b}, now=ts + pd.Timedelta(hours=10)).empty   # 24 h not complete yet
