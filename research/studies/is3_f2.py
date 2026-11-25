"""F2: filters for tsmom@bn, blend@bn, listing_short on bnall 1d through the F0 harness (notes.md section F2).

    .venv/bin/python -m research.studies.is3_f2 a|c|d|e      # explore only (<= 2023)
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from research.studies import is3_filter as F

CFG = json.load(open("config/strategies.json"))
BOOKS = {"tsmom": ("tsmom", CFG["tsmom@bn"]["params"]), "blend": ("blend", {}), "listing_short": ("listing_short", CFG["listing_short"]["params"])}
_cache: dict = {}


def get(name):
    if name not in _cache:
        strat, prm = BOOKS[name]
        _cache[name] = F.book(strat, "bnall", prm)
    return _cache[name]


def touched(w, ww) -> float:
    a, b = F.cut(w.fillna(0).abs().sum(axis=1), "explore"), F.cut((w.fillna(0) - ww).abs().sum(axis=1), "explore")
    return round(float(b.sum() / a.sum()), 4)


def per_year(w, p, s, ww) -> str:
    b, f = F.run(w, p, s), F.run(ww, p, s)
    return " ".join(f"{y}:{F.stats(f[str(y)])['sr'] - F.stats(b[str(y)])['sr']:+.2f}" for y in (2021, 2022, 2023))


def J(tag, name, mask, side, n, note, tf=F.noadd):
    w, p, s = get(name)
    ww = tf(w, mask, side)
    note = f"{note}; touched {touched(w, ww)}; per-year dSR {per_year(w, p, s, ww)}"
    return F.judge(f"F2{tag}_{name}", w, p, s, mask, "explore", side=side, n_random=n, note=note, tf=tf)


def cascade_mask(close: pd.DataFrame, thr: float) -> pd.Series:
    return ~((close / close.shift(1) - 1).median(axis=1) <= thr)


def run_a() -> None:
    """L5 as a DELAY: the day's close after a cascade day (median coin <= thr), no short may be opened or increased (held shorts stay)."""
    for name in BOOKS:
        c = get(name)[1]["close"]
        for thr, n in ((-0.07, 200), (-0.05, 100), (-0.10, 100)):
            m = cascade_mask(c, thr)
            J(f"a_casc{int(-thr * 100)}", name, m, -1, n, f"no new/larger shorts at a cascade day's close (median coin <= {thr:.0%}); days {int((~m).loc[:'2023-12-31'].sum())}")


def run_c() -> None:
    """R8 volume on rallies, new longs only (noadd): c1 spike into a 20-d high blocks; c2 only rallies on FALLING volume may add; c3 mirror."""
    for name in ("tsmom", "blend"):
        w, p, s = get(name)
        c, v = p["close"], p["volume"]
        hi = c >= c.rolling(20, min_periods=20).max()
        for k, n in ((3, 200), (2, 50), (5, 50)):
            sp = v >= k * v.rolling(20, min_periods=20).median().shift(1)
            J(f"c1_spike{k}x", name, ~(hi & sp), 1, n, f"no new longs at a 20-d high on volume >= {k}x the 20-d median")
        rally = c / c.shift(14) - 1 > 0
        vr = v.rolling(7).mean() / v.rolling(7).mean().shift(7)
        for q, n in ((1.0, 200), (0.8, 50)):
            J(f"c2_fallvol{int(q * 100)}", name, ~(rally & (vr >= q)), 1, n, f"new longs only if the 14-d rally's last-7-d volume < {q}x the prior 7 d (R8: rising price, falling volume continues)")
        J("c3_risevol", name, ~(rally & (vr < 1.0)), 1, 100, "mirror: new longs only on RISING volume")


def run_d() -> None:
    """Macro days: flat (or half) through the FOMC / CPI UTC day: the weights set at the previous day's close (row label E-1) are scaled."""
    d = json.load(open("research/is3/C1_dates.json"))
    w, _, _ = get("tsmom")
    idx = w.index
    def mk(dates, before=1):
        ev = pd.DatetimeIndex(pd.to_datetime(dates)).tz_localize(idx.tz) if idx.tz is not None else pd.DatetimeIndex(pd.to_datetime(dates))
        rows = set()
        for b in range(1, before + 1):
            rows |= set(ev - pd.Timedelta(days=b))
        return pd.Series(~idx.isin(list(rows)), idx)
    for name in BOOKS:
        for tag, dates in (("fomc", d["fomc"]), ("cpi", d["cpi"]), ("both", d["fomc"] + d["cpi"])):
            m = mk(dates)
            J(f"d_{tag}_flat", name, m, None, 200 if tag == "both" else 100, f"flat through the {tag} day; days {int((~m).loc[:'2023-12-31'].sum())}", tf=lambda w, m, s: F.scale(w, m, s, 0.0))
        m = mk(d["fomc"] + d["cpi"])
        J("d_both_half", name, m, None, 50, "half size through FOMC+CPI days", tf=lambda w, m, s: F.scale(w, m, s, 0.5))
        m2 = mk(d["fomc"], before=2)
        J("d_fomc_flat2", name, m2, None, 50, "flat the day before AND the FOMC day", tf=lambda w, m, s: F.scale(w, m, s, 0.0))


def run_e() -> None:
    """P5 location of trend ENTRIES (noadd): e1 no adding against location (long below VAL / short above VAH), e2 no adding inside value,
    e3 no adding WITH initiative (long above VAH / short below VAL). VA 70% (50/85 dose for e1)."""
    from research.studies.is3_f1loc import wide
    for name in ("tsmom", "blend"):
        w, p, s = get(name)
        for frac in (70, 50, 85):
            loc = wide(f"loc{frac}", w.index, w.columns)
            for side in (1, -1):
                sg = "L" if side == 1 else "S"
                against = (loc == -1) if side == 1 else (loc == 1)
                J(f"e1_va{frac}{sg}", name, ~against, side, 100 if frac == 70 else 30, f"no adding {sg} against location, VA {frac}%")
                if frac == 70:
                    J(f"e2_va70{sg}", name, ~(loc == 0), side, 100, f"no adding {sg} while close inside VA 70%")
                    withi = (loc == 1) if side == 1 else (loc == -1)
                    J(f"e3_va70{sg}", name, ~withi, side, 100, f"no adding {sg} with initiative (Dalton responsive reading)")


if __name__ == "__main__":
    {"a": run_a, "c": run_c, "d": run_d, "e": run_e}[sys.argv[1]]()
