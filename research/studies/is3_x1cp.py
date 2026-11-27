"""InSilico pass 3, X1C: fspread_hold@pair robustness (backlog X1c/X1f). Descriptive, NOT registered. Live params lookback 14, enter 0.1.

  nice -n 19 .venv/bin/python -m research.studies.is3_x1cp ab     # forms a (accounts/basis at alloc 0.5) and b (P&L by BN funding interval x year) -> data/is3/x1cp_ab.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto import strategies as S
from kripto.research import bars_per_day

OUT = data.DATA / "is3"
ALLOC = 0.5


def bn_interval(coin, idx):
    """Binance funding interval (h) per day from the print times (median gap of the trailing 7 days of prints), causal-enough for a descriptive split."""
    f = data.DATA / "bn" / "funding_all" / f"{coin}USDT.parquet"
    if not f.exists():
        return pd.Series(np.nan, idx)
    t = pd.to_datetime(pd.read_parquet(f, columns=["time"])["time"], unit="ms", utc=True).sort_values()
    gap = t.diff().dt.total_seconds() / 3600
    g = pd.Series(gap.to_numpy(), t.to_numpy()).groupby(t.dt.floor("D").to_numpy()).median()
    g.index = pd.DatetimeIndex(g.index).tz_localize("UTC") if g.index.tz is None else g.index
    return g.rolling(7, min_periods=1).median().reindex(idx).ffill().round()


def run_ab():
    p = data.load_panel("pair", "1d")
    c, f = p["close"], p["funding"].fillna(0.0)
    w = S.REGISTRY["fspread_hold"](p, lookback=14, enter=0.1).ffill().fillna(0.0)
    res = bt.run(w, c, p["funding"], bt.slippage_model(p["volume"], bars_per_day(c.index)), band=0.0)
    r = (c / c.shift(1) - 1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    wl = w.shift(1).fillna(0.0)
    price, fund = wl * r, -wl * f
    tot = (price + fund).sum(axis=1)
    chk = float(np.corrcoef(tot.loc["2023-06":], (res.returns + res.costs).loc["2023-06":])[0, 1])
    print("known answer: per-cell price+funding vs bt.run returns+costs, corr", round(chk, 4), "sum", round(float(tot.sum()), 3), round(float((res.returns + res.costs).sum()), 3), flush=True)
    out = {"check_corr": round(chk, 4)}
    # ---------------- a: two accounts at alloc 0.5 (each account = half of the book's equity), no transfers
    a = {}
    for v in ("hl", "bn"):
        cols = [x for x in w.columns if x.endswith("@" + v)]
        acc = (price[cols].sum(axis=1) + fund[cols].sum(axis=1)) * 2 * ALLOC
        lev = (w[cols].abs().sum(axis=1) * 2 * ALLOC)
        a[v] = {"lev_median": round(float(lev[lev > 0].median()), 2),
                **{f"worst_{k}d": round(float(acc.rolling(k).sum().min()), 4) for k in (1, 3, 7)},
                "worst_7d_when": str(acc.rolling(7).sum().idxmin().date()),
                "by_year_worst_1d": {int(y): round(float(x.min()), 4) for y, x in acc.groupby(acc.index.year) if (lev.loc[x.index] > 0).any()}}
    hl = [x for x in w.columns if x.endswith("@hl")]
    bn = [x[:-3] + "@bn" for x in hl]
    held = w[hl].abs() > 0
    basis = np.log(c[hl] / c[bn].set_axis(hl, axis=1))
    bh = basis.where(held).abs().stack()
    side = np.sign(w[hl].shift(1))
    pair_pnl = (price[hl] + price[bn].set_axis(hl, axis=1)) * 2 * ALLOC     # basis P&L of the pair in account-equity units
    pp = pair_pnl.where(side != 0).stack()
    a["basis_abs_bp"] = {"p50": round(float(bh.quantile(.5)) * 1e4, 1), "p99": round(float(bh.quantile(.99)) * 1e4, 1), "max": round(float(bh.max()) * 1e4, 1),
                         "max_pair": str(bh.idxmax())}
    a["pair_day_price_pnl_worst"] = [[str(k[0].date()), k[1], round(float(v), 4)] for k, v in pp.nsmallest(5).items()]
    out["a"] = a
    print("a", json.dumps(a), flush=True)
    # ---------------- b: P&L by BN funding interval x year (pair = HL leg + BN leg), costs allocated by |dw| share of the day's cost
    iv = pd.DataFrame({h: bn_interval(h[:-3], c.index) for h in hl})
    dw = w.diff().abs().fillna(0.0)
    cshare = dw.div(dw.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0).mul(res.costs.reindex(c.index).fillna(0.0), axis=0)
    rows = []
    for h, b in zip(hl, bn):
        d = pd.DataFrame({"price": price[h] + price[b], "fund": fund[h] + fund[b], "cost": cshare[h] + cshare[b], "iv": iv[h], "held": (wl[h] != 0)})
        d = d[(d.held) | (d.cost > 0)]
        d["coin"] = h[:-3]
        rows.append(d)
    D = pd.concat(rows)
    D["year"] = D.index.year
    D["iv"] = D["iv"].fillna(-1).astype(int)
    tab = D.groupby(["year", "iv"])[["price", "fund", "cost"]].sum()
    tab["net"] = tab.price + tab.fund - tab.cost
    tab["pair_days"] = D[D.held].groupby(["year", "iv"]).size()
    tab = tab.round(4)
    print(tab.to_string(), flush=True)
    recent = D[D.index >= "2025-07-01"]
    top = recent.assign(net=recent.price + recent.fund - recent.cost).groupby("coin").net.sum().sort_values()
    print("2025-07+ net by coin: top 5", top.tail(5).round(4).to_dict(), "bottom 5", top.head(5).round(4).to_dict(), "total", round(float(top.sum()), 4), flush=True)
    out["b"] = {"table": {f"{y}_{i}h": v for (y, i), v in tab.to_dict("index").items()},
                "recent_top5": top.tail(5).round(4).to_dict(), "recent_bottom5": top.head(5).round(4).to_dict(), "recent_total": round(float(top.sum()), 4),
                "recent_top3_share": round(float(top.tail(3).sum() / top.sum()), 2) if top.sum() > 0 else None}
    (OUT / "x1cp_ab.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    {"ab": run_ab}[sys.argv[1]]()
