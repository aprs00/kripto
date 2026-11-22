"""InSilico third pass, item W1 (weekend and CME rules; think-through in research/is3/notes.md).

  nice -n 19 .venv/bin/python -m research.studies.is3_weekend build [workers]    # 5-min bars of all coins -> events in data/is3/weekend.parquet
  nice -n 19 .venv/bin/python -m research.studies.is3_weekend checks
  nice -n 19 .venv/bin/python -m research.studies.is3_weekend explore
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from kripto import data
from research.studies import is3_lib as L
from research.studies.is3_lshock import coins, sample

OUT = data.DATA / "is3"
NY = "America/New_York"


def bars(coin: str, rule="5min") -> pd.DataFrame:
    df = pd.read_parquet(data.DATA / "bn" / "klines_1m" / f"{coin}USDT.parquet", columns=["t", "h", "l", "c", "qv", "tbqv"])
    df.index = pd.to_datetime(df["t"].where(df["t"] < 1e14, df["t"] // 1000), unit="ms", utc=True)
    df = df[~df.index.duplicated()].sort_index()
    r = df[df.index >= "2020-12-28"].resample(rule)
    x = pd.DataFrame({"h": r["h"].max(), "l": r["l"].min(), "c": r["c"].last(), "v": r["qv"].sum(), "tb": r["tbqv"].sum()})
    x["c"] = x["c"].ffill()
    x["h"], x["l"] = x["h"].fillna(x["c"]), x["l"].fillna(x["c"])
    return x


def at(days: pd.DatetimeIndex, hhmm: str) -> pd.DatetimeIndex:
    """UTC instants of a New York clock time on given calendar days."""
    h, m = map(int, hhmm.split(":"))
    return (days + pd.Timedelta(hours=h, minutes=m)).tz_localize(NY, ambiguous=True, nonexistent="shift_forward").tz_convert("UTC")


def touch(x: pd.DataFrame, t0, t1, target) -> float:
    """Simple return of going from the close at t0 toward target (limit, 1 bp trade-through), else out at the close at t1."""
    w = x[(x.index >= t0) & (x.index < t1)]                  # bars that start at or after t0
    p = px(x, t0)
    if not len(w) or not np.isfinite(p) or w.index[-1] < t1 - pd.Timedelta("1h"):
        return np.nan
    s = np.sign(target - p)
    hit = (w["h"] >= target * 1.0001) if s > 0 else (w["l"] <= target * 0.9999)
    return s * ((target if hit.any() else w["c"].iloc[-1]) / p - 1)


def px(x, t):
    """Last close known at instant t (bars are stamped by their start)."""
    i = x.index.searchsorted(t - pd.Timedelta("5min"), side="right") - 1
    return float(x["c"].iloc[i]) if i >= 0 and t - x.index[i] <= pd.Timedelta("15min") else np.nan


def node(w: pd.DataFrame) -> float:
    k = np.round(np.log(np.sqrt(w["h"] * w["l"])) / 1e-3).astype(int)
    return float(np.exp(w["v"].groupby(k).sum().idxmax() * 1e-3)) if len(w) and w["v"].sum() > 0 else np.nan


def events(x: pd.DataFrame, b: pd.DataFrame | None = None) -> pd.DataFrame:
    """All W1 events of one coin. kind 'wk' = Friday -> Sunday 18:00 -> Monday 17:00; 'pl' = the same clock distances from Tuesday."""
    rows = []
    d0, d1 = x.index[0].tz_convert(NY).normalize().tz_localize(None), x.index[-1].tz_convert(NY).normalize().tz_localize(None)
    for kind, wd in (("wk", 4), ("pl", 1)):
        days = pd.date_range(d0, d1, freq="1D")
        days = days[days.dayofweek == wd]
        for f in days:
            D = lambda n, hm: at(pd.DatetimeIndex([f + pd.Timedelta(days=n)]), hm)[0]
            f0930, f14, f16, f17 = D(0, "09:30"), D(0, "14:00"), D(0, "16:00"), D(0, "17:00")
            s16, s18, m17 = D(2, "16:00"), D(2, "18:00"), D(3, "17:00")
            if f0930 < x.index[0] or m17 > x.index[-1]:
                continue
            w = x[(x.index >= f14) & (x.index < f16)]
            us = x[(x.index >= f0930) & (x.index < f17)]
            p = px(x, s18)
            if not len(w) or w["v"].sum() <= 0 or not np.isfinite(p):
                continue
            refs = {"vwap": float((w["v"] * np.sqrt(w["h"] * w["l"])).sum() / w["v"].sum()), "node": node(us), "c16": px(x, f16), "c17": px(x, f17)}
            row = {"time": s18, "kind": kind, "p": p}
            for k, r in refs.items():
                row[f"gap_{k}"] = r / p - 1
                row[f"t_{k}"] = touch(x, s18, m17, r)
                row[f"hold_{k}"] = np.sign(r - p) * (px(x, m17) / p - 1)
            g17 = refs["c17"]
            for n in (1, 3, 5):
                end = s18 + pd.Timedelta(days=n)
                row[f"cme{n}"] = touch(x, s18, end, g17) if end <= x.index[-1] else np.nan
            p16 = px(x, s16)
            row["bait"] = p / p16 - 1
            row["bait_v"] = x["v"][(x.index >= s16) & (x.index < s18)].sum() / max(x["v"][(x.index >= s16 - pd.Timedelta("2h")) & (x.index < s16)].sum(), 1.0)
            row["fwd_m17"], row["fwd_24"] = px(x, m17) / p - 1, px(x, s18 + pd.Timedelta("24h")) / p - 1
            if b is not None:
                bp = px(b, s18)
                row["xgap"] = (g17 / p - 1) - (px(b, f17) / bp - 1)
                row["xfwd"] = row["fwd_m17"] - (px(b, m17) / bp - 1)
            rows.append(row)
    return pd.DataFrame(rows)


def openflow(x: pd.DataFrame) -> pd.DataFrame:
    """Form e: first-hour taker imbalance 09:30-10:30 NY -> return to 16:00 and over the next 4 days, per weekday."""
    d = pd.date_range(x.index[0].tz_convert(NY).normalize().tz_localize(None), x.index[-1].tz_convert(NY).normalize().tz_localize(None) - pd.Timedelta(days=5), freq="1D")
    d = d[d.dayofweek < 5]
    t0, t1, t2 = at(d, "09:30"), at(d, "10:30"), at(d, "16:00")
    rows = []
    for day, a, e, z in zip(d, t0, t1, t2):
        w = x[(x.index >= a) & (x.index < e)]
        if len(w) < 12 or w["v"].sum() <= 0:
            continue
        p = px(x, e)
        rows.append({"time": e, "wd": day.dayofweek, "imb": float(2 * w["tb"].sum() / w["v"].sum() - 1), "eod": px(x, z) / p - 1,
                     "wk": px(x, e + pd.Timedelta(days=4)) / p - 1, "oh": p / px(x, a) - 1})
    t = pd.DataFrame(rows)
    t["z"] = (t.imb - t.imb.rolling(60, min_periods=20).mean().shift(1)) / t.imb.rolling(60, min_periods=20).std().shift(1)
    return t


def one(coin: str):
    x = bars(coin)
    b = None if coin == "BTC" else bars("BTC")
    print(coin, flush=True)
    return events(x, b).assign(coin=coin), openflow(x).assign(coin=coin)


def build(workers=2):
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(one, coins()))
    pd.concat([a for a, _ in res]).reset_index(drop=True).to_parquet(OUT / "weekend.parquet")
    pd.concat([b for _, b in res]).reset_index(drop=True).to_parquet(OUT / "openflow.parquet")


def ev(t, gross, side=None):
    t = t[gross.notna()]
    return t.assign(gross=gross[gross.notna()], side=1 if side is None else side[gross.notna()])[["time", "coin", "side", "gross"]]


def explore(s="explore", prefix="W1"):
    t = sample(pd.read_parquet(OUT / "weekend.parquet"), s)
    W, P = t[t.kind == "wk"], t[t.kind == "pl"]
    print("== a: target = Friday's collar, entered Sunday 18:00 NY, out at touch or Monday 17:00")
    for k in ("vwap", "node", "c16", "c17"):
        for g in (0.005, 0.01, 0.02, 0.04):
            q, pl = W[W[f"gap_{k}"].abs() >= g], P[P[f"gap_{k}"].abs() >= g]
            L.card(f"{prefix}a_{k}_{g * 100:g}", ev(q, q[f"t_{k}"], np.sign(q[f"gap_{k}"])), s, base=ev(pl, pl[f"t_{k}"], np.sign(pl[f"gap_{k}"])),
                   note=f"touch rate wk {(q[f't_{k}'] >= q[f'gap_{k}'].abs() * 0.99).mean():.0%} vs placebo {(pl[f't_{k}'] >= pl[f'gap_{k}'].abs() * 0.99).mean():.0%}")
    for k in ("BTC", "ETH"):
        q, pl = (u[(u.coin == k) & (u.gap_vwap.abs() >= 0.01)] for u in (W, P))
        if len(q):
            L.card(f"{prefix}a_{k}", ev(q, q.t_vwap, np.sign(q.gap_vwap)), s, base=ev(pl, pl.t_vwap, np.sign(pl.gap_vwap)), note="the coin he trades")
    print("== b: CME gap by size")
    for lo, hi in ((0.0, 0.01), (0.01, 0.03), (0.03, 9)):
        for n in (1, 3, 5):
            f = lambda u: u[(u.gap_c17.abs() >= lo) & (u.gap_c17.abs() < hi)]
            q, pl = f(W), f(P)
            L.card(f"{prefix}b_{lo * 100:g}_{n}d", ev(q, q[f"cme{n}"], np.sign(q.gap_c17)), s, base=ev(pl, pl[f"cme{n}"], np.sign(pl.gap_c17)),
                   note=f"filled wk {(q[f'cme{n}'] >= q.gap_c17.abs() * 0.99).mean():.0%} vs placebo {(pl[f'cme{n}'] >= pl.gap_c17.abs() * 0.99).mean():.0%}")
    print("== c: excess gap relative to BTC (hedged, to Monday 17:00)")
    for g in (0.01, 0.02, 0.04):
        q, pl = W[W.xgap.abs() >= g], P[P.xgap.abs() >= g]
        L.card(f"{prefix}c_{g * 100:g}", ev(q, np.sign(q.xgap) * q.xfwd, np.sign(q.xgap)), s, base=ev(pl, np.sign(pl.xgap) * pl.xfwd, np.sign(pl.xgap)))
    print("== d: Sunday 16-18 NY bait move, faded to Monday 17:00, by volume")
    for g in (0.005, 0.01, 0.02):
        for nm, f in (("all", lambda u: u), ("vol_up", lambda u: u[u.bait_v >= 1]), ("vol_dn", lambda u: u[u.bait_v < 1])):
            q, pl = f(W[W.bait.abs() >= g]), f(P[P.bait.abs() >= g])
            L.card(f"{prefix}d_{g * 100:g}_{nm}", ev(q, -np.sign(q.bait) * q.fwd_m17, -np.sign(q.bait)), s, base=ev(pl, -np.sign(pl.bait) * pl.fwd_m17, -np.sign(pl.bait)))
    print("== e: first US hour taker imbalance, Monday vs other weekdays")
    o = sample(pd.read_parquet(OUT / "openflow.parquet"), s)
    for z in (0.5, 1, 2):
        for h in ("eod", "wk"):
            q = o[o.z.abs() >= z]
            m, r = q[q.wd == 0], q[q.wd > 0]
            L.card(f"{prefix}e_{h}_z{z}", ev(m, np.sign(m.z) * m[h], np.sign(m.z)), s, base=ev(r, np.sign(r.z) * r[h], np.sign(r.z)))


def checks():
    x = {k: bars(k).loc["2022-01-01":"2022-12-31"] for k in ("BTC", "ETH", "DOGE")}
    P = {n: pd.DataFrame({k: v[f] for k, v in x.items()}) for n, f in (("close", "c"), ("high", "h"), ("low", "l"), ("volume", "v"), ("tb", "tb"))}

    def fn(p):
        out = []
        for k in p["close"]:
            y = pd.DataFrame({"c": p["close"][k], "h": p["high"][k], "l": p["low"][k], "v": p["volume"][k], "tb": p["tb"][k]})
            t = events(y).assign(coin=k)
            t = t[(t.kind == "wk") & (t.gap_vwap.abs() >= 0.005)]
            out.append(ev(t, t.t_vwap, np.sign(t.gap_vwap)))
        return pd.concat(out)
    L.null_check(fn, P, n=12)
    L.check_causal(fn, P, "2022-07-01", "4D")


if __name__ == "__main__":
    {"build": lambda: build(int(sys.argv[2]) if len(sys.argv) > 2 else 2), "checks": checks, "explore": explore}[sys.argv[1]]()
