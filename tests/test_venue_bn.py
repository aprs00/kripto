"""Binance paper venue: known-answer tests with a fake public client (no network)."""
import numpy as np
import pandas as pd
import pytest

from kripto import paper as P
from kripto import venue_bn as V
from kripto.bn import BN

COINS = {"BTC": (60000.0, 0.001, 50.0), "ETH": (3000.0, 0.001, 20.0), "SOL": (150.0, 1.0, 5.0), "DOGE": (0.2, 1.0, 5.0)}


class FakeBN:
    def __init__(self, days=240, seed=0):
        rng = np.random.default_rng(seed)
        end = (pd.Timestamp.now("UTC") - pd.Timedelta(hours=4)).floor("1D")  # last closed bar is a 00:00 (daily rebalance) bar
        self.idx = pd.date_range(end=end, periods=days * 6, freq="4h")
        self.close = {}
        for i, (c, (p0, _, _)) in enumerate(COINS.items()):
            drift = [0.002, -0.002, 0.003, -0.001][i]  # clear trends so tsmom takes positions
            self.close[c] = p0 * np.exp(np.cumsum(rng.normal(drift, 0.01, len(self.idx))))
        self.funding = []
        self.calls = []

    def exchange_info(self):
        return {"symbols": [{"symbol": c + "USDT", "contractType": "PERPETUAL", "quoteAsset": "USDT", "status": "TRADING",
                             "filters": [{"filterType": "LOT_SIZE", "stepSize": str(st)},
                                         {"filterType": "MARKET_LOT_SIZE", "stepSize": str(st)},
                                         {"filterType": "MIN_NOTIONAL", "notional": str(mn)}]}
                            for c, (_, st, mn) in COINS.items()]}

    def ticker_24h(self):
        return [{"symbol": c + "USDT", "quoteVolume": str(1e9 / (i + 1))} for i, c in enumerate(COINS)]

    def premium_index(self):
        return [{"symbol": c + "USDT", "markPrice": str(self.close[c][-1])} for c in COINS]

    def klines(self, symbol, interval, start_ms=None, limit=1500):
        c = symbol.removesuffix("USDT")
        out = []
        for t, px in zip(self.idx, self.close[c]):
            ms = int(t.timestamp() * 1000)
            if start_ms is None or ms >= start_ms:
                qv = 5e7
                out.append([ms, str(px), str(px * 1.01), str(px * 0.99), str(px), "1", ms + 1, str(qv), 1, "0", str(qv * 0.52), "0"])
        return out[-limit:]

    def depth(self, symbol, limit=20):
        c = symbol.removesuffix("USDT")
        m = self.close[c][-1]
        return {"bids": [[str(m * (1 - 0.0001 * (i + 1))), "1e9"] for i in range(limit)],
                "asks": [[str(m * (1 + 0.0001 * (i + 1))), "1e9"] for i in range(limit)]}

    def funding_rate(self, symbol, start_ms, end_ms=None):
        self.calls.append(symbol)
        return [r for r in self.funding if r["symbol"] == symbol]


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "LIVE_DIR", tmp_path / "live")
    monkeypatch.setattr(V, "INFO_CACHE", tmp_path / "info.json")
    monkeypatch.setattr(V, "FUND_DIR", tmp_path / "fund")
    store = P.Store(tmp_path / "paper.db")
    cfg = {"tsmom": {"status": "candidate", "params": {}},  # HL entry: must be ignored by the BN venue
           "tsmom@bn": {"strategy": "tsmom", "venue": "bn", "status": "candidate", "params": {"top_n": 4}}}
    risk = {"start_equity": 200.0, "shadow_equity": 2000.0, "max_gross": 3.0, "max_asset_weight": 0.35, "kill_drawdown": 0.25}
    return store, cfg, risk, FakeBN()


def test_round_step_rounds_toward_zero():
    assert V.round_step(1.2345, 0.001) == 1.234
    assert V.round_step(-1.2345, 0.001) == -1.234
    assert V.round_step(7.9, 1.0) == 7.0
    assert V.round_step(0.0004, 0.001) == 0.0


def test_book_venue_and_strategy_fn():
    assert P.book_venue("main_bn") == "bn" and P.book_venue("shadow:flow@bn") == "bn"
    assert P.book_venue("main") == "hl" and P.book_venue("shadow:tsmom") == "hl"
    assert P.strategy_fn("tsmom@bn", {"strategy": "tsmom"}) is P.REGISTRY["tsmom"]


def test_fill_walks_book():
    class B:
        def depth(self, s, n):
            return {"bids": [["99", "1"]], "asks": [["100", "1"], ["101", "1"]]}
    px, mid, slip = V.simulate_fill(B(), "X", 1.5)
    assert px == pytest.approx((100 + 0.5 * 101) / 1.5) and mid == 99.5 and slip > 0


def test_run_trades_bn_books_only_with_bn_rules(env):
    store, cfg, risk, bn = env
    V.run(store, cfg, risk, bn)
    books = {b for (b,) in store.q("select name from books")}
    assert books == {"shadow:tsmom@bn", "main_bn"}  # no HL books touched
    fills = store.q("select coin, size, px, fee, reason from fills where book='shadow:tsmom@bn'")
    assert fills, "shadow book should trade on the first closed bar"
    for coin, size, px, fee, reason in fills:
        _, step, mn = COINS[coin]
        assert fee == pytest.approx(abs(size) * px * V.TAKER_FEE_BN)
        assert abs(size) * px >= mn * 0.999
        assert abs(size / step - round(size / step)) < 1e-6
    assert store.get_meta("bn_last_bar") is not None
    assert not store.q("select 1 from fills where book='main_bn'")  # no incubation entries -> main_bn flat
    n = len(store.q("select * from fills"))
    V.run(store, cfg, risk, bn)  # same bar again -> no new trades
    assert len(store.q("select * from fills")) == n


def test_funding_accrues_only_on_bn_positions(env):
    store, cfg, risk, bn = env
    V.run(store, cfg, risk, bn)
    store.ensure_book("shadow:tsmom", 2000.0)  # an HL book holding the same coin must not be charged BN funding
    store.x("insert into positions values('shadow:tsmom','BTC',0.01)")
    pos = store.positions("shadow:tsmom@bn")
    coin, size = next(iter(pos.items()))
    cash0, hl0 = store.cash("shadow:tsmom@bn"), store.cash("shadow:tsmom")
    bn.funding = [{"symbol": coin + "USDT", "fundingTime": int(pd.Timestamp.now("UTC").timestamp() * 1000),
                   "fundingRate": "0.0001", "markPrice": "100"}]
    V.accrue_funding(bn, store, {})
    expected = -size * 100 * 0.0001
    assert store.cash("shadow:tsmom@bn") - cash0 == pytest.approx(expected)
    assert store.cash("shadow:tsmom") == hl0


def test_client_refuses_non_whitelisted_endpoints():
    with pytest.raises(ValueError):
        BN().get("/fapi/v1/order", {"symbol": "BTCUSDT"})


def test_funding_panel_known_answer(tmp_path):
    """2026-11-26: the live BN panel carries funding (blend_nested@bn's carry legs). A print at tau pays for the bar ending at tau;
    covered bars without a print are 0, bars before the cache NaN; uncached coins NaN."""
    idx = pd.date_range("2026-11-01", periods=6, freq="4h", tz="UTC")
    ms = lambda t: int(pd.Timestamp(t).timestamp() * 1000)
    tmp_path.mkdir(exist_ok=True)
    pd.DataFrame({"time": [ms("2026-11-01 08:00Z"), ms("2026-11-01 16:00Z")], "fundingRate": [1e-4, 2e-4]}).to_parquet(tmp_path / "AAA.parquet")
    f = V.funding_panel(["AAA", "BBB"], idx, tmp_path)
    a = f["AAA"].tolist()
    assert np.isnan(a[0]) and a[1] == 1e-4 and a[2] == 0.0 and a[3] == 2e-4 and a[4] == 0.0 and a[5] == 0.0
    assert f["BBB"].isna().all()


def test_funding_cache_refresh_incremental(tmp_path):
    class B:
        def __init__(self): self.calls = []
        def funding_rate(self, symbol, start_ms, end_ms=None):
            self.calls.append((symbol, start_ms))
            return [{"fundingTime": 1_000_000 + i, "fundingRate": "0.0001"} for i in range(3) if 1_000_000 + i >= start_ms]
    b = B()
    V.funding_cache_refresh(b, ["AAA"], tmp_path, now_ms=1_000_100, days=1)
    V.funding_cache_refresh(b, ["AAA"], tmp_path, now_ms=1_000_200, days=1)
    assert b.calls[0][0] == "AAAUSDT" and b.calls[1][1] == 1_000_003
    assert len(pd.read_parquet(tmp_path / "AAA.parquet")) == 3
