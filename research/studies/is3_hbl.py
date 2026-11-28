"""InSilico pass 3, HBL: HL listing_short net P&L split alt-short legs vs BTC hedge leg (price, funding) by year; young-coin beta by age.
Per-leg P&L from the backtest's held weights: price = w_held[t] * r[t]; funding = -w_held[t] * funding[t] (positive funding: longs pay). Costs are book-level."""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY


def split(panel, w, band=0.005):
    slip = bt.slippage_model(panel["volume"], bars_per_day(panel["close"].index))
    res = bt.run(w, panel["close"], panel.get("funding"), slip, band=band)
    W = res.weights.reindex(columns=panel["close"].columns).fillna(0.0)
    r = panel["close"].pct_change(fill_method=None).reindex(W.index).fillna(0.0)
    f = panel["funding"].reindex(index=W.index, columns=W.columns).fillna(0.0) if "funding" in panel else 0 * W
    price, fund = W * r, -W * f
    btc = ["BTC"]
    alts = [c for c in W.columns if c != "BTC"]
    d = pd.DataFrame({"net": res.returns, "costs": -res.costs, "btc_price": price[btc].sum(1), "btc_funding": fund[btc].sum(1),
                      "alt_price": price[alts].sum(1), "alt_funding": fund[alts].sum(1)})
    d["resid"] = d["net"] - d.drop(columns="net").sum(1)
    return d, res


def by_year(d, btc_r):
    out = {}
    for y, g in d.groupby(d.index.year):
        s = {k: round(float(v * 365 / len(g)), 4) for k, v in g.sum().items()}
        s["days"] = int(len(g))
        s["sr"] = round(float(g["net"].mean() / g["net"].std() * np.sqrt(365)), 3) if g["net"].std() > 0 else 0.0
        s["corr_btc"] = round(float(g["net"].corr(btc_r.reindex(g.index))), 3)
        out[int(y)] = s
    return out


def young_beta(panel, w, lo_age, hi_age, lo, hi):
    """pooled OLS beta of held listing coins' daily returns on BTC, coin-days with age in [lo_age, hi_age] and a short held."""
    c, v = panel["close"], panel["volume"]
    traded = (v.fillna(0) > 0) & c.notna()
    age = traded.cummax().cumsum()
    r = c.pct_change(fill_method=None)
    held = (w.shift(1).reindex(c.index) < 0)
    m = held & (age.shift(1) >= lo_age) & (age.shift(1) <= hi_age) & r.notna()
    m.loc[:, "BTC"] = False
    ix = (c.index >= pd.Timestamp(lo, tz="UTC")) & (c.index < pd.Timestamp(hi, tz="UTC"))
    m = m & pd.DataFrame(np.broadcast_to(ix[:, None], m.shape), m.index, m.columns)
    x = np.broadcast_to(r["BTC"].to_numpy()[:, None], r.shape)[m.to_numpy()]
    y = r.to_numpy()[m.to_numpy()]
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 30:
        return {"n": int(len(x))}
    b = float(np.cov(x, y)[0, 1] / np.var(x, ddof=1))
    # coin-day bootstrap CI clustered by day is overkill here; report n and a robust (winsorised 1/99) beta too
    yw = np.clip(y, *np.quantile(y, [0.01, 0.99]))
    bw = float(np.cov(x, yw)[0, 1] / np.var(x, ddof=1))
    up, dn = x > 0, x < 0
    return {"n": int(len(x)), "beta": round(b, 3), "beta_winsor": round(bw, 3),
            "beta_up": round(float(np.cov(x[up], y[up])[0, 1] / np.var(x[up], ddof=1)), 3),
            "beta_down": round(float(np.cov(x[dn], y[dn])[0, 1] / np.var(x[dn], ddof=1)), 3)}


if __name__ == "__main__":
    form = sys.argv[1] if len(sys.argv) > 1 else "a"
    out = {}
    if form == "a":
        p = data.load_panel("hl", "1d")
        w = REGISTRY["listing_short"](p)
        d, res = split(p, w)
        out["hl_listing_short"] = by_year(d[d.index >= pd.Timestamp("2023-01-01", tz="UTC")], p["close"]["BTC"].pct_change(fill_method=None))
        wb = REGISTRY["blend"](p, components={"listing_short": {}, "lowvol": {}, "tsmom": {}})
        db, _ = split(p, wb)
        out["hl_blend_main"] = by_year(db[db.index >= pd.Timestamp("2023-01-01", tz="UTC")], p["close"]["BTC"].pct_change(fill_method=None))
        for k, v in out.items():
            print(k, flush=True)
            for y, s in v.items():
                print(" ", y, s, flush=True)
    else:
        import pickle
        for nm, (p, lo, hi) in {"hl": (data.load_panel("hl", "1d"), "2023-01-01", "2025-01-01"),
                                "bnall_cache": (pickle.load(open(sys.argv[2], "rb")), "2021-01-01", "2024-01-01")}.items():
            w = REGISTRY["listing_short"](p)
            out[nm] = {f"{a}-{b}": young_beta(p, w, a, b, lo, hi) for a, b in ((2, 7), (8, 20), (21, 61))}
            print(nm, out[nm], flush=True)
    json.dump(out, open(f"research/is3/hbl_{form}.json", "w"), indent=1)
