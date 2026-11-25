"""M6 c: consecutive reversals at one level = a range -> fade its edge (notes.md section M6).

Swings from the zigzag of retrace R (0.5 / 1 / 2 %) on micro bars. A swing high is known when the down-reversal confirms it. Event:
the new swing high S_k lies within tol = 0.25R of the previous swing high S_{k-1} ("two reversals at one level"); level = max of the two.
Trade: first return of price to level*(1 - 0.1R) within 24 h (and before price falls a further 2R) -> short at the price as of +1 s,
target level*(1 - R), stop level*(1 + 0.5R), timeout 6 h; exits checked on micro-bar closes, filled as of +1 s. Mirror for double bottoms.
Baseline (same coin, same R, same rules): swing highs whose previous swing high is more than R away (a single reversal at the level).
Placebo (same events): level shifted by +-0.37R. Gross simple returns; costs from the card ladder (taker both legs = 13 bp).

    nice -n 19 .venv/bin/python -W ignore -m research.studies.is3_m6c explore
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from research.studies import is3_lib as L
from research.studies.is3_m6 import COINS, load

LAT = 1000


def swings(h, l, R):
    """(index of confirmation, extreme price, +1 high / -1 low) for each zigzag swing."""
    out, d, E, c0 = [], 0, None, None
    for i in range(len(h)):
        if d == 0:
            c0 = h[0] if c0 is None else c0
            if h[i] >= c0 * (1 + R):
                d, E = 1, h[i]
            elif l[i] <= c0 * (1 - R):
                d, E = -1, l[i]
        elif d == 1:
            E = max(E, h[i])
            if l[i] <= E * (1 - R):
                out.append((i, E, 1))
                d, E = -1, l[i]
        else:
            E = min(E, l[i])
            if h[i] >= E * (1 + R):
                out.append((i, E, -1))
                d, E = 1, h[i]
    return out


def asof(t1, c, t):
    return c[max(np.searchsorted(t1, t, side="right") - 1, 0)]


def trade(b, i0, lev, side, R):
    """side -1 = fade a high (short). Returns (entry time, gross) or None."""
    t1, c = b["t1"], b["c"]
    end = np.searchsorted(t1, t1[i0] + 86_400_000, side="right")
    if side == -1:
        hit, away = c[i0 + 1:end] >= lev * (1 - 0.1 * R), c[i0 + 1:end] <= lev * (1 - 2 * R)
    else:
        hit, away = c[i0 + 1:end] <= lev * (1 + 0.1 * R), c[i0 + 1:end] >= lev * (1 + 2 * R)
    if not hit.any():
        return None
    j = int(hit.argmax())
    if away[:j].any():
        return None
    ie = i0 + 1 + j
    te = t1[ie] + LAT
    pe = asof(t1, c, te)
    s = np.searchsorted(t1, te, side="right")
    e2 = np.searchsorted(t1, te + 6 * 3_600_000, side="right")
    cc = c[s:e2]
    if side == -1:
        done = (cc <= lev * (1 - R)) | (cc >= lev * (1 + 0.5 * R))
    else:
        done = (cc >= lev * (1 + R)) | (cc <= lev * (1 - 0.5 * R))
    if done.any():
        px = asof(t1, c, t1[s + int(done.argmax())] + LAT)
    else:
        px = asof(t1, c, te + 6 * 3_600_000)
    return te, side * (px / pe - 1)


def run(sample: str):
    lo, hi = L.SAMPLES[sample]
    ev, base, plc = [], [], []
    tend = pd.Timestamp(hi, tz="UTC").value // 1_000_000 - 7 * 3_600_000    # entry + 6 h exit inside the sample
    for coin in COINS:
        b = load(coin, lo, hi)
        for R in (0.005, 0.01, 0.02):
            sw = swings(b["h"], b["l"], R)
            for typ in (1, -1):
                s = [x for x in sw if x[2] == typ]
                for k in range(1, len(s)):
                    i0, S, _ = s[k]
                    gap = abs(S / s[k - 1][1] - 1)
                    if gap <= 0.25 * R:
                        kind = "ev"
                        lev = max(S, s[k - 1][1]) if typ == 1 else min(S, s[k - 1][1])
                    elif gap > R:
                        kind, lev = "base", S
                    else:
                        continue
                    side = -typ
                    r = trade(b, i0, lev, side, R)
                    if r is None or r[0] >= tend:
                        continue
                    row = {"time": pd.Timestamp(r[0], unit="ms", tz="UTC"), "coin": coin, "side": side, "gross": r[1], "R": R}
                    (ev if kind == "ev" else base).append(row)
                    if kind == "ev":
                        for f in (-0.37, 0.37):
                            rp = trade(b, i0, lev * (1 + f * R), side, R)
                            if rp is not None and rp[0] < tend:
                                plc.append({"time": pd.Timestamp(rp[0], unit="ms", tz="UTC"), "coin": coin, "side": side, "gross": rp[1], "R": R})
        del b
    E, B, P = pd.DataFrame(ev), pd.DataFrame(base), pd.DataFrame(plc)
    for R in (0.005, 0.01, 0.02):
        e, bb, pp = E[E.R == R], B[B.R == R], P[P.R == R]
        print(f"R {R:.3f}: double n {len(e)} {e.gross.mean()*1e4:+.1f} bp | single n {len(bb)} {bb.gross.mean()*1e4:+.1f} | placebo n {len(pp)} {pp.gross.mean()*1e4:+.1f}"
              f" | by year double/single " + " ".join(f"{y}:{e[e.time.dt.year == y].gross.mean()*1e4:+.1f}/{bb[bb.time.dt.year == y].gross.mean()*1e4:+.1f}" for y in (2021, 2022, 2023)))
        L.card(f"m6c_R{R*100:g}", e, sample, base=bb, note="double reversal level fade vs single-swing fade; placebo printed above")
    return E, B, P


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "explore")
