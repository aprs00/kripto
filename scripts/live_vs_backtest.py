"""T0a: live paper book vs a backtest replay of exactly the live period (tracking check).

For every non-retired single-entry shadow book on HL or Binance (pair books are skipped: their legs have no panel replay yet):
re-run the strategy on the same 4h panel the live engine uses, with the live engine's weight clipping (apply_risk) and the
shadow book's band (min order / shadow equity), starting flat at the book's first rebalance bar, and compare with the live
equity series day by day:
  ret      cumulative return over the common days (live vs backtest)
  corr     correlation of daily returns;  te = std of the daily difference (bp/day)
  cost     trading cost as % of equity: live = fees + (fill - mid) slippage from the fills table; bt = fee + slippage_model
  fund     funding as % of equity (live funding table vs the panel's funding; Binance live panels carry no funding, so bt=0 there)
  turn     traded notional / equity (sum over the period)
  wcorr    correlation of live position weights (last equity snapshot) with the backtest's held weights at the last bar
A large gap is a bug or a bad cost model until proven otherwise (CLAUDE.md T0a). The universe is the point-in-time one recorded by paper.record_universe where it exists (from 2026-11-17); before that
an approximation (today's list), which on Binance adds coins that only joined the top-volume list later. Read-only: no API calls, no registry lines
(a replay of the live period is bookkeeping, not an experiment).

Replays use the CURRENT config params: after a param change (e.g. the 2026-11-17 5% cap on the Binance x-sec books) compare
only days after the change.

--since YYYY-MM-DD restricts returns / costs / turnover to days after that date (the replay still starts at the book's first bar, so
its positions are warmed up). Use it after a param change or for the point-in-time-universe era (`--since 2026-11-18`).
--daily prints the day-by-day live and replay returns.

--main replays the MAIN books instead (LVB 2026-11-28): main_scale x sum(alloc x each live entry's last saved target), apply_risk,
band = min order / the book's own equity; overlay-sleeve (ladder) fills are excluded from its costs and counted in sleeve_fills.
Current allocs / main_scale are used: compare only days after the last alloc or main_scale change (--since).

usage: python -m scripts.live_vs_backtest [--main] [--since YYYY-MM-DD] [--daily] [book ...]
"""
from __future__ import annotations

import argparse
import json
import sqlite3

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data, paper as P, venue_bn
from kripto.strategies import REGISTRY, bars_per_day

MIN_ORDER = {"hl": 10.0, "bn": 5.0}


def _db():
    return sqlite3.connect(f"file:{P.DB}?mode=ro", uri=True)


def live_universe(c, venue: str) -> list[str]:
    """Approximation of the live engine's universe (it drifts hourly): HL = the first LIVE_UNIVERSE names of the latest
    ctx snapshot (same order as paper.refresh_data); Binance = live kline files with a bar in the last day. Plus every
    coin any book of that venue ever traded."""
    traded = set(pd.read_sql("select distinct coin from fills", c)["coin"])
    if venue == "bn":
        now = pd.Timestamp.now("UTC")
        coins = [f.stem for f in venue_bn.LIVE_DIR.glob("*.parquet")
                 if now - pd.Timestamp(f.stat().st_mtime, unit="s", tz="UTC") < pd.Timedelta(days=1)]
        return sorted(set(coins) | (traded & {f.stem for f in venue_bn.LIVE_DIR.glob("*.parquet")}))
    ctx = pd.read_parquet(sorted((data.DATA / "hl" / "ctx").glob("*.parquet"))[-1])
    last = ctx[ctx["ts"] == ctx["ts"].max()]["name"].tolist()[:P.LIVE_UNIVERSE]
    have = {f.stem for f in (data.DATA / "hl" / f"candles_{P.LIVE_INTERVAL}").glob("*.parquet")}
    return sorted((set(last) | traded) & have)


def recorded_universe(venue: str) -> dict[pd.Timestamp, list[str]]:
    c = _db()
    try:
        rows = c.execute("select bar, coins from universe where venue=?", (venue,)).fetchall()
    except sqlite3.OperationalError:
        return {}
    return {pd.Timestamp(b): json.loads(cs) for b, cs in rows}


def daily_live(c, book: str) -> pd.Series:
    """Equity at the first snapshot of each UTC day (taken right after the 00:xx rebalance), as a series by day."""
    eq = pd.read_sql("select ts, equity from equity where book=? order by ts", c, params=(book,))
    eq["ts"] = pd.to_datetime(eq["ts"], utc=True)
    eq["day"] = eq["ts"].dt.floor("D")
    return eq.groupby("day")["equity"].first()


def entry_targets(name: str, sc: dict, venue: str, panel: dict, start_bar: pd.Timestamp) -> pd.DataFrame:
    """One entry's raw target rows as live computed them (point-in-time universe where recorded), before apply_risk."""
    fn = REGISTRY[sc.get("strategy", name.split("@")[0])]
    w = fn(panel, **sc.get("params", {}))
    univ = recorded_universe(venue)
    if univ:   # point-in-time universe (paper.record_universe, since 2026-11-17): recompute each bar's row on what live saw
        sets: dict[tuple, list] = {}
        for b, cs in univ.items():
            if b in w.index and b >= start_bar:
                sets.setdefault(tuple(cs), []).append(b)
        for cs, bars in sets.items():
            cols = [x for x in cs if x in panel["close"].columns]
            sub = fn({k: v[cols] for k, v in panel.items()}, **sc.get("params", {}))
            w.loc[bars] = sub.loc[bars].reindex(columns=w.columns).to_numpy()
    return w


def _panel(venue: str, coins: list[str]) -> dict:
    return venue_bn.live_panel(coins) if venue == "bn" else P.live_panel(coins)


def main_targets(parts: list[tuple[float, pd.DataFrame]], scale: float) -> pd.DataFrame:
    """paper.run_books' main-book blend: scale x sum(alloc x the entry's LAST SAVED target), where a bar on which an entry produced no
    row keeps its previous one (the `targets` table) and a produced row's NaNs are 0."""
    cols = sorted(set().union(*[set(w.columns) for _, w in parts]))
    idx = parts[0][1].index
    tot = pd.DataFrame(0.0, idx, cols)
    for a, w in parts:
        w = w.reindex(index=idx, columns=cols)
        have = w.notna().any(axis=1)
        w = w.mask(have, w.fillna(0.0), axis=0)
        tot = tot + a * w.ffill().fillna(0.0)
    any_row = pd.concat([w.reindex(idx).notna().any(axis=1) for _, w in parts], axis=1).any(axis=1).cummax()
    return (tot * scale).where(any_row, np.nan, axis=0)


def run_replay(w: pd.DataFrame, panel: dict, venue: str, start_bar: pd.Timestamp, risk: dict, eq0: float):
    w = w.apply(lambda row: P.apply_risk(row, risk) if row.notna().any() else row, axis=1)
    if venue == "bn":   # each symbol's own MIN_NOTIONAL (BTC $50, ETH $20): a target below it is never opened live (LVB 11-28:
        # without this small:main_bn's replay held BTC at $36 and tracked live at corr -.02; with it .79). Zeroing approximates live,
        # which can keep an older, bigger position; disk cache only, no request.
        mins = pd.Series({k: v["min_notional"] for k, v in venue_bn.symbol_filters(None, max_age_h=1e9).items()}).reindex(w.columns).fillna(5.0)
        w = w.where((w.abs() * eq0 >= mins.to_numpy()) | (w == 0) | w.isna(), 0.0)
    w.loc[w.index < start_bar] = np.nan                   # flat until the live book's first rebalance bar
    bpd = bars_per_day(panel["close"].index)
    slip = bt.slippage_model(panel["volume"], bpd)
    fee = 0.0005 if venue == "bn" else bt.TAKER_FEE
    res = bt.run(w, panel["close"], panel.get("funding"), slip, band=MIN_ORDER[venue] / eq0, fee=fee)
    res.target = w   # targets incl. the last bar's rebalance (res.weights = held DURING a bar, i.e. before it)
    return res, panel


def replay(name: str, sc: dict, venue: str, start_bar: pd.Timestamp, coins: list[str], risk: dict, eq0: float):
    panel = _panel(venue, coins)
    return run_replay(entry_targets(name, sc, venue, panel, start_bar), panel, venue, start_bar, risk, eq0)


MAIN_BOOKS = {"hl": "main", "bn": "main_bn"}


def main(only: list[str], since: str | None = None, daily: bool = False, mains: bool = False):
    """Shadow books (default) or, with mains=True, the main books and their small twins (LVB, 2026-11-28)."""
    since_ts = pd.Timestamp(since, tz="UTC") if since else None
    cfg, risk = P.load_cfg()
    c = _db()
    rows = []
    jobs = []   # (book, venue, build(panel, start_bar) -> raw targets, coins)
    if not mains:
        for name, sc in cfg.items():
            venue = P.venue_of(sc)
            if sc.get("status") == "retired" or venue not in ("hl", "bn"):
                continue
            if only and f"shadow:{name}" not in only and name not in only:
                continue
            jobs.append((f"shadow:{name}", venue, lambda pn, sb, name=name, sc=sc, venue=venue: entry_targets(name, sc, venue, pn, sb)))
    else:
        for venue, mb in MAIN_BOOKS.items():
            live_e = {n: sc for n, sc in cfg.items() if P.venue_of(sc) == venue and sc.get("status") in ("incubation", "active")
                      and sc.get("alloc", 0) > 0}
            if not live_e:
                continue
            scale = float(risk.get("main_scale", {}).get(mb, 1.0))
            build = lambda pn, sb, live_e=live_e, scale=scale, venue=venue: main_targets(
                [(sc["alloc"], entry_targets(n, sc, venue, pn, sb)) for n, sc in live_e.items()], scale)
            for book in (mb, f"small:{mb}"):
                if not only or book in only:
                    jobs.append((book, venue, build))
    for book, venue, build in jobs:
        reb = pd.read_sql("select bar from rebalances where book=? order by bar", c, params=(book,))
        if reb.empty:
            continue
        start_bar = pd.Timestamp(reb["bar"].iloc[0])
        eq0 = float(pd.read_sql("select start_equity from books where name=?", c, params=(book,)).iloc[0, 0])
        fills = pd.read_sql("select * from fills where book=?", c, params=(book,))
        fund = pd.read_sql("select * from funding where book=?", c, params=(book,))
        sleeve = fills["reason"].fillna("").str.startswith("ladder")   # overlay sleeve fills (kripto/ladder.py): not part of the replayed mix
        coins = live_universe(c, venue)
        try:
            panel = _panel(venue, coins)
            res, panel = run_replay(build(panel, start_bar), panel, venue, start_bar, risk, eq0)
        except Exception as e:
            print(f"{book}: replay failed: {e!r}")
            continue
        live = daily_live(c, book)
        # backtest: bar t's return is realised at t + bar; group by that close time's UTC day
        bar = panel["close"].index[1] - panel["close"].index[0]
        r = res.returns[res.returns.index >= start_bar]
        # live equity on day D (first snapshot, ~00:10) closes the return of day D-1 (00:00 -> 24:00 bar closes),
        # so a bar closing in (D-1 00:00, D 00:00] belongs to live day D
        r.index = r.index + bar - pd.Timedelta(microseconds=1)
        bt_day = (1 + r).groupby(r.index.floor("D") + pd.Timedelta(days=1)).prod() - 1
        live_ret = live.pct_change().dropna()
        days = live_ret.index.intersection(bt_day.index)
        days = days[days > live.index[0]]
        sel = res.costs.index >= start_bar
        if since_ts is not None:      # a live day D's return closes the bars of D-1: keep days strictly after `since`
            days = days[days > since_ts]
            sel &= res.costs.index >= since_ts
            keep = pd.to_datetime(fills["ts"], utc=True, format="ISO8601") >= since_ts
            fills, sleeve = fills[keep], sleeve[keep]
            fund = fund[pd.to_datetime(fund["ts"], utc=True, format="ISO8601") >= since_ts]
        if len(days) == 0:
            continue
        lr, br = live_ret.reindex(days), bt_day.reindex(days)
        eq_mean = float(live.mean())
        mf = fills[~sleeve]
        live_fee = float(mf["fee"].sum())
        live_slip = float((mf["size"] * (mf["px"] - mf["mid"])).sum())
        if daily:
            print(book)
            print((100 * pd.DataFrame({"live%": lr, "bt%": br, "diff%": lr - br})).round(2).to_string())
        row = {
            "book": book, "days": len(days),
            "ret_live%": round(100 * ((1 + lr).prod() - 1), 2), "ret_bt%": round(100 * ((1 + br).prod() - 1), 2),
            "corr": round(float(lr.corr(br)), 2) if len(days) > 2 else None,
            "te_bp": round(1e4 * float((lr - br).std()), 1) if len(days) > 2 else None,
            "cost_live%": round(100 * (live_fee + live_slip) / eq_mean, 3),
            "cost_bt%": round(100 * float(res.costs[sel].sum()), 3),
            "fund_live%": round(100 * float(fund["amount"].sum()) / eq_mean, 3),
            "fund_bt%": round(100 * float(res.funding[sel].sum()), 3),
            "turn_live": round(float((mf["size"].abs() * mf["px"]).sum()) / eq_mean, 2),
            "turn_bt": round(float(res.turnover[sel].sum()), 2),
            "wcorr": wcorr(c, book, res, panel),
        }
        if sleeve.any():
            row["sleeve_fills"] = int(sleeve.sum())
            row["sleeve_turn"] = round(float((fills.loc[sleeve, "size"].abs() * fills.loc[sleeve, "px"]).sum()) / eq_mean, 3)
        rows.append(row)
    out = pd.DataFrame(rows)
    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print(out.to_string(index=False))
    return out


def wcorr(c, book: str, res, panel) -> float | None:
    """Live weights now vs backtest weights held during the last bar (same coins)."""
    pos = pd.read_sql("select coin, size from positions where book=?", c, params=(book,)).set_index("coin")["size"]
    if pos.empty:
        return None
    px = panel["close"].ffill().iloc[-1]
    eq = float(pd.read_sql("select equity from equity where book=? order by ts desc limit 1", c, params=(book,)).iloc[0, 0])
    lw = (pos * px.reindex(pos.index)).dropna() / eq
    # live positions are AFTER the last bar's rebalance; res.weights is held DURING a bar (before it), so compare with the
    # last target row (the 2026-11-17 blend check: 0.32 against held weights, a timing artefact, not a bug)
    bw = res.target.ffill().iloc[-1].fillna(0.0)
    allc = lw.index.union(bw[bw != 0].index)
    a, b = lw.reindex(allc).fillna(0), bw.reindex(allc).fillna(0)
    return round(float(a.corr(b)), 2) if len(allc) > 2 else None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("books", nargs="*")
    ap.add_argument("--since")
    ap.add_argument("--daily", action="store_true")
    ap.add_argument("--main", action="store_true", help="the main books (main, main_bn + small twins) instead of the shadows")
    a = ap.parse_args()
    main(a.books, a.since, a.daily, a.main)
