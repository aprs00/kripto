"""LVB (2026-11-28): the main-book replay blends entries exactly as paper.run_books does."""
import numpy as np
import pandas as pd

from scripts.live_vs_backtest import main_targets

IDX = pd.date_range("2026-11-01", periods=4, freq="4h", tz="UTC")


def test_one_entry_alloc_one_is_the_entry_itself_where_it_has_rows():
    w = pd.DataFrame({"A": [np.nan, .2, .3, .1], "B": [np.nan, -.2, np.nan, .1]}, IDX)
    m = main_targets([(1.0, w)], 1.0)
    assert m.iloc[0].isna().all()                       # flat until the first produced row
    assert np.allclose(m.iloc[1:].to_numpy(), w.iloc[1:].fillna(0.0).to_numpy(), atol=1e-12)   # NaN in a produced row = 0, not carried


def test_blend_keeps_the_last_saved_row_of_an_entry_that_produced_none_and_scales():
    a = pd.DataFrame({"A": [.2, .4, np.nan, np.nan]}, IDX)          # entry a produces nothing on bars 2-3 (e.g. a daily schedule)
    b = pd.DataFrame({"B": [np.nan, -.2, -.4, -.6]}, IDX)
    m = main_targets([(.5, a), (.5, b)], 2.0)
    assert np.allclose(m["A"].to_numpy(), [.2, .4, .4, .4])             # 2 x .5 x last saved .4
    assert np.allclose(m["B"].to_numpy(), [0, -.2, -.4, -.6])
