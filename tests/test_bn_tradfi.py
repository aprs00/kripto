"""Binance stock / commodity perps (TRADIFI_PERPETUAL) are cut from the research panels at their onboarding day (2026-11-22):
live never trades them, so research must not. A reused ticker keeps its earlier life as a coin."""
import json

import pandas as pd

from kripto import data

D = 86_400_000
T0 = int(pd.Timestamp("2026-10-01").value // 10**6)


def _write(root, sym, days, start=T0):
    kd = root / "bn" / "klines_1d_all"
    kd.mkdir(parents=True, exist_ok=True)
    (root / "bn" / "funding_all").mkdir(parents=True, exist_ok=True)
    t = [start + i * D for i in range(days)]
    pd.DataFrame({"t": t, "o": 1.0, "h": 1.0, "l": 1.0, "c": 1.0, "v": 1.0, "qv": 1.0, "tbqv": 0.5}).to_parquet(kd / f"{sym}.parquet")


def test_panel_cuts_tradfi_and_keeps_reused_ticker_history(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "DATA", tmp_path)
    f = tmp_path / "tf.json"
    f.write_text(json.dumps({"STOCKUSDT": T0, "REUSEDUSDT": T0 + 10 * D}))
    monkeypatch.setattr(data, "BN_TRADFI", f)
    for s in ("COINUSDT2", "STOCKUSDT", "REUSEDUSDT", "BTCUSDT"):
        _write(tmp_path, s, 20)
    c = data.load_bn_all_panel()["close"]
    assert "STOCK" not in c.columns                       # stock perp from its first bar: gone
    assert c["BTC"].notna().sum() == 20                   # crypto untouched
    assert c["REUSED"].notna().sum() == 10                # only the bars before the TradFi listing
    assert c["REUSED"].last_valid_index() == pd.Timestamp("2026-10-10", tz="UTC")


def test_update_merges_and_never_removes(tmp_path, monkeypatch):
    f = tmp_path / "tf.json"
    f.write_text(json.dumps({"OLDUSDT": 1}))
    monkeypatch.setattr(data, "BN_TRADFI", f)
    info = {"symbols": [{"symbol": "AAPLUSDT", "contractType": "TRADIFI_PERPETUAL", "onboardDate": 5},
                        {"symbol": "BTCUSDT", "contractType": "PERPETUAL", "onboardDate": 2}]}
    assert data.update_bn_tradfi(info) == 1
    assert data.bn_tradfi() == {"AAPLUSDT": 5, "OLDUSDT": 1}
    assert data.update_bn_tradfi(info) == 0


def test_refresh_marker(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(data, "DATA", tmp_path)
    assert not data.warn_if_refreshing("bnall")
    with data.refreshing("bnall"):
        assert data.warn_if_refreshing("bnall")
        assert "being refreshed" in capsys.readouterr().err
    assert not data.warn_if_refreshing("bnall")
