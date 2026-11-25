"""M6 a/b: trend systems on move bars vs time bars with the same number of trades (notes.md section M6).

a: tsmom on range bars (w 0.5/1/2 %, lookback N 5/10/20 bars) vs hourly tsmom whose lookback L is chosen only to match the flips per year.
b: trend-reverse (TR, ATAS rangeUS-like) bars, trend X, reverse R = 0.6X, always in the last bar's direction; variant zigzag (retrace R from
   the running extreme). Same matched hourly baseline.
P&L on the micro-bar grid: a decision at micro bar i fills at the price as of 1 s later (5 s stress); 6 bp per side; simple returns.
(First run filled at the deciding trade itself: 2021-02-22's millisecond +-2 % crash prints made 2,070 fake flips in one day; discarded.)
Null: sign-flipped micro returns (same sizes, coin-toss direction). Bad data days (mbars_bad_days, |dh| or |dl| > 1 %) are dropped from both.

    nice -n 19 .venv/bin/python -m research.studies.is3_m6 a|b|null [sample]
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import mbars
from research.studies import is3_lib as L

COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
TK = 6e-4
LGRID = [1, 2, 3, 4, 6, 8, 12, 16, 24, 36, 48, 72, 96, 144, 192, 288, 384, 576, 768, 1152, 1536]
BAD = json.loads((L.OUT / "mbars_bad_days.json").read_text())


def load(coin: str, start: str, end: str, flow: bool = False) -> dict:
    fs = [f for f in sorted((mbars.DIR / coin).glob("????-??-??.npz")) if start <= f.stem < end]
    parts = []
    for f in fs:
        with np.load(f) as z:
            d = {k: z[k] for k in ("t1", "h", "l", "c")}
            if flow:
                bs, ss = z["buy"].sum(1, dtype=np.float64), z["sell"].sum(1, dtype=np.float64)
                d["v"], d["dl"] = bs + ss, bs - ss
            parts.append(d)
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


def flip(b: dict, seed: int) -> dict:
    r = np.diff(np.log(b["c"]), prepend=np.log(b["c"][0]))
    s = np.random.default_rng(seed).choice([-1.0, 1.0], len(r))
    c = b["c"][0] * np.exp(np.cumsum(r * s))
    cp = np.concatenate([[c[0]], c[:-1]])
    return {"t1": b["t1"], "c": c, "h": np.maximum(c, cp), "l": np.minimum(c, cp)}


def range_ends(h, l, w):
    ends, H, Lo = [], -np.inf, np.inf
    for i in range(len(h)):
        H, Lo = max(H, h[i]), min(Lo, l[i])
        if H / Lo - 1 >= w:
            ends.append(i)
            H, Lo = -np.inf, np.inf
    return np.asarray(ends, dtype=np.int64)


def tr_signal(h, l, c, X, R, zigzag=False):
    """Direction after each micro bar. TR: bars of X in the trend direction from the last bar close C; a reversal bar when price
    moves R against C. zigzag: reverse when price retraces R from the running extreme E."""
    out = np.zeros(len(c))
    d, C = 0, c[0]
    for i in range(len(c)):
        hi, lo = h[i], l[i]
        if zigzag:
            if d == 0:
                if hi >= C * (1 + R):
                    d, C = 1, hi
                elif lo <= C * (1 - R):
                    d, C = -1, lo
            elif d == 1:
                C = max(C, hi)
                if lo <= C * (1 - R):
                    d, C = -1, lo
            else:
                C = min(C, lo)
                if hi >= C * (1 + R):
                    d, C = 1, hi
        else:
            if d == 0:
                if hi >= C * (1 + X):
                    d = 1
                elif lo <= C * (1 - X):
                    d = -1
            if d == 1:
                while hi >= C * (1 + X):
                    C *= 1 + X
                if lo <= C * (1 - R):
                    d, C = -1, C * (1 - R)
            elif d == -1:
                while lo <= C * (1 - X):
                    C *= 1 - X
                if hi >= C * (1 + R):
                    d, C = 1, C * (1 + R)
        out[i] = d
    return out


def pf_signal(h, l, B, rev=3):
    """Point & figure, log boxes of B, `rev`-box reversal. Long when an X column rises above the previous X column's top
    (double-top break), short when an O column falls below the previous O column's bottom; held until the opposite break."""
    out = np.zeros(len(h))
    u, k = np.log1p(B), rev
    lh, ll = np.log(h), np.log(l)
    col, top, bot, pX, pO, pos = 0, np.floor(lh[0] / u), np.floor(ll[0] / u), np.inf, -np.inf, 0
    for i in range(len(h)):
        H, Lw = np.floor(lh[i] / u), np.ceil(ll[i] / u)
        if col >= 0 and H > top:
            top, col = H, 1
        elif col <= 0 and Lw < bot:
            bot, col = Lw, -1
        if col == 1 and Lw <= top - k:
            pX, bot, col = top, Lw, -1
        elif col == -1 and H >= bot + k:
            pO, top, col = bot, H, 1
        if col == 1 and top > pX:
            pos = 1
        elif col == -1 and bot < pO:
            pos = -1
        out[i] = pos
    return out


def flow_ends(b: dict, kind: str, K: float) -> np.ndarray:
    """Volume bars (notional) or delta bars (|cumulative taker delta|) whose size is the previous 30 days' mean daily notional / K (causal)."""
    day = b["t1"] // 86_400_000
    dv = pd.Series(b["v"]).groupby(day).sum()
    size = (dv.rolling(30, min_periods=10).mean().shift(1) / K).reindex(day).to_numpy()
    x = b["v"] if kind == "vol" else b["dl"]
    ends, acc = [], 0.0
    for i in range(len(x)):
        if np.isnan(size[i]):
            continue
        acc += x[i]
        if abs(acc) >= size[i]:
            ends.append(i)
            acc = 0.0
    return np.asarray(ends, dtype=np.int64)


def hourly_targets(t1, c, Lh):
    """Hourly tsmom: sign of the last close of hour h vs hour h-L, set at the last micro bar of hour h."""
    hr = t1 // 3_600_000
    last = np.flatnonzero(np.diff(hr, append=hr[-1] + 1) != 0)       # last micro bar index of each hour present
    H = hr[last]
    grid = np.arange(H[0], H[-1] + 1)
    cc = pd.Series(c[last], index=H).reindex(grid).ffill().to_numpy()
    sig = np.full(len(grid), np.nan)
    sig[Lh:] = np.sign(cc[Lh:] / cc[:-Lh] - 1)
    tgt = np.full(len(c), np.nan)
    tgt[last] = sig[H - H[0]]
    return tgt


def pnl(b: dict, tgt: np.ndarray, lat_ms: int = 1000) -> tuple[pd.DataFrame, pd.DataFrame]:
    """tgt: decided position at micro bars (nan = unchanged). A decision at micro bar i takes effect at the price as of t1[i] + lat_ms
    (the close of the last micro bar finished by then; several decisions inside one latency window collapse to the last one).
    -> daily (gross, cost) and trade list."""
    idx = np.flatnonzero(~np.isnan(tgt))
    j = np.searchsorted(b["t1"], b["t1"][idx] + lat_ms, side="right") - 1
    eff = pd.Series(tgt[idx]).groupby(j).last()
    t2 = np.full(len(tgt), np.nan)
    t2[eff.index.to_numpy()] = eff.to_numpy()
    pos = pd.Series(t2).ffill().fillna(0).to_numpy()
    pos = np.concatenate([[0.0], pos[:-1]])                       # held over micro bar i's return
    c = b["c"]
    r = np.concatenate([[0.0], c[1:] / c[:-1] - 1])
    dpos = np.abs(np.diff(pos, prepend=0.0))
    day = pd.to_datetime(b["t1"], unit="ms", utc=True).floor("D")
    d = pd.DataFrame({"gross": pos * r, "cost": dpos * TK, "flips": dpos > 0}).groupby(day).sum()
    # trades: runs of constant non-zero position (entry = the bar before the first held return)
    ch = np.flatnonzero(np.diff(pos, prepend=0.0) != 0)
    tr = []
    for k, s in enumerate(ch):
        e = ch[k + 1] if k + 1 < len(ch) else len(pos)
        if pos[s] != 0:
            tr.append((b["t1"][s - 1], pos[s], pos[s] * (c[e - 1] / c[s - 1] - 1)))
    t = pd.DataFrame(tr, columns=["t", "side", "gross"])
    t["time"] = pd.to_datetime(t["t"], unit="ms", utc=True)
    return d, t.drop(columns="t")


def drop_bad(d: pd.DataFrame, coin: str) -> pd.DataFrame:
    bad = [pd.Timestamp(k, tz="UTC") for k, v in BAD.get(coin, {}).items() if abs(v.get("dh", 0)) > 0.01 or abs(v.get("dl", 0)) > 0.01]
    return d.drop(index=[x for x in bad if x in d.index])


def sr(x: pd.Series) -> float:
    return float(x.mean() / (x.std() + 1e-18) * np.sqrt(365))


def block_p(diff: pd.Series, reps=2000, block=20, seed=5) -> tuple[float, float]:
    """mean daily diff (bp) and two-sided p, moving-block bootstrap (20-day blocks)."""
    x = diff.to_numpy()
    n = len(x)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    ms = np.empty(reps)
    for k in range(reps):
        st = rng.integers(0, n - block, nb)
        ms[k] = np.concatenate([x[s:s + block] for s in st])[:n].mean()
    ms = ms - ms.mean()
    return float(x.mean() * 1e4), float((np.abs(ms) >= abs(x.mean())).mean())


def matched_time(b, flips_target, cache):
    best = None
    for Lh in LGRID:
        if Lh not in cache:
            cache[Lh] = pnl(b, hourly_targets(b["t1"], b["c"], Lh))
        f = cache[Lh][0]["flips"].sum()
        sc = abs(np.log((f + 1) / (flips_target + 1)))
        if best is None or sc < best[0]:
            best = (sc, Lh)
    return best[1]


def run(form: str, sample: str, null_seed: int | None = None):
    lo, hi = L.SAMPLES[sample]
    rows, trades, tbase = [], [], []
    pooled = {}
    for coin in COINS:
        b = load(coin, lo, hi, flow=form == "e")
        if null_seed is not None:
            b = flip(b, null_seed + COINS.index(coin))
        cache = {}
        if form == "a":
            cfgs = []
            for w in (0.005, 0.01, 0.02):
                e = range_ends(b["h"], b["l"], w)
                rc = b["c"][e]
                for N in (5, 10, 20):
                    tgt = np.full(len(b["c"]), np.nan)
                    tgt[e[N:]] = np.sign(rc[N:] / rc[:-N] - 1)
                    cfgs.append((f"w{w*100:g}N{N}", tgt))
        elif form == "e":
            cfgs = []
            for kind, Ks in (("vol", (48, 192)), ("dlt", (200, 800))):
                for K in Ks:
                    e = flow_ends(b, kind, K)
                    rc = b["c"][e]
                    for N in (5, 20):
                        tgt = np.full(len(b["c"]), np.nan)
                        tgt[e[N:]] = np.sign(rc[N:] / rc[:-N] - 1)
                        cfgs.append((f"{kind}{K}N{N}", tgt))
                    if kind == "dlt":
                        sg = np.sign(np.add.reduceat(b["dl"], np.concatenate([[0], e[:-1] + 1]))) if len(e) else []
                        tgt = np.full(len(b["c"]), np.nan)
                        tgt[e] = sg
                        cfgs.append((f"dlt{K}sign", tgt))
        elif form == "d":
            cfgs = []
            for B in (0.0025, 0.005, 0.01, 0.02):
                s = pf_signal(b["h"], b["l"], B)
                cfgs.append((f"pf{B*100:g}", np.where(np.diff(s, prepend=0) != 0, s, np.nan)))
        else:
            cfgs = []
            for X in (0.005, 0.01, 0.02, 0.04):
                for zz in (False, True):
                    s = tr_signal(b["h"], b["l"], b["c"], X, 0.6 * X, zz)
                    tgt = np.where(np.diff(s, prepend=0) != 0, s, np.nan)
                    cfgs.append((f"{'zz' if zz else 'tr'}{X*100:g}", tgt))
        for name, tgt in cfgs:
            d, t = pnl(b, tgt)
            d1, _ = pnl(b, tgt, lat_ms=5000)
            f = d["flips"].sum()
            Lh = matched_time(b, f, cache)
            dt, tt = cache[Lh]
            d, d1, dt = drop_bad(d, coin), drop_bad(d1, coin), drop_bad(dt, coin)
            net, netd, nett = d.gross - d.cost, d1.gross - d1.cost, dt.gross - dt.cost
            yrs = {}
            for y in sorted(set(d.index.year)):
                m = d.index.year == y
                mt = dt.index.year == y
                yrs[int(y)] = round(sr(net[m]) - sr(nett[mt]), 2)
            diff = (net - nett).dropna()
            mdiff, p = block_p(diff)
            yrs_n = len(d) / 365
            rows.append({"coin": coin[:3], "cfg": name, "flips_yr": round(f / yrs_n), "L_h": Lh, "flips_t_yr": round(dt["flips"].sum() / yrs_n),
                         "SRg": round(sr(d.gross), 2), "SRn": round(sr(net), 2), "SRn_5s": round(sr(netd), 2),
                         "SRg_t": round(sr(dt.gross), 2), "SRn_t": round(sr(nett), 2), "diff_bp_d": round(mdiff, 2), "p": round(p, 3), "yr_dSR": yrs})
            pooled.setdefault(name, []).append((net, nett))
            t["coin"], t["cfg"] = coin, name
            tt = tt.assign(coin=coin, cfg=name)
            trades.append(t)
            tbase.append(tt)
        del b, cache
    df = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    print(df.to_string(index=False))
    print("\npooled equal-weight 3 coins (net daily):")
    for name, v in pooled.items():
        a = pd.concat([x[0] for x in v], axis=1).mean(1)
        t = pd.concat([x[1] for x in v], axis=1).mean(1)
        m, p = block_p((a - t).dropna())
        print(f"  {name:8s} SRn move {sr(a):+.2f}  time {sr(t):+.2f}  diff {m:+.2f} bp/d p {p:.3f}  by year move/time "
              + " ".join(f"{y}:{sr(a[a.index.year == y]):+.2f}/{sr(t[t.index.year == y]):+.2f}" for y in sorted(set(a.index.year))))
    return df, pd.concat(trades), pd.concat(tbase)


if __name__ == "__main__":
    form = sys.argv[1]
    sample = sys.argv[2] if len(sys.argv) > 2 else "explore"
    if form == "null":
        for f in ("a", "b", "d"):
            print(f"== null {f}")
            run(f, sample, null_seed=11)
        sys.exit()
    df, tr, tb = run(form, sample)
    df.to_csv(L.OUT / f"m6{form}_{sample}.csv", index=False)
    if sample == "explore":
        for key in sorted(tr.cfg.unique()):
            e, base = tr[tr.cfg == key], tb[tb.cfg == key]
            L.card(f"m6{form}_{key}", e, sample, base=base, note="per-trade gross, base = hourly tsmom with matched flips, same coin")
