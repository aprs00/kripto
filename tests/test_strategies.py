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


def _listing_panel(T=6 * 200, late_at=6 * 60):
    idx = pd.date_range("2024-01-01", periods=T, freq="4h", tz="UTC")
    rng = np.random.default_rng(1)
    close = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, (T, 3)), 0)), idx, ["BTC", "OLD", "NEW"])
    vol = pd.DataFrame(1e7, idx, close.columns)
    close.iloc[:late_at, 2] = np.nan
    vol.iloc[:late_at, 2] = 0.0
    return {"close": close, "volume": vol, "funding": pd.DataFrame(0.0, idx, close.columns),
            "high": close, "low": close}


def test_listing_short_only_shorts_new_listing_in_window_and_is_causal():
    from kripto.strategies import listing_short
    p = _listing_panel()
    w = listing_short(p, skip_days=1, hold_days=30, min_dv=0).ffill().fillna(0)
    assert (w["OLD"] == 0).all()                      # pre-existing coin never a listing event
    new = w["NEW"]
    assert (new <= 0).all() and (new < 0).any()
    first_short = new[new < 0].index.min()
    listed = p["close"]["NEW"].first_valid_index()
    assert listed + pd.Timedelta(days=1) <= first_short <= listed + pd.Timedelta(days=2)  # after skip_days
    assert new[new.index > listed + pd.Timedelta(days=32)].eq(0).all()  # exited after hold window
    cut = 6 * 100
    full = listing_short(p, min_dv=0)
    trunc = listing_short({k: v.iloc[:cut] for k, v in p.items()}, min_dv=0)
    pd.testing.assert_frame_equal(full.iloc[:cut].fillna(0), trunc.fillna(0), atol=1e-10)


def test_hl_loader_masks_pre_listing_zero_volume(tmp_path, monkeypatch):
    from kripto import data
    d = tmp_path / "hl" / "candles_1d"
    d.mkdir(parents=True)
    t = [1704067200000 + i * 86_400_000 for i in range(6)]  # explicit ms (never derive via asi8/astype: unit varies)
    df = pd.DataFrame({"t": t, "c": [1.0, 1, 1, 2, 3, 4], "v": [0.0, 0, 0, 5, 0, 5], "h": 1.0, "l": 1.0})
    df.to_parquet(d / "X.parquet")
    monkeypatch.setattr(data, "DATA", tmp_path)
    monkeypatch.setattr(data, "_hl_funding_panel", lambda idx, bar, coins: pd.DataFrame(index=idx, columns=coins))
    c = data.load_hl_panel("1d")["close"]["X"]
    assert c.iloc[:3].isna().all() and c.iloc[3:].tolist() == [2.0, 3.0, 4.0]  # later zero-vol bar kept
