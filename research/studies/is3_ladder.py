"""InSilico third pass, item T1: resting bids (and offers) k sigma away from the last close, re-quoted every minute.

  nice -n 19 .venv/bin/python -m research.studies.is3_ladder build [workers]    # fills of all coins -> data/is3/ladder.parquet
  nice -n 19 .venv/bin/python -m research.studies.is3_ladder checks
  nice -n 19 .venv/bin/python -m research.studies.is3_ladder explore

A fill: during minute t the low trades at least THROUGH bp beyond limit = close[t-1] * (1 - k * sig[t-1]), sig = trailing-24h std
of 1-min log returns, known at t-1. The entry price is the limit (no improvement). After the fill, exits are measured from minute
t+1 on (minute t's path after the fill is unknown, so nothing good may happen in it): holds of 5/15/60/240 min as taker, and the
author's two levels as resting offers. One open position per coin. Entry maker 2 bp; taker exit 5 bp + modelled slippage.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from kripto import data
from kripto import events as ev
from research.studies import is3_lib as L
from research.studies.is3_lshock import DEAD24, coins, sample

OUT = data.DATA / "is3"
KS, HOLDS = (6, 8, 10, 12, 15, 20, 30), (1, 5, 15, 60, 240)


def fills(c, h, l, v, idx, through=10e-4, sides=(1, -1), ks=KS) -> pd.DataFrame:
    r = np.diff(np.log(c), prepend=np.nan)
    sig = pd.Series(r).rolling(1440, min_periods=720).std().to_numpy()
    vb = pd.Series(v).rolling(1440, min_periods=720).mean().to_numpy()
    hi10, lo10 = pd.Series(h).rolling(10).max().to_numpy(), pd.Series(l).rolling(10).min().to_numpy()
    r60 = pd.Series(np.log(c)).diff(60).to_numpy()
    T, rows = len(c), []
    cp, sp = np.roll(c, 1), np.roll(sig, 1)
    for side in sides:
        for k in ks:
            lim = cp * (1 - side * k * sp)
            hit = (l <= lim * (1 - through)) if side > 0 else (h >= lim * (1 + through))
            last = -1
            for t in np.flatnonzero(hit & (sp > 0)):
                if t < 12 or t <= last or t + 241 >= T:
                    continue
                p, O = lim[t], (hi10[t - 1] if side > 0 else lo10[t - 1])
                row = {"time": idx[t], "side": side, "k": k, "sig": sp[t], "depth": k * sp[t], "r60": side * r60[t - 1], "vm": v[t] / vb[t - 1],
                       "through": side * (p - (l[t] if side > 0 else h[t])) / p, "close_vs": side * (c[t] / p - 1)}
                for hh in HOLDS:
                    row[f"h{hh}"] = side * (c[t + hh] / p - 1)
                # author's exits as resting offers from t+1, no stop for 240 min, then out at the close; entry price = the limit, not the close
                mid, g, rem = p + 0.5 * (O - p), 0.0, 1.0
                for tp, f in ((mid, 0.5), (O, 0.5)):
                    w = h[t + 1:t + 241] if side > 0 else l[t + 1:t + 241]
                    ok = (w >= tp * 1.0001) if side > 0 else (w <= tp * 0.9999)
                    g += f * side * ((tp if ok.any() else c[t + 240]) / p - 1)
                row["x240"] = g
                w = slice(t + 1, t + 61)
                row["mae60"] = (l[w].min() / p - 1) if side > 0 else (p / h[w].max() - 1)
                rows.append(row)
                last = t + 60
    return pd.DataFrame(rows)


def one(coin):
    P = data.load_bn_minute_panel([coin])
    idx = P["close"].index
    t = fills(*(P[k][coin].to_numpy(dtype=np.float64) for k in ("close", "high", "low", "volume")), idx)
    t["slip"] = ev.slip_per_day(P["volume"])[coin].reindex(t["time"].dt.floor("D")).to_numpy()
    t["coin"] = coin
    print(coin, len(t), flush=True)
    return t


def build(workers=3):
    with ProcessPoolExecutor(workers) as ex:
        t = pd.concat(ex.map(one, coins())).sort_values(["time", "coin"]).reset_index(drop=True)
    # breadth known BEFORE the fill: other coins with a k>=6 fill in the 30 minutes up to the previous minute
    for side in (1, -1):
        a = t[(t.side == side) & (t.k == 6)]
        tm, cn = a["time"].to_numpy(), a["coin"].to_numpy()
        m = t.side == side
        hi = np.searchsorted(tm, t.loc[m, "time"].to_numpy(), side="left")
        lo = np.searchsorted(tm, (t.loc[m, "time"] - pd.Timedelta("30min")).to_numpy(), side="left")
        t.loc[m, "breadth"] = [len(set(cn[i:j])) for i, j in zip(lo, hi)]
    t.to_parquet(OUT / "ladder.parquet")
    print(len(t), t.groupby(["side", "k"]).size().to_dict())


def rows(t, col, maker_exit=False):
    c = 4e-4 if maker_exit else 7e-4 + t.slip
    return t.assign(gross=t[col], cost=c)[t[col].notna()]


def explore(s="explore", prefix="T1"):
    t = sample(pd.read_parquet(OUT / "ladder.parquet"), s)
    for side, nm in ((1, "bid"), (-1, "offer")):
        print(f"== a: {nm}s k sigma away, exit after 1/5/15/60/240 min (gross bp, net of maker entry + taker exit)")
        for k in KS:
            q = t[(t.side == side) & (t.k == k)]
            if len(q) < 10:
                continue
            r = {h: L.stats(rows(q, f"h{h}"), reps=400) for h in HOLDS}
            print(f"  k={k:2d} n={len(q):6d} days={r[60]['days']} depth {q.depth.median() * 1e4:.0f} bp, mae60 {q.mae60.mean() * 1e4:+.0f} |",
                  " | ".join(f"h{h} {x['mean_bp']:+.0f} net {x['net_bp']['own_cost']:+.0f} (p {x['p']:.2f}, ex3 {x['mean_ex_top3_bp']:+.0f})" for h, x in r.items()))
        for k in (8, 12, 20):
            q = t[(t.side == side) & (t.k == k)]
            if len(q) >= 30:
                L.card(f"{prefix}a_{nm}_k{k}", rows(q, "h60"), s, note="hold 60")
                L.card(f"{prefix}b_{nm}_k{k}", rows(q, "x240", True), s, note="author levels as resting offers, 240 min cap")
        print("== c: by breadth before the fill")
        for k in (8, 12):
            q = t[(t.side == side) & (t.k == k)]
            for lo, hi in ((0, 0), (1, 4), (5, 19), (20, 99)):
                g = q[(q.breadth >= lo) & (q.breadth <= hi)]
                if len(g) >= 20:
                    L.card(f"{prefix}c_{nm}_k{k}_b{lo}", rows(g, "h60"), s, note=f"breadth {lo}-{hi}")


def stress_one(coin):
    P = data.load_bn_minute_panel([coin])
    P = {k: x[x.index < "2024-01-03"] for k, x in P.items()}
    idx = P["close"].index
    c, h, l, v = (P[k][coin].to_numpy(dtype=np.float64) for k in ("close", "high", "low", "volume"))
    slip = ev.slip_per_day(P["volume"])[coin]
    out = []
    for th in (10, 30, 60, 100):
        t = fills(c, h, l, v, idx, through=th / 1e4, sides=(1,), ks=(12, 20, 30))
        if len(t):
            pos = idx.get_indexer(t.time)
            # pessimistic: the fill is the close of the fill minute if that is WORSE for us than our limit (no credit for the bounce inside the minute)
            t["p_close"] = [c[i] for i in pos]
            for hh in (15, 60, 240):
                t[f"w{hh}"] = [c[i + hh] / max(c[i], c[i - 1] * (1 - k * sg)) - 1 for i, k, sg in zip(pos, t.k, t.sig)]      # bought at the HIGHER of limit and that minute's close
                t[f"d{hh}"] = [c[i + 1 + hh] / c[i + 1] - 1 for i in pos]                        # bought one minute later at market
            t["wick"] = [(min(c[i], c[i - 1]) - l[i]) / c[i] for i in pos]
            out.append(t.assign(through_bp=th))
    t = pd.concat(out)
    t["slip"] = slip.reindex(t.time.dt.floor("D")).to_numpy()
    return t.assign(coin=coin)


def stress():
    """Form e and d on the explore sample: harder fills, no credit for the bounce inside the fill minute, worst trades, account."""
    with ProcessPoolExecutor(3) as ex:
        t = pd.concat(ex.map(stress_one, L.COINS10))
    t = t[t.time < "2024-01-01"].sort_values("time").reset_index(drop=True)
    for k in (12, 20, 30):
        print(f"== e: k={k}: gross bp after 60 min by how far price must trade through our limit")
        for th in (10, 30, 60, 100):
            q = t[(t.k == k) & (t.through_bp == th)]
            a, b, d = (L.stats(q.assign(gross=q[x]), reps=400) for x in ("h60", "w60", "d60"))
            print(f"  through {th:3d} bp n={len(q):5d}: limit fill {a['mean_bp']:+.0f} (p {a['p']:.3f}, ex3 {a['mean_ex_top3_bp']:+.0f}) | bought at max(limit, minute close) {b['mean_bp']:+.0f} (p {b['p']:.3f}) "
                  f"| bought 1 min later {d['mean_bp']:+.0f} (p {d['p']:.3f})")
    q = t[(t.k == 20) & (t.through_bp == 10)]
    L.card("T1e_k20_through60", rows(t[(t.k == 20) & (t.through_bp == 60)], "h60"), "explore", note="fill only if price trades 60 bp through")
    L.card("T1e_k20_maxclose", rows(q, "w60"), "explore", note="entry = max(limit, close of the fill minute)")
    print("worst 8 trades:", q.nsmallest(8, "h60")[["time", "coin", "h60", "mae60"]].round(3).to_string(index=False))
    print("top days:", (q.assign(d=q.time.dt.date).groupby("d").h60.agg(["sum", "size"]).nlargest(6, "sum")).round(3).to_string())
    print("fills per day: max", q.groupby(q.time.dt.date).size().max(), " share of fills in minutes with >= 4 coins:", round((q.groupby("time").coin.transform("size") >= 4).mean(), 2))
    print("== d: account: rest one bid per coin, 10 coins, size = 10% of equity each (max gross 1x), exit after 60 min")
    for k in (12, 20, 30):
        for col, nm in (("h60", "limit"), ("w60", "max(limit, close)")):
            for th in (10, 60):
                g = t[(t.k == k) & (t.through_bp == th)]
                net = g[col] - 7e-4 - g.slip
                d = (net * 0.1).groupby(g.time.dt.floor("D")).sum().reindex(pd.date_range("2021-01-01", "2023-12-31", tz="UTC"), fill_value=0.0)
                eq = (1 + d).cumprod()
                print(f"  k={k} {nm} through {th}: cagr {eq.iloc[-1] ** (1 / 3) - 1:+.1%} SR {d.mean() / d.std() * 365 ** 0.5:.2f} mdd {(eq / eq.cummax() - 1).min():.1%} worst day {d.min():.1%} "
                      + " ".join(f"{y}:{x.sum():+.1%}" for y, x in d.groupby(d.index.year)))


def frozen_one(coin):
    """Frozen T1k20 / T1k30: fills only if price trades 30 bp through the limit; h60 from the limit, w60 = entry at max(limit, minute close).
    A delisted coin is settled at its last price: its series is padded, so fills in its last hours count."""
    P = data.load_bn_minute_panel([coin])
    if coin in DEAD24:
        ix = P["close"].index
        ix = ix.append(pd.date_range(ix[-1] + pd.Timedelta("1min"), periods=300, freq="1min"))
        cl = P["close"].reindex(ix).ffill()
        P = {"close": cl, "high": P["high"].reindex(ix).fillna(cl), "low": P["low"].reindex(ix).fillna(cl), "volume": P["volume"].reindex(ix).fillna(0.0)}
    return frozen_core(coin, P)


def frozen_core(coin, P):
    idx = P["close"].index
    c, h, l, v = (P[k][coin].to_numpy(dtype=np.float64) for k in ("close", "high", "low", "volume"))
    t = fills(c, h, l, v, idx, through=30e-4, sides=(1,), ks=(20, 30))
    if not len(t):
        return t
    pos = idx.get_indexer(t.time)
    t["w60"] = [c[i + 60] / max(c[i], c[i - 1] * (1 - k * sg)) - 1 for i, k, sg in zip(pos, t.k, t.sig)]
    t["d60"] = [c[i + 61] / c[i + 1] - 1 for i in pos]
    dv = pd.Series(v, idx).resample("1D").sum().rolling(30, min_periods=5).mean().shift(1)
    t["dv30"] = dv.reindex(t.time.dt.floor("D")).to_numpy()
    t["slip"] = ev.slip_per_day(P["volume"])[coin].reindex(t.time.dt.floor("D")).to_numpy()
    return t.assign(coin=coin)


def frozen_build(workers=3):
    with ProcessPoolExecutor(workers) as ex:
        t = pd.concat([x for x in ex.map(frozen_one, coins()) if len(x)]).sort_values(["time", "coin"]).reset_index(drop=True)
    t.to_parquet(OUT / "ladder_frozen.parquet")
    print(len(t), t.groupby("k").size().to_dict())


def account(t, col, start, end, size=0.1, max_open=10):
    """One account: every fill takes `size` of equity if fewer than max_open positions are open; exit after 60 min. Daily series."""
    until, keep = [], []
    for tm in t.time:
        until = [x for x in until if x > tm]
        ok = len(until) < max_open
        keep.append(ok)
        if ok:
            until.append(tm + pd.Timedelta("60min"))
    g = t[keep]
    net = g[col] - 7e-4 - g.slip
    d = (net * size).groupby(g.time.dt.floor("D")).sum().reindex(pd.date_range(start, end, tz="UTC", inclusive="left"), fill_value=0.0)
    eq = (1 + d).cumprod()
    return (f"n {len(g)}/{len(t)} cagr {eq.iloc[-1] ** (365 / len(d)) - 1:+.1%} SR {d.mean() / (d.std() + 1e-12) * 365 ** 0.5:.2f} mdd {(eq / eq.cummax() - 1).min():.1%} "
            f"worst day {d.min():.1%} " + " ".join(f"{y}:{x.sum():+.1%}" for y, x in d.groupby(d.index.year)))


def confirm(samples=("confirmT", "confirmC")):
    T = pd.read_parquet(OUT / "ladder_frozen.parquet")
    for s in samples:
        t = sample(T, s)
        for k in (20, 30):
            q = t[t.k == k]
            L.card(f"T1k{k}", rows(q, "h60"), s, note="bid k sigma below the last close, fill if 30 bp through, taker exit after 60 min")
            w = L.stats(rows(q, "w60"), reps=1000)
            print(f"   pessimistic entry max(limit, minute close): mean {w['mean_bp']:+.0f} net {w['net_bp']['own_cost']:+.0f} p {w['p']:.3f} ex-top3 {w['mean_ex_top3_bp']:+.0f} years {w['by_year']}")
            w = L.stats(rows(q, "d60"), reps=1000)
            print(f"   bought 1 min later at market: mean {w['mean_bp']:+.0f} p {w['p']:.3f} ex-top3 {w['mean_ex_top3_bp']:+.0f}")
            lo, hi = L.SAMPLES[s]
            for mo in (5, 10):
                print(f"   account {mo} slots x 10%: limit {account(q, 'h60', lo, hi, 0.1, mo)} | pessimistic {account(q, 'w60', lo, hi, 0.1, mo)}")
            print("   worst 5:", q.nsmallest(5, "h60")[["time", "coin", "h60", "mae60"]].round(3).values.tolist())


def dead(workers=3):
    """Form f (survivorship): the frozen rule on 24 coins that were delisted (LUNA, SRM, ANC, ...). They are in no earlier sample."""
    from scripts import minute_study as ms
    for i in range(0, len(DEAD24), 4):
        ms.download(DEAD24[i:i + 4], [str(p) for p in pd.period_range("2021-01", "2024-09", freq="M")], log=lambda x: print(x, flush=True))
    with ProcessPoolExecutor(workers) as ex:
        t = pd.concat([x for x in ex.map(frozen_one, [c for c in DEAD24 if (data.DATA / "bn" / "klines_1m" / f"{c}USDT.parquet").exists()]) if len(x)])
    t = t.sort_values(["time", "coin"]).reset_index(drop=True)
    t.to_parquet(OUT / "ladder_dead.parquet")
    for k in (20, 30):
        q = t[t.k == k]
        L.card(f"T1f_k{k}", rows(q, "h60"), "confirmC", note="delisted coins only, settled at the last price")
        w = L.stats(rows(q, "w60"), reps=1000)
        print(f"   pessimistic entry: mean {w['mean_bp']:+.0f} net {w['net_bp']['own_cost']:+.0f} p {w['p']:.3f}")
        print("   by coin:", (q.groupby("coin").h60.agg(["size", "mean", "min"])).round(3).sort_values("mean").head(6).to_dict("index"))
        print("   worst 6:", q.nsmallest(6, "h60")[["time", "coin", "h60", "mae60"]].round(3).values.tolist())
        lu = q[q.coin == "LUNA"]
        print("   LUNA 2022-05-07..13:", lu[lu.time >= "2022-05-07"][["time", "h60", "h240"]].round(3).values.tolist()[:40])
        live = pd.read_parquet(OUT / "ladder_frozen.parquet")
        both = pd.concat([sample(live[live.k == k], "confirmC"), q]).sort_values("time")
        a = L.stats(rows(both, "h60"), reps=1000)
        print(f"   pooled confirmC + delisted: n {a['n']} mean {a['mean_bp']:+.0f} net {a['net_bp']['own_cost']:+.0f} p {a['p']:.3f} ex-top3 {a['mean_ex_top3_bp']:+.0f}; account 5x10%: {account(both, 'h60', '2021-01-01', '2026-01-01', 0.1, 5)}")


def fresh60() -> list[str]:
    """Form g: 60 coins picked by a fixed hash from the point-in-time top-100 list, in none of the earlier sets, no stock perps."""
    import zlib
    tf = data.bn_tradfi()
    used = set(coins()) | set(DEAD24)
    pool = [x[:-4] for x in data.bn_top_symbols(100, 30) if x.endswith("USDT") and x not in tf and x[:-4] not in used]
    return sorted(sorted(pool, key=lambda c: zlib.crc32(("T1g" + c).encode()))[:60])


def fresh(workers=3):
    """Download each fresh coin's minutes (kept under data/is3/k1m so the 83-coin sets never change), run the frozen rule, card it."""
    from scripts import minute_study as ms
    names = fresh60()
    print(len(names), "fresh coins:", " ".join(names), flush=True)
    ms.DIR = OUT / "k1m"
    for i in range(0, len(names), 6):
        ms.download(names[i:i + 6], [str(p) for p in pd.period_range("2021-01", "2025-12", freq="M")], log=lambda x: print(x, flush=True))
    with ProcessPoolExecutor(workers) as ex:
        t = pd.concat([x for x in ex.map(fresh_one, names) if len(x)]).sort_values(["time", "coin"]).reset_index(drop=True)
    t.to_parquet(OUT / "ladder_fresh.parquet")
    for k in (20, 30):
        q = t[(t.k == k) & (t.time < "2026-01-01")]
        L.card(f"T1g_k{k}", rows(q, "h60"), "confirmC", note="60 fresh coins (hash sample of the point-in-time top 100)")
        for col, nm in (("w60", "max(limit, minute close)"), ("d60", "market 1 min later")):
            w = L.stats(rows(q, col), reps=1000)
            print(f"   {nm}: mean {w['mean_bp']:+.0f} p {w['p']:.3f} ex-top3 {w['mean_ex_top3_bp']:+.0f} years {w['by_year']}")
        for mo in (5, 10):
            print(f"   account {mo} slots x 10%: limit {account(q, 'h60', '2021-01-01', '2026-01-01', 0.1, mo)} | pessimistic {account(q, 'w60', '2021-01-01', '2026-01-01', 0.1, mo)}")


def fresh_one(coin):
    f = OUT / "k1m" / f"{coin}USDT.parquet"
    if not f.exists():
        return pd.DataFrame()
    df = pd.read_parquet(f, columns=["t", "h", "l", "c", "qv"])
    df.index = pd.to_datetime(df["t"].where(df["t"] < 1e14, df["t"] // 1000), unit="ms", utc=True)
    df = df[~df.index.duplicated()].sort_index()
    ended = df.index[-1] < pd.Timestamp("2025-12-30", tz="UTC")
    idx = pd.date_range(df.index[0], df.index[-1] + pd.Timedelta(minutes=300 if ended else 0), freq="1min")
    cl = df["c"].reindex(idx).ffill().astype(float)
    P = {"close": cl.to_frame(coin), "high": df["h"].reindex(idx).fillna(cl).astype(float).to_frame(coin),
         "low": df["l"].reindex(idx).fillna(cl).astype(float).to_frame(coin), "volume": df["qv"].reindex(idx).fillna(0.0).astype(float).to_frame(coin)}
    return frozen_core(coin, P)


def sizing():
    """Form d on explore only (choices, not evidence): slots, size, $200, order in which simultaneous fills are taken."""
    live = pd.read_parquet(OUT / "ladder_frozen.parquet")
    dead = pd.read_parquet(OUT / "ladder_dead.parquet")
    t = pd.concat([live, dead])
    t = t[(t.time >= "2021-01-01") & (t.time < "2024-01-01")]
    rng = np.random.default_rng(0)
    for k in (20, 30):
        q = t[t.k == k]
        for nm, g in (("first-come alphabetical", q.sort_values(["time", "coin"])), ("most liquid first", q.sort_values(["time", "dv30"], ascending=[True, False])),
                      ("thinnest first", q.sort_values(["time", "dv30"])), ("worst first (hindsight bound)", q.sort_values(["time", "h60"]))):
            print(f"k={k} {nm}: 5 x 10% {account(g, 'h60', '2021-01-01', '2024-01-01', 0.1, 5)}")
        for mo, sz in ((3, 0.2), (5, 0.2), (10, 0.1), (10, 0.05), (20, 0.05)):
            print(f"k={k} {mo} slots x {sz:.0%}: {account(q.sort_values(['time', 'dv30'], ascending=[True, False]), 'h60', '2021-01-01', '2024-01-01', sz, mo)}")
        r = []
        for _ in range(20):
            g = q.assign(u=rng.random(len(q))).sort_values(["time", "u"])
            r.append(float(account(g, "h60", "2021-01-01", "2024-01-01", 0.1, 5).split("SR ")[1].split()[0]))
        print(f"k={k} random order of simultaneous fills, 20 draws: SR {min(r):.2f}..{max(r):.2f}")
        L.card(f"T1d_k{k}", rows(sample(live[live.k == k], "explore"), "h60"), "explore", note="$1,000: 10% = $100 per order; $200: 10% = $20 (Binance min $5, BTC $50 / ETH $20, HL $10): BTC needs 25% of $200, so skip BTC there")


def checks():
    P = data.load_bn_minute_panel(["BTC", "DOGE", "AVAX"])
    P = {k: x[(x.index >= "2021-03-01") & (x.index < "2021-09-01")].astype("float64") for k, x in P.items()}

    def fn(p):
        out = [fills(*(p[f][k].to_numpy(dtype=float) for f in ("close", "high", "low", "volume")), p["close"].index, sides=(1,), ks=(8,)).assign(coin=k) for k in p["close"]]
        return pd.concat(out).assign(gross=lambda d: d.h60)
    L.null_check(fn, P, n=20)
    L.check_causal(fn, P, "2021-06-15")


if __name__ == "__main__":
    {"build": lambda: build(int(sys.argv[2]) if len(sys.argv) > 2 else 3), "checks": checks, "explore": explore, "stress": stress, "frozen": frozen_build, "confirm": confirm, "dead": dead, "fresh": fresh, "sizing": sizing}[sys.argv[1]]()
