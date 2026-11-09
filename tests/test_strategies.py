"""Regression: rebalance grid must be correct for any datetime unit (pandas 3 loads parquet as us)."""
import numpy as np
import pandas as pd
import pytest

from kripto.strategies import rebalance_rows


@pytest.mark.parametrize("unit", ["ns", "us", "ms", "s"])
@pytest.mark.parametrize("every", [1, 6, 18])
def test_rebalance_rows_grid(unit, every):
    idx = pd.date_range("2024-01-01", periods=200, freq="4h", tz="UTC").as_unit(unit)
    w = pd.DataFrame(1.0, index=idx, columns=["A", "B"])
    out = rebalance_rows(w, every)
    kept = out.index[out.notna().all(axis=1)]
    assert out.notna().all(axis=1).sum() == out.notna().any(axis=1).sum()  # whole rows only
    hours = ((kept - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(hours=4))
    assert len(kept) in (200 // every, 200 // every + 1)
    assert (np.asarray(hours) % every == 0).all()
    if every == 6:  # daily grid on 4h bars = the 00:00 UTC bar
        assert (kept.hour == 0).all()
