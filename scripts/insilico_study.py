"""Descriptive tables behind the InSilico rule tests (research/insilico_rules.md; batch 2026-11-11-insilico.json).

  nice -n 19 .venv/bin/python -m scripts.insilico_study calendar            # R21 weekend, R22 Friday close, R23 break hour
  nice -n 19 .venv/bin/python -m scripts.insilico_study tsize               # R1/R2/R6 forward returns after signal days
  nice -n 19 .venv/bin/python -m scripts.insilico_study decomp lshock bnm 1m '{"z":4,"m":5,"e":1.0}' ['{"side":"both"}' ...]
decomp = one config through research.evaluate (logged, tag "diag"): gross / costs / net by year and by era, trade stats.
Extra JSON arguments are variants of the first config (each also evaluated and logged). Nothing here selects parameters.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data, metrics as mx, tsize
from kripto.events import EVENTS
from kripto.research import evaluate

ERA = "2023-01-01"          # the author traded BitMEX/Bybit 2020-22: before / after


def tstat(x) -> float:
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


def by_era(x: pd.Series) -> str:
    out = []
    for name, seg in (("to 2022", x[x.index < ERA]), ("2023+", x[x.index >= ERA])):
        out.append(f"{name}: n={len(seg):4d} mean={seg.mean() * 1e4:+7.1f} bp t={tstat(seg):+5.1f}")
    return "   ".join(out)


# --------------------------------------------------------------------------- calendar
def calendar():
    p = data.load_bn_panel("1h", ["BTCUSDT", "ETHUSDT"])
    c, h, l = p["close"], p["high"], p["low"]
    ny = (c.index + pd.Timedelta(hours=1)).tz_convert("America/New_York")
    wd, hr = np.asarray(ny.weekday), np.asarray(ny.hour)
    print(f"hourly bars {c.index[0]} .. {c.index[-1]}; times are New York (CME) time; returns in bp, gross of costs\n")
    print("R21 weekend gap = Sunday 18:00 price / Friday 17:00 price - 1. 'fade' = -sign(gap) held to Monday 17:00.")
    fri, sun, mon = (np.flatnonzero((wd == a) & (hr == b)) for a, b in ((4, 17), (6, 18), (0, 17)))
    for coin in c.columns:
        px, hi, lo = (x[coin].to_numpy(dtype=float) for x in (c, h, l))
        rows = []
        for f in fri:
            i, j = np.searchsorted(sun, f), np.searchsorted(mon, f)
            if i >= len(sun) or j >= len(mon) or not (f < sun[i] < mon[j]) or mon[j] - f > 100:
                continue
            s, m = sun[i], mon[j]
            g = px[s] / px[f] - 1
            filled = bool(((lo[s + 1:m + 1] <= px[f]) & (hi[s + 1:m + 1] >= px[f])).any())
            rows.append((c.index[s], g, -np.sign(g) * (px[m] / px[s] - 1), filled))
        d = pd.DataFrame(rows, columns=["t", "gap", "fade", "filled"]).set_index("t").dropna()
        for thr in (0.0, 0.005, 0.01, 0.02):
            e = d[d.gap.abs() >= thr]
            print(f"  {coin} |gap|>={thr:.3f}: touched Friday's price by Monday close {e.filled.mean():5.1%} | fade {by_era(e.fade)}")
    print("\nR22 Friday after the US cash close: return 16:00 -> 20:00 (4 h) by weekday")
    r4 = np.log(c.shift(-4) / c)            # bar i closes at hour hr[i]; 4 bars later = +4 h
    at16 = hr == 16
    for coin in c.columns:
        x = r4[coin][at16].dropna()
        w = pd.Series(wd[at16], r4[coin][at16].index).reindex(x.index)
        fr, rest = x[w == 4], x[(w < 4)]
        print(f"  {coin} Friday {by_era(fr)}  | Mon-Thu {by_era(rest)}")
    print("\nR23 legacy break hour 17:00 -> 18:00 (Mon-Thu): signed and absolute 1 h return vs every other hour")
    r1 = np.log(c / c.shift(1))
    brk = (hr == 18) & (wd < 4)
    for coin in c.columns:
        x = r1[coin]
        print(f"  {coin} break hour {by_era(x[brk].dropna())} | |ret| {x[brk].abs().mean() * 1e4:.1f} bp vs {x[~brk].abs().mean() * 1e4:.1f} bp other hours")


# --------------------------------------------------------------------------- trade-size event study
def tsize_study():
    p = data.load_bn_tsize_panel("1d")
    c = p["close"]
    print(f"daily panel {c.index[0].date()} .. {c.index[-1].date()}, coins {list(c.columns)}; forward close-to-close returns in bp")
    for scheme in ("author7", "fine12"):
        for coin in c.columns:
            d = tsize.group(p["ts_delta"][coin].to_numpy(float), scheme)
            v = tsize.group(p["ts_vol"][coin].to_numpy(float), scheme)
            sig = pd.Series(tsize.one_voiced(d, v, 0.01), c.index)
            cvd = pd.Series(d.sum(axis=1) / v.sum(axis=1), c.index)
            z = (cvd - cvd.rolling(90, min_periods=30).mean().shift(1)) / cvd.rolling(90, min_periods=30).std().shift(1)
            low20 = c[coin] <= c[coin].rolling(20).min()
            print(f"\n[{scheme}] {coin}: all-negative days {int((sig == -1).sum())}, all-positive {int((sig == 1).sum())} of {int(c[coin].notna().sum())}")
            for hd in (1, 3, 5):
                f = np.log(c[coin].shift(-hd) / c[coin])
                base = f.dropna()
                print(f"  +{hd}d  all days      {by_era(base)}")
                for name, mask in (("ALL NEGATIVE ", sig == -1), ("all positive ", sig == 1),
                                   ("neg & z<-2   ", (sig == -1) & (z < -2)), ("neg & z>=-2  ", (sig == -1) & (z >= -2)),
                                   ("20d low, neg ", low20 & (sig == -1)), ("20d low, mixed", low20 & (sig != -1))):
                    x = f[mask].dropna()
                    ex = x - base.reindex(x.index).mean() if len(x) else x
                    print(f"       {name} {by_era(x)}   | excess over all days: {x.mean() * 1e4 - base.mean() * 1e4:+7.1f} bp")


# --------------------------------------------------------------------------- one config, decomposed
def decomp(name: str, ds: str, interval: str, base: dict, variants: list[dict]):
    p = data.load_panel(ds, interval)
    label = ds if interval == "4h" else f"{ds}_{interval}"
    for extra in [{}] + variants:
        params = {**base, **extra}
        res, s = evaluate(name, p, params, label, tag="diag")
        r = res.returns[res.gross.cumsum() > 0]
        ppy = mx.periods_per_year(r.index)
        cost = res.costs.reindex(r.index)
        before = r + cost
        print(f"\n== {name} {label} {json.dumps(params)}")
        print("   net  ", {k: s.get(k) for k in ("sharpe", "cagr", "max_dd", "turnover_yr", "cost_yr", "avg_gross")})
        print(f"   before costs: sharpe {mx.sharpe(before, ppy):.2f}, {before.mean() * ppy:+.1%}/yr | costs {cost.mean() * ppy:.1%}/yr")
        yr = pd.DataFrame({"net": r.groupby(r.index.year).sum(), "before_costs": before.groupby(r.index.year).sum(),
                           "costs": cost.groupby(r.index.year).sum(),
                           "sharpe": r.groupby(r.index.year).apply(lambda x: mx.sharpe(x, ppy))}).round(3)
        print(yr.T.to_string())
        for nm, seg in (("to 2022", r[r.index < ERA]), ("2023+", r[r.index >= ERA])):
            print(f"   {nm}: net sharpe {mx.sharpe(seg, ppy):+.2f}, before costs {mx.sharpe((seg + cost.reindex(seg.index)), ppy):+.2f}")
        if name in EVENTS and len(res.trades):
            t = res.trades
            net = t.gross - t.cost
            for nm, m in (("all", slice(None)), ("to 2022", t.time < ERA), ("2023+", t.time >= ERA)):
                g, n_ = t.gross[m], net[m]
                print(f"   trades {nm:8s} n={len(g):6d} win={float((n_ > 0).mean()):5.1%} gross={g.mean() * 1e4:+6.1f} bp "
                      f"cost={t.cost[m].mean() * 1e4:5.1f} bp net={n_.mean() * 1e4:+6.1f} bp (t {tstat(n_):+.1f}) hold={float((t.t_out - t.t_in)[m].mean()):.0f} bars")
            pc = pd.DataFrame({"n": t.groupby("coin").size(), "net_bp": (net.groupby(t.coin).mean() * 1e4).round(1)})
            pc.index = [p["close"].columns[i] for i in pc.index]
            print("   by coin:", pc.T.to_dict())


# --------------------------------------------------------------------------- frozen-config replication on unseen coins
REP = "DOT BCH TRX ATOM ETC XLM FIL NEAR UNI AAVE MATIC ARB OP APT SUI INJ SAND MANA AXS FTM".split()


def replicate():
    """lshock with the config frozen on 2026-11-11 (z=6, m=5, e=1.0), on 20 coins that were not in the test (batch file
    `_lshock_replication`). Two 10-coin halves (RAM); each is one logged config line tagged "replication"."""
    parts = []
    for half in (REP[:10], REP[10:]):
        p = data.load_bn_minute_panel(half)
        res, s = evaluate("lshock", p, {"z": 6, "m": 5, "e": 1.0}, "bnm_rep_1m", tag="replication")
        print("half", list(p["close"].columns), {k: s.get(k) for k in ("sharpe", "cagr", "max_dd", "turnover_yr", "cost_yr")})
        if len(res.trades):
            parts.append(res.trades.assign(coin=[p["close"].columns[i] for i in res.trades.coin]))
        del p
    t = pd.concat(parts)
    net = t.gross - t.cost
    rows = {"all": net, "to 2022": net[t.time < ERA], "2023+": net[t.time >= ERA]}
    for k, x in rows.items():
        print(f"   {k:8s} n={len(x):5d} win={float((x > 0).mean()):5.1%} gross={t.gross[x.index].mean() * 1e4:+7.1f} bp "
              f"net={x.mean() * 1e4:+7.1f} bp t={tstat(x):+.2f}")
    print("   by coin (n, net bp):", {c: (len(g), round(float((g.gross - g.cost).mean() * 1e4), 1)) for c, g in t.groupby("coin")})
    print("   by year (n, net bp):", {int(y): (len(g), round(float((g.gross - g.cost).mean() * 1e4), 1)) for y, g in t.groupby(t.time.dt.year)})
    ok = net.mean() > 0 and tstat(net) > 2 and all(len(rows[k]) and rows[k].mean() > 0 for k in ("to 2022", "2023+"))
    print("verdict by the pre-registered rule:", "REPLICATED" if ok else "NOT REPLICATED")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "replicate":
        replicate()
        sys.exit()
    if cmd == "calendar":
        calendar()
    elif cmd == "tsize":
        tsize_study()
    else:
        decomp(sys.argv[2], sys.argv[3], sys.argv[4], json.loads(sys.argv[5]), [json.loads(x) for x in sys.argv[6:]])
