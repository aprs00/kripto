"""Known-answer check: load_bn_panel(lean=True) (bn100, 2026-11-19) must equal the original path except dtype and high/low."""
import numpy as np
import pandas as pd

from kripto import data


def _write(tmp, sym, start, n, seed, with_funding=True):
    rng = np.random.default_rng(seed)
    t = pd.date_range(start, periods=n, freq="1h", tz="UTC")
    ms = (t - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(milliseconds=1)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    qv = rng.uniform(0, 1e6, n)
    qv[3] = 0.0                                      # a zero-volume bar must become NaN in close and volume
    pd.DataFrame({"t": ms, "c": c, "qv": qv, "h": c * 1.01, "l": c * 0.99}).to_parquet(tmp / "k" / f"{sym}.parquet")
    if with_funding:
        ft = ms[::8] + 1
        pd.DataFrame({"time": ft, "fundingRate": rng.normal(0, 1e-4, len(ft))}).to_parquet(tmp / "f" / f"{sym}.parquet")


def test_lean_equals_full(tmp_path):
    (tmp_path / "k").mkdir(); (tmp_path / "f").mkdir()
    _write(tmp_path, "AAAUSDT", "2024-01-01", 200, 1)
    _write(tmp_path, "BBBUSDT", "2024-01-03", 150, 2, with_funding=False)   # later listing, no funding file
    _write(tmp_path, "CCCUSDT", "2023-12-30", 60, 3)                         # delisted early
    full = data.load_bn_panel("1h", kdir=tmp_path / "k", fdir=tmp_path / "f")
    lean = data.load_bn_panel("1h", kdir=tmp_path / "k", fdir=tmp_path / "f", lean=True)
    assert set(lean) == {"close", "volume", "funding"}
    for k in lean:
        a, b = lean[k], full[k]
        assert list(a.index) == list(b.index) and list(a.columns) == list(b.columns)
        assert a.dtypes.iloc[0] == np.float32
        np.testing.assert_array_equal(a.isna().to_numpy(), b.isna().to_numpy())
        np.testing.assert_allclose(a.to_numpy(float), b.to_numpy(float), rtol=1e-6, equal_nan=True)
    assert np.isnan(lean["close"].loc[pd.Timestamp("2024-01-01 03:00", tz="UTC"), "AAA"])
    assert np.isfinite(lean["close"].loc[pd.Timestamp("2024-01-01 04:00", tz="UTC"), "AAA"])
