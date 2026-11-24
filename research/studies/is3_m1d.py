"""M1d: form a with ADAPTIVE size groups (tg:205: his TSize levels are the previous day's quantiles, 'AI levels'). Each UTC day the 12
fixed bins are merged into <= 7 groups holding ~1/7 of the PREVIOUS day's taker volume each (bins cannot be split, so groups are
coarse at the edges). Everything else = is3_m1 form a (same exits, same within-day matched baseline). Usage: python -m research.studies.is3_m1d explore
"""
from __future__ import annotations

import sys

import numpy as np

from kripto.tsize import NBINS
from research.studies import is3_lib as L
from research.studies import is3_m1 as M

_RB = M.rbars


def rbars_adaptive(b: dict, width: float) -> dict:
    r = _RB(b, width)
    h = b["h"]
    e = r["end"]
    st = np.concatenate([[0], e[:-1] + 1])
    buy, sell = np.add.reduceat(b["buy"], st, axis=0).astype(np.float64), np.add.reduceat(b["sell"], st, axis=0).astype(np.float64)
    day_m = b["t1"] // 86_400_000
    vol_day = {}
    for d in np.unique(day_m):
        m = day_m == d
        vol_day[d] = b["buy"][m].sum(0).astype(np.float64) + b["sell"][m].sum(0)
    day_r = r["t1"] // 86_400_000
    green = np.zeros(len(e), bool)
    red = np.zeros(len(e), bool)
    for d in np.unique(day_r):
        prev = vol_day.get(d - 1)
        ix = np.flatnonzero(day_r == d)
        if prev is None or prev.sum() == 0:
            continue
        cs = np.cumsum(prev) / prev.sum()
        gid = np.minimum((cs - 1e-12) * 7, 6).astype(int)          # group of each bin by the cumulative share it ENDS at
        _, gid = np.unique(gid, return_inverse=True)
        Mx = np.zeros((NBINS, gid.max() + 1))
        Mx[np.arange(NBINS), gid] = 1
        gb, gs = buy[ix] @ Mx, sell[ix] @ Mx
        dd, v = gb - gs, gb + gs
        ne = (v > 0).sum(1)
        need = min(4, Mx.shape[1])
        green[ix] = ((dd > 0) | (v == 0)).all(1) & (ne >= need)
        red[ix] = ((dd < 0) | (v == 0)).all(1) & (ne >= need)
    r["green"], r["red"] = green, red
    return r


if __name__ == "__main__":
    M.rbars = rbars_adaptive
    lo, hi = L.SAMPLES[sys.argv[1]]
    D = M.collect(lo, hi, [0.0043])
    a, ab = D["a"], D["a_base"]
    for r, x in a.groupby("r"):
        y = ab
        print(f"adaptive r={r}: {M.bp(x.gross):+.1f} vs matched {M.bp(M.rew(x, y)):+.1f} n {len(x)} | by yr "
              + " ".join(f"{t}:{M.bp(g.gross) - M.bp(M.rew(g, y[y.time.dt.year == t])):+.1f}" for t, g in x.groupby(x.time.dt.year)))
    x = a[a.r == 1]
    L.card("M1d_r1_w43", x, sys.argv[1], base=L.matched(x, ab), note="form a with previous-day quantile size groups, 0.43% bars")
