import json

import pandas as pd

from kripto import paper as P


def test_record_universe_first_run_of_bar_wins(tmp_path):
    store = P.Store(tmp_path / "p.db")
    idx = pd.date_range("2026-11-01", periods=3, freq="4h", tz="UTC")
    p1 = {"close": pd.DataFrame(1.0, idx, ["BTC", "ETH"])}
    p2 = {"close": pd.DataFrame(1.0, idx, ["BTC", "ETH", "AGT"])}
    P.record_universe(store, "bn", p1, str(idx[-1]))
    P.record_universe(store, "bn", p2, str(idx[-1]))      # later hourly run of the same bar: ignored
    P.record_universe(store, "hl", p2, str(idx[-1]))      # other venue: its own row
    rows = dict(((v, b), json.loads(c)) for v, b, c in store.q("select * from universe"))
    assert rows[("bn", str(idx[-1]))] == ["BTC", "ETH"]
    assert rows[("hl", str(idx[-1]))] == ["AGT", "BTC", "ETH"]
