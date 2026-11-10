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
