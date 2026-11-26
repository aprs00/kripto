from datetime import datetime, timezone

import pandas as pd

from scripts import data_status


def test_status_known_answer(tmp_path):
    d = tmp_path / "data" / "bn" / "klines_1d_all"
    d.mkdir(parents=True)
    t = pd.Timestamp("2026-10-31", tz="UTC")
    pd.DataFrame({"t": [int(t.value // 10**6) - 86400000, int(t.value // 10**6)], "c": [1.0, 2.0]}).to_parquet(d / "BTCUSDT.parquet")
    l2 = tmp_path / "data" / "hl" / "l2"
    l2.mkdir(parents=True)
    (l2 / "2026-11-20.jsonl").write_text("")
    (l2 / "2026-11-23.jsonl").write_text("")
    now = datetime(2026, 11, 26, tzinfo=timezone.utc)
    rows = {r["source"]: r for r in data_status.status(tmp_path, now)}
    assert rows["bnall 1d klines"]["age_d"] == 26.0
    assert rows["hl l2"]["last"].startswith("2026-11-23") and rows["hl l2"]["files"] == 2
    assert rows["hl flow (ws)"]["files"] == 0 and rows["hl flow (ws)"]["last"] is None
    assert rows["paper ledger"]["files"] == 0
