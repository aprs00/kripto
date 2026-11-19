"""T5b nightly metrics downloader (2026-11-19): incremental, round-robin, remembers 404s, no network in tests."""
import io
import zipfile

import pandas as pd

from kripto import data


def _zip(day, sym):
    t = pd.date_range(day, periods=3, freq="5min")
    df = pd.DataFrame({"create_time": t.strftime("%Y-%m-%d %H:%M:%S"), "symbol": sym, "sum_open_interest": [1.0, 2, 3],
                       "sum_open_interest_value": [10.0, 20, 30], "count_toptrader_long_short_ratio": 1.1,
                       "sum_toptrader_long_short_ratio": 1.2, "count_long_short_ratio": 1.3, "sum_taker_long_short_vol_ratio": 0.9})
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr(f"{sym}-metrics-{day}.csv", df.to_csv(index=False))
    return b.getvalue()


def test_metrics_incremental(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "METRICS_DIR", tmp_path)
    calls = []

    def get(url):
        calls.append(url)
        sym, day = url.split("/")[-2], url.split("-metrics-")[1][:10]
        if day == "2024-01-03":
            return None                                    # 404
        if day == "2024-01-04":
            return b""                                     # transient failure: retried next night
        return _zip(day, sym)
    targets = {"AAAUSDT": ["2024-01-04", "2024-01-03", "2024-01-02", "2024-01-01"], "BBBUSDT": ["2024-01-02"]}
    assert data.bn_download_metrics(targets, max_files=3, get=get, log=lambda m: None) == 1   # round-robin: A 01-04 (fail), B 01-02 (ok), A 01-03 (404)
    df = pd.read_parquet(tmp_path / "BBBUSDT.parquet")
    assert list(df.columns) == ["t", "oi", "oiv", "top_acct_ls", "top_pos_ls", "all_acct_ls", "taker_ls"] and len(df) == 3
    calls.clear()
    data.bn_download_metrics(targets, max_files=100, get=get, log=lambda m: None)
    assert not any("2024-01-03" in u for u in calls)           # known 404 not retried
    assert not any("BBBUSDT" in u for u in calls)              # already held
    assert any("2024-01-04" in u for u in calls)               # transient failure retried
    a = pd.read_parquet(tmp_path / "AAAUSDT.parquet")
    assert sorted(a["t"].dt.strftime("%Y-%m-%d").unique()) == ["2024-01-01", "2024-01-02"]


def test_targets_point_in_time():
    idx = pd.date_range("2021-01-01", periods=60, freq="1D", tz="UTC")
    v = pd.DataFrame({"A": 1e9, "B": 1e6, "C": 1e7}, idx)
    v.loc[idx[40]:, "B"] = 1e10                               # B becomes big later
    t = data.bn_metrics_targets(top=2, since="2021-01-01", panel={"volume": v})
    assert set(t) == {"AUSDT", "BUSDT", "CUSDT"}
    assert "2021-01-10" not in t["BUSDT"] and "2021-02-25" in t["BUSDT"] and t["AUSDT"][0] > t["AUSDT"][-1]
