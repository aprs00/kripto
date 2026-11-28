"""Paper ledger bookkeeping."""
from kripto.paper import Store


def test_untouched_book_is_resized_but_a_traded_book_is_not(tmp_path):
    s = Store(tmp_path / "p.db")
    s.ensure_book("main", 200.0)
    s.x("insert into equity values('t','main',200.0,0,0)")
    s.resize_untouched("main", 1000.0)
    assert s.q("select cash, start_equity, peak from books where name='main'") == [(1000.0, 1000.0, 1000.0)]
    assert s.q("select count(*) from equity where book='main'") == [(0,)]

    s.ensure_book("shadow:x", 2000.0)
    s.x("insert into fills values('t','shadow:x','BTC',0.01,100.0,100.0,0.0,0.0,'r')")
    s.x("update books set cash=1999.0 where name='shadow:x'")
    s.resize_untouched("shadow:x", 1000.0)
    assert s.q("select cash, start_equity from books where name='shadow:x'") == [(1999.0, 2000.0)]

    s.resize_untouched("main", 1000.0)       # same size: no-op, no extra event
    assert s.q("select count(*) from events where msg like 'resized%'") == [(1,)]


def test_retired_entry_book_is_flattened_once_and_live_books_still_trade(tmp_path):
    import pandas as pd
    from kripto.paper import run_books
    s = Store(tmp_path / "p.db")
    s.ensure_book("shadow:old", 2000.0)
    s.x("insert into positions values('shadow:old','BTC',0.01)")
    s.x("insert into equity values('2026-01-01T00:00:00Z','shadow:old',2000.0,1.0,1)")
    calls = []

    def reb(book, tgt, reason):
        calls.append((book, len(tgt), reason))
        if reason == "retired":
            s.x("update positions set size=0 where book=?", book)
    entries = {"old": {"status": "retired"}, "new": {"status": "candidate"}}
    risk = {"start_equity": 1000.0, "shadow_equity": 2000.0, "kill_drawdown": 0.5, "max_asset_weight": 1.0, "max_gross": 3.0}
    w = {"new": pd.Series({"BTC": 0.5})}
    books = run_books(s, entries, risk, {"BTC": 100.0}, w, "bar1", "main", reb)
    assert ("shadow:old", 0, "retired") in calls and "shadow:old" not in books
    assert any(b == "shadow:new" for b, _, _ in calls)
    assert s.q("select n_pos, gross from equity where book='shadow:old' order by ts desc limit 1") == [(0, 0.0)]
    calls.clear()
    run_books(s, entries, risk, {"BTC": 100.0}, w, "bar2", "main", reb)
    assert not any(b == "shadow:old" for b, _, _ in calls)        # already flat: not touched again


def test_small_account_twins_get_the_same_targets_and_the_min_order_bites(tmp_path):
    """risk.json small_equity adds small:<entry> and small:<main>; a 3% target is $60 in the $2,000 shadow book and
    $6 in the $200 twin, which is under the $10 minimum and must not be opened."""
    import pandas as pd
    from kripto import paper as P
    s = Store(tmp_path / "p.db")
    marks = {"BTC": 100.0, "ETH": 50.0}
    fills = []

    def reb(book, tgt, reason):
        P.rebalance(None, s, book, tgt, marks, {}, reason, fill=lambda c, d: (fills.append((book, c)), (marks[c], marks[c], 0.0))[1])
    entries = {"a": {"status": "candidate"}, "b@bn": {"status": "candidate"}}
    risk = {"start_equity": 1000.0, "shadow_equity": 2000.0, "small_equity": 200.0, "kill_drawdown": 0.5,
            "max_asset_weight": 1.0, "max_gross": 3.0}
    w = {"a": pd.Series({"BTC": 0.30, "ETH": 0.03}), "b@bn": pd.Series({"BTC": 0.30})}
    books = P.run_books(s, entries, risk, marks, w, "bar1", "main", reb)
    assert set(books) == {"shadow:a", "small:a", "shadow:b@bn", "small:b@bn", "main", "small:main"}
    size = dict(s.q("select name, start_equity from books"))
    assert size["small:a"] == 200.0 and size["small:main"] == 200.0 and size["shadow:a"] == 2000.0 and size["main"] == 1000.0
    assert ("shadow:a", "ETH") in fills and ("small:a", "ETH") not in fills      # $60 trades, $6 does not
    assert ("shadow:a", "BTC") in fills and ("small:a", "BTC") in fills          # $60 in the small book does
    assert s.positions("small:a") == {"BTC": 0.6} and not s.positions("small:main")
    assert P.book_venue("small:b@bn") == "bn" and P.book_venue("small:main_bn") == "bn"
    assert P.book_venue("small:a") == "hl" and P.book_venue("small:main") == "hl" and P.book_venue("main_bn") == "bn"

    # without small_equity nothing changes
    s2 = Store(tmp_path / "q.db")
    risk2 = {k: v for k, v in risk.items() if k != "small_equity"}
    assert set(P.run_books(s2, entries, risk2, marks, w, "bar1", "main", lambda *a: None)) == {"shadow:a", "shadow:b@bn", "main"}


def test_order_book_is_fetched_once_per_coin_per_run_when_cached(tmp_path, monkeypatch):
    from kripto import paper as P
    monkeypatch.setattr(P.collect, "store_l2", lambda *a, **k: None)

    class HL:
        n = 0

        def l2_book(self, coin):
            self.n += 1
            return {"levels": [[{"px": "99", "sz": "10"}], [{"px": "101", "sz": "10"}]]}
    hl, cache = HL(), {}
    a = P.simulate_fill(hl, "X", 1.0, cache)
    b = P.simulate_fill(hl, "X", -2.0, cache)
    assert hl.n == 1 and a[0] == 101.0 and b[0] == 99.0
    P.simulate_fill(hl, "Y", 1.0, cache)
    assert hl.n == 2
    cache["X"] = (cache["X"][0] - P.L2_TTL - 1, cache["X"][1])       # stale snapshot is refetched
    P.simulate_fill(hl, "X", 1.0, cache)
    assert hl.n == 3
    P.simulate_fill(hl, "X", 1.0)                                    # no cache: always fetch
    assert hl.n == 4


def test_funding_is_accrued_on_the_positions_held_before_the_trades(tmp_path):
    """run_once accrues HL funding after trading (2026-11-25, fill delay) on a pre-trade snapshot: the hour's funding belongs to
    what was held over that hour, not to what the rebalance just bought."""
    from kripto import paper as P
    s = Store(tmp_path / "p.db")
    s.ensure_book("main", 1000.0)
    s.x("insert into positions values('main','BTC',0.01)")
    s.set_meta("funding_accrued_ms", 1_000)
    held, t0 = P.hl_held(s), 5_000
    s.x("update positions set size=0.03 where book='main' and coin='BTC'")      # the rebalance trades after the snapshot

    class FakeHL:
        def funding_history(self, coin, start, end):
            assert (coin, start, end) == ("BTC", 1_001, 5_000)
            return [{"time": 3_600, "fundingRate": "0.0001"}]
    P.accrue_funding(FakeHL(), s, {"BTC": 50_000.0}, held, t0)
    # long 0.01 BTC at 50,000 = $500 notional pays 1 bp = $0.05 (0.03 would have paid $0.15)
    assert abs(s.cash("main") - (1000.0 - 0.05)) < 1e-9
    assert int(s.get_meta("funding_accrued_ms")) == 5_000


def test_main_scale_multiplies_main_and_small_main_targets_and_triggers_rebalance(tmp_path):
    """AL2b (2026-11-26): risk.json main_scale {book: s} multiplies the main book's mix (and its small twin's); absent = 1;
    a changed scale counts as an allocation change (rebalance on the next run)."""
    import json
    import pandas as pd
    from kripto import paper as P
    s = Store(tmp_path / "p.db")
    s.x("insert into targets values(?,?,?)", "a", "bar0", json.dumps({"BTC": 0.2}))
    got = {}

    def reb(book, tgt, reason):
        got[book] = dict(tgt)
    entries = {"a": {"status": "incubation", "alloc": 1.0}}
    risk = {"start_equity": 1000.0, "shadow_equity": 2000.0, "small_equity": 200.0, "kill_drawdown": 0.5,
            "max_asset_weight": 1.0, "max_gross": 3.0}
    P.run_books(s, entries, risk, {"BTC": 100.0}, {}, "bar1", "main", reb)
    assert abs(got["main"]["BTC"] - 0.2) < 1e-12
    got.clear()
    risk["main_scale"] = {"main": 1.5}
    P.run_books(s, entries, risk, {"BTC": 100.0}, {}, "bar2", "main", reb)
    assert abs(got["main"]["BTC"] - 0.3) < 1e-12 and abs(got["small:main"]["BTC"] - 0.3) < 1e-12


def test_main_scale_known_answer():
    import numpy as np
    import pandas as pd
    from scripts.main_scale import scale_from_returns
    idx = pd.date_range("2025-01-01", periods=400, freq="D", tz="UTC")
    r = pd.Series(np.tile([0.01, -0.01], 200), index=idx)          # daily sd 0.01 -> 19.1% a year
    s, vol = scale_from_returns(r)
    assert abs(vol - 0.01 * np.sqrt(365) * np.sqrt(365 / 364)) < 1e-3 and abs(s - 0.25 / vol) < 1e-9
    assert scale_from_returns(r.iloc[:100])[0] == 1.0                                       # < 120 days -> 1
    assert scale_from_returns(r * 0.1)[0] == 2.0                                            # clipped


def test_a_flip_below_the_minimum_closes_the_old_side(tmp_path):
    """TWC 11-28: small:flow@bn kept DOGE +20 ($1) while its target was a small short: a flip whose new size is below the
    minimum now closes the position instead of leaving the wrong side on; a same-side small change still waits."""
    import pandas as pd
    from kripto import paper as P
    s = Store(tmp_path / "p.db")
    s.ensure_book("small:x", 200.0)
    s.x("insert into positions values('small:x','DOGE',20.0)")
    s.x("insert into positions values('small:x','SOL',0.1)")
    marks = {"DOGE": 0.05, "SOL": 100.0}
    fills = []
    P.rebalance(None, s, "small:x", pd.Series({"DOGE": -0.015, "SOL": 0.06}), marks, {"DOGE": 0, "SOL": 2}, "bar",
                fill=lambda c, d: (fills.append((c, d)), (marks[c], marks[c], 0.0))[1], min_notional=lambda c: 5.0)
    pos = s.positions("small:x")
    assert pos.get("DOGE", 0.0) == 0.0                     # target -$3 < $5: the +$1 long is closed, not kept
    assert pos["SOL"] == 0.1                               # +$2 resize on the same side: below the minimum, waits
    assert fills == [("DOGE", -20.0)]
