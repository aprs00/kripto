"""F2 b: execution-hour tilt for the daily books (E2 kill zones / CME break / weekend). notes.md section F2.

The daily books trade at the 00:00 UTC close. Delaying a trade by H hours forgoes the move of the TRADED amount from 00 to 00+H:
D_H(d) = sum_i dw_i(d) * r_i(00 -> 00+H). Mean D_H < 0 (trades lose in their first hours) means a later hour is better.
Per unit traded: D_H / sum|dw|, in bp. Prices from bn100 1h per-coin files (close of the bar before 00+H). Coins without hourly data skipped (coverage printed).

    .venv/bin/python -m research.studies.is3_f2b
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from kripto import data
from research.studies import is3_f2 as F2

HOURS = (1, 2, 4, 6, 8, 12, 14, 16, 20, 23)


def main() -> None:
    for name in ("tsmom", "blend"):
        w, p, _ = F2.get(name)
        w = w.fillna(0.0)
        dw = w.diff().loc["2020-06-01":"2025-12-31"]
        dw = dw.loc[:, dw.abs().sum() > 0]
        exec_t = dw.index + pd.Timedelta(days=1)                 # close of row d = 00:00 of d+1
        res = {H: pd.Series(0.0, dw.index) for H in HOURS}
        cov_num, tot = pd.Series(0.0, dw.index), dw.abs().sum(axis=1)
        for coin in dw.columns:
            f = data.BN100_DIR / f"{coin}USDT.parquet"
            if not f.exists():
                continue
            k = pd.read_parquet(f, columns=["t", "c"])
            s = pd.Series(k.c.to_numpy(), pd.to_datetime(k.t, unit="ms", utc=True)).sort_index()
            s = s[~s.index.duplicated()]
            s.index = s.index + pd.Timedelta(hours=1)               # label = the bar's close time
            if dw.index.tz is None:
                s.index = s.index.tz_convert(None)
            p0 = s.reindex(exec_t).to_numpy()
            d = dw[coin].to_numpy()
            ok = np.isfinite(p0)
            cov_num += np.where(ok, np.abs(d), 0.0)
            for H in HOURS:
                pH = s.reindex(exec_t + pd.Timedelta(hours=H)).to_numpy()
                r = np.where(ok & np.isfinite(pH), pH / p0 - 1, 0.0)
                res[H] += d * r
        traded = cov_num.replace(0, np.nan)
        print(f"\n{name}: traded weight covered by hourly data {cov_num.sum() / tot.sum():.1%}; days {int((traded > 0).sum())}")
        dow = pd.Series(exec_t.dayofweek, dw.index)
        rows = []
        for H in HOURS:
            x = res[H] / traded * 1e4
            yrs = {y: round(float(x[x.index.year == y].mean()), 1) for y in range(2021, 2026)}
            se = x.std() / np.sqrt(x.notna().sum())
            rows.append((H, round(float(x.mean()), 1), round(float(se), 1), yrs, round(float(x[dow >= 5].mean()), 1), round(float(x[dow < 5].mean()), 1)))
        print("H  mean_bp_per_unit_traded  se  per-year  exec-on-weekend  exec-on-weekday   (negative = trades lose in their first H hours, delaying helps)")
        for r in rows:
            print(*r)


if __name__ == "__main__":
    main()
