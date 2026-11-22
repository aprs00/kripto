"""InSilico third pass, T1 forms j + i: the frozen k = 30 sigma resting bid on a CAUSAL top-20 universe (30-d mean volume known at the
previous day's close, clean bnall, delisted coins included), and what to do about the crash tail (exits, stops, when not to quote).

  .venv/bin/python -m research.studies.is3_ladtop universe | fetch [end-year] | build <start> <end> <out> | checks | explore | confirm <name>

Only coins and days inside the universe count. Minute data: klines_1m, is3/k1m, and is3/k1m_top (fetched here, per coin-month needed).
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from kripto import data
from kripto import events as ev
from research.studies import is3_lib as L

OUT = data.DATA / "is3"
DIRS = (data.DATA / "bn" / "klines_1m", OUT / "k1m", OUT / "k1m_top")
K, THROUGH, TOPN = 30, 30e-4, 20


def universe() -> pd.DataFrame:
    """Daily boolean-ish table (day, coin, rank, age): rank by 30-day mean volume through the previous day's close."""
    P = data.load_panel("bnall", "1d")
    v = P["volume"]
    d30 = v.rolling(30, min_periods=20).mean().shift(1)
    age = v.notna().cumsum().shift(1)
    rk = d30.where(v.notna()).rank(axis=1, ascending=False, method="first")
    r = rk.stack().rename("rank").reset_index()
    r.columns = ["day", "coin", "rank"]
    a = age.stack().rename("age").reset_index()
    a.columns = ["day", "coin", "age"]
    r = r[r["rank"] <= TOPN].merge(a, on=["day", "coin"])
    return r[(r.day >= "2021-01-01") & (r.day < "2026-11-01")].reset_index(drop=True)


def have_months(coin) -> set[str]:
    s = set()
    for d in DIRS:
        f = d / f"{coin}USDT.parquet"
        if f.exists():
            t = pd.read_parquet(f, columns=["t"])["t"]
            ms = t.where(t < 1e14, t // 1000).to_numpy(dtype="int64")
            s |= set(np.unique(ms.astype("datetime64[ms]").astype("datetime64[M]")).astype(str))
    return s


def fetch(end="2026-11"):
    from scripts import minute_study as ms
    u = pd.read_parquet(OUT / "top_universe.parquet")
    u = u[u.day < pd.Timestamp(end, tz="UTC")]
    u["m"] = u.day.dt.strftime("%Y-%m")
    u["pm"] = (u.day - pd.Timedelta("2D")).dt.strftime("%Y-%m")
    u["nm"] = (u.day + pd.Timedelta("2D")).dt.strftime("%Y-%m")
    ms.DIR = OUT / "k1m_top"
    ms.DIR.mkdir(parents=True, exist_ok=True)
    def job(cg):
        need = sorted(set(cg[1].m) | set(cg[1].pm) | set(cg[1].nm))
        got = have_months(cg[0])
        need = [m for m in need if m not in got and m < "2026-11"]
        if need:
            ms.download([cg[0]], need, log=lambda x: None)
            print(cg[0], len(need), "months", flush=True)
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(job, u.groupby("coin")))


def series(coin, lo, hi):
    """Contiguous pieces (gaps > 1 day cut them) of one coin's minutes in [lo - 2 d, hi + 2 d)."""
    dfs = []
    for d in DIRS:
        f = d / f"{coin}USDT.parquet"
        if f.exists():
            x = pd.read_parquet(f, columns=["t", "h", "l", "c", "qv"])
            x.index = pd.to_datetime(x["t"].where(x["t"] < 1e14, x["t"] // 1000), unit="ms", utc=True)
            dfs.append(x.drop(columns="t"))
    if not dfs:
        return []
    x = pd.concat(dfs)
    x = x[~x.index.duplicated()].sort_index()
    x = x[(x.index >= lo - pd.Timedelta("2D")) & (x.index < hi + pd.Timedelta("2D"))].astype(float)
    if not len(x):
        return []
    cut = (x.index.to_series().diff() > pd.Timedelta("1D")).cumsum().to_numpy()
    out = []
    for _, p in x.groupby(cut):
        ix = pd.date_range(p.index[0], p.index[-1] + pd.Timedelta("1500min"), freq="1min")    # padded: a delisted coin settles at its last price
        c = p["c"].reindex(ix).ffill()
        out.append(pd.DataFrame({"h": p["h"].reindex(ix).fillna(c), "l": p["l"].reindex(ix).fillna(c), "c": c, "qv": p["qv"].reindex(ix).fillna(0.0)}))
    return out


HOLDS, STOPS = (5, 15, 60, 240, 1440), (0.03, 0.05, 0.10)


def events(c, h, l, v, idx, k=K, through=THROUGH, lock=60) -> pd.DataFrame:
    r = np.diff(np.log(c), prepend=np.nan)
    sig = pd.Series(r).rolling(1440, min_periods=720).std().to_numpy()
    cp, sp = np.roll(c, 1), np.roll(sig, 1)
    lim = cp * (1 - k * sp)
    rows, last, T = [], -1, len(c)
    for t in np.flatnonzero((l <= lim * (1 - through)) & (sp > 0)):
        if t < 720 or t <= last or t + 1441 >= T:
            continue
        p = lim[t]
        row = {"time": idx[t], "t": t, "depth": k * sp[t], "wick": l[t] / p - 1, "w": max(c[t], p) / p - 1, "mae60": l[t + 1:t + 61].min() / p - 1}
        for hh in HOLDS:
            row[f"h{hh}"] = c[t + hh] / p - 1
        for s in STOPS:
            for hh in (60, 240):
                w = l[t + 1:t + hh + 1] <= p * (1 - s)
                j = int(np.argmax(w)) + t + 1 if w.any() else 0
                row[f"s{int(s * 100)}_{hh}"] = (min(p * (1 - s), c[j]) if j else c[t + hh]) / p - 1
        rows.append(row)
        last = t + lock
    return pd.DataFrame(rows)


def one(a):
    coin, lo, hi, days = a
    out = []
    for x in series(coin, lo, hi):
        e = events(*(x[f].to_numpy() for f in ("c", "h", "l", "qv")), x.index)
        if len(e):
            e["slip"] = ev.slip_per_day(x["qv"].to_frame(coin))[coin].reindex(e.time.dt.floor("D")).to_numpy()
            out.append(e)
    if not out:
        return pd.DataFrame()
    e = pd.concat(out).assign(coin=coin, day=lambda d: d.time.dt.floor("D")).merge(days, on="day")
    return e[(e.time >= lo) & (e.time < hi)].drop(columns="t")


def build(lo, hi, name, workers=2):
    lo, hi = pd.Timestamp(lo, tz="UTC"), pd.Timestamp(hi, tz="UTC")
    u = pd.read_parquet(OUT / "top_universe.parquet")
    u = u[(u.day >= lo) & (u.day < hi)]
    jobs = [(c, lo, hi, g[["day", "rank", "age"]]) for c, g in u.groupby("coin")]
    with ProcessPoolExecutor(workers) as ex:
        t = pd.concat([x for x in ex.map(one, jobs) if len(x)]).sort_values(["time", "coin"]).reset_index(drop=True)
    b = series("BTC", lo, hi)[0]["c"]
    for hh in (60, 240, 1440):
        t[f"btc{hh}"] = (b.shift(1) / b.shift(1 + hh) - 1).reindex(t.time).to_numpy()
    t.to_parquet(OUT / f"{name}.parquet")
    print(len(t), "fills", t.coin.nunique(), "coins", t.time.min(), t.time.max())


def checks():
    """Null data, causality, and the new code against the old one (is3_ladder.fills, k = 30, 30 bp through)."""
    from research.studies.is3_ladder import fills
    P = data.load_bn_minute_panel(["BTC", "DOGE", "AVAX"])
    P = {k: x[(x.index >= "2021-03-01") & (x.index < "2021-09-01")].astype("float64") for k, x in P.items()}
    get = lambda p, k: [p[f][k].to_numpy(dtype=float) for f in ("close", "high", "low", "volume")]
    for k in P["close"]:
        a, b = events(*get(P, k), P["close"].index), fills(*get(P, k), P["close"].index, through=THROUGH, sides=(1,), ks=(K,))
        m = a.merge(b, on="time", suffixes=("", "_o"))
        print(k, "new", len(a), "old", len(b), "common", len(m), "max h60 diff", float((m.h60 - m.h60_o).abs().max()) if len(m) else None)

    def fn(p):
        return pd.concat([events(*get(p, k), p["close"].index, k=8).assign(coin=k, side=1, gross=lambda d: d["s5_240"]) for k in p["close"]])
    L.null_check(fn, P, n=20)
    L.check_causal(fn, P, "2021-06-15")


def account(t, col, lo, hi, size=0.1, max_open=5, hold=60, pause=False, btc=None):
    """Orders cannot be cancelled inside a minute: a minute that starts with < max_open open fills every bid hit in it. pause = after the
    first batch no quotes for 24 h. btc = do not quote while BTC's 4-h return at t-1 is below it. P&L booked on the fill day (close of the position)."""
    until, keep, quiet = [], [], pd.Timestamp("2000-01-01", tz="UTC")
    if btc is not None:
        t = t[~(t.btc240 < btc)]
    for tm, g in t.groupby("time", sort=True):
        until = [x for x in until if x > tm]
        if len(until) < max_open and tm >= quiet:
            keep.append(g)
            until += [tm + pd.Timedelta(minutes=hold)] * len(g)
            if pause:
                quiet = tm + pd.Timedelta("1D")
    g = pd.concat(keep)
    net = g[col] - 7e-4 - g.slip
    d = (net * size).groupby(g.time.dt.floor("D")).sum().reindex(pd.date_range(lo, hi, tz="UTC", inclusive="left"), fill_value=0.0)
    eq = (1 + d).cumprod()
    return {"n": len(g), "cagr": eq.iloc[-1] ** (365 / len(d)) - 1, "sr": d.mean() / (d.std() + 1e-12) * 365 ** 0.5, "mdd": (eq / eq.cummax() - 1).min(),
            "worst": d.min(), "yr": " ".join(f"{y}:{x.sum():+.1%}" for y, x in d.groupby(d.index.year))}


COLS = ["h5", "h15", "h60", "h240", "h1440", "s3_60", "s5_60", "s10_60", "s3_240", "s5_240", "s10_240"]


def explore(name="ladtop_x", lo="2021-01-01", hi="2024-01-01"):
    t = pd.read_parquet(OUT / f"{name}.parquet")
    t["side"] = 1
    for lab, u in (("top20", t), ("top20 age>=365", t[t.age >= 365]), ("top10", t[t["rank"] <= 10])):
        same = u.groupby("time").size()
        print(f"== {lab}: fills {len(u)} days {u.day.nunique()} coins {u.coin.nunique()} biggest minute {same.max()} ({same.idxmax()}), fills in minutes >= 5 coins {same[same >= 5].sum() / len(u):.2f}; depth median {u.depth.median():.3f}")
        for c in COLS:
            s = L.stats(u.assign(gross=u[c], cost=7e-4 + u.slip), reps=500)
            print(f"   {c:8s} mean {s['mean_bp']:+.0f} net {s['net_bp']['own_cost']:+.0f} med {s['median_bp']:+.0f} p {s['p']:.3f} ex3 {s['mean_ex_top3_bp']:+.0f} worst {u[c].min():+.1%} yrs {s['by_year']}", flush=True)
        s = L.stats(u.assign(gross=(1 + u.h60) / (1 + u.w) - 1), reps=500)
        print(f"   pessimistic entry (max limit, close) h60 {s['mean_bp']:+.0f} p {s['p']:.3f} {s['by_year']}")
        for c in COLS:
            hold = {"h5": 5, "h15": 15, "h1440": 1440}.get(c, 240 if c.endswith("240") else 60)
            for pause, btc in ((False, None), (True, None), (False, -0.02), (False, -0.03), (False, -0.05)):
                if (pause or btc) and c not in ("h15", "h60", "h240", "s5_60"):
                    continue
                a = account(u, c, lo, hi, hold=hold, pause=pause, btc=btc)
                print(f"   ACC {c:8s} pause {pause} btc {btc}: n {a['n']} cagr {a['cagr']:+.1%} SR {a['sr']:.2f} mdd {a['mdd']:.1%} worst day {a['worst']:.1%} {a['yr']}", flush=True)
    print("== dose: BTC 4-h return before the fill (h60, bp)")
    for a, b in ((-1, -.05), (-.05, -.03), (-.03, -.01), (-.01, .01), (.01, 1)):
        g = t[(t.btc240 >= a) & (t.btc240 < b)]
        if len(g):
            print(f"   [{a:+.2f},{b:+.2f}) n {len(g)} days {g.day.nunique()} h15 {g.h15.mean() * 1e4:+.0f} h60 {g.h60.mean() * 1e4:+.0f} h240 {g.h240.mean() * 1e4:+.0f} h1440 {g.h1440.mean() * 1e4:+.0f}")
    print("== by coins filled in the same minute (known only after)")
    t["same"] = t.groupby("time").coin.transform("size")
    for a, b in ((1, 1), (2, 4), (5, 9), (10, 20)):
        g = t[(t.same >= a) & (t.same <= b)]
        if len(g):
            print(f"   {a}-{b}: n {len(g)} days {g.day.nunique()} h15 {g.h15.mean() * 1e4:+.0f} h60 {g.h60.mean() * 1e4:+.0f} h240 {g.h240.mean() * 1e4:+.0f} h1440 {g.h1440.mean() * 1e4:+.0f} worst h60 {g.h60.min():+.1%}")


def confirm(sample="confirmT", name="ladtop_c"):
    """T1i as pre-registered: causal top-20, k 30, 30 bp through, taker exit after 60 min."""
    t = pd.read_parquet(OUT / f"{name}.parquet").assign(side=1)
    lo, hi = L.SAMPLES[sample]
    e = t[(t.time >= lo) & (t.time < hi)]
    L.card("T1i", e.assign(gross=e.h60, cost=7e-4 + e.slip), sample, note="causal top-20 by 30-d volume, hold 60, no stop")
    for lab, q in (("top20", e), ("top10", e[e["rank"] <= 10]), ("age>=365", e[e.age >= 365])):
        for c in ("h15", "h60", "h240"):
            a = account(q, c, lo, hi, hold=int(c[1:]))
            s = L.stats(q.assign(gross=q[c]), reps=500)
            print(f"   {lab} {c}: n {len(q)} mean {s['mean_bp']:+.0f} p {s['p']:.3f} ex3 {s['mean_ex_top3_bp']:+.0f} worst {q[c].min():+.1%} | ACC cagr {a['cagr']:+.1%} SR {a['sr']:.2f} mdd {a['mdd']:.1%} worst day {a['worst']:.1%} {a['yr']}")
        s = L.stats(q.assign(gross=(1 + q.h60) / (1 + q.w) - 1), reps=500)
        a = account(q.assign(h60=(1 + q.h60) / (1 + q.w) - 1), "h60", lo, hi)
        print(f"   {lab} pessimistic entry h60 {s['mean_bp']:+.0f} p {s['p']:.3f} | ACC SR {a['sr']:.2f} cagr {a['cagr']:+.1%} {a['yr']}")
    d = e.groupby("day").h60.agg(["sum", "mean", "size"])
    print("   worst days:", d.nsmallest(4, "sum").round(3).to_dict("index"), "best:", d.nlargest(4, "sum").round(3).to_dict("index"))
    print("   by BTC 4-h:", [(a, int(((e.btc240 >= a) & (e.btc240 < b)).sum()), round(e[(e.btc240 >= a) & (e.btc240 < b)].h60.mean() * 1e4)) for a, b in ((-1, -.05), (-.05, -.03), (-.03, -.01), (-.01, .01), (.01, 1))])


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "universe":
        u = universe()
        u.to_parquet(OUT / "top_universe.parquet")
        print(len(u), u.coin.nunique())
    elif a == "fetch":
        fetch(*sys.argv[2:])
    elif a == "build":
        build(*sys.argv[2:5])
    elif a == "checks":
        checks()
    elif a == "confirm":
        confirm(*sys.argv[2:])
    elif a == "explore":
        explore(*sys.argv[2:])
