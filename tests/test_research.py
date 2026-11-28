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


def test_robustness_reports_the_small_account_when_configured(tmp_path, monkeypatch):
    monkeypatch.setattr(research, "REG", tmp_path / "registry.jsonl")
    risk = tmp_path / "risk.json"
    risk.write_text(json.dumps({"start_equity": 1000.0, "small_equity": 200.0}))
    monkeypatch.setattr(research, "RISK", risk)
    assert research.small_band() == pytest.approx(0.05)
    rb = research.robustness("xsmom", _panel(), {"lookback": 14, "every_days": 1, "top_n": 6}, "t")
    assert "small_acct" in rb
    bands = [json.loads(x)["band"] for x in (tmp_path / "registry.jsonl").read_text().splitlines()]
    assert 0.05 in bands and 0.01 in bands
    risk.write_text(json.dumps({"start_equity": 1000.0}))
    assert research.small_band() is None
    assert "small_acct" not in research.robustness("xsmom", _panel(), {"lookback": 14, "every_days": 1, "top_n": 6}, "t")


def _panel(days=900, n=6, seed=1):
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-01", periods=days, freq="1D", tz="UTC")
    cols = ["BTC"] + [f"C{i}" for i in range(n - 1)]
    close = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0.001, 0.03, (days, n)), axis=0)), idx, cols)
    return {"close": close, "volume": pd.DataFrame(1e8, idx, cols), "high": close * 1.01, "low": close * 0.99,
            "funding": pd.DataFrame(0.0, idx, cols)}


def test_walk_forward_grid_average_known_answer(tmp_path, monkeypatch):
    """One-config grid: the no-selection average IS the walk-forward choice, so both OOS Sharpes agree (2026-11-15)."""
    monkeypatch.setattr(research, "REG", tmp_path / "registry.jsonl")
    p = _panel()
    one = research.walk_forward("tsmom", p, {"top_n": [5]}, "synthetic")
    assert one["oos_grid_avg"] is not None and abs(one["oos_grid_avg"] - one["oos"]["sharpe"]) < 0.01
    two = research.walk_forward("tsmom", p, {"top_n": [5], "every_days": [1, 3]}, "synthetic")
    assert two["oos_grid_avg"] is not None


def test_small_minima_per_venue_and_the_small_account_min_block(tmp_path, monkeypatch):
    """SMR 2026-11-28: Binance symbols use their own minimum (cache), HL $10, pair columns by suffix; robustness reports
    small_acct_min + small_deployed and logs the line with min_w (a robust line: never a walk-forward)."""
    from kripto import venue_bn
    monkeypatch.setattr(venue_bn, "symbol_filters", lambda bn, max_age_h=24: {"BTC": {"step": .001, "min_notional": 50.0}, "ETH": {"step": .001, "min_notional": 20.0}})
    m = research.small_minima(["BTC", "ETH", "DOGE"], "bnall")
    assert m.to_dict() == {"BTC": 50.0, "ETH": 20.0, "DOGE": 5.0}
    assert research.small_minima(["BTC", "DOGE"], "hl").to_dict() == {"BTC": 10.0, "DOGE": 10.0}
    assert research.small_minima(["BTC@bn", "BTC@hl"], "pair").to_dict() == {"BTC@bn": 50.0, "BTC@hl": 10.0}
    monkeypatch.setattr(research, "REG", tmp_path / "registry.jsonl")
    risk = tmp_path / "risk.json"
    risk.write_text(json.dumps({"start_equity": 1000.0, "small_equity": 200.0}))
    monkeypatch.setattr(research, "RISK", risk)
    rb = research.robustness("xsmom", _panel(), {"lookback": 14, "every_days": 1, "top_n": 6}, "t")
    assert "small_acct_min" in rb and 0 <= rb["small_deployed"] <= 1.0 + 1e-9
    lines = [json.loads(x) for x in (tmp_path / "registry.jsonl").read_text().splitlines()]
    assert any(x.get("min_w") == "symbol" and x.get("tag") == "robust" and "kind" not in x for x in lines)


def test_min_weight_never_opens_a_target_below_the_minimum(tmp_path, monkeypatch):
    monkeypatch.setattr(research, "REG", tmp_path / "registry.jsonl")
    p = _panel()
    mw = pd.Series(1.0, p["close"].columns)          # a minimum no weight can reach -> nothing is ever held
    res, _ = research.evaluate("xsmom", p, {"lookback": 14, "every_days": 1, "top_n": 6}, "t", min_weight=mw, log=False)
    assert float(res.weights.abs().sum().sum()) == 0.0
    res0, _ = research.evaluate("xsmom", p, {"lookback": 14, "every_days": 1, "top_n": 6}, "t", min_weight=mw * 0, log=False)
    res1, _ = research.evaluate("xsmom", p, {"lookback": 14, "every_days": 1, "top_n": 6}, "t", log=False)
    assert np.allclose(res0.returns.to_numpy(), res1.returns.to_numpy())   # a zero minimum changes nothing


def test_round_min_places_half_minimum_targets_at_the_minimum(tmp_path, monkeypatch):
    """SMA 11-28: |w| >= half the minimum -> AT the minimum, below half -> 0, above the minimum unchanged, NaN kept."""
    w = pd.DataFrame({"A": [0.04, 0.02, -0.03, np.nan], "B": [0.06, -0.06, 0.0, 0.01]})
    out = research.round_to_min(w, pd.Series({"A": 0.05, "B": 0.05}))
    assert out["A"].iloc[:3].tolist() == [0.05, 0.0, -0.05] and np.isnan(out["A"].iloc[3])
    assert out["B"].tolist() == [0.06, -0.06, 0.0, 0.0]
    monkeypatch.setattr(research, "REG", tmp_path / "registry.jsonl")
    risk = tmp_path / "risk.json"
    risk.write_text(json.dumps({"start_equity": 1000.0, "small_equity": 200.0}))
    monkeypatch.setattr(research, "RISK", risk)
    rb = research.robustness("xsmom", _panel(), {"lookback": 14, "every_days": 1, "top_n": 6}, "t")
    assert "small_acct_round" in rb
