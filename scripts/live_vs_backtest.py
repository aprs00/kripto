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

usage: python -m scripts.live_vs_backtest [--since YYYY-MM-DD] [--daily] [book ...]
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


def replay(name: str, sc: dict, venue: str, start_bar: pd.Timestamp, coins: list[str], risk: dict, eq0: float):
    if venue == "bn":
        panel = venue_bn.live_panel(coins)
    else:
        panel = P.live_panel(coins)
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
    w = w.apply(lambda row: P.apply_risk(row, risk) if row.notna().any() else row, axis=1)
    w.loc[w.index < start_bar] = np.nan                   # flat until the live book's first rebalance bar
    bpd = bars_per_day(panel["close"].index)
    slip = bt.slippage_model(panel["volume"], bpd)
    fee = 0.0005 if venue == "bn" else bt.TAKER_FEE
    res = bt.run(w, panel["close"], panel.get("funding"), slip, band=MIN_ORDER[venue] / eq0, fee=fee)
    res.target = w   # targets incl. the last bar's rebalance (res.weights = held DURING a bar, i.e. before it)
    return res, panel


def main(only: list[str], since: str | None = None, daily: bool = False):
    since_ts = pd.Timestamp(since, tz="UTC") if since else None
    cfg, risk = P.load_cfg()
    c = _db()
    rows = []
    for name, sc in cfg.items():
        venue = P.venue_of(sc)
        if sc.get("status") == "retired" or venue not in ("hl", "bn"):
            continue
        book = f"shadow:{name}"
        if only and book not in only and name not in only:
            continue
        reb = pd.read_sql("select bar from rebalances where book=? order by bar", c, params=(book,))
        if reb.empty:
            continue
        start_bar = pd.Timestamp(reb["bar"].iloc[0])
        eq0 = float(pd.read_sql("select start_equity from books where name=?", c, params=(book,)).iloc[0, 0])
        fills = pd.read_sql("select * from fills where book=?", c, params=(book,))
        fund = pd.read_sql("select * from funding where book=?", c, params=(book,))
        coins_traded = sorted(set(fills["coin"]))
        coins = live_universe(c, venue)
        try:
            res, panel = replay(name, sc, venue, start_bar, coins, risk, eq0)
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
            fills = fills[pd.to_datetime(fills["ts"], utc=True, format="ISO8601") >= since_ts]
            fund = fund[pd.to_datetime(fund["ts"], utc=True, format="ISO8601") >= since_ts]
        if len(days) == 0:
            continue
        lr, br = live_ret.reindex(days), bt_day.reindex(days)
        eq_mean = float(live.mean())
        live_fee = float(fills["fee"].sum())
        live_slip = float((fills["size"] * (fills["px"] - fills["mid"])).sum())
        if daily:
            print(book)
            print((100 * pd.DataFrame({"live%": lr, "bt%": br, "diff%": lr - br})).round(2).to_string())
        rows.append({
            "book": book, "days": len(days),
            "ret_live%": round(100 * ((1 + lr).prod() - 1), 2), "ret_bt%": round(100 * ((1 + br).prod() - 1), 2),
            "corr": round(float(lr.corr(br)), 2) if len(days) > 2 else None,
            "te_bp": round(1e4 * float((lr - br).std()), 1) if len(days) > 2 else None,
            "cost_live%": round(100 * (live_fee + live_slip) / eq_mean, 3),
            "cost_bt%": round(100 * float(res.costs[sel].sum()), 3),
            "fund_live%": round(100 * float(fund["amount"].sum()) / eq_mean, 3),
            "fund_bt%": round(100 * float(res.funding[sel].sum()), 3),
            "turn_live": round(float((fills["size"].abs() * fills["px"]).sum()) / eq_mean, 2),
            "turn_bt": round(float(res.turnover[sel].sum()), 2),
            "wcorr": wcorr(c, book, res, panel),
        })
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
    a = ap.parse_args()
    main(a.books, a.since, a.daily)
