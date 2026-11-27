"""scripts.ledger_decomp: known-answer split of a book's daily equity change into funding, fees and price."""
import pytest

from kripto import paper as P
from scripts.ledger_decomp import decompose


def test_known_answer(tmp_path):
    s = P.Store(tmp_path / "p.db")
    s.ensure_book("b", 1000.0)
    for ts, eq in (("2026-01-01T00:05:00Z", 1000.0), ("2026-01-02T00:05:00Z", 1010.0), ("2026-01-03T00:05:00Z", 1005.0)):
        s.x("insert into equity values(?,?,?,?,?)", ts, "b", eq, 1.0, 1)
    s.x("insert into funding values(?,?,?,?,?)", "2026-01-01T08:00:00Z", "b", "X", 4.0, 1e-4)
    s.x("insert into fills values(?,?,?,?,?,?,?,?,?)", "2026-01-02T01:00:00Z", "b", "X", 1.0, 10.0, 10.0, 0.5, 0.0, "r")
    d = decompose(s, "b")
    assert list(d["d_eq"]) == [10.0, -5.0]
    assert d["funding"].iloc[0] == 4.0 and d["price"].iloc[0] == pytest.approx(6.0)
    assert d["fees"].iloc[1] == 0.5 and d["price"].iloc[1] == pytest.approx(-4.5)
