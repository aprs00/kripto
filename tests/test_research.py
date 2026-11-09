import json

from kripto import research


def test_n_trials_counts_by_kind(tmp_path, monkeypatch):
    reg = tmp_path / "registry.jsonl"
    monkeypatch.setattr(research, "REG", reg)
    assert research.n_trials() == 1 and research.n_trials("walk_forward") == 1  # empty/missing registry
    lines = [{"strategy": "a", "params": {}}] * 5 + [{"kind": "walk_forward", "strategy": "a"}] * 2
    reg.write_text("".join(json.dumps(x) + "\n" for x in lines))
    assert research.n_trials() == 5
    assert research.n_trials("config") == 5
    assert research.n_trials("walk_forward") == 2


# --------------------------------------------------------------------------- band, execution delay, robustness block
import numpy as np
import pandas as pd
import pytest

from kripto import strategies as st


def _panel(T=6 * 260, N=6, seed=2):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=T, freq="4h", tz="UTC")
    names = ["BTC"] + [f"C{i}" for i in range(N - 1)]
    close = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, (T, N)), 0)), idx, names)
    return {"close": close, "volume": pd.DataFrame(1e7, idx, names), "funding": pd.DataFrame(0.0, idx, names)}


def test_default_band_is_min_order_over_main_equity(tmp_path, monkeypatch):
    risk = tmp_path / "risk.json"
    risk.write_text(json.dumps({"start_equity": 1000.0}))
    monkeypatch.setattr(research, "RISK", risk)
    assert research.default_band() == pytest.approx(0.01)
    risk.write_text(json.dumps({"start_equity": 200.0}))
    assert research.default_band() == pytest.approx(0.05)


def test_evaluate_lag_delays_execution_and_is_logged(tmp_path, monkeypatch):
    monkeypatch.setattr(research, "REG", tmp_path / "registry.jsonl")
    p = _panel()

    def toy(panel):                                  # buys A on bar 10 and holds
        w = pd.DataFrame(np.nan, panel["close"].index, panel["close"].columns)
        w.iloc[10] = 0.0
        w.iloc[10, 1] = 1.0
        return w
    monkeypatch.setitem(st.REGISTRY, "toy", toy)
    r0, _ = research.evaluate("toy", p, {}, "t", band=0.0)
    r3, _ = research.evaluate("toy", p, {}, "t", band=0.0, lag=3, tag="robust")
    first = lambda r: int(np.flatnonzero(r.gross.to_numpy() > 0)[0])
    assert first(r0) == 11 and first(r3) == 14       # held from the bar after the (delayed) trade
    lines = [json.loads(x) for x in (tmp_path / "registry.jsonl").read_text().splitlines()]
    assert "lag" not in lines[0] and lines[0]["band"] == 0.0
    assert lines[1]["lag"] == 3 and lines[1]["tag"] == "robust"


def test_robustness_block_has_the_stresses_and_every_phase(tmp_path, monkeypatch):
    monkeypatch.setattr(research, "REG", tmp_path / "registry.jsonl")
    rb = research.robustness("xsmom", _panel(), {"lookback": 14, "every_days": 3, "top_n": 6}, "t")
    for k in ("base", "cost_x2", "delay_1bar", "band_tiny", "skip_first_6m", "corr_btc", "worst"):
        assert k in rb
    assert len(rb["phases"]) == 3 and rb["phase_min"] <= rb["phase_mean"] <= rb["phase_max"]
    assert rb["worst"] <= rb["base"] and rb["cost_x2"] <= rb["base"]
    wf = [json.loads(x) for x in (tmp_path / "registry.jsonl").read_text().splitlines()]
    assert all(x.get("tag") == "robust" and "kind" not in x for x in wf)   # never raises the walk-forward DSR bar
