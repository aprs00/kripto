"""bn_all_recent tops up the survivorship-free daily panel past the monthly archive (known answers, fake client, tmp DATA)."""
import pandas as pd

from kripto import data

D = 86_400_000
T0 = int(pd.Timestamp("2026-10-01").value // 10**6)       # first archived day


class FakeClient:
    def __init__(self):
        self.calls = []

    def klines(self, sym, interval, start_ms=None, limit=1500):
        self.calls.append(("k", sym, start_ms))
        # 3 bars from start: two closed, the last one still open at now_ms
        return [[start_ms + i * D, "1", "2", "0.5", str(10 + i), "5", start_ms + (i + 1) * D - 1, "100", 7, "2", "40", "0"]
                for i in range(3)]

    def funding_rate(self, sym, start_ms, end_ms=None):
        self.calls.append(("f", sym, start_ms))
        return [{"fundingTime": start_ms + 7, "fundingRate": "0.0001"}]


def _write(tmp_path, sym, days, start=T0):
    kd, fd = tmp_path / "bn" / "klines_1d_all", tmp_path / "bn" / "funding_all"
    kd.mkdir(parents=True, exist_ok=True)
    fd.mkdir(parents=True, exist_ok=True)
    t = [start + i * D for i in range(days)]
    pd.DataFrame({"t": t, "o": 1.0, "h": 1.0, "l": 1.0, "c": 1.0, "v": 1.0, "qv": 1.0, "tbqv": 0.5}).to_parquet(kd / f"{sym}.parquet")
    pd.DataFrame({"time": [x + D - 1 for x in t], "fundingRate": 0.0}).to_parquet(fd / f"{sym}.parquet")


def test_tops_up_live_symbols_only_with_closed_bars(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "DATA", tmp_path)
    _write(tmp_path, "LIVEUSDT", 31)          # through 2026-10-31
    _write(tmp_path, "DEADUSDT", 5, T0 - 60 * D)  # delisted in August (> 45 days before the newest bar)
    last = T0 + 30 * D
    now = last + 3 * D + D // 2               # 11-03 12:00: bars of 11-01 and 11-02 are closed, 11-03 is open
    c = FakeClient()
    assert data.bn_all_recent(client=c, now_ms=now, log=lambda *_: None) == 1
    assert {x[1] for x in c.calls} == {"LIVEUSDT"}
    k = pd.read_parquet(tmp_path / "bn" / "klines_1d_all" / "LIVEUSDT.parquet")
    assert k["t"].iloc[-1] == last + 2 * D and len(k) == 33       # two closed bars added, the open one not
    assert list(k["c"].iloc[-2:]) == [10.0, 11.0] and k["tbqv"].iloc[-1] == 40.0
    f = pd.read_parquet(tmp_path / "bn" / "funding_all" / "LIVEUSDT.parquet")
    assert len(f) == 32 and f["fundingRate"].iloc[-1] == 0.0001
    # the panel loader now reaches past the archive month
    p = data.load_bn_all_panel()
    assert p["close"].index[-1] == pd.Timestamp("2026-11-02", tz="UTC")
