"""T6S: T6b's frozen signal / IC code, hand-computed."""
import numpy as np
import pandas as pd
import pytest

from research.studies.is3_t6b import signal_x, signal_dx, daily_ic, guard


def _pos(rows):
    d = pd.DataFrame(rows, columns=["ts", "user", "coin", "szi", "value"])
    d["t"] = pd.to_datetime(d.ts, unit="s", utc=True)
    return d


def test_x_and_dx_by_hand():
    day0, day1 = pd.Timestamp("2026-12-01", tz="UTC").timestamp(), pd.Timestamp("2026-12-02", tz="UTC").timestamp()
    rows = []
    for t in (day0, day1):
        rows += [(t, "a", "C", 1, 100.0), (t, "b", "C", 1, 100.0), (t, "c", "C", -1, 200.0 if t == day0 else 100.0)]
    x = signal_x(_pos(rows))
    assert np.isclose(x.loc[pd.Timestamp("2026-12-01", tz="UTC"), "C"], 0.0)          # (100+100-200)/400
    assert np.isclose(x.loc[pd.Timestamp("2026-12-02", tz="UTC"), "C"], 100 / 300)
    dx = signal_dx(_pos(rows))
    # c: sv -200 -> -100 (+100); avg values a 100, b 100, c 150 -> 350
    assert np.isclose(dx.loc[pd.Timestamp("2026-12-02", tz="UTC"), "C"], 100 / 350)
    rows2 = [r for r in rows if r[1] != "b"]                                             # only 2 accounts: dropped
    assert signal_x(_pos(rows2)).empty


def test_ic_and_guards():
    idx = pd.DatetimeIndex([pd.Timestamp("2026-12-01", tz="UTC")])
    x = pd.DataFrame([np.arange(10.0)], idx, list("ABCDEFGHIJ"))
    assert np.isclose(daily_ic(x, x * 2).iloc[0], 1.0) and np.isclose(daily_ic(x, -x).iloc[0], -1.0)
    with pytest.raises(SystemExit):
        guard("explore", pd.Timestamp("2026-12-07", tz="UTC"))
    guard("explore", pd.Timestamp("2026-12-09", tz="UTC"))
    with pytest.raises(SystemExit):
        guard("confirm", pd.Timestamp("2027-01-15", tz="UTC"))
