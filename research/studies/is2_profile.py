"""InSilico second pass, profile / auction rules (research/insilico_pass2.md section 2). Descriptive, not registered.

  nice -n 19 .venv/bin/python -m research.studies.is2_profile [explore|confirm]

explore = 2021-01..2023-12 on the 10 original coins (the only sample this script may be tuned on).
Profiles: 10 bp price bins; time profile (TPO) from each 30-minute period's high/low (exact), volume profile from 1-minute
bars with each bar's volume spread evenly over its range (approximation). Value area = 70% of volume around the POC.

P3  80% rule: open outside yesterday's value area, two consecutive 30-min closes back inside -> trade to the far edge,
    stop 25% of the area's width outside the near edge, out at the day's end. Compared with what a driftless random walk
    gives for the same geometry (probability of target before stop = distance to stop / distance between stop and target).
P2  first touch of yesterday's POC / value-area high / low: return after the touch, signed away from the approach, and
    "+X before -X" (X = 25% of yesterday's value-area width; random walk = 50%). Placebo = the same levels taken from
    the profile 8 days earlier, moved to today's price (same distances, wrong day).
P1  session single prints (band of >= 30 bp inside a session's range visited by one 30-min period only): from the session's
    close, is the band filled (far edge reached) before price moves the same distance the other way (random walk = 50%)?
    And after the fill, does price bounce? Placebo = the band geometry of the same session 8 days earlier.
All returns are log returns in bp BEFORE costs (a taker round trip is ~13 bp, maker entry + taker exit ~9 bp).
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from kripto import data

BIN = np.log(1.001)
SESS = [(0, 420, "asia"), (420, 810, "london"), (810, 1155, "cme"), (1155, 1440, "preclose")]
REP = "DOT BCH TRX ATOM ETC XLM FIL NEAR UNI AAVE MATIC ARB OP APT SUI INJ SAND MANA AXS FTM".split()
SAMPLES = {"explore": ("2021-01-01", "2024-01-01", data.MINUTE_COINS),
           "confirm10": ("2024-01-01", "2026-11-01", data.MINUTE_COINS),      # the original coins, later period
           "rep_a": ("2021-01-01", "2026-11-01", REP[:10]), "rep_b": ("2021-01-01", "2026-11-01", REP[10:])}   # unseen coins


def confirm(c: pd.DataFrame, m: pd.DataFrame):
    """The pre-registered measures B and C (research/batches/2026-11-15-insilico-pass2.json)."""
    def tt(x):
        d = x.groupby(level=0).mean()
        return float(d.mean() / d.std() * np.sqrt(len(d))) if len(d) > 5 and d.std() > 0 else float("nan")
    q = m[m.sess == "cme"].copy()
    for k in ("n24h", "n72h"):
        q["x" + k] = q[k] - q.groupby("coin")[k].transform("mean")          # excess over the coin's own unconditional mean
    print("B US-session momentum (excess over the coin's unconditional mean from 19:15 UTC, bp, day-clustered t)")
    for name, sel in (("up-move >= 1.5%", q.r_s >= 0.015), ("up-move >= 1.5% and closed above a single-print band", (q.r_s >= 0.015) & (q.band == 1)),
                      ("down-move <= -1.5%", q.r_s <= -0.015), ("up-move >= 3%", q.r_s >= 0.03)):
        e = q[sel]
        yrs = {int(y): round(float(g.xn72h.mean() * 1e4)) for y, g in e.groupby(e.index.year)}
        print(f"   {name:52s} n={len(e):5d} 24h {e.xn24h.mean() * 1e4:+7.1f} (t {tt(e.xn24h):+.1f}) | 72h {e.xn72h.mean() * 1e4:+7.1f} (t {tt(e.xn72h):+.1f}) "
              f"| coins>0: {int((e.groupby('coin').xn72h.mean() > 0).sum())}/{e.coin.nunique()} | 72h by year {yrs}")
    r, pl = c[(c.kind == "real")].b30.dropna(), c[(c.kind == "placebo")].b30.dropna()
    dr, dp = r.groupby(level=0).mean(), pl.groupby(level=0).mean()
    w = (dr.mean() - dp.mean()) / np.sqrt(dr.var() / len(dr) + dp.var() / len(dp))
    print(f"C bounce in the 30 min after a single-print band is filled: real {r.mean() * 1e4:+.1f} bp (n={len(r)}) vs placebo {pl.mean() * 1e4:+.1f} bp (n={len(pl)}), "
          f"difference {(r.mean() - pl.mean()) * 1e4:+.1f} bp, t {w:+.1f}")



def profile(h, l, v, per=30):
    lb = np.floor(np.log(l) / BIN).astype(np.int64)
    hb = np.floor(np.log(h) / BIN).astype(np.int64)
    b0, n = int(lb.min()), int(hb.max() - lb.min() + 1)
    d = np.zeros(n + 1)
    w = v / (hb - lb + 1)
    np.add.at(d, lb - b0, w)
    np.add.at(d, hb - b0 + 1, -w)
    t = np.zeros(n + 1)
    for s in range(0, len(h), per):
        t[lb[s:s + per].min() - b0] += 1
        t[hb[s:s + per].max() - b0 + 1] -= 1
    return b0, np.cumsum(d)[:n], np.cumsum(t)[:n]


def value_area(vol, frac=0.7):
    poc = int(vol.argmax())
    lo = hi = poc
    tot, acc = vol.sum(), vol[poc]
    while acc < frac * tot and (lo > 0 or hi < len(vol) - 1):
        dn = vol[lo - 1] if lo > 0 else -1.0
        up = vol[hi + 1] if hi < len(vol) - 1 else -1.0
        if up >= dn:
            hi += 1
            acc += vol[hi]
        else:
            lo -= 1
            acc += vol[lo]
    return poc, lo, hi


def first_passage(H, L, C, t0, up, dn, horizon):
    """From minute t0 (exclusive): +1 if `up` is reached first, -1 if `dn`, 0 if neither within horizon (then C at the end)."""
    end = min(t0 + horizon, len(C) - 1)
    hh, ll = H[t0 + 1:end + 1], L[t0 + 1:end + 1]
    iu = np.argmax(hh >= up) if (hh >= up).any() else 10 ** 9
    il = np.argmax(ll <= dn) if (ll <= dn).any() else 10 ** 9
    if iu == il == 10 ** 9:
        return 0, end
    return (1, t0 + 1 + iu) if iu < il else (-1, t0 + 1 + il)      # same minute: counted against (dn first)


def tday(x: pd.Series) -> float:
    d = x.groupby(level=0).mean()
    return float(d.mean() / d.std() * np.sqrt(len(d))) if len(d) > 5 and d.std() > 0 else float("nan")


def show(name, df, cols):
    if not len(df):
        print(f"  {name}: no events")
        return
    parts = [f"n={len(df)}"]
    for c in cols:
        x = df[c].dropna()
        if c.startswith("p_"):
            parts.append(f"{c}={x.mean():.3f}")
        else:
            parts.append(f"{c}={x.mean() * 1e4:+.1f}bp(t {tday(x):+.1f})")
    pos = int((df.groupby("coin")[cols[-1]].mean() > 0).sum())
    print(f"  {name}: " + " ".join(parts) + f" | coins>0 on last col: {pos}/{df.coin.nunique()}")


def run(sample="explore"):
    start, end, coins = SAMPLES[sample]
    P = data.load_bn_minute_panel(coins, start=start)
    P = {k: v[v.index < end] for k, v in P.items()}
    idx = P["close"].index
    nd = len(idx) // 1440
    days = idx[::1440][:nd]
    p3, p2, p1, sm = [], [], [], []
    for coin in P["close"].columns:
        H, L, C, V = (P[k][coin].to_numpy(dtype=np.float64)[:nd * 1440] for k in ("high", "low", "close", "volume"))
        if np.isnan(C).any():                       # listed after the sample starts: use the part where it trades
            first = int(np.flatnonzero(~np.isnan(C))[0])
            first = (first // 1440 + 1) * 1440
            H, L, C, V = H[first:], L[first:], C[first:], V[first:]
            cdays, cnd = days[first // 1440:], nd - first // 1440
        else:
            cdays, cnd = days, nd
        if cnd < 60:
            continue
        prof = []                                   # per day: poc, val, vah, close
        for d in range(cnd):
            a = d * 1440
            b0, vol, _ = profile(H[a:a + 1440], L[a:a + 1440], V[a:a + 1440] + 1e-9)
            poc, lo, hi = value_area(vol)
            prof.append((np.exp((b0 + poc + 0.5) * BIN), np.exp((b0 + lo) * BIN), np.exp((b0 + hi + 1) * BIN), C[a + 1439]))
        prof = np.array(prof)
        for d in range(9, cnd - 1):
            a = d * 1440
            poc, val, vah, pc = prof[d - 1]
            w = np.log(vah / val)
            O = pc
            # ---------------- P3: 80% rule
            if w >= 0.003 and (O > vah * 1.0005 or O < val * 0.9995):
                side = -1 if O > vah else 1                     # trade back through the value area
                c30 = C[a + 29:a + 1440:30]
                inside = (c30 > val) & (c30 < vah)
                k = np.flatnonzero(inside[1:] & inside[:-1])
                if len(k):
                    t0 = a + (k[0] + 1) * 30 + 29
                    e = C[t0]
                    tgt = val if side < 0 else vah
                    stp = vah * np.exp(0.25 * w) if side < 0 else val * np.exp(-0.25 * w)
                    up, dn = (stp, tgt) if side < 0 else (tgt, stp)
                    res, t1 = first_passage(H, L, C, t0, up, dn, a + 1439 - t0)
                    hit = (res == -1) if side < 0 else (res == 1)
                    stopped = (res == 1) if side < 0 else (res == -1)
                    px = tgt if hit else stp if stopped else C[t1]
                    p_rw = abs(np.log(stp / e)) / abs(np.log(stp / tgt))
                    p3.append((cdays[d], coin, side * np.log(px / e), float(hit), p_rw, float(hit) - p_rw))
            # ---------------- P2: first touch of yesterday's levels (real vs the profile of 8 days earlier)
            x = 0.25 * w
            for kind, src in (("real", d - 1), ("placebo", d - 8)):
                ref = prof[src][3]
                for name, lv in zip(("poc", "val", "vah"), prof[src][:3]):
                    Lv = lv / ref * pc                      # real: unchanged; placebo: same offset from the reference close
                    if abs(np.log(O / Lv)) < 0.002 or x < 0.001:
                        continue
                    side = 1 if O > Lv else -1              # +1: level below price (support, we would buy there)
                    seg = (L[a:a + 1440] <= Lv * 0.9999) if side > 0 else (H[a:a + 1440] >= Lv * 1.0001)
                    if not seg.any():
                        continue
                    t0 = a + int(np.argmax(seg))
                    r30 = side * np.log(C[min(t0 + 30, len(C) - 1)] / Lv)
                    r120 = side * np.log(C[min(t0 + 120, len(C) - 1)] / Lv)
                    up, dn = Lv * np.exp(x), Lv * np.exp(-x)
                    res, _ = first_passage(H, L, C, t0, up, dn, 1440)
                    win = np.nan if res == 0 else float(res == side)
                    p2.append((cdays[d], coin, kind, name, r30, r120, win, side * res * x if res else np.nan))
            # ---------------- P1: single prints of each session of day d (real vs geometry of day d-8)
            for s0, s1, sname in SESS:
                geo = {}
                for kind, dd in (("real", d), ("placebo", d - 8)):
                    aa = dd * 1440
                    b0, _, tpo = profile(H[aa + s0:aa + s1], L[aa + s0:aa + s1], np.ones(s1 - s0))
                    thin = tpo <= 1
                    thin[0] = thin[-1] = False
                    best, i = None, 1
                    while i < len(thin) - 1:                # widest interior run that is not a tail
                        if thin[i]:
                            j = i
                            while thin[j + 1]:
                                j += 1
                            top_tail = not (tpo[j + 1:] >= 2).any()
                            bot_tail = not (tpo[:i] >= 2).any()
                            if not top_tail and not bot_tail and (best is None or j - i > best[1] - best[0]):
                                best = (i, j)
                            i = j + 1
                        else:
                            i += 1
                    if best and best[1] - best[0] + 1 >= 3:
                        ref = C[aa + s1 - 1]
                        geo[kind] = (np.exp((b0 + best[0]) * BIN) / ref, np.exp((b0 + best[1] + 1) * BIN) / ref)
                pc_s = C[a + s1 - 1]
                t0 = a + s1 - 1
                r_s = np.log(pc_s / C[a + s0 - 1])                       # the session's own move
                band = 0
                if "real" in geo and not (geo["real"][0] * pc_s <= pc_s <= geo["real"][1] * pc_s):
                    band = 1 if pc_s > geo["real"][1] * pc_s else -1      # +1: closed above its single-print band (up impulse)
                nxt = lambda m: np.log(C[min(t0 + m, len(C) - 1)] / pc_s)
                sm.append((cdays[d], coin, sname, r_s, band, nxt(240), nxt(1440), nxt(4320)))
                for kind, (lo_r, hi_r) in geo.items():
                    lo_e, hi_e = lo_r * pc_s, hi_r * pc_s
                    if lo_e <= pc_s <= hi_e:
                        continue
                    side = -1 if pc_s > hi_e else 1         # direction price must travel to fill the band
                    far = lo_e if side < 0 else hi_e
                    D = abs(np.log(far / pc_s))
                    other = pc_s * np.exp(-side * D)
                    up, dn = (other, far) if side < 0 else (far, other)
                    res, t1 = first_passage(H, L, C, t0, up, dn, 1440)
                    fill = np.nan if res == 0 else float(res == side)
                    ret = D * (1 if res == side else -1) if res else side * np.log(C[t1] / pc_s)
                    bounce = np.nan
                    if res == side:                         # after the fill: move back out of the band within 2 h
                        bounce = -side * np.log(C[min(t1 + 120, len(C) - 1)] / far)
                    b30 = -side * np.log(C[min(t1 + 30, len(C) - 1)] / far) if res == side else np.nan
                    b480 = -side * np.log(C[min(t1 + 480, len(C) - 1)] / far) if res == side else np.nan
                    p1.append((cdays[d], coin, kind, sname, D, fill, ret, bounce, side, b30, b480))
    print(f"sample {sample}: {start}..{end}, {P['close'].shape[1]} coins, {nd} days")
    a = pd.DataFrame(p3, columns=["day", "coin", "ret", "p_hit", "p_rw", "edge"]).set_index("day")
    print("P3 80% rule (ret = per trade, before costs; edge = hit rate minus the random-walk rate for the same geometry)")
    show("all", a, ["p_hit", "p_rw", "edge", "ret"])
    b = pd.DataFrame(p2, columns=["day", "coin", "kind", "level", "r30", "r120", "p_win", "fp"]).set_index("day")
    print("P2 first touch of yesterday's level (r = return after the touch away from the approach; p_win = +X before -X, random walk 0.5; fp = that bet's return)")
    for lv in ("poc", "val", "vah"):
        for kind in ("real", "placebo"):
            show(f"{lv:3s} {kind:7s}", b[(b.level == lv) & (b.kind == kind)], ["p_win", "r30", "r120", "fp"])
    c = pd.DataFrame(p1, columns=["day", "coin", "kind", "sess", "D", "p_fill", "ret", "bounce", "side", "b30", "b480"]).set_index("day")
    print("P1 session single prints (p_fill = band filled before the same distance the other way, random walk 0.5; ret = that bet; bounce = 2 h after the fill)")
    for kind in ("real", "placebo"):
        show(f"all sessions {kind:7s} (mean band distance {c[c.kind == kind].D.mean() * 1e4:.0f} bp)", c[c.kind == kind], ["p_fill", "bounce", "ret"])
    for s in ("asia", "london", "cme", "preclose"):
        show(f"{s:8s} real", c[(c.kind == "real") & (c.sess == s)], ["p_fill", "bounce", "ret"])
    r = c[c.kind == "real"]
    print("P1 detail, real bands: CME session by year and by direction of the fill (side +1 = band above price, i.e. after a DOWN impulse)")
    for y in sorted(set(r.index.year)):
        show(f"cme {y}", r[(r.sess == "cme") & (r.index.year == y)], ["p_fill", "ret"])
    for sd in (1, -1):
        show(f"cme fill-side {sd:+d}", r[(r.sess == "cme") & (r.side == sd)], ["p_fill", "ret"])
    print("   bounce after the fill by horizon (real vs placebo):")
    for kind in ("real", "placebo"):
        show(f"   {kind:7s}", c[c.kind == kind], ["b30", "bounce", "b480"])
    m = pd.DataFrame(sm, columns=["day", "coin", "sess", "r_s", "band", "n4h", "n24h", "n72h"]).set_index("day")
    for k in ("n4h", "n24h", "n72h"):
        m["f" + k] = np.sign(m.r_s) * m[k]
    print("S session momentum: sign(session move) x what follows, measured from the session's close (follow = positive)")
    for sname in ("asia", "london", "cme", "preclose"):
        q = m[m.sess == sname]
        show(f"{sname:8s} all sessions", q, ["fn4h", "fn24h", "fn72h"])
        show(f"{sname:8s} |move| >= 1.5%", q[q.r_s.abs() >= 0.015], ["fn4h", "fn24h", "fn72h"])
        show(f"{sname:8s} |move| >= 1.5%, closed beyond a single-print band", q[(q.r_s.abs() >= 0.015) & (q.band != 0)], ["fn4h", "fn24h", "fn72h"])
        show(f"{sname:8s} |move| >= 1.5%, no band", q[(q.r_s.abs() >= 0.015) & (q.band == 0)], ["fn4h", "fn24h", "fn72h"])
    q = m[(m.sess == "cme") & (m.r_s.abs() >= 0.015)]
    for y in sorted(set(q.index.year)):
        show(f"cme |move|>=1.5% {y}", q[q.index.year == y], ["fn4h", "fn24h", "fn72h"])
    show("cme |move|>=1.5% up moves", q[q.r_s > 0], ["fn4h", "fn24h", "fn72h"])
    show("cme |move|>=1.5% down moves", q[q.r_s < 0], ["fn4h", "fn24h", "fn72h"])
    confirm(c, m)
    return a, b, c, m


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "explore")
