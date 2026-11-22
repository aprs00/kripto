"""Known-answer tests of the InSilico third-pass test battery (research/studies/is3_lib.py)."""
import numpy as np
import pandas as pd
import pytest

from research.studies import is3_lib as L


@pytest.fixture(autouse=True)
def tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "OUT", tmp_path)
    monkeypatch.setattr(L, "committed_prereg", lambda: L.read_prereg())


def events(mean_bp, n_days=400, per_day=3, seed=0, same_day_equal=False):
    g = np.random.default_rng(seed)
    days = pd.date_range("2021-02-01", periods=n_days, freq="1D", tz="UTC")
    rows = []
    for d in days:
        x = g.normal(mean_bp, 100)
        for k in range(per_day):
            rows.append({"time": d + pd.Timedelta(minutes=k), "coin": f"C{k}", "side": 1,
                         "gross": (x if same_day_equal else g.normal(mean_bp, 100)) / 1e4})
    return pd.DataFrame(rows)


def test_zero_effect_is_not_significant_and_a_planted_one_is():
    z = L.card("T1a", events(0), "explore")
    assert z["p"] > 0.05 and not z["passes"]
    x = L.card("T1b", events(40), "explore")
    assert x["p"] < 0.01 and x["passes"] and abs(x["mean_bp"] - 40) < 10 and x["n"] == 1200


def test_same_day_copies_do_not_inflate_the_evidence():
    a = L.card("T2a", events(0, per_day=1, same_day_equal=True), "explore")
    b = L.card("T2b", events(0, per_day=30, same_day_equal=True), "explore")
    assert b["n"] == 30 * a["n"] and 0.8 < b["se_bp"] / a["se_bp"] < 1.25


def test_effect_equal_to_its_baseline_does_not_pass():
    c = L.card("T3", events(40, seed=1), "explore", base=events(40, seed=2))
    assert c["p"] < 0.01 and c["p_vs_base"] > 0.05 and not c["passes"]


def test_three_lucky_days_do_not_pass():
    e = events(-3)
    e.loc[e.time.dt.floor("D").isin(pd.to_datetime(["2021-03-01", "2021-03-02", "2021-03-03"], utc=True)), "gross"] = 2.0
    c = L.card("T4", e, "explore")
    assert c["mean_bp"] > 0 and c["mean_ex_top3_bp"] < 0 and not c["passes"]


def test_confirm_needs_a_preregistration_and_runs_once():
    with pytest.raises(SystemExit, match="pre-regist"):
        L.card("T5", events(40), "confirmT")
    L.prereg("T5", "goes up", "mean > 0")
    L.card("T5", events(40).assign(time=lambda d: d.time + pd.Timedelta(days=1200)), "confirmT")
    with pytest.raises(SystemExit, match="already"):
        L.card("T5", events(41).assign(time=lambda d: d.time + pd.Timedelta(days=1200)), "confirmT")


def test_vault_needs_a_passed_confirm_card():
    L.prereg("T6", "x", "y")
    v = events(40, n_days=200).assign(time=lambda d: d.time + pd.Timedelta(days=1800))
    with pytest.raises(SystemExit, match="vault"):
        L.card("T6", v, "vault")


def test_events_outside_the_sample_dates_are_refused():
    with pytest.raises(SystemExit, match="outside"):
        L.card("T7", events(0).assign(time=lambda d: d.time + pd.Timedelta(days=1500)), "explore")


def walk(n=4000, phi=0.0, seed=0):
    g = np.random.default_rng(seed)
    e = g.normal(0, 1e-3, (n, 2))
    r = e.copy()
    for t in range(1, n):
        r[t] += phi * r[t - 1]
    idx = pd.date_range("2021-01-01", periods=n, freq="1min", tz="UTC")
    c = pd.DataFrame(100 * np.exp(np.cumsum(r, 0)), idx, ["A", "B"])
    o = c.shift(1).fillna(100.0)
    w = np.abs(g.normal(0, 5e-4, (n, 2)))
    v = pd.DataFrame(g.uniform(1, 2, (n, 2)), idx, ["A", "B"])
    return {"close": c, "high": np.maximum(o, c) * (1 + w), "low": np.minimum(o, c) * (1 - w / 2), "volume": v, "tb": v * 0.6}


def test_surrogate_keeps_volatility_and_kills_momentum():
    p = walk(phi=0.5)
    s = L.surrogate(p, 1)
    r, rs = np.log(p["close"]).diff().iloc[1:], np.log(s["close"]).diff().iloc[1:]
    assert np.allclose(r.abs(), rs.abs(), atol=1e-9)
    assert r["A"].autocorr() > 0.4 and abs(rs["A"].autocorr()) < 0.1
    assert (s["high"] >= s["close"] - 1e-9).all().all() and (s["low"] <= s["close"] + 1e-9).all().all()
    assert np.allclose(p["volume"], s["volume"])
    flip = np.sign(r["A"]) != np.sign(rs["A"])
    assert np.allclose(s["tb"]["A"].iloc[1:][flip] / s["volume"]["A"].iloc[1:][flip], 0.4)


def test_null_check_flags_a_lookahead():
    def cheat(p):
        r = np.log(p["close"]).diff().shift(-1)["A"].dropna()
        x = r[r > 2e-3]
        return pd.DataFrame({"time": x.index, "coin": "A", "side": 1, "gross": x.values})

    def honest(p):
        r = np.log(p["close"]).diff()["A"]
        f = r.shift(-1)
        m = (r > 2e-3) & f.notna()
        return pd.DataFrame({"time": r.index[m], "coin": "A", "side": 1, "gross": f[m].values})
    assert L.null_check(cheat, walk(), n=10)["bad"] is True
    assert L.null_check(honest, walk(), n=10)["bad"] is False
    assert L.check_causal(honest, walk(), "2021-01-03", "10min") is True
    assert L.check_causal(lambda p: honest(p).assign(gross=lambda d: d.gross - d.gross.mean()), walk(), "2021-01-03", "10min") is False


def test_matched_baseline_matches_coin_and_bin_and_excludes_events():
    pool = pd.DataFrame({"time": pd.date_range("2021-01-01", periods=1000, freq="1h", tz="UTC"), "coin": "A", "side": 1,
                         "gross": 0.0, "m": np.arange(1000) % 4})
    ev = pool.iloc[[0, 4, 8]].copy()
    b = L.matched(ev, pool, k=5)
    assert len(b) == 15 and set(b.m) == {0} and not set(b.time) & set(ev.time)


def test_fdr_keeps_strong_and_drops_weak():
    ps = {"a": 0.0005, "b": 0.04, "c": 0.2, "d": 0.5, "e": 0.9}
    assert L.bh(ps, q=0.10) == {"a", "b"} or L.bh(ps, q=0.10) == {"a"}
    assert L.bh({"a": 0.0005, "b": 0.3, "c": 0.4}, q=0.10) == {"a"}
