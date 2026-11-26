"""T5b: how complete is the Binance positioning-metrics backfill, per year? (2026-11-26)
The nightly job fills coin-days NEWEST FIRST per coin, so an incomplete early year holds only coins with short top-60 spells (on 11-26
BTC started 2024-07 while 2022 already had 13k coin-days): exploring such a year studies a biased subset. Run this before any T5b study;
explore a year only when its coverage is >= 95 %.

    nice -n 19 .venv/bin/python -m scripts.metrics_coverage
"""
import collections

import pandas as pd

from kripto import data


def coverage(targets: dict[str, list[str]]) -> dict[int, tuple[int, int]]:
    """{year: (fetched or known-404 coin-days, target coin-days)}."""
    import json
    miss_p = data.METRICS_DIR / "_missing.json"
    missing = set(json.loads(miss_p.read_text())) if miss_p.exists() else set()
    got, tot = collections.Counter(), collections.Counter()
    for sym, days in targets.items():
        f = data.METRICS_DIR / f"{sym}.parquet"
        have = set(pd.read_parquet(f, columns=["t"])["t"].dt.strftime("%Y-%m-%d")) if f.exists() else set()
        for d in days:
            y = int(d[:4])
            tot[y] += 1
            got[y] += d in have or f"{sym}/{d}" in missing
    return {y: (got[y], tot[y]) for y in sorted(tot)}


if __name__ == "__main__":
    cov = coverage(data.bn_metrics_targets())
    for y, (g, t) in cov.items():
        print(f"{y}: {g:6d} / {t:6d} coin-days = {g / t:5.1%}{'' if g / t >= 0.95 else '  <- incomplete: do not explore this year yet'}")
