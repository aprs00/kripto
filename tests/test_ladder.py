"""Ladder paper book (kripto/ladder.py): known-answer tests with a fake public Binance client and a fake clock (no network)."""
import numpy as np
import pytest

from kripto import ladder as LD
from kripto import paper as P

M = 60_000
T0 = 1_700_000_000_000 - 1_700_000_000_000 % M


class FakeBN:
    """1-min bars of two coins; prices for minute index i given by self.close[c][i], lows by self.low[c][i]."""
    def __init__(self, n=1600):
        rng = np.random.default_rng(1)
        self.close = {c: p * np.exp(np.cumsum(rng.normal(0, 0.001, n))) for c, p in (("SOL", 150.0), ("BTC", 60000.0))}
        self.low = {c: v * 0.9995 for c, v in self.close.items()}
        self.now = T0 + 1500 * M + 3000
        self.calls = []

    def klines(self, symbol, interval, start_ms=None, limit=1500):
        c = symbol.removesuffix("USDT")
        self.calls.append((c, limit))
        last = (self.now - T0) // M          # minute index currently forming
        out = []
        for i in range(max(0, last - limit + 1), last + 1):
            o = T0 + i * M
            out.append([o, "0", "0", str(self.low[c][i]), str(self.close[c][i]), "0", o + M - 1])
        return out

    def depth(self, symbol, limit=20):
        c = symbol.removesuffix("USDT")
        i = (self.now - T0) // M - 1
        p = self.close[c][i]
        return {"bids": [[str(p * 0.9999), "1e9"]], "asks": [[str(p * 1.0001), "1e9"]]}


@pytest.fixture
def lad(tmp_path):
    store = P.Store(tmp_path / "p.db")
    bn = FakeBN()
    L = LD.Ladder(store, bn, {"start_equity": 1000.0, "shadow_equity": 2000.0, "small_equity": 200.0}, now_ms=lambda: bn.now)
    L.coins = ["SOL", "BTC"]
    L.filters = {"SOL": {"step": 0.01, "min_notional": 5.0}, "BTC": {"step": 0.001, "min_notional": 50.0}}
    L.band = {"SOL": 0.15, "BTC": 0.05}
    return L, bn, store


def tick(L, bn):
    bn.now += M
    return L.step()


def test_sigma_matches_pandas():
    import pandas as pd
    c = np.exp(np.cumsum(np.random.default_rng(0).normal(0, 0.002, 3000)))
    ref = pd.Series(np.diff(np.log(c), prepend=np.nan)).rolling(1440, min_periods=720).std().iloc[-1]
    assert LD.sigma(c) == pytest.approx(ref, rel=1e-9)
    assert np.isnan(LD.sigma(c[:700]))


def test_quote_judges_only_minutes_opening_after_it(lad):
    L, bn, store = lad
    L.step()                                  # history only, first quotes placed at bn.now (inside minute 1500)
    q = L.quotes["SOL"][-1][1]
    i = (bn.now - T0) // M                    # minute 1500 opened BEFORE the quote: a crash in it must NOT fill
    bn.low["SOL"][i] = q * 0.9
    out = tick(L, bn)
    assert out["fills"] == 0
    q2 = [x for x in L.quotes["SOL"] if x[0] <= T0 + (i + 1) * M][-1][1]   # the quote valid for minute 1501
    bn.low["SOL"][i + 1] = q2 * (1 - LD.THROUGH) * 0.999
    out = tick(L, bn)
    assert out["fills"] == 2                  # shadow and small books
    f = store.q("select book, px, size, fee, reason from fills order by book")
    assert all(abs(px - q2) < 1e-9 for _, px, *_ in f)
    sh = [r for r in f if r[0].startswith("shadow")][0]
    assert sh[2] == pytest.approx(round(np.floor(0.05 * 2000 / q2 / 0.01) * 0.01, 2))
    assert sh[3] == pytest.approx(sh[2] * q2 * LD.MAKER_FEE_BN)
    assert sh[4] == f"ladder bid {T0 + (i + 1) * M}"


def test_not_through_by_30bp_no_fill(lad):
    L, bn, store = lad
    L.step()
    tick(L, bn)
    i = (bn.now - T0) // M
    q = [x for x in L.quotes["SOL"] if x[0] <= T0 + i * M][-1][1]
    bn.low["SOL"][i] = q * (1 - LD.THROUGH / 2)
    assert tick(L, bn)["fills"] == 0


def test_exit_after_hold_and_lock(lad):
    L, bn, store = lad
    L.step()
    tick(L, bn)
    i = (bn.now - T0) // M
    q = [x for x in L.quotes["SOL"] if x[0] <= T0 + i * M][-1][1]
    bn.low["SOL"][i] = q * 0.99
    assert tick(L, bn)["fills"] == 2
    for k in range(59):                       # exit due at fill-minute open + 61 min
        bn.low["SOL"][i + 1 + k] = 1e-9       # deep crashes inside the lock never add a second fill
        out = tick(L, bn)
        assert out["exits"] == 0 and out["fills"] == 0, k
    out = tick(L, bn)
    assert out["exits"] == 2
    assert not store.positions("shadow:ladder@bn") and not store.positions("small:ladder@bn")


def test_band_and_min_notional(lad):
    L, bn, store = lad
    L.band["SOL"] = 1e-4                      # 30 sigma deeper than the PERCENT_PRICE band -> no quote
    L.step()
    assert "SOL" not in L.quotes and "BTC" in L.quotes
    tick(L, bn)
    i = (bn.now - T0) // M
    q = [x for x in L.quotes["BTC"] if x[0] <= T0 + i * M][-1][1]
    bn.low["BTC"][i] = q * 0.99
    tick(L, bn)
    books = {r[0] for r in store.q("select book from fills")}
    assert books == {"shadow:ladder@bn"}       # 5% of $200 = $10 < BTC's $50 minimum


def test_halted_book_does_not_trade(lad):
    L, bn, store = lad
    L.step()
    store.x("update books set halted=1 where name='small:ladder@bn'")
    tick(L, bn)
    i = (bn.now - T0) // M
    q = [x for x in L.quotes["SOL"] if x[0] <= T0 + i * M][-1][1]
    bn.low["SOL"][i] = q * 0.99
    tick(L, bn)
    assert {r[0] for r in store.q("select book from fills")} == {"shadow:ladder@bn"}
