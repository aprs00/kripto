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


def test_xsmom_k_longs_winners_shorts_losers():
    """Known answer: 8 coins with fixed drifts; k=2 must long the 2 strongest and short the 2 weakest."""
    from kripto.strategies import xsmom_k
    T = 6 * 200
    idx = pd.date_range("2024-01-01", periods=T, freq="4h", tz="UTC")
    rng = np.random.default_rng(3)
    drift = np.linspace(-0.002, 0.002, 8)
    names = ["BTC"] + [f"C{i}" for i in range(7)]
    close = pd.DataFrame(100 * np.exp(np.cumsum(drift + rng.normal(0, 0.003, (T, 8)), 0)), idx, names)
    p = {"close": close, "volume": pd.DataFrame(1e7, idx, names), "funding": pd.DataFrame(0.0, idx, names)}
    w = xsmom_k(p, lookback=28, k=2, every_days=1, beta_neutral=False)
    last = w.dropna(how="all").iloc[-1]
    assert set(last[last > 0].index) == {"C5", "C6"}
    assert set(last[last < 0].index) == {"BTC", "C0"}
    assert (last != 0).sum() == 4


def test_blend_is_mean_of_rescaled_components():
    from kripto import strategies as st
    p = _listing_panel()
    comps = {"listing_short": {"skip_days": 1, "hold_days": 30, "min_dv": 0}}
    w = st.blend(p, components=comps, target_vol=0.2, unit_vol=0.2)
    nz = w.dropna(how="all")
    assert (nz["NEW"] <= 0).all() and (nz["NEW"] < 0).any()


def test_resrev_fades_an_idiosyncratic_spike_and_ignores_btc():
    from kripto import strategies as st
    rng = np.random.default_rng(1)
    T = 24 * 120
    idx = pd.date_range("2024-01-01", periods=T, freq="4h", tz="UTC")
    r = rng.normal(0, 0.01, (T, 4))
    k = int(np.flatnonzero(idx.hour == 0)[-1])  # last daily rebalance bar
    r[k - 2:k + 1, 1] += 0.08  # coin A jumps on its own in the 3 bars up to that rebalance
    close = pd.DataFrame(100 * np.exp(np.cumsum(r, 0)), idx, ["BTC", "A", "B", "C"])
    vol = pd.DataFrame(1e7, idx, close.columns)
    p = {"close": close, "volume": vol, "funding": vol * 0, "high": close, "low": close}
    w = st.resrev(p, lookback=1, thr=1.5, every_days=1).dropna(how="all")
    last = w.iloc[-1]
    assert last["A"] < 0 and abs(last["A"]) == last.drop("BTC").abs().max()


# --------------------------------------------------------------------------- staggered tranches (2026-11-09 review, H1)
def _daily_targets(days=12, bpd=6):
    idx = pd.date_range("2024-01-01", periods=days * bpd, freq="4h", tz="UTC")
    w = pd.DataFrame(np.nan, idx, ["A", "B"])
    daily = idx[idx.hour == 0]
    w.loc[daily, "A"] = np.arange(1.0, days + 1)      # day d (1-based) targets A = d
    w.loc[daily, "B"] = -1.0
    return w, daily


def test_tranche_mean_known_answer():
    from kripto.strategies import tranche_mean
    w, daily = _daily_targets()
    out = tranche_mean(w, 3)
    assert out.loc[~out.index.isin(daily)].isna().all().all()           # still only trades on rebalance rows
    a = out.loc[daily, "A"].tolist()
    assert a[:4] == pytest.approx([1 / 3, (1 + 2) / 3, 2.0, 3.0])       # ramps in, then mean of the last 3 days
    assert out.loc[daily, "B"].tolist()[2:] == pytest.approx([-1.0] * (len(daily) - 2))


def test_tranches_equal_the_average_of_all_schedule_phases():
    """The tranche book must hold, on every day, the mean of what the n single-phase schedules hold."""
    from kripto.strategies import rebalance_rows, tranche_mean
    w, daily = _daily_targets(days=20)
    n, bpd = 4, 6
    phases = [rebalance_rows(w, n * bpd, offset=k * bpd).loc[daily].ffill().fillna(0.0) for k in range(n)]
    want = sum(phases) / n
    got = tranche_mean(rebalance_rows(w, bpd), n).loc[daily]
    pd.testing.assert_frame_equal(got, want, check_exact=False, atol=1e-12)


def test_scheduled_phase0_is_the_legacy_single_schedule_and_default_is_tranched():
    from kripto import strategies as st
    p = _listing_panel()
    raw = pd.DataFrame(0.0, p["close"].index, p["close"].columns)
    raw["BTC"], raw["OLD"] = 0.5, -0.5
    legacy = st.vol_target(st.rebalance_rows(raw, 3 * 6), p, 0.2)
    pd.testing.assert_frame_equal(st.scheduled(raw, p, 3, 0.2, phase=0), legacy)
    tr = st.scheduled(raw, p, 3, 0.2)
    assert tr.notna().any(axis=1).sum() == pytest.approx(3 * legacy.notna().any(axis=1).sum(), abs=3)  # trades daily
    one = st.scheduled(raw, p, 1, 0.2)                 # every_days=1: nothing to stagger
    pd.testing.assert_frame_equal(one, st.vol_target(st.rebalance_rows(raw, 6), p, 0.2))


@pytest.mark.parametrize("name", ["xsmom", "xsmom_k", "lowvol", "tsmom"])
def test_strategy_phase_argument_moves_the_rebalance_day(name):
    from kripto import strategies as st
    T = 6 * 150
    idx = pd.date_range("2024-01-01", periods=T, freq="4h", tz="UTC")
    rng = np.random.default_rng(5)
    names = ["BTC"] + [f"C{i}" for i in range(9)]
    close = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, (T, 10)), 0)), idx, names)
    p = {"close": close, "volume": pd.DataFrame(1e7, idx, names), "funding": pd.DataFrame(0.0, idx, names)}
    kw = {"k": 2} if name == "xsmom_k" else {}
    days = lambda w: set((w.dropna(how="all").index - pd.Timestamp(0, tz="UTC")).days % 3)
    assert days(st.REGISTRY[name](p, every_days=3, phase=0, **kw)) == {0}
    assert days(st.REGISTRY[name](p, every_days=3, phase=2, **kw)) == {2}
    assert days(st.REGISTRY[name](p, every_days=3, **kw)) == {0, 1, 2}     # default: tranches, some trade every day
