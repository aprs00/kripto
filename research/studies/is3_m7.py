"""M7 a: the day's outlier delta-at-price cell (exact 10-bp profile from aggTrades micro bars) and where it sits -> next day / retest.
notes.md section M7.

Per coin-day (UTC): 10-bp bins, volume and taker delta per bin (mbars.vap). Cells: the most negative and most positive delta bin; dose = |delta| / day volume;
location tercile in the day's range; POC flag. Direction convention 'absorption': a sell cell below the close -> long, a buy cell above the close -> short.
Outcomes: (1) next-day simple return close->close, side-signed; (2) retest: the first touch of the cell's bin within 3 days -> trade in the absorption direction,
fill as of +1 s, exit 60 min later. Baselines: (1) matched days: same coin, same day-return decile x close-location tercile; (2) placebo bin: same day, same side
of the close, |delta| share below the day's median, nearest in distance to the close -> same retest rule.

    nice -n 19 .venv/bin/python -W ignore -m research.studies.is3_m7 explore [b]
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from kripto import mbars
from research.studies import is3_lib as L

COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
BIN = 1e-3                      # 10 bp in log price
LAT, HOLD = 1000, 3_600_000


def load(coin, lo, hi):
    fs = [f for f in sorted((mbars.DIR / coin).glob("????-??-??.npz")) if lo <= f.stem < hi]
    parts = []
    for f in fs:
        with np.load(f) as z:
            d = {k: z[k] for k in ("t1", "h", "l", "c")}
            d["bs"], d["ss"] = z["buy"].sum(1, dtype=np.float64), z["sell"].sum(1, dtype=np.float64)
            parts.append(d)
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


def asof(t1, c, t):
    return c[max(np.searchsorted(t1, t, side="right") - 1, 0)]


def retest(b, i_from, lo_px, hi_px, side, t_end):
    """First micro bar after i_from whose [l, h] overlaps the bin [lo_px, hi_px] before t_end -> side * 60-min return (fills as of +1 s)."""
    t1 = b["t1"]
    e = np.searchsorted(t1, t_end, side="right")
    hit = np.flatnonzero((b["l"][i_from:e] <= hi_px) & (b["h"][i_from:e] >= lo_px))
    if not len(hit):
        return None
    j = i_from + hit[0]
    te = t1[j] + LAT
    p0, p1 = asof(t1, b["c"], te), asof(t1, b["c"], te + HOLD)
    return te, side * (p1 / p0 - 1)


def days(coin, lo, hi):
    b = load(coin, lo, hi)
    day = b["t1"] // 86_400_000
    cut = np.flatnonzero(np.diff(day)) + 1
    st = np.concatenate([[0], cut])
    en = np.concatenate([cut, [len(day)]])
    rows, rt = [], []
    for a, z in zip(st, en):
        if z - a < 50:
            continue
        h, l, c = b["h"][a:z], b["l"][a:z], b["c"][a:z]
        k = np.floor(np.log(np.sqrt(h * l)) / BIN).astype(np.int64)
        k0 = k.min()
        V = np.bincount(k - k0, weights=b["bs"][a:z] + b["ss"][a:z])
        D = np.bincount(k - k0, weights=b["bs"][a:z] - b["ss"][a:z])
        tv = V.sum()
        if tv <= 0:
            continue
        H, Lo, C, O = h.max(), l.min(), c[-1], b["c"][a - 1] if a > 0 else c[0]
        rng = np.log(H / Lo)
        price = lambda i: np.exp((k0 + i + 0.5) * BIN)
        poc = int(V.argmax())
        loc = lambda i: min(int(3 * np.log(price(i) / Lo) / max(rng, 1e-9)), 2)
        closeloc = min(int(3 * np.log(C / Lo) / max(rng, 1e-9)), 2)
        share = np.abs(D) / tv
        med = np.median(share[V > 0])
        for kind, i in (("sell", int(D.argmin())), ("buy", int(D.argmax()))):
            side = 1 if kind == "sell" else -1          # absorption direction
            px = price(i)
            above = px > C
            rows.append({"t": int(b["t1"][z - 1]), "coin": coin, "day": int(day[a]), "kind": kind, "dose": float(share[i]), "loc": loc(i), "poc": i == poc,
                         "below_close": not above, "ret": np.log(C / O), "closeloc": closeloc, "C": C})
            # retest only when the cell is on the absorption side of the close (sell cell below, buy cell above)
            if (kind == "sell" and not above) or (kind == "buy" and above):
                t_end = b["t1"][z - 1] + 3 * 86_400_000
                r = retest(b, z, np.exp((k0 + i) * BIN), np.exp((k0 + i + 1) * BIN), side, t_end)
                ok = (share < med) & (V > 0)
                same = (np.exp((k0 + np.arange(len(V)) + 0.5) * BIN) > C) == above
                cand = np.flatnonzero(ok & same)
                rp = None
                if len(cand):
                    j = cand[np.argmin(np.abs(np.abs((k0 + cand + 0.5) * BIN - np.log(C)) - abs(np.log(px / C))))]
                    rp = retest(b, z, np.exp((k0 + j) * BIN), np.exp((k0 + j + 1) * BIN), side, t_end)
                rt.append({"coin": coin, "kind": kind, "dose": float(share[i]), "loc": loc(i), "real": r, "plc": rp})
    d = pd.DataFrame(rows)
    closes = d.groupby("day")["C"].first()
    nxt = closes.shift(-1) / closes - 1
    d["next"] = d["day"].map(nxt)
    return d, rt


def run(sample):
    lo, hi = L.SAMPLES[sample]
    D, R = [], []
    for coin in COINS:
        d, rt = days(coin, lo, hi)
        D.append(d)
        R += rt
    d = pd.concat(D).dropna(subset=["next"])
    d["side"] = np.where(d.kind == "sell", 1, -1)
    d["gross"] = d["side"] * d["next"]
    d["time"] = pd.to_datetime(d["t"], unit="ms", utc=True)
    d["m"] = d.groupby("coin")["ret"].transform(lambda x: pd.qcut(x, 10, labels=False, duplicates="drop")).astype(str) + "_" + d["closeloc"].astype(str) + "_" + d["kind"]
    d["q"] = d.groupby(["coin", "kind"])["dose"].transform(lambda x: pd.qcut(x, 5, labels=False, duplicates="drop"))
    pd.set_option("display.width", 200)
    print("next-day absorption-signed return (bp) by kind x location tercile x dose quintile; matched = same coin, return decile, close tercile, kind")
    base_m = d.groupby("m")["gross"].mean()
    d["ex"] = d["gross"] - d["m"].map(base_m)
    print((d.pivot_table(index=["kind", "loc"], columns="q", values="ex", aggfunc="mean") * 1e4).round(1).to_string())
    print((d.pivot_table(index=["kind", "loc"], columns="q", values="ex", aggfunc="count")).to_string())
    print("POC cell:", (d.groupby(["kind", "poc"])["ex"].agg(["mean", "count"]).assign(mean=lambda x: x["mean"] * 1e4)).round(1).to_string())
    # card 1: his anomaly at the extreme: top-quintile dose, sell cell in the bottom third (long) / buy cell in the top third (short)
    ev = d[(d.q == 4) & (((d.kind == "sell") & (d["loc"] == 0)) | ((d.kind == "buy") & (d["loc"] == 2)))]
    pool = d[~d.index.isin(ev.index)]
    base = L.matched(ev.assign(m=ev["m"]), pool, k=5)
    L.card("m7a_extreme_absorb", ev[["time", "coin", "side", "gross"]], sample, base=base, note="top-quintile delta cell at the day's extreme, absorption direction, next day c->c")
    # retest
    rr = [x for x in R if x["real"] is not None]
    e2 = pd.DataFrame([{"time": pd.Timestamp(x["real"][0], unit="ms", tz="UTC"), "coin": x["coin"], "side": 1 if x["kind"] == "sell" else -1, "gross": x["real"][1],
                        "dose": x["dose"]} for x in rr])
    p2 = pd.DataFrame([{"time": pd.Timestamp(x["plc"][0], unit="ms", tz="UTC"), "coin": x["coin"], "side": 1 if x["kind"] == "sell" else -1, "gross": x["plc"][1],
                        "dose": x["dose"]} for x in R if x["plc"] is not None])
    hi_t = pd.Timestamp(hi, tz="UTC") - pd.Timedelta("2h")
    e2, p2 = e2[e2.time < hi_t], p2[p2.time < hi_t]
    e2["q"] = pd.qcut(e2.dose, 5, labels=False)
    print("retest 60 min (bp) by dose quintile real:", (e2.groupby("q").gross.mean() * 1e4).round(1).to_dict(), " placebo all:", round(p2.gross.mean() * 1e4, 1))
    L.card("m7a_retest", e2[["time", "coin", "side", "gross"]], sample, base=p2[["time", "coin", "side", "gross"]], note="first retest of the day's outlier delta cell, 60 min, vs low-delta placebo bin same side")
    L.card("m7a_retest_top", e2[e2.q == 4][["time", "coin", "side", "gross"]], sample, base=p2[["time", "coin", "side", "gross"]], note="top dose quintile")


if __name__ == "__main__" and len(sys.argv) <= 2:
    run(sys.argv[1] if len(sys.argv) > 1 else "explore")


# ---------------------------------------------------------------- b: P3's best form with the exact POC
def form_b(sample):
    """First touch within 5 days of a daily POC (exact 10-bp profile), trade toward the approach side (from above -> long), fill as of +1 s,
    60-min return. Placebo: the POC mirrored around the day's close (C^2 / POC), approached from the other side. Dose: POC distance from the
    close and the POC bin's volume share (thin / fat node)."""
    lo, hi = L.SAMPLES[sample]
    out = []
    for coin in COINS:
        b = load(coin, lo, hi)
        day = b["t1"] // 86_400_000
        cut = np.flatnonzero(np.diff(day)) + 1
        st, en = np.concatenate([[0], cut]), np.concatenate([cut, [len(day)]])
        for a, z in zip(st, en):
            if z - a < 50 or z >= len(day):
                continue
            h, l, c = b["h"][a:z], b["l"][a:z], b["c"][a:z]
            k = np.floor(np.log(np.sqrt(h * l)) / BIN).astype(np.int64)
            k0 = k.min()
            V = np.bincount(k - k0, weights=b["bs"][a:z] + b["ss"][a:z])
            i = int(V.argmax())
            C = c[-1]
            lev_lo, lev_hi = np.exp((k0 + i) * BIN), np.exp((k0 + i + 1) * BIN)
            mid = np.sqrt(lev_lo * lev_hi)
            if lev_lo <= C <= lev_hi:
                continue
            dist = abs(np.log(mid / C))
            t_end = b["t1"][z - 1] + 5 * 86_400_000
            side = 1 if mid < C else -1
            r = retest(b, z, lev_lo, lev_hi, side, t_end)
            m_lo, m_hi = C * C / lev_hi, C * C / lev_lo
            rp = retest(b, z, m_lo, m_hi, -side, t_end)
            for kind, x, sd in (("real", r, side), ("mirror", rp, -side)):
                if x is not None:
                    out.append({"time": pd.Timestamp(x[0], unit="ms", tz="UTC"), "coin": coin, "side": sd, "gross": x[1], "kind": kind,
                                "dist": dist, "share": V[i] / V.sum()})
        del b
    d = pd.DataFrame(out)
    d = d[d.time < pd.Timestamp(hi, tz="UTC") - pd.Timedelta("2h")]
    d["dq"] = pd.qcut(d.dist, 4, labels=False)
    d["sq"] = pd.qcut(d.share, 4, labels=False)
    print("60-min bp, real vs mirror by side:\n", (d.pivot_table(index="side", columns="kind", values="gross", aggfunc="mean") * 1e4).round(1).to_string())
    print("by distance quartile:\n", (d.pivot_table(index="dq", columns="kind", values="gross", aggfunc="mean") * 1e4).round(1).to_string())
    print("by POC volume-share quartile (0 = thin):\n", (d.pivot_table(index="sq", columns="kind", values="gross", aggfunc="mean") * 1e4).round(1).to_string())
    e, base = d[d.kind == "real"], d[d.kind == "mirror"]
    for s in (1, -1):
        L.card(f"m7b_poc_touch_side{s:+d}", e[e.side == s][["time", "coin", "side", "gross"]], sample, base=base[base.side == s][["time", "coin", "side", "gross"]],
               note="first touch of exact daily POC within 5 d, 60 min, vs mirrored levels approached from the same side")


# ---------------------------------------------------------------- c: flow AT the level (absorption at the POC touch)
W = 5 * 60_000


def touch_flow(b, i_from, lo_px, hi_px, side, t_end):
    """First touch; then the next 5 min: opposing taker delta share and whether price held (never more than one bin through the level).
    Entry as of touch + 5 min + 1 s, exit 60 min later."""
    t1 = b["t1"]
    e = np.searchsorted(t1, t_end, side="right")
    hit = np.flatnonzero((b["l"][i_from:e] <= hi_px) & (b["h"][i_from:e] >= lo_px))
    if not len(hit):
        return None
    j = i_from + hit[0]
    w_end = np.searchsorted(t1, t1[j] + W, side="right")
    bs, ss = b["bs"][j:w_end].sum(), b["ss"][j:w_end].sum()
    opp = (ss - bs) / max(bs + ss, 1e-9) * side            # > 0 = takers pushing against our trade (sellers into a long)
    if side == 1:
        held = b["l"][j:w_end].min() >= lo_px * (1 - BIN)
    else:
        held = b["h"][j:w_end].max() <= hi_px * (1 + BIN)
    te = t1[j] + W + LAT
    p0, p1 = asof(t1, b["c"], te), asof(t1, b["c"], te + HOLD)
    return te, side * (p1 / p0 - 1), opp, bool(held), bs + ss


def form_c(sample):
    lo, hi = L.SAMPLES[sample]
    out = []
    for coin in COINS:
        b = load(coin, lo, hi)
        day = b["t1"] // 86_400_000
        cut = np.flatnonzero(np.diff(day)) + 1
        st, en = np.concatenate([[0], cut]), np.concatenate([cut, [len(day)]])
        for a, z in zip(st, en):
            if z - a < 50 or z >= len(day):
                continue
            h, l, c = b["h"][a:z], b["l"][a:z], b["c"][a:z]
            k = np.floor(np.log(np.sqrt(h * l)) / BIN).astype(np.int64)
            k0 = k.min()
            V = np.bincount(k - k0, weights=b["bs"][a:z] + b["ss"][a:z])
            i = int(V.argmax())
            C = c[-1]
            lev_lo, lev_hi = np.exp((k0 + i) * BIN), np.exp((k0 + i + 1) * BIN)
            if lev_lo <= C <= lev_hi:
                continue
            side = 1 if lev_hi < C else -1
            t_end = b["t1"][z - 1] + 5 * 86_400_000
            for kind, (x0, x1), sd in (("real", (lev_lo, lev_hi), side), ("mirror", (C * C / lev_hi, C * C / lev_lo), -side)):
                x = touch_flow(b, z, x0, x1, sd, t_end)
                if x is not None:
                    out.append({"time": pd.Timestamp(x[0], unit="ms", tz="UTC"), "coin": coin, "side": sd, "gross": x[1], "kind": kind, "opp": x[2], "held": x[3]})
        del b
    d = pd.DataFrame(out)
    d = d[d.time < pd.Timestamp(hi, tz="UTC") - pd.Timedelta("2h")]
    d["oq"] = d.groupby("coin")["opp"].transform(lambda x: pd.qcut(x, 3, labels=False))
    print("60-min bp after the 5-min window, by held x opposing-delta tercile (2 = most opposing):")
    print((d.pivot_table(index=["held", "oq"], columns="kind", values="gross", aggfunc="mean") * 1e4).round(1).to_string())
    print(d.pivot_table(index=["held", "oq"], columns="kind", values="gross", aggfunc="count").to_string())
    ab = d[(d.kind == "real") & d.held & (d.oq == 2)]
    L.card("m7c_absorb_real", ab[["time", "coin", "side", "gross"]], sample, base=d[(d.kind == "real") & d.held & (d.oq == 0)][["time", "coin", "side", "gross"]],
           note="POC touch, held 5 min against top-tercile opposing delta vs held with the least opposing delta")
    L.card("m7c_absorb_vs_mirror", ab[["time", "coin", "side", "gross"]], sample, base=d[(d.kind == "mirror") & d.held & (d.oq == 2)][["time", "coin", "side", "gross"]],
           note="same condition at mirrored levels")


# ---------------------------------------------------------------- d: stacked diagonal footprint imbalances on 1-h footprint bars
def stacks(ratio_ok: np.ndarray, n: int = 3) -> list[tuple[int, int]]:
    """(first, last) row of each run of >= n consecutive True rows."""
    out, k = [], 0
    for i, v in enumerate(np.append(ratio_ok, False)):
        if v:
            k += 1
        else:
            if k >= n:
                out.append((i - k, i - 1))
            k = 0
    return out


def form_d(sample):
    """1-h footprint bars, 10-bp rows. Buy diagonal imbalance at row p: taker buys at p >= X * taker sells at p-1 (X = 2.5 / 4 / 7.5), row volume
    >= 1% of the bar; sell imbalance mirrored. >= 3 stacked rows = zone: buy zone below the bar close -> support (long on first retest within 3 d),
    sell zone above the close -> resistance (short). Baseline: a 3-row zone in the same bar on the same side of the close, every row's ratio within
    1/1.5..1.5, nearest in distance. Entry as of touch + 1 s, 60 min."""
    lo, hi = L.SAMPLES[sample]
    out = []
    for coin in COINS:
        b = load(coin, lo, hi)
        hr = b["t1"] // 3_600_000
        cut = np.flatnonzero(np.diff(hr)) + 1
        st, en = np.concatenate([[0], cut]), np.concatenate([cut, [len(hr)]])
        for a, z in zip(st, en):
            if z - a < 20 or z >= len(hr):
                continue
            h, l = b["h"][a:z], b["l"][a:z]
            k = np.floor(np.log(np.sqrt(h * l)) / BIN).astype(np.int64)
            k0 = k.min()
            B = np.bincount(k - k0, weights=b["bs"][a:z])
            S = np.bincount(k - k0, weights=b["ss"][a:z])
            if len(B) < 5:
                continue
            tot = (B + S).sum()
            C = b["c"][z - 1]
            vol_ok = (B + S) >= 0.01 * tot
            rb = B[1:] / np.maximum(S[:-1], 1e-9)          # row p (p >= 1): buys at p vs sells at p-1
            rs = S[:-1] / np.maximum(B[1:], 1e-9)          # row p-1: sells at p-1 vs buys at p
            neutral = (rb < 1.5) & (rb > 1 / 1.5) & vol_ok[1:] & vol_ok[:-1]
            price = lambda r: np.exp((k0 + r) * BIN)
            t_end = b["t1"][z - 1] + 3 * 86_400_000
            for X in (2.5, 4.0, 7.5):
                for kind, ok, side in (("buy", (rb >= X) & vol_ok[1:], 1), ("sell", (rs >= X) & vol_ok[:-1], -1)):
                    zs = stacks(ok)
                    for (r0, r1) in zs:
                        rows = (r0 + 1, r1 + 1) if kind == "buy" else (r0, r1)
                        zlo, zhi = price(rows[0]), price(rows[1] + 1)
                        if (side == 1 and zhi >= C) or (side == -1 and zlo <= C):
                            continue
                        dist = abs(np.log(np.sqrt(zlo * zhi) / C))
                        r = retest(b, z, zlo, zhi, side, t_end)
                        if r is not None:
                            out.append({"time": pd.Timestamp(r[0], unit="ms", tz="UTC"), "coin": coin, "side": side, "gross": r[1], "kind": "real", "X": X})
                        if X == 2.5:                          # one baseline zone per real zone (computed once)
                            nz = stacks(neutral)
                            cand = []
                            for (q0, q1) in nz:
                                for q in range(q0, q1 - 1):
                                    blo, bhi = price(q + (1 if kind == "buy" else 0)), price(q + 3 + (1 if kind == "buy" else 0))
                                    if (side == 1 and bhi < C) or (side == -1 and blo > C):
                                        cand.append((abs(abs(np.log(np.sqrt(blo * bhi) / C)) - dist), blo, bhi))
                            if cand:
                                _, blo, bhi = min(cand)
                                rp = retest(b, z, blo, bhi, side, t_end)
                                if rp is not None:
                                    out.append({"time": pd.Timestamp(rp[0], unit="ms", tz="UTC"), "coin": coin, "side": side, "gross": rp[1], "kind": "base", "X": 0})
        del b
    d = pd.DataFrame(out)
    d = d[d.time < pd.Timestamp(hi, tz="UTC") - pd.Timedelta("2h")]
    base = d[d.kind == "base"]
    print("60-min bp by imbalance X and side (base = neutral zones same bar, same side, nearest distance):")
    print((d.pivot_table(index="X", columns="side", values="gross", aggfunc="mean") * 1e4).round(1).to_string())
    print(d.pivot_table(index="X", columns="side", values="gross", aggfunc="count").to_string())
    for X in (2.5, 4.0, 7.5):
        e = d[(d.kind == "real") & (d.X == X)]
        L.card(f"m7d_stack_X{X:g}", e[["time", "coin", "side", "gross"]], sample, base=base[["time", "coin", "side", "gross"]],
               note=f"first retest of >= 3 stacked diagonal imbalance rows (X {X}) from a 1-h footprint bar vs neutral 3-row zones")


if __name__ == "__main__" and len(sys.argv) > 2:
    {"b": form_b, "c": form_c, "d": form_d}[sys.argv[2]](sys.argv[1])
