"""Two-venue (pair) paper books: known-answer tests with fake public clients (no network)."""
import numpy as np
import pandas as pd
import pytest

from kripto import paper as P
from kripto import venue_bn as V
from kripto import venue_pair as VP
from kripto.backtest import TAKER_FEE

NOW = pd.Timestamp("2026-06-01 00:30", tz="UTC")
DAYS = 45
PX = {"AAA": 10.0, "BBB": 2.0, "kPEPE": 0.01}


class FakeHL:
    def l2_book(self, coin):
        m = PX[coin]
        return {"levels": [[{"px": str(m * (1 - 1e-4 * (i + 1))), "sz": "1e9"} for i in range(20)],
                           [{"px": str(m * (1 + 1e-4 * (i + 1))), "sz": "1e9"} for i in range(20)]]}


class FakeBN:
    def __init__(self, rates):
        self.rates = rates        # {bn coin: per-8h funding rate}
        self.calls = []

    def funding_rate(self, symbol, start_ms, end_ms=None):
        self.calls.append(symbol)
        c = symbol.removesuffix("USDT")
        t = pd.date_range(NOW - pd.Timedelta(days=DAYS), NOW, freq="8h")
        ms = [int(x.timestamp() * 1000) for x in t]
        return [{"symbol": symbol, "fundingTime": m, "fundingRate": str(self.rates.get(c, 0.0))}
                for m in ms if start_ms <= m <= (end_ms or 10**15)]

    def depth(self, symbol, limit=20):
        c = symbol.removesuffix("USDT")
        m = PX["kPEPE" if c == "1000PEPE" else c]
        return {"bids": [[str(m * (1 - 1e-4 * (i + 1))), "1e9"] for i in range(limit)],
                "asks": [[str(m * (1 + 1e-4 * (i + 1))), "1e9"] for i in range(limit)]}


def _write(tmp_path, hl_rate):
    idx = pd.date_range(NOW.floor("1D") - pd.Timedelta(days=DAYS), NOW, freq="4h")
    ms = np.array([int(t.timestamp() * 1000) for t in idx])
    for c, px in PX.items():
        cl = np.full(len(idx), px) * np.exp(np.linspace(0, 0.01, len(idx)))
        pd.DataFrame({"t": ms, "o": cl, "h": cl, "l": cl, "c": cl, "v": 1e7 / px, "n": 1}).to_parquet(
            VP.HL_CANDLES / f"{c}.parquet")
        b = "1000PEPE" if c == "kPEPE" else c
        pd.DataFrame({"t": ms, "o": cl, "h": cl, "l": cl, "c": cl, "qv": 1e7, "tbqv": 5e6}).to_parquet(V.LIVE_DIR / f"{b}.parquet")
        h = pd.date_range(NOW - pd.Timedelta(days=DAYS), NOW, freq="1h")
        pd.DataFrame({"time": [int(t.timestamp() * 1000) + 5 for t in h], "fundingRate": hl_rate.get(c, 0.0),
                      "premium": 0.0}).to_parquet(VP.HL_FUND / f"{c}.parquet")


@pytest.fixture
def env(tmp_path, monkeypatch):
    for attr, sub in (("HL_CANDLES", "hl4h"), ("HL_FUND", "hlf"), ("BN_FUND_DIR", "bnf")):
        (tmp_path / sub).mkdir()
        monkeypatch.setattr(VP, attr, tmp_path / sub)
    (tmp_path / "bn4h").mkdir()
    monkeypatch.setattr(V, "LIVE_DIR", tmp_path / "bn4h")
    monkeypatch.setattr(P, "DB", tmp_path / "paper.db")
    store = P.Store(tmp_path / "paper.db")
    cfg = {"tsmom": {"status": "candidate", "params": {}},
           "fspread_hold@pair": {"strategy": "fspread_hold", "venue": "pair", "status": "candidate",
                                 "params": {"lookback": 14, "enter": 0.1}}}
    risk = {"start_equity": 1000.0, "shadow_equity": 2000.0, "small_equity": 200.0, "max_gross": 3.0,
            "max_asset_weight": 0.35, "kill_drawdown": 0.25}
    # AAA: HL longs pay 0.01%/h (87.6%/yr), Binance 0 -> short HL, long Binance. BBB: no spread -> no pair.
    _write(tmp_path, {"AAA": 1e-4})
    filters = {"AAA": {"step": 0.01, "min_notional": 5.0}, "BBB": {"step": 0.01, "min_notional": 5.0},
               "1000PEPE": {"step": 1.0, "min_notional": 5.0}}
    bn = FakeBN({})
    bn_run = {"bn": bn, "coins": ["AAA", "BBB", "1000PEPE"], "marks": {"AAA": PX["AAA"], "BBB": PX["BBB"], "1000PEPE": PX["kPEPE"]},
              "filters": filters}
    return store, cfg, risk, bn_run


def _run(env, now=NOW):
    store, cfg, risk, bn_run = env
    return VP.run(store, cfg, risk, FakeHL(), bn_run, dict(PX), {"AAA": 2, "BBB": 2, "kPEPE": 0}, list(PX), now=now)


def test_book_venue_and_held_coins_see_pair_legs(env):
    store = env[0]
    assert P.book_venue("shadow:fspread_hold@pair") == "pair" and P.book_venue("small:fspread_hold@pair") == "pair"
    assert P.book_venue("shadow:flow@bn") == "bn" and P.book_venue("main") == "hl"
    store.ensure_book("shadow:x@pair", 2000.0)
    store.x("insert into positions values('shadow:x@pair','kPEPE@bn',100.0)")
    store.x("insert into positions values('shadow:x@pair','kPEPE@hl',-100.0)")
    assert P.held_coins(store, "bn") == {"1000PEPE"} and P.held_coins(store, "hl") == {"kPEPE"}


def test_live_panel_uses_closed_days_and_daily_funding_sums(env):
    VP.bn_funding_refresh(env[3]["bn"], list(PX), int(NOW.timestamp() * 1000))
    p = VP.live_panel(list(PX), NOW)
    assert set(p["close"].columns) == {f"{c}@{v}" for c in PX for v in ("hl", "bn")}
    assert p["close"].index[-1] == NOW.floor("1D") - pd.Timedelta(days=1)        # today is not closed yet
    day = p["close"].index[-2]
    assert p["funding"].loc[day, "AAA@hl"] == pytest.approx(24 * 1e-4)          # 24 hourly prints
    assert p["funding"].loc[day, "AAA@bn"] == pytest.approx(0.0)
    hl4 = pd.read_parquet(VP.HL_CANDLES / "AAA.parquet")
    last = hl4[pd.to_datetime(hl4["t"], unit="ms", utc=True) == day + pd.Timedelta(hours=20)]["c"].iloc[0]
    assert p["close"].loc[day, "AAA@hl"] == pytest.approx(last)


def test_run_opens_the_pair_with_venue_rules_and_only_once_per_day(env):
    store = env[0]
    _run(env)
    books = {b for (b,) in store.q("select name from books")}
    assert books == {"shadow:fspread_hold@pair", "small:fspread_hold@pair"}       # no HL / BN / main books
    pos = store.positions("shadow:fspread_hold@pair")
    assert set(pos) == {"AAA@hl", "AAA@bn"}
    assert pos["AAA@hl"] < 0 < pos["AAA@bn"]                                      # short the venue whose longs pay
    assert abs(pos["AAA@hl"] * PX["AAA"]) == pytest.approx(200, rel=0.01)         # 10% of $2,000 per leg
    for coin, size, px, fee in store.q("select coin,size,px,fee from fills"):
        rate = TAKER_FEE if coin.endswith("@hl") else V.TAKER_FEE_BN
        assert fee == pytest.approx(abs(size) * px * rate)
    n = len(store.q("select * from fills"))
    _run(env, NOW + pd.Timedelta(hours=1))                                      # same day: no new trades
    assert len(store.q("select * from fills")) == n


def test_funding_accrues_per_leg_from_stored_prints(env):
    store = env[0]
    VP.bn_funding_refresh(env[3]["bn"], ["AAA"], int(NOW.timestamp() * 1000))
    store.ensure_book("shadow:x@pair", 2000.0)
    store.ensure_book("shadow:tsmom", 2000.0)
    store.x("insert into positions values('shadow:x@pair','AAA@hl',-10.0)")
    store.x("insert into positions values('shadow:x@pair','AAA@bn',10.0)")
    store.x("insert into positions values('shadow:tsmom','AAA',10.0)")           # HL book: must not be touched
    t0 = int((NOW - pd.Timedelta(hours=3)).timestamp() * 1000)
    store.set_meta("pair_funding_accrued_ms", t0)
    cash0 = store.cash("shadow:x@pair")
    VP.accrue_funding(store, {"AAA@hl": 10.0, "AAA@bn": 10.0}, int(NOW.timestamp() * 1000))
    # HL: 3 hourly prints of 1e-4 on a short of 10 x $10 -> receives 3 * 0.01; Binance rate 0 -> 0
    assert store.cash("shadow:x@pair") - cash0 == pytest.approx(0.03)
    assert store.cash("shadow:tsmom") == 2000.0


def test_incubation_entry_trades_the_two_account_main_book_at_its_alloc(env):
    store, cfg, risk, bn_run = env
    cfg["fspread_hold@pair"].update(status="incubation", alloc=0.5)
    _run(env)
    books = {b for (b,) in store.q("select name from books")}
    assert {"main@pair", "small:main@pair"} <= books
    assert P.book_venue("main@pair") == "pair" and P.book_venue("small:main@pair") == "pair"
    pos = store.positions("main@pair")
    assert pos["AAA@hl"] < 0 < pos["AAA@bn"]
    assert abs(pos["AAA@hl"] * PX["AAA"]) == pytest.approx(0.5 * 0.1 * 1000, rel=0.02)   # alloc x 10% leg x $1,000
    n = len(store.q("select * from fills where book='main@pair'"))
    _run(env, NOW + pd.Timedelta(hours=1))
    assert len(store.q("select * from fills where book='main@pair'")) == n
    cfg["fspread_hold@pair"].update(status="retired", alloc=0.0)                      # leaving: main book closes out at the next day
    _run(env, NOW + pd.Timedelta(days=1))
    assert not store.positions("main@pair")


def test_account_equity_transfer_and_guard_known_answer(tmp_path):
    """KS1: two accounts of $500 each. Long 10 A@bn at 10, short 10 A@hl at 10 (fees 0). A rises to 13: HL -30, BN +30
    -> 470 / 530, no transfer (470 > 0.7*530). A at 20: HL -100, BN +100 -> 400 / 600 < 70 % -> move 100 to HL, 500/500.
    Accounts always sum to book equity. Then A at 100 (HL short -800 from 20): HL account deep below its peak -> guard."""
    s = P.Store(tmp_path / "p.db")
    s.ensure_book("shadow:x@pair", 1000.0)
    with s.c:
        for coin, d in (("A@bn", 10.0), ("A@hl", -10.0)):
            s.c.execute("update books set cash=cash-? where name=?", (d * 10.0, "shadow:x@pair"))
            s.c.execute("insert into positions values(?,?,?)", ("shadow:x@pair", coin, d))
            s.c.execute("insert into fills values(?,?,?,?,?,?,?,?,?)", (P.now_iso(), "shadow:x@pair", coin, d, 10.0, 10.0, 0.0, 0.0, "t"))
    m = lambda px: {"A@bn": px, "A@hl": px}
    st = VP.account_step(s, "shadow:x@pair", m(13.0))
    assert np.allclose([st["accounts"]["hl"], st["accounts"]["bn"]], [470, 530]) and st["transferred"] == 0 and not st["guard"]
    st = VP.account_step(s, "shadow:x@pair", m(20.0))
    assert np.isclose(st["transferred"], 100.0)
    acc = VP.account_equity(s, "shadow:x@pair", m(20.0))
    assert np.allclose([acc["hl"], acc["bn"]], [500, 500])
    assert np.isclose(sum(acc.values()), P.book_equity(s, "shadow:x@pair", m(20.0))[0])
    assert s.q("select count(*) from transfers")[0][0] == 1
    st = VP.account_step(s, "shadow:x@pair", m(30.0))   # HL 500-100 = 400 vs BN 600: transfer again, no guard
    assert np.isclose(st["transferred"], 100.0) and not st["guard"]
    st = VP.account_step(s, "shadow:x@pair", m(60.0))   # HL 500-300 = 200 < 60 % of its 500 peak, before any transfer
    assert st["guard"] and st["transferred"] == 0


def test_whole_pairs_drops_both_legs_when_one_is_below_its_minimum():
    """SMP 11-28: the $200 twin held Binance legs whose HL hedge was below HL's $10 minimum."""
    mins = lambda col: 10.0 if col.endswith("@hl") else 5.0
    t = pd.Series({"AAA@hl": -0.04, "AAA@bn": 0.04, "BBB@hl": -0.06, "BBB@bn": 0.06})
    out = VP.whole_pairs(t, 200.0, mins)                           # AAA: HL leg $8 < $10 -> both 0; BBB: $12 / $12 -> kept
    assert out["AAA@hl"] == 0 and out["AAA@bn"] == 0
    assert out["BBB@hl"] == -0.06 and out["BBB@bn"] == 0.06
    assert VP.whole_pairs(t, 1000.0, mins).equals(t)               # at $1,000 every leg clears its minimum


def test_small_pair_book_never_holds_a_one_legged_pair(env):
    store, cfg, risk, bn_run = env
    cfg["fspread_hold@pair"].update(status="incubation", alloc=0.4)    # small:main@pair legs = .4 x 10 % x $200 = $8: HL leg < $10
    store.ensure_book("small:main@pair", 200.0)
    store.x("insert into positions values('small:main@pair','AAA@bn',0.9)")   # an orphan left by the old engine
    _run(env)
    pos = {c: s for c, s in store.positions("small:main@pair").items() if abs(s) > 0}
    assert pos == {}                                                    # nothing one-legged: the orphan is closed, no new single leg
    big = store.positions("main@pair")
    assert big["AAA@hl"] < 0 < big["AAA@bn"]                             # $40 legs at $1,000 still trade
