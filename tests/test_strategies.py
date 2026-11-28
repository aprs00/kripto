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


# --------------------------------------------------------------------------- cross-venue (2026-11-10)
def _pair_panel(T=120):
    idx = pd.date_range("2025-01-01", periods=T, freq="1D", tz="UTC")
    rng = np.random.default_rng(7)
    cols = ["A@hl", "B@hl", "C@hl", "A@bn", "B@bn", "C@bn"]
    px = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, (T, 3)), 0))
    close = pd.DataFrame(np.hstack([px, px * (1 + rng.normal(0, 0.0005, (T, 3)))]), idx, cols)   # same asset, tiny basis
    fund = pd.DataFrame(0.0, idx, cols)
    fund["A@hl"] = 0.001                  # HL longs in A pay 0.1%/day more than on Binance = 36.5%/yr
    fund["B@bn"] = 0.001                  # the mirror case in B
    return {"close": close, "volume": pd.DataFrame(1e7, idx, cols), "funding": fund}


def test_fspread_shorts_the_expensive_venue_and_is_price_neutral_and_causal():
    from kripto import backtest as bt
    from kripto.strategies import fspread
    p = _pair_panel()
    w = fspread(p, lookback=7, thr=0.10, gross=2.0, max_pair=0.5)
    last = w.dropna(how="all").iloc[-1]
    assert last["A@hl"] < 0 and last["A@bn"] == pytest.approx(-last["A@hl"])      # short where longs pay more
    assert last["B@hl"] > 0 and last["B@bn"] == pytest.approx(-last["B@hl"])
    assert last["C@hl"] == 0 and last["C@bn"] == 0                                 # no spread, no position
    assert last.abs().sum() <= 2.0 + 1e-9 and abs(last.sum()) < 1e-12
    capped = fspread(p, lookback=7, thr=0.10, gross=2.0, max_pair=0.25).dropna(how="all").iloc[-1]
    assert capped.abs().max() == pytest.approx(0.25)
    res = bt.run(w, p["close"], p["funding"], fee=0.0)
    yr = res.funding.iloc[30:].mean() * 365
    assert yr == pytest.approx(0.365, rel=0.05)          # 1 unit per side earning 36.5%/yr of funding difference
    assert res.returns.iloc[30:].std() * np.sqrt(365) < 0.05                       # price risk cancels
    cut = 80
    trunc = fspread({k: v.iloc[:cut] for k, v in p.items()}, lookback=7, thr=0.10)
    pd.testing.assert_frame_equal(fspread(p, lookback=7, thr=0.10).iloc[:cut].fillna(0), trunc.fillna(0), atol=1e-12)


def test_flow_uses_the_flow_venue_volume_when_given():
    from kripto.strategies import flow
    T = 200
    idx = pd.date_range("2025-01-01", periods=T, freq="1D", tz="UTC")
    rng = np.random.default_rng(9)
    names = ["BTC"] + [f"C{i}" for i in range(7)]
    close = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.02, (T, 8)), 0)), idx, names)
    hl_vol = pd.DataFrame(1e6, idx, names)                       # traded venue: 10x thinner
    bn_vol = pd.DataFrame(1e7, idx, names)
    share = np.linspace(0.35, 0.65, 8)                           # C6 most bought, BTC most sold (on the flow venue)
    p = {"close": close, "volume": hl_vol, "funding": hl_vol * 0, "taker_buy": bn_vol * share, "flow_volume": bn_vol}
    last = flow(p, lookback=7, top_n=8, beta_neutral=False).dropna(how="all").iloc[-1]
    assert last.idxmax() == "C6" and last.idxmin() == "BTC"
    assert last.abs().max() < 1.0                                # imbalance measured against Binance volume, not HL's


def test_hl_to_bn_names():
    from kripto.data import hl_to_bn
    assert hl_to_bn("kPEPE") == "1000PEPE" and hl_to_bn("BTC") == "BTC" and hl_to_bn("kBONK") == "1000BONK"


def test_blend_nested_is_causal_and_trades_once_history_allows():
    """H4: component selection uses only returns up to the refit bar (short min_days so selection actually happens)."""
    from kripto import strategies as st
    from tests.test_backtest import _panel
    p = _panel(T=6 * 150)
    cut = 6 * 120
    kw = dict(min_days=30, refit_days=10)
    full = st.blend_nested(p, **kw)
    trunc = st.blend_nested({k: v.iloc[:cut] for k, v in p.items()}, **kw)
    assert full.iloc[:cut].abs().sum(axis=1).max() > 0
    pd.testing.assert_frame_equal(full.iloc[:cut].fillna(0), trunc.fillna(0), check_exact=False, atol=1e-10)


def test_fspread_hold_opens_on_a_wide_spread_holds_through_a_narrow_one_and_exits_on_the_flip():
    from kripto.strategies import fspread_hold
    p = _pair_panel(T=160)
    f = p["funding"]
    f.loc[f.index[60]:, "A@hl"] = 0.0002          # spread narrows to 7.3%/yr: below `enter`, still positive -> hold
    f.loc[f.index[100]:, "A@hl"] = -0.0005        # spread flips sign -> exit (and re-open the other way once wide)
    w = fspread_hold(p, lookback=7, enter=0.20, max_pair=0.1, gross=2.0).ffill()
    a = w["A@hl"]
    assert a.iloc[30] == pytest.approx(-0.1) and w["A@bn"].iloc[30] == pytest.approx(0.1)   # short HL, long Binance
    assert w["B@hl"].iloc[30] == pytest.approx(0.1)                                         # mirror pair
    assert w["C@hl"].iloc[30] == 0
    assert (a.iloc[30:100] == -0.1).all()                                                   # hysteresis: held while 7%/yr > 0
    assert a.iloc[110] == 0                                                                 # the 7-day mean flipped sign: closed
    assert a.iloc[-1] == 0                                                                  # -18%/yr never exceeds enter=20%
    cut = 90
    trunc = fspread_hold({k: v.iloc[:cut] for k, v in p.items()}, lookback=7)
    pd.testing.assert_frame_equal(fspread_hold(p, lookback=7).iloc[:cut].fillna(0), trunc.fillna(0), atol=1e-12)


def test_fractional_every_days_decides_intraday_never_finer_than_a_bar():
    from kripto import strategies as st
    p = _listing_panel()                         # 4h bars
    raw = pd.DataFrame(0.0, p["close"].index, p["close"].columns)
    raw["BTC"], raw["OLD"] = 0.5, -0.5
    rows = lambda w: int(w.notna().any(axis=1).sum())
    daily, four_h, hourly = (st.scheduled(raw, p, e, 0.2) for e in (1, 1 / 6, 1 / 24))
    assert rows(four_h) == len(raw) and rows(hourly) == len(raw)      # every bar; 1h on 4h bars cannot go below a bar
    assert rows(daily) == pytest.approx(len(raw) / 6, abs=1)
    pd.testing.assert_frame_equal(st.scheduled(raw, p, 1, 0.2), st.vol_target(st.rebalance_rows(raw, 6), p, 0.2))


def test_partial_path_known_answer_and_blend_slow_legs():
    """PRB2: a step target 0 -> 1 is approached as 1 - (1 - lam)^k; lam 1 = unchanged; slow_lam is causal in blend_nested."""
    from kripto import strategies as st
    idx = pd.date_range("2024-01-01", periods=4, freq="1D", tz="UTC")
    w = pd.DataFrame({"A": [1.0, 1.0, 1.0, 0.0]}, idx)
    out = st.partial_path(w, 0.5)["A"].tolist()
    assert np.allclose(out, [0.5, 0.75, 0.875, 0.4375])
    assert np.allclose(st.partial_path(w, 1.0)["A"], w["A"])
    h = pd.DataFrame({"A": np.ones(18)}, pd.date_range("2024-01-01", periods=18, freq="4h", tz="UTC"))
    assert np.allclose(st.partial_path(h, 0.5, bpd=6)["A"].iloc[[5, 11, 17]], [0.5, 0.75, 0.875])   # 4h bars, same daily speed
    from tests.test_backtest import _panel
    p = _panel(T=6 * 150)
    cut = 6 * 120
    kw = dict(min_days=30, refit_days=10, slow_lam=0.33, slow_legs=("tsmom", "lowvol", "xsmom"))
    full = st.blend_nested(p, **kw)
    trunc = st.blend_nested({k: v.iloc[:cut] for k, v in p.items()}, **kw)
    pd.testing.assert_frame_equal(full.iloc[:cut].fillna(0), trunc.fillna(0), check_exact=False, atol=1e-10)
    base = st.blend_nested(p, min_days=30, refit_days=10)
    assert (full.fillna(0) - base.fillna(0)).abs().max().max() > 1e-6   # not inert (turnover is checked on real data in the WF)


def test_flow_fund_resid_removes_the_funding_sort_and_default_is_unchanged():
    """FLX2 arm (iii): imbalance = funding sort + an independent part; fund_resid ranks by the independent part only."""
    from kripto.strategies import flow
    idx = pd.date_range("2024-01-01", periods=120, freq="1D", tz="UTC")
    cols = ["BTC"] + [f"C{i}" for i in range(9)]
    rng = np.random.default_rng(3)
    close = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.02, (120, 10)), 0)), idx, cols)
    vol = pd.DataFrame(1e7, idx, cols)
    fr = np.linspace(-1e-3, 1e-3, 10)
    z = np.array([3, -1, 4, -1, -5, 9, -2, 6, -5, 3], float) * 1e-3
    z = z - fr * (z @ fr) / (fr @ fr) - z.mean()                  # independent of the funding sort
    fund = pd.DataFrame(np.tile(fr, (120, 1)), idx, cols)
    tb = vol * (0.5 + 100 * fund + pd.DataFrame(np.tile(z, (120, 1)), idx, cols))
    p = {"close": close, "volume": vol, "funding": fund, "taker_buy": tb}
    w0 = flow(p, lookback=3, top_n=10, beta_neutral=False).dropna(how="all").iloc[-1]
    w1 = flow(p, lookback=3, top_n=10, beta_neutral=False, fund_resid=True).dropna(how="all").iloc[-1]
    assert np.corrcoef(w0.to_numpy(), fr)[0, 1] > 0.8 and abs(np.corrcoef(w1.to_numpy(), fr)[0, 1]) < 0.2
    assert np.corrcoef(w1.to_numpy(), z)[0, 1] > 0.9
    pd.testing.assert_series_equal(w0, flow(p, lookback=3, top_n=10, beta_neutral=False, fund_resid=False).dropna(how="all").iloc[-1])
