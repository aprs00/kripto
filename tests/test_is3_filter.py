"""Known-answer tests of the F0 filter harness (research/studies/is3_filter.py)."""
import numpy as np
import pandas as pd
import pytest

from research.studies import is3_filter as F
from research.studies import is3_lib as L


@pytest.fixture(autouse=True)
def tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "OUT", tmp_path)


def synth(T=900, N=6, seed=1):
    g = np.random.default_rng(seed)
    idx = pd.date_range("2021-01-01", periods=T, freq="1D")
    r = g.normal(0.0005, 0.03, (T, N))
    close = pd.DataFrame(100 * np.cumprod(1 + r, 0), idx, [f"C{i}" for i in range(N)])
    panel = {"close": close}
    w = pd.DataFrame(1.0 / N, idx, close.columns)            # equal-weight long book
    return w, panel, r


def test_all_true_mask_is_identity():
    w, panel, _ = synth()
    m = pd.DataFrame(True, w.index, w.columns)
    a, b = F.run(w, panel, None, band=0.0), F.run(F.apply(w, m), panel, None, band=0.0)
    assert np.allclose(a.to_numpy(), b.to_numpy())


def test_random_masks_keep_share_and_runs():
    g = np.random.default_rng(3)
    idx = pd.date_range("2021-01-01", periods=300, freq="1D")
    m = pd.DataFrame(np.repeat(g.random((30, 4)) < 0.6, 10, axis=0), idx, list("ABCD"))   # runs of 10
    for rm in F.random_masks(m, 5, seed=1):
        assert (rm.sum() == m.sum()).all()
        changes = lambda x: int((x.astype(int).diff().abs() > 0).sum().sum())
        assert abs(changes(rm) - changes(m)) <= 2 * m.shape[1]          # the wrap-around joint may add one change per column


def test_oracle_filter_beats_random_and_random_filter_does_not():
    w, panel, r = synth(T=1200)
    # oracle: block a coin on day t when its NEXT bar loses (weights at close t are held over bar t+1): pure look-ahead, must win
    nxt = pd.DataFrame(np.vstack([r[1:], np.zeros((1, r.shape[1]))]), w.index, w.columns)
    oracle = nxt > -0.01
    out = F.judge("T_oracle", w, panel, None, oracle, "explore", n_random=40)
    assert out["pct_dSR_vs_random"] >= 0.95 and out["passes"]
    g = np.random.default_rng(9)
    rnd = pd.DataFrame(np.repeat(g.random((120, w.shape[1])) < 0.7, 10, axis=0), w.index, w.columns)
    out2 = F.judge("T_random", w, panel, None, rnd, "explore", n_random=40)
    assert 0.02 <= out2["pct_dSR_vs_random"] <= 0.98


def test_side_mask_only_touches_that_side():
    w, panel, _ = synth()
    w = w.copy()
    w.iloc[:, :3] = -w.iloc[:, :3]
    m = pd.DataFrame(False, w.index, w.columns)
    out = F.apply(w, m, side=-1)
    assert (out.iloc[:, :3] == 0).all().all() and (out.iloc[:, 3:] == w.iloc[:, 3:]).all().all()


def test_confirm_needs_prereg(monkeypatch):
    w, panel, _ = synth()
    monkeypatch.setattr(L, "committed_prereg", lambda: {})
    with pytest.raises(SystemExit):
        F.judge("T_x", w, panel, None, pd.DataFrame(True, w.index, w.columns), "confirmT", n_random=2)


def test_noadd_delays_new_shorts_only():
    idx = pd.date_range("2021-01-01", periods=4, freq="1D")
    w = pd.DataFrame({"A": [-0.1, -0.3, -0.3, -0.3], "B": [0.2, -0.2, -0.2, 0.1], "C": [-0.2, -0.1, -0.1, -0.1]}, idx)
    m = pd.Series([True, False, True, True], idx)
    out = F.noadd(w, m, side=-1)
    assert out["A"].tolist() == [-0.1, -0.1, -0.3, -0.3]        # increase delayed one day, then the target
    assert out["B"].tolist() == [0.2, 0.0, -0.2, 0.1]           # long -> short flip: short not opened on the blocked day
    assert out["C"].tolist() == [-0.2, -0.1, -0.1, -0.1]        # shrinking a short is always allowed
    out2 = F.noadd(w, m, side=1)
    assert np.allclose(out2.to_numpy(), w.to_numpy())            # nothing to block on the long side here
