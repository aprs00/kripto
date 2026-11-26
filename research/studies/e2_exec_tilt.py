"""E2 execution-time tilt (backlog E2, calendar finding 11-11: BTC/ETH +5-9 bp in the CME-shut hour 17-18 New York, t 2.3-3.6).
Descriptive, not a backtest, not registered. Question: would timing the daily books' BUYS before and SELLS after the CME break (or
at the best hours generally) save money per unit traded, net of the signal decay that the delay costs?

THINK-THROUGH (written 2026-11-26 before any number of this script was seen)
(a) Mechanism. Hypothesised: CME bitcoin futures stop 17-18 NY; basis/hedging flow that normally leans on CME moves to the perps
    or pauses, leaving a small positive drift. Nobody "pays" us for timing; a positive drift in one hour is earned by being net long
    in that hour. For a market-neutral book a buys-first / sells-later split makes the book net long the market for exactly the
    gap between the two fills, so the "saving" is a one-hour timing bet on the drift, sized by half the turnover. For a directional
    book the same is true per traded unit.
(b) Baseline (how the daily books trade NOW, read from kripto/paper.py + strategies.scheduled + deploy/systemd/kripto-trader.timer):
    live panels are 4h bars labelled by open time; a daily grid (rebalance_rows, epoch anchored) keeps the 00:00 UTC bar, which
    closes at 04:00 UTC; the trader timer fires at hh:03, so every daily book (HL and Binance) trades ~04:03-04:15 UTC, i.e.
    23:0x New York in winter (EST) and 00:0x in summer (EDT). The CME break (22-23 UTC EST / 21-22 UTC EDT) is 17-19 hours LATER.
    So the literal rule "buy before 17:00 NY, sell after 18:00 NY" with today's decision clock means delaying every trade ~17-19 h.
(c) Formulations (materially different):
    F1 universe: BTC+ETH only (where the finding was measured) | all 82 Binance coins EW | trade-weighted coin-level (each book's
       real trade list, which nets the market out for market-neutral books: the coin-minus-market form).
    F2 policy: (i) CME literal at the current clock: buys at the first 17:00 NY after the 04 UTC decision, sells at 18:00 NY;
       (ii) CME re-anchored: the book's clock moved to the break, buys at 17:00 NY, sells one hour later at 18:00 NY, measured
       relative to both sides at 17:00 NY (requires a 1h decision bar; signal staleness of the re-anchor is NOT part of this cost
       comparison); (iii) fixed shift of both sides by d hours (pure decay/drift curve); (iv) the best (buy hour, sell hour) pair
       for each book chosen on explore from the 24x24 grid of delays, then read once on confirm.
    F3 venue: Binance 82 (2020-2026-10) for explore+confirm; HL (hourly only 2026-04-14 -> 2026-11-09) confirm-only, unconditional
       + xsmom/tsmom trade lists (no taker flow on HL).
    Signals for the trade lists = the live books' own functions and params: flow@bn (lookback 3, cap .05), xsmom@bn (28, daily,
    cap .05), tsmom@bn ([14,28,56], top 12, tv .3). Computed on DAILY bars (close 00:00 UTC; hourly klines carry no taker volume)
    and executed from 04:00 UTC, i.e. 4 h staler than live: decay over the delay is if anything understated by a hair.
    Trades = w_D - w_{D-1} (no intraday drift of held weights, no no-trade band).
(d) Failure modes not about the idea: the 82-coin set is survivor-biased (irrelevant to clock effects, relevant to drift); hourly
    close at T = close of the bar opened T-1h (no intrabar fill); delay saving of a split policy is beta when the gap spans many
    hours (crypto drift ~ +0.4 bp/h 2020-26), so only policies whose gap is short or market-neutral are cost savings; 2026 is a
    partial confirm year (to 10-31).
(e) What changes my mind: a CME split that saves >= 2 bp/unit with t >= 2.24 on confirm, every year positive, would justify
    re-anchoring the daily books' clock (code change). If the hour profile itself no longer shows the drift on 2024+, the finding
    is an explore-era artefact.

SAMPLES (fixed before results): EXPLORE = decision days 2020-01-01 .. 2023-12-31. CONFIRM = 2024-01-01 .. 2026-10-30 (BN),
    HL confirm-only 2026-04 .. 2026-11. The best pair (F2 iv) is chosen on explore only.
PASS RULE (written before confirm; two primaries -> Bonferroni t >= 2.24 instead of 2):
    PRIMARY A = CME literal at the current clock, flow@bn trade list on BN-82, net of decay (turnover-weighted bp per unit traded).
    PRIMARY B = CME re-anchored (buys 17:00 NY, sells 18:00 NY vs both at 17:00 NY), same trade list.
    PASS if either primary on CONFIRM has saving >= 2 bp per unit traded, t >= 2.24, and the same (positive) sign in each confirm
    year 2024, 2025, 2026. Everything else is descriptive.
Sign convention: positive = saving (cheaper buys / dearer sells than the 04 UTC baseline). Simple returns.

    nice -n 19 .venv/bin/python -m research.studies.e2_exec_tilt [explore|confirm|all]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from kripto import data, strategies as S

ROOT = Path(__file__).resolve().parents[2]
NY = "America/New_York"
SPLIT = pd.Timestamp("2024-01-01", tz="UTC")
BASE_H = 4                     # decision bar 00:00 UTC (4h) closes 04:00 UTC; trader fires at hh:03
MAXD = 24
BOOKS = {"flow": ("flow", {"lookback": 3, "cap": 0.05}),
         "xsmom": ("xsmom", {"lookback": 28, "every_days": 1, "cap": 0.05}),
         "tsmom": ("tsmom", {"lookbacks": [14, 28, 56], "every_days": 1, "top_n": 12, "target_vol": 0.3})}


# --------------------------------------------------------------------------- data
def hourly_bn() -> pd.DataFrame:
    cols = {}
    for f in sorted((ROOT / "data/bn/klines_1h").glob("*.parquet")):
        d = pd.read_parquet(f, columns=["t", "c", "qv"])
        t = d["t"].where(d["t"] < 1e14, d["t"] // 1000)
        s = pd.Series(d["c"].to_numpy(), pd.to_datetime(t, unit="ms", utc=True) + pd.Timedelta(hours=1))   # price AT bar end
        s = s[~s.index.duplicated()].where(d["qv"].to_numpy() > 0)
        cols[f.stem.removesuffix("USDT")] = s
    p = pd.DataFrame(cols).sort_index()
    return p.reindex(pd.date_range(p.index.min(), p.index.max(), freq="1h"))


def hourly_hl() -> pd.DataFrame:
    cols = {}
    for f in sorted((ROOT / "data/hl/candles_1h").glob("*.parquet")):
        d = pd.read_parquet(f, columns=["t", "c", "v"])
        s = pd.Series(d["c"].to_numpy(), pd.to_datetime(d["t"], unit="ms", utc=True) + pd.Timedelta(hours=1))
        cols[f.stem] = s[~s.index.duplicated()].where(d["v"].to_numpy() > 0)
    p = pd.DataFrame(cols).sort_index()
    return p.reindex(pd.date_range(p.index.min(), p.index.max(), freq="1h"))


def daily_bn(coins) -> dict:
    return data.load_bn_all_panel([f"{c}USDT" for c in coins])


def daily_hl() -> dict:
    return data.load_hl_panel("1d")


# --------------------------------------------------------------------------- stats
def tstat(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan, np.nan, len(x)
    return x.mean(), x.mean() / (x.std(ddof=1) / np.sqrt(len(x))), len(x)


def ratio(num, den):
    """Turnover-weighted mean (sum num / sum den) with a day-clustered linearised t."""
    m = np.isfinite(num) & np.isfinite(den) & (den > 0)
    num, den = num[m], den[m]
    if m.sum() < 3:
        return np.nan, np.nan, int(m.sum())
    s = num.sum() / den.sum()
    z = num - s * den
    se = np.sqrt((z ** 2).sum() * len(z) / (len(z) - 1)) / den.sum()
    return s, s / se if se > 0 else np.nan, int(m.sum())


def fmt(v, t, n):
    return f"{v * 1e4:+7.2f} bp t {t:+5.2f} n {n:4d}" if np.isfinite(v) else "      n/a"


def by_year(days, num, den=None):
    out = []
    for y in sorted(set(days.year)):
        m = np.asarray(days.year == y)
        out.append(f"{y}:{(ratio(num[m], den[m]) if den is not None else tstat(num[m]))[0] * 1e4:+.1f}")
    return " ".join(out)


# --------------------------------------------------------------------------- hour profile
def hour_profile(P: pd.DataFrame, coins, lo, hi, label):
    r = (P[coins] / P[coins].shift(1) - 1)
    r = r[(r.index > lo) & (r.index <= hi)]
    start = (r.index - pd.Timedelta(hours=1)).tz_convert(NY)
    x = r.mean(axis=1)                                                  # EW across the coin set, one number per hour
    df = pd.DataFrame({"x": x.to_numpy(), "h": start.hour, "y": start.year, "d": start.date})
    df = df.dropna()
    print(f"\n[{label}] hourly simple return by NEW YORK start hour, EW {len(coins)} coins, {lo.date()}..{hi.date()}")
    allm = df["x"].mean()
    rows = []
    for h, g in df.groupby("h"):
        m, t, n = tstat(g["x"])
        yr = " ".join(f"{y}:{gg['x'].mean() * 1e4:+.1f}" for y, gg in g.groupby("y"))
        rows.append((h, m, np.median(g["x"]), t, n, yr))
    for h, m, med, t, n, yr in rows:
        flag = " <- CME shut" if h == 17 else (" <- baseline fill (23 EST/00 EDT)" if h in (23, 0) else "")
        print(f"  {h:02d}-{(h + 1) % 24:02d} NY mean {m * 1e4:+6.2f} med {med * 1e4:+6.2f} t {t:+5.2f} n {n}  | {yr}{flag}")
    print(f"  all hours mean {allm * 1e4:+.2f} bp/h")
    return rows


# --------------------------------------------------------------------------- trade lists and policies
def trades(daily: dict, book: str) -> pd.DataFrame:
    fn, params = BOOKS[book]
    w = S.REGISTRY[fn](daily, **params)
    w = w.fillna(0.0)
    started = (w.abs().sum(axis=1) > 0).cumsum() > 1
    dw = w.diff().where(started, np.nan)
    dw.index = dw.index + pd.Timedelta(days=1, hours=BASE_H)          # day bar D closes D+1 00:00; executed from D+1 04:00 UTC
    return dw.dropna(how="all")


def price_cube(P: pd.DataFrame, T0: pd.DatetimeIndex, coins) -> np.ndarray:
    """cum[k, j, i] = P_i(T0_k + j h) / P_i(T0_k) - 1, j = 0..MAXD."""
    Pc = P.reindex(columns=coins)
    base = Pc.reindex(T0).to_numpy()
    cube = np.empty((len(T0), MAXD + 1, len(coins)))
    for j in range(MAXD + 1):
        cube[:, j, :] = Pc.reindex(T0 + pd.Timedelta(hours=j)).to_numpy() / base - 1
    return cube


def ny_delay(T0: pd.DatetimeIndex, hour: int) -> np.ndarray:
    """Hours from T0 to the first `hour`:00 New York strictly after T0 (DST aware)."""
    out = np.empty(len(T0), int)
    for k, t in enumerate(T0):
        loc = t.tz_convert(NY)
        c = pd.Timestamp(loc.year, loc.month, loc.day, hour).tz_localize(NY, ambiguous=False, nonexistent="shift_forward")
        if c <= loc:
            c = (pd.Timestamp(loc.year, loc.month, loc.day) + pd.Timedelta(days=1)).replace(hour=hour).tz_localize(
                NY, ambiguous=False, nonexistent="shift_forward")
        out[k] = int(round((c.tz_convert("UTC") - t).total_seconds() / 3600))
    return out


def policy(dw: np.ndarray, cube: np.ndarray, db: np.ndarray, ds: np.ndarray, ref_b=None, ref_s=None):
    """Per-day (num, den): saving = -sum dw_i * cum_i(delay_i) over the day's trades, den = sum |dw| (both sides priced).
    ref_*: delays of the reference policy (default 0 = the 04 UTC baseline)."""
    k = np.arange(len(dw))
    cb, cs = cube[k, db, :], cube[k, ds, :]
    if ref_b is not None:
        cb = cb - cube[k, ref_b, :]
        cs = cs - cube[k, ref_s, :]
    buy, sell = dw > 0, dw < 0
    c = np.where(buy, cb, np.where(sell, cs, 0.0))
    ok = np.isfinite(c) & np.isfinite(dw) & (dw != 0)
    num = -np.where(ok, dw * c, 0.0).sum(axis=1)
    den = np.where(ok, np.abs(dw), 0.0).sum(axis=1)
    return num, den


def uncond(cube_mean: np.ndarray, db, ds, ref_b=None, ref_s=None):
    """No signal: half the units are buys, half sells, of the EW set. saving = 0.5 (cum(ds) - cum(db))."""
    k = np.arange(len(cube_mean))
    a, b = cube_mean[k, ds], cube_mean[k, db]
    if ref_b is not None:
        a, b = a - cube_mean[k, ref_s], b - cube_mean[k, ref_b]
    return 0.5 * (a - b)


def report(days, num, den, lo, hi, label):
    m = np.asarray((days >= lo) & (days < hi))
    v, t, n = ratio(num[m], den[m]) if den is not None else tstat(num[m])
    print(f"  {label:<46s} {fmt(v, t, n)} | {by_year(days[m], num[m], den[m] if den is not None else None)}")
    return v, t


def run(sample: str):
    P = hourly_bn()
    coins = list(P.columns)
    lo_all, hi_all = P.index.min(), P.index.max()
    samples = {"explore": (lo_all, SPLIT), "confirm": (SPLIT, hi_all)}
    todo = ["explore", "confirm"] if sample == "all" else [sample]
    for s in todo:
        hour_profile(P, ["BTC", "ETH"], *samples[s], f"BN BTC+ETH {s}")
        hour_profile(P, coins, *samples[s], f"BN EW-82 {s}")

    daily = daily_bn(coins)
    T0 = pd.date_range(P.index.min().ceil("1D") + pd.Timedelta(days=60, hours=BASE_H), hi_all - pd.Timedelta(hours=MAXD),
                       freq="1D")
    d17, d18 = ny_delay(T0, 17), ny_delay(T0, 18)
    z = np.zeros(len(T0), int)
    cube = price_cube(P, T0, coins)
    best = {}
    for s in todo:
        lo, hi = samples[s]
        print(f"\n===== {s.upper()} {lo.date()}..{hi.date()}  (bp per unit traded, + = saving vs 04 UTC execution) =====")
        for uname, uc in (("BTC+ETH", ["BTC", "ETH"]), ("EW-82", coins)):
            cm = np.nanmean(cube[:, :, [coins.index(c) for c in uc]], axis=2)
            print(f" unconditional {uname} (half buys, half sells, no signal):")
            report(T0, uncond(cm, d17, d18), None, lo, hi, "CME literal: buy 17 NY, sell 18 NY")
            report(T0, uncond(cm, d17, d18, d17, d17), None, lo, hi, "CME re-anchored (vs both at 17 NY)")
        for book in BOOKS:
            dwf = trades(daily, book).reindex(T0).reindex(columns=coins)
            dw = dwf.to_numpy()
            print(f" {book} trade list (turnover/day {np.nanmean(np.nansum(np.abs(dw), axis=1)):.3f}):")
            for d in (1, 2, 4, 8, 12, 17, 18, 23):
                report(T0, *policy(dw, cube, z + d, z + d), lo, hi, f"both sides delayed {d:2d} h (decay+drift)")
            report(T0, *policy(dw, cube, d17, d18), lo, hi, "PRIMARY A  CME literal (17/18 NY)")
            report(T0, *policy(dw, cube, d17, d18, d17, d17), lo, hi, "PRIMARY B  CME re-anchored")
            # placebo: same 1h split at every other NY hour (re-anchored form)
            plc = []
            for h in range(24):
                dh, dh1 = ny_delay(T0, h), ny_delay(T0, (h + 1) % 24)
                ok = (dh1 == dh + 1) & (dh1 <= MAXD)                # skip pairs that wrap past the 24h window / DST jumps
                dh, dh1 = np.where(ok, dh, 0), np.where(ok, dh1, 0)   # masked days are dropped below
                n_, d_ = policy(dw, cube, dh, dh1, dh, dh)
                m = np.asarray((T0 >= lo) & (T0 < hi)) & ok
                plc.append((h, ratio(n_[m], d_[m])[0]))
            pl = " ".join(f"{h:02d}:{v * 1e4:+.1f}" for h, v in plc)
            print(f"  placebo 1h sell-after-buy split by NY hour: {pl}")
            # best pair on explore (chosen once, then read on confirm)
            if s == "explore" or book not in best:
                m = np.asarray((T0 >= samples['explore'][0]) & (T0 < samples['explore'][1]))
                grid = np.full((MAXD, MAXD), np.nan)
                for a in range(MAXD):
                    for b in range(MAXD):
                        n_, d_ = policy(dw[m], cube[m], z[m] + a, z[m] + b)
                        grid[a, b] = n_.sum() / d_.sum()
                a, b = np.unravel_index(np.nanargmax(grid), grid.shape)
                best[book] = (int(a), int(b))
            a, b = best[book]
            report(T0, *policy(dw, cube, z + a, z + b), lo, hi, f"best explore pair: buys +{a}h, sells +{b}h")
            # POST HOC (added after the confirm was read; descriptive, NOT part of the pass rule): a form the live 4h grid can run
            # without NY-clock logic: decide on the 16:00 UTC bar (closes 20:00 UTC, before the break in EST and EDT), buy at
            # 20 UTC, sell at 23 UTC (after the break in both), vs both sides at 20 UTC. The 3 h gap carries other hours' drift.
            report(T0, *policy(dw, cube, z + 16, z + 19, z + 16, z + 16), lo, hi, "post hoc: buys 20 UTC, sells 23 UTC")
            report(T0, *policy(dw, cube, z + 16, z + 20, z + 16, z + 16), lo, hi, "post hoc: buys 20 UTC, sells 00 UTC")
    if "confirm" in todo:
        hl_confirm()


def hl_confirm():
    P = hourly_hl()
    lo, hi = P.index.min() + pd.Timedelta(days=1), P.index.max()
    print(f"\n===== HL CONFIRM-ONLY {lo.date()}..{hi.date()} =====")
    hour_profile(P, ["BTC", "ETH"], lo, hi, "HL BTC+ETH")
    hour_profile(P, list(P.columns), lo, hi, f"HL EW-{P.shape[1]}")
    daily = daily_hl()
    coins = list(P.columns)
    T0 = pd.date_range(lo.ceil("1D") + pd.Timedelta(hours=BASE_H), hi - pd.Timedelta(hours=MAXD), freq="1D")
    d17, d18 = ny_delay(T0, 17), ny_delay(T0, 18)
    cube = price_cube(P, T0, coins)
    for uname, uc in (("BTC+ETH", ["BTC", "ETH"]), (f"EW-{len(coins)}", coins)):
        cm = np.nanmean(cube[:, :, [coins.index(c) for c in uc]], axis=2)
        report(T0, uncond(cm, d17, d18, d17, d17), None, lo, hi, f"uncond {uname} CME re-anchored")
    for book in ("xsmom", "tsmom"):
        dw = trades(daily, book).reindex(T0).reindex(columns=coins).to_numpy()
        report(T0, *policy(dw, cube, d17, d18), lo, hi, f"{book} A CME literal")
        report(T0, *policy(dw, cube, d17, d18, d17, d17), lo, hi, f"{book} B CME re-anchored")
        report(T0, *policy(dw, cube, d17 * 0 + 17, d17 * 0 + 17), lo, hi, f"{book} both delayed 17 h")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "all")
