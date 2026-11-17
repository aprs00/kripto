import json

import pandas as pd

from kripto import liq

MSG = {"e": "forceOrder", "E": 1763337600123, "o": {"s": "AKEUSDT", "S": "BUY", "o": "LIMIT", "f": "IOC", "q": "1000",
                                                    "p": "0.0125", "ap": "0.0124", "X": "FILLED", "l": "1000", "z": "1000",
                                                    "T": 1763337600100}}


def test_parse_known_message():
    r = liq.parse(json.dumps(MSG))
    assert r["sym"] == "AKEUSDT" and r["side"] == "BUY" and r["T"] == 1763337600100
    assert abs(r["ntl"] - 12.4) < 1e-9
    assert liq.parse({"e": "aggTrade"}) is None
    assert liq.parse({"e": "forceOrder", "o": {"s": "X"}}) is None    # malformed: dropped, never raises


def test_write_and_compact_roundtrip(tmp_path):
    r = liq.parse(MSG)
    day = pd.Timestamp(r["T"], unit="ms", tz="UTC").strftime("%Y-%m-%d")
    liq.write_rows([r, r], d=tmp_path)                    # a duplicate (e.g. replay) is removed at compaction
    liq.log_gap("connect", d=tmp_path)
    liq.compact(d=tmp_path, today=day)                   # the day is still open: untouched
    assert (tmp_path / f"{day}.jsonl").exists()
    liq.compact(d=tmp_path, today="2099-01-01")
    df = pd.read_parquet(tmp_path / f"{day}.parquet")
    assert len(df) == 1 and df["sym"].iloc[0] == "AKEUSDT"
    assert not (tmp_path / f"{day}.jsonl").exists() and (tmp_path / "gaps.jsonl").exists()
