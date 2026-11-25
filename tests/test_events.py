"""Known-answer tests for the intraday order engine, the trade-size buckets and the InSilico strategies (2026-11-11)."""
import json

import numpy as np
import pandas as pd
import pytest

from kripto import events as ev
from kripto import research, tsize
from kripto import strategies as st


# --------------------------------------------------------------------------- trade-size buckets
def test_bucket_trades_puts_notional_in_the_right_bin_bar_and_side():
    d0 = 1_700_000_000_000
    price = np.array([100.0, 100.0, 100.0, 100.0])
    qty = np.array([5.0, 500.0, 10_000.0, 300.0])            # 500, 50k, 1M, 30k USD
    t = d0 + np.array([0, 300_000, 300_001, 86_399_999])     # bars 0, 1, 1, 287
    maker = np.array([False, True, False, True])             # buyer is maker = taker SELL
    buy, sell, n = tsize.bucket_trades(price, qty, t, maker, d0)
    assert buy.shape == (288, 12)
    assert buy[0, 0] == 500 and sell[1, 5] == 50_000 and buy[1, 11] == 1_000_000 and sell[287, 5] == 30_000
    assert buy.sum() == 1_000_500 and sell.sum() == 80_000 and n.sum() == 4 and n[1].sum() == 2


def test_group_and_one_voiced():
    d = np.zeros((3, 12))
    v = np.ones((3, 12))
    d[0] = -1.0                                   # every bin negative
    d[1] = -1.0
    d[1, 7] = 5.0                                 # one bucket positive -> mixed
    d[2] = 1.0
    g, gv = tsize.group(d, "author7"), tsize.group(v, "author7")
    assert g.shape == (3, 7) and g[0, 0] == -5 and gv[0, 6] == 2
    assert list(tsize.one_voiced(g, gv)) == [-1, 0, 1]
    # an empty bucket, or one below min_share, has no vote
    v2 = v.copy()
    v2[1, 7] = 0.0
    assert tsize.one_voiced(tsize.group(d, "author7"), tsize.group(v2, "author7"))[1] == -1
    v3 = v.copy() * 100
    v3[1, 7] = 1.0
    assert tsize.one_voiced(tsize.group(d, "author7"), tsize.group(v3, "author7"), 0.05)[1] == -1
    assert tsize.one_voiced(tsize.group(d, "author7"), tsize.group(v3, "author7"), 0.0)[1] == 0


# --------------------------------------------------------------------------- order engine
def _bars(rows):
    """rows: (open, high, low, close) for one coin -> (T,1) arrays + zero slippage."""
    a = np.array(rows, dtype=float)
    return a[:, [0]], a[:, [1]], a[:, [2]], a[:, [3]], np.zeros((len(a), 1))


def test_market_entry_two_targets_costs():
    o, h, l, c, slip = _bars([(100, 100, 100, 100)] * 3 + [(100, 101.5, 100, 101), (101, 102.5, 101, 102)] + [(102, 102, 102, 102)] * 3)
    it = {"coin": 0, "t": 2, "side": 1, "limit": None, "ttl": 0, "targets": [(101.0, 0.5), (102.0, 0.5)], "stop": 99.0, "hold": 5}
    (tr,) = ev.simulate([it], o, h, l, c, slip)
    assert (tr["t_in"], tr["t_out"]) == (2, 4)
    assert tr["gross"] == pytest.approx(0.5 * 0.01 + 0.5 * 0.02)
    assert tr["cost"] == pytest.approx(ev.FEE_TAKER + ev.FEE_MAKER)          # taker in, two maker halves out
    (tr2,) = ev.simulate([dict(it, targets=[(101.0, 0.5), (102.0, 0.5)])], o, h, l, c, slip + 1e-4, cost_mult=2.0)
    assert tr2["cost"] == pytest.approx(2 * (ev.FEE_TAKER + 1e-4) + 2 * ev.FEE_MAKER)


def test_stop_wins_when_a_bar_touches_both_and_gaps_fill_at_the_open():
    o, h, l, c, slip = _bars([(100, 100, 100, 100)] * 3 + [(100, 103, 98, 100)] + [(100, 100, 100, 100)] * 2)
    it = {"coin": 0, "t": 2, "side": 1, "limit": None, "ttl": 0, "targets": [(101.0, 1.0)], "stop": 99.0, "hold": 3}
    (tr,) = ev.simulate([it], o, h, l, c, slip)
    assert tr["gross"] == pytest.approx(-0.01) and tr["cost"] == pytest.approx(2 * ev.FEE_TAKER)
    o, h, l, c, slip = _bars([(100, 100, 100, 100)] * 3 + [(97, 97.5, 96, 97)] + [(97, 97, 97, 97)] * 2)
    (tr,) = ev.simulate([dict(it, targets=[(101.0, 1.0)])], o, h, l, c, slip)
    assert tr["gross"] == pytest.approx(-0.03)                               # gapped through the stop: filled at the open


def test_limit_needs_a_trade_through_and_cannot_take_profit_in_the_fill_bar():
    it = {"coin": 0, "t": 1, "side": 1, "limit": 100.0, "ttl": 3, "targets": [(100.5, 1.0)], "stop": 99.0, "hold": 3}
    # touch only (low == limit): no fill, nothing traded
    o, h, l, c, slip = _bars([(101, 101, 101, 101)] * 2 + [(101, 101, 100.0, 100.5)] * 3 + [(101, 101, 101, 101)] * 3)
    assert ev.simulate([dict(it)], o, h, l, c, slip) == []
    # trade-through in bar 2, whose high is above the target: the target fills only from bar 3 on
    o, h, l, c, slip = _bars([(101, 101, 101, 101)] * 2 + [(101, 101, 99.9, 100.2), (100.2, 100.3, 100.1, 100.2), (100.2, 100.8, 100.2, 100.6)]
                             + [(100.6, 100.6, 100.6, 100.6)] * 3)
    (tr,) = ev.simulate([dict(it)], o, h, l, c, slip)
    assert (tr["t_in"], tr["t_out"]) == (2, 4)
    assert tr["gross"] == pytest.approx(0.005) and tr["cost"] == pytest.approx(2 * ev.FEE_MAKER)
    # a fill bar that also reaches the stop is a stopped trade
    o, h, l, c, slip = _bars([(101, 101, 101, 101)] * 2 + [(101, 101, 98.5, 100.2)] + [(100.2, 100.2, 100.2, 100.2)] * 4)
    (tr,) = ev.simulate([dict(it)], o, h, l, c, slip)
    assert tr["t_out"] == 2 and tr["gross"] == pytest.approx(-0.01) and tr["cost"] == pytest.approx(ev.FEE_MAKER + ev.FEE_TAKER)


def test_time_exit_short_side_lag_and_one_position_per_coin():
    rows = [(100, 100, 100, 100)] * 3 + [(100, 100, 99.5, 99.5), (99.5, 99.5, 99, 99), (99, 99, 98, 98)] + [(98, 98, 98, 98)] * 4
    o, h, l, c, slip = _bars(rows)
    it = {"coin": 0, "t": 2, "side": -1, "limit": None, "ttl": 0, "targets": [], "stop": 101.0, "hold": 2}
    (tr,) = ev.simulate([dict(it)], o, h, l, c, slip)
    assert tr["t_out"] == 4 and tr["gross"] == pytest.approx(0.01)           # short 100 -> close of bar 4 = 99
    (lagged,) = ev.simulate([dict(it)], o, h, l, c, slip, lag=1)
    assert lagged["t_in"] == 3 and lagged["gross"] == pytest.approx(1 - 98 / 99.5)
    two = ev.simulate([dict(it), dict(it, t=3)], o, h, l, c, slip)
    assert len(two) == 1                                                     # the second signal arrives while in the trade
    o2, h2, l2, c2, s2 = (np.hstack([x, x]) for x in (o, h, l, c, slip))
    both = ev.simulate([dict(it), dict(it, coin=1)], o2, h2, l2, c2, s2, max_open=1)
    assert len(both) == 1                                                    # book-level cap on open trades


def test_to_result_books_pnl_on_the_exit_day_scaled_by_size():
    idx = pd.date_range("2024-01-01", periods=3 * 1440, freq="1min", tz="UTC")
    trades = [{"coin": 0, "t_in": 100, "t_out": 160, "side": 1, "gross": 0.01, "cost": 0.001},
              {"coin": 0, "t_in": 1430, "t_out": 1450, "side": 1, "gross": -0.02, "cost": 0.001}]
    res = ev.to_result(trades, idx, size=0.5)
    assert list(res.returns.round(6)) == [0.0045, -0.0105, 0.0]
    assert res.costs.sum() == pytest.approx(0.001) and res.turnover.iloc[0] == 1.0
    assert res.gross.iloc[0] == pytest.approx(0.5 * 61 / 1440)
    assert ev.to_result(trades, idx, size=0.02, band=0.05).returns.abs().sum() == 0     # below the minimum order
    assert ev.to_result([], idx, size=0.5).returns.abs().sum() == 0


# --------------------------------------------------------------------------- event strategies
def _minute_panel(T=4000, seed=5, cols=("BTC", "ETH")):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=T, freq="1min", tz="UTC")
    c = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.0006, (T, len(cols))), 0)), idx, list(cols))
    span = pd.DataFrame(np.abs(rng.normal(0, 0.0005, c.shape)), idx, c.columns)
    return {"close": c, "high": c * (1 + span), "low": c * (1 - span),
            "volume": pd.DataFrame(rng.lognormal(11, 0.6, c.shape), idx, c.columns)}


def test_lshock_finds_the_planted_pattern_and_trades_it_as_specified():
    p = _minute_panel()
    c, h, l, v = (p[k]["BTC"].copy() for k in ("close", "high", "low", "volume"))
    t = 3000
    base = float(c.iloc[t - 2])
    c.iloc[t - 1], l.iloc[t - 1], h.iloc[t - 1], v.iloc[t - 1] = base * 0.97, base * 0.968, base, v.iloc[:t].mean() * 50   # dump
    c.iloc[t], l.iloc[t], h.iloc[t], v.iloc[t] = base * 0.972, base * 0.969, base * 0.973, v.iloc[:t].mean() * 20          # weak bounce
    after = base * np.array([0.975, 0.98, 0.99, 1.002] + [1.002] * 200)
    c.iloc[t + 1:t + 1 + len(after)] = after
    h.iloc[t + 1:t + 1 + len(after)] = after * 1.0005
    l.iloc[t + 1:t + 1 + len(after)] = after * 0.9995
    c.iloc[t + 1 + len(after):] = base * 1.002
    h.iloc[t + 1 + len(after):], l.iloc[t + 1 + len(after):] = base * 1.0025, base * 1.0015
    for k, x in (("close", c), ("high", h), ("low", l), ("volume", v)):
        p[k]["BTC"] = x
    res = ev.lshock(p, z=4, m=5, e=0.05)
    tr = res.trades[res.trades.t_in == t]
    assert len(tr) == 1
    origin, low, entry = float(p["high"]["BTC"].iloc[t - 10:t].max()), base * 0.968, base * 0.972
    mid = low + 0.5 * (origin - low)
    assert tr.gross.iloc[0] == pytest.approx(0.5 * (mid / entry - 1) + 0.5 * (origin / entry - 1), rel=1e-6)
    at = lambda r: 0 if r.trades.empty else int((r.trades.t_in == t).sum())
    assert at(ev.lshock(p, z=4, m=5, e=1.0)) == 0        # the bounce does not engulf the dump bar
    assert at(ev.lshock(p, z=4, m=100, e=0.05)) == 0     # volume condition


@pytest.mark.parametrize("name,kw", [("lshock", {"z": 2, "m": 1.5, "e": 0.3, "side": "both"}),
                                     ("range_retest", {"n": 15, "tight": 1.0}), ("mousetrap", {"n": 24, "vol_mult": 1.0})])
def test_event_strategies_do_not_use_future_data(name, kw):
    p = _minute_panel(T=6000)
    rng = np.random.default_rng(1)
    p["d_small"] = pd.DataFrame(rng.normal(0, 1, p["close"].shape), p["close"].index, p["close"].columns)
    p["d_large"] = -p["d_small"]
    cut = 4500
    full = ev.EVENTS[name](p, **kw).trades
    part = ev.EVENTS[name]({k: x.iloc[:cut] for k, x in p.items()}, **kw).trades
    assert len(part) > 3
    keep = lambda d: d[d.t_out < cut - 100][["coin", "t_in", "t_out", "side", "gross", "cost"]].reset_index(drop=True)
    pd.testing.assert_frame_equal(keep(full), keep(part))


def test_evaluate_runs_an_event_strategy_and_logs_it(tmp_path, monkeypatch):
    monkeypatch.setattr(research, "REG", tmp_path / "registry.jsonl")
    p = _minute_panel(T=6000)
    res, s = research.evaluate("range_retest", p, {"n": 15, "tight": 1.0}, "toy_1m")
    res2, s2 = research.evaluate("range_retest", p, {"n": 15, "tight": 1.0}, "toy_1m", cost_mult=2.0, tag="robust")
    assert len(res.trades) > 3 and res2.costs.sum() == pytest.approx(2 * res.costs.sum())
    lines = [json.loads(x) for x in (tmp_path / "registry.jsonl").read_text().splitlines()]
    assert lines[0]["strategy"] == "range_retest" and lines[1]["cost_mult"] == 2.0


# --------------------------------------------------------------------------- daily / hourly strategies
def test_tsize_capit_goes_long_after_an_all_negative_day_and_only_then():
    idx = pd.date_range("2024-01-01", periods=30, freq="1D", tz="UTC")
    coins = ["BTC", "ETH"]
    close = pd.DataFrame(100.0, idx, coins)
    cols = pd.MultiIndex.from_product([coins, range(12)])
    d = pd.DataFrame(1.0, idx, cols)
    d.loc[:, ("BTC", 3)] = -1.0                      # one negative bin per coin: every day is mixed ...
    d.loc[:, ("ETH", 0)] = -1.0
    d.iloc[10] = -1.0                                # ... except day 10: every bin of both coins negative
    p = {"close": close, "volume": close * 1e6, "ts_delta": d, "ts_vol": pd.DataFrame(1.0, idx, cols)}
    w = st.tsize_capit(p, scheme="fine12", hold_days=3)
    assert w["ETH"].iloc[10:13].tolist() == [0.5, 0.5, 0.5] and w["ETH"].drop(idx[10:13]).abs().sum() == 0
    assert w["BTC"].iloc[10:13].tolist() == [0.5, 0.5, 0.5] and w["BTC"].drop(idx[10:13]).abs().sum() == 0
    short = st.tsize_capit(p, scheme="fine12", hold_days=1, side="short")
    assert short.abs().sum().sum() == 0              # no all-positive day in this panel
    cut = {k: v.iloc[:12] for k, v in p.items()}     # causal: same weights without the future
    pd.testing.assert_frame_equal(st.tsize_capit(cut, scheme="fine12", hold_days=3), w.iloc[:12])


@pytest.mark.parametrize("friday,utc_hour", [("2024-01-12", 22), ("2024-07-12", 21)])       # winter / summer time
def test_weekend_revert_fades_the_weekend_move_back_to_friday(friday, utc_hour):
    idx = pd.date_range(pd.Timestamp(friday, tz="UTC") - pd.Timedelta(days=2), periods=24 * 7, freq="1h")
    px = pd.Series(100.0, idx)
    fri_bar = pd.Timestamp(friday, tz="UTC") + pd.Timedelta(hours=utc_hour - 1)   # bar that CLOSES at 17:00 New York
    sun_bar = fri_bar + pd.Timedelta(hours=49)                                    # closes Sunday 18:00 New York
    px[(idx > fri_bar) & (idx <= sun_bar + pd.Timedelta(hours=5))] = 103.0        # weekend pump, still there after the reopen
    back = sun_bar + pd.Timedelta(hours=6)
    px[idx >= back] = 100.0
    close = pd.DataFrame({"BTC": px, "ETH": 50.0})
    p = {"close": close, "high": close, "low": close, "volume": close * 1e6}
    w = st.weekend_revert(p, thr=0.01, exit="fill")
    held = w["BTC"][w["BTC"] != 0]
    assert held.index[0] == sun_bar and (held == -0.5).all()
    assert held.index[-1] == back - pd.Timedelta(hours=1)        # flat from the close of the bar that got back to 100
    assert w["ETH"].abs().sum() == 0                             # no gap, no trade
    assert st.weekend_revert(p, thr=0.05).abs().sum().sum() == 0
    mon = st.weekend_revert(p, thr=0.01, exit="monday")["BTC"]
    assert mon[mon != 0].index[-1] == fri_bar + pd.Timedelta(hours=71)   # last held bar: the one before Monday 17:00's


# --------------------------------------------------------------------------- panel loaders (alignment needs known answers)
def test_minute_panel_aligns_bars_fills_gaps_and_resamples(tmp_path, monkeypatch):
    from kripto import data
    monkeypatch.setattr(data, "DATA", tmp_path)
    d = tmp_path / "bn" / "klines_1m"
    d.mkdir(parents=True)
    t0 = int(pd.Timestamp("2024-01-01", tz="UTC").timestamp() * 1000)
    mins = [0, 1, 2, 4, 5, 6, 7, 8, 9]                                    # minute 3 is missing
    a = pd.DataFrame({"t": [t0 + m * 60_000 for m in mins], "h": [m + 1.5 for m in mins], "l": [m + 0.5 for m in mins],
                      "c": [m + 1.0 for m in mins], "qv": [10.0] * len(mins)})
    a.loc[a.index[-1], "t"] *= 1000                                       # one row in microseconds, as in some archive months
    a.to_parquet(d / "AAAUSDT.parquet")
    b = a.iloc[2:].copy()                                                 # BBB starts two minutes later
    b.to_parquet(d / "BBBUSDT.parquet")
    p = data.load_bn_minute_panel(["AAA", "BBB", "MISSING"], start="2024-01-01")
    assert list(p["close"].columns) == ["AAA", "BBB"] and len(p["close"]) == 10
    assert p["close"]["AAA"].tolist() == [1, 2, 3, 3, 5, 6, 7, 8, 9, 10]   # the gap repeats the last close ...
    assert p["high"]["AAA"].iloc[3] == 3 and p["low"]["AAA"].iloc[3] == 3 and p["volume"]["AAA"].iloc[3] == 0   # ... flat, no volume
    assert np.isnan(p["close"]["BBB"].iloc[0]) and p["close"]["BBB"].iloc[2] == 3
    q = data.load_bn_minute_panel(["AAA"], start="2024-01-01", rule="5min")
    assert q["close"]["AAA"].tolist() == [5, 10] and q["high"]["AAA"].tolist() == [5.5, 10.5] and q["volume"]["AAA"].tolist() == [40, 50]


def test_tsize_frames_index_and_panel_columns(tmp_path, monkeypatch):
    monkeypatch.setattr(tsize, "DIR", tmp_path)
    days = np.array(["2024-01-01", "2024-01-02"], dtype="datetime64[D]")
    buy = np.zeros((2, 288, 12), dtype=np.float32)
    sell = np.zeros_like(buy)
    buy[0, 0, 0], sell[0, 287, 11], buy[1, 5, 6] = 100, 40, 7
    np.savez(tmp_path / "XUSDT.npz", days=days, buy=buy, sell=sell, n=np.zeros((2, 288, 12), dtype=np.uint32))
    dd, vv = tsize.frames("XUSDT", "fine12", "1D")
    assert dd.index[1] == pd.Timestamp("2024-01-02", tz="UTC") and dd.iloc[0, 0] == 100 and dd.iloc[0, 11] == -40 and vv.iloc[1, 6] == 7
    d5, _ = tsize.frames("XUSDT", "small_large", "5min")
    assert len(d5) == 576 and d5.index[287] == pd.Timestamp("2024-01-01 23:55", tz="UTC")
    assert d5.iloc[0, 0] == 100 and d5.iloc[287, 1] == -40 and d5.index[288 + 5] == pd.Timestamp("2024-01-02 00:25", tz="UTC") and d5.iloc[288 + 5, 1] == 7


# --------------------------------------------------------------------------- second-pass strategies
def test_spike_high_short_shorts_only_after_a_new_high_on_a_volume_spike():
    idx = pd.date_range("2024-01-01", periods=140, freq="1D", tz="UTC")
    rng = np.random.default_rng(3)
    coins = ["BTC", "AAA", "BBB"]
    close = pd.DataFrame(100.0 + rng.normal(0, 0.05, (140, 3)).cumsum(0) * 0, idx, coins) + np.arange(140)[:, None] * 0.0
    close["AAA"] = 100 - np.arange(140) * 0.1                      # drifts down: never at a 20-day high ...
    close.loc[idx[100], "AAA"] = 150.0                             # ... except one spike day
    close["BBB"] = 100 + np.arange(140) * 0.1                      # at a new high every day, on ordinary volume
    vol = pd.DataFrame(1e7, idx, coins)
    vol["AAA"] = 1e7 * np.exp(rng.normal(0, 0.1, 140))             # only AAA's volume varies (a z-score needs variance)
    vol.loc[idx[100], "AAA"] = 1e9                                 # the spike day has 100x volume
    p = {"close": close, "volume": vol}
    w = st.spike_high_short(p, zthr=2.0, hold_days=5, top_n=3, beta_neutral=False)
    assert (w["AAA"].iloc[100:105] == -0.1).all() and w["AAA"].drop(idx[100:105]).abs().sum() == 0
    assert w["BBB"].abs().sum() == 0 and w["BTC"].abs().sum() == 0
    cut = {k: v.iloc[:103] for k, v in p.items()}
    pd.testing.assert_frame_equal(st.spike_high_short(cut, zthr=2.0, hold_days=5, top_n=3, beta_neutral=False), w.iloc[:103])


@pytest.mark.parametrize("friday,utc_hour", [("2024-01-12", 22), ("2024-07-12", 21)])
def test_friday_follow_holds_fridays_movers_for_a_day(friday, utc_hour):
    idx = pd.date_range(pd.Timestamp(friday, tz="UTC") - pd.Timedelta(days=40), periods=24 * 45, freq="1h")
    fri_bar = pd.Timestamp(friday, tz="UTC") + pd.Timedelta(hours=utc_hour - 1)      # closes Friday 17:00 New York
    up = pd.Series(100.0, idx)
    up[idx > fri_bar - pd.Timedelta(hours=10)] = 105.0                               # +5% inside the 24 h before the close
    down = pd.Series(100.0, idx)
    down[idx > fri_bar - pd.Timedelta(hours=10)] = 96.0
    close = pd.DataFrame({"UP": up, "DOWN": down, "FLAT": 50.0})
    p = {"close": close, "volume": close * 0 + 1e6}
    w = st.friday_follow(p, thr=0.02, hold_h=24, top_n=3)
    held = w[(w != 0).any(axis=1)]
    assert held.index[0] == fri_bar and len(held) == 24
    assert (held["UP"] == 0.1).all() and (held["DOWN"] == -0.1).all() and (held["FLAT"] == 0).all()
    assert st.friday_follow(p, thr=0.10).abs().sum().sum() == 0


@pytest.mark.parametrize("sunday,utc_hour", [("2024-01-14", 23), ("2024-07-14", 22)])
def test_sunday_fade_fades_the_sunday_afternoon_move_for_a_day(sunday, utc_hour):
    idx = pd.date_range(pd.Timestamp(sunday, tz="UTC") - pd.Timedelta(days=40), periods=24 * 45, freq="1h")
    bar = pd.Timestamp(sunday, tz="UTC") + pd.Timedelta(hours=utc_hour - 1)          # the hour that closes Sunday 18:00 New York
    up = pd.Series(100.0, idx)
    up[idx > bar - pd.Timedelta(hours=3)] = 103.0                                     # +3% inside the 6 h before the cut
    down = pd.Series(100.0, idx)
    down[idx > bar - pd.Timedelta(hours=3)] = 97.0
    early = pd.Series(100.0, idx)
    early[idx > bar - pd.Timedelta(hours=10)] = 105.0                                 # moved BEFORE the 6 h window: not an event
    close = pd.DataFrame({"UP": up, "DOWN": down, "EARLY": early})
    p = {"close": close, "volume": close * 0 + 1e6}
    w = st.sunday_fade(p, thr=0.01, hold_h=24, top_n=3, max_names=20)
    held = w[(w != 0).any(axis=1)]
    assert held.index[0] == bar and len(held) == 24
    assert (held["UP"] == -0.05).all() and (held["DOWN"] == 0.05).all() and (held["EARLY"] == 0).all()
    assert st.sunday_fade(p, thr=0.05).abs().sum().sum() == 0
