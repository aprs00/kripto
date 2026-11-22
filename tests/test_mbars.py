"""Known-answer tests of move bars (kripto/mbars.py): bars that close on distance travelled, not on time."""
import numpy as np

from kripto import mbars


def day(prices, qty=None, maker=None, t=None):
    p = np.asarray(prices, dtype=float)
    n = len(p)
    return mbars.micro(p, np.ones(n) if qty is None else np.asarray(qty, float), np.arange(n) * 1000 if t is None else np.asarray(t),
                       np.zeros(n, bool) if maker is None else np.asarray(maker, bool), step=1e-3)


def test_bar_closes_on_the_first_trade_that_is_one_step_away():
    b = day([100, 100.05, 100.11, 100.12, 100.0, 99.99])
    assert list(b["n"]) == [3, 2, 1]                       # 100.11 closes up; 100.0 closes down (from 100.11); the rest is the day's last bar
    assert np.allclose(b["o"], [100, 100.11, 100.0]) and np.allclose(b["c"], [100.11, 100.0, 99.99], rtol=1e-6)
    assert np.allclose(b["h"], [100.11, 100.12, 100.0], rtol=1e-6) and np.allclose(b["l"], [100, 100.0, 99.99], rtol=1e-6)
    assert list(b["t0"]) == [0, 3000, 5000] and list(b["t1"]) == [2000, 4000, 5000]
    assert list(b["full"]) == [True, True, False]


def test_flow_is_bucketed_by_size_and_side_and_conserved():
    b = day([100, 100.2, 100.2, 100.2], qty=[5, 500, 2000, 20_000], maker=[0, 1, 0, 1])
    assert b["buy"].shape[1] == 12 and np.isclose(b["buy"].sum() + b["sell"].sum(), 500 + 50_100 + 200_400 + 2_004_000)
    assert np.isclose(b["sell"][0].sum(), 50_100) and np.isclose(b["sell"][1].sum(), 2_004_000) and np.isclose(b["buy"][1].sum(), 200_400)


def test_same_result_as_a_plain_loop_on_random_trades():
    g = np.random.default_rng(0)
    p = 100 * np.exp(np.cumsum(g.normal(0, 2e-4, 20_000)))
    b = day(p)
    ends, o = [], p[0]
    start = 0
    for i, x in enumerate(p):
        if i > start - 1 and (x >= o * 1.001 or x <= o / 1.001) and i >= start:
            ends.append(i)
            start = i + 1
            o = x
    assert np.array_equal(np.cumsum(b["n"])[b["full"]] - 1, ends)


def test_range_bars_aggregate_micro_bars_and_close_when_high_minus_low_reaches_the_width():
    p = [100, 100.11, 100.22, 100.33, 100.44, 100.40, 100.3, 100.2, 100.1, 99.9]
    b = day(p)
    r = mbars.range_bars(b, 0.004)
    assert (r["h"] / r["l"] - 1 >= 0.004 - 1e-6)[r["full"]].all()
    assert r["n"].sum() == len(p) and np.isclose(r["buy"].sum(), b["buy"].sum())
    assert r["c"][0] > r["o"][0] and r["c"][1] < r["o"][1]
    assert np.array_equal(r["o"][1:], r["c"][:-1])


def test_volume_at_price_puts_micro_bar_volume_at_its_price():
    b = day([100, 100.11, 100.22, 100.11, 100.0], qty=[10] * 5)
    edges, vol, delta = mbars.vap(b, bin_bp=10)
    assert np.isclose(vol.sum(), b["buy"].sum() + b["sell"].sum()) and len(edges) == len(vol) == len(delta)
    assert np.isclose(delta.sum(), b["buy"].sum() - b["sell"].sum())
