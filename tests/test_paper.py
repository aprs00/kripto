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
