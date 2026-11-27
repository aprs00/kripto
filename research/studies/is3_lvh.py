"""InSilico pass 3, LVH: lowvol on HL vs bnall (why does the HL main book's leg work when bnall's is dead?). Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_lvh      # forms a, b -> research/is3/lvh_ab.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto.research import bars_per_day, default_band
from kripto.strategies import REGISTRY
from research.studies import is3_lib as L

LO, HI = pd.Timestamp("2023-04-01", tz="UTC"), pd.Timestamp("2026-11-22", tz="UTC")


def sr(x):
    return round(float(x.mean() / x.std() * np.sqrt(365)), 2) if x.std() > 0 else 0.0


def decomp(p, tag):
    c = p["close"]
    w = REGISTRY["lowvol"](p)
    slip = bt.slippage_model(p["volume"], bars_per_day(c.index))
    res = bt.run(w, c, p.get("funding"), slip, band=default_band())
    wf = w.ffill().fillna(0.0)
    wl = wf.shift(1).fillna(0.0)
    r = (c / c.shift(1) - 1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    f = p["funding"].reindex(index=c.index, columns=c.columns).fillna(0.0)
    price, fund = wl * r, -wl * f
    win = lambda s: s[(s.index >= LO) & (s.index < HI)]
    ret = win(res.returns)
    longp = win((price.where(wl > 0, 0.0)).sum(axis=1)); shortp = win((price.where(wl < 0, 0.0)).sum(axis=1))
    longf = win((fund.where(wl > 0, 0.0)).sum(axis=1)); shortf = win((fund.where(wl < 0, 0.0)).sum(axis=1))
    yrs = len(ret) / 365
    by_coin = win(price + fund).sum().sort_values()
    out = {"sr": sr(ret), "net_yr": round(float(ret.sum() / yrs), 4), "cost_yr": round(float(win(res.costs).sum() / yrs), 4),
           "long_price_yr": round(float(longp.sum() / yrs), 4), "short_price_yr": round(float(shortp.sum() / yrs), 4),
           "long_funding_yr": round(float(longf.sum() / yrs), 4), "short_funding_yr": round(float(shortf.sum() / yrs), 4),
           "by_year": {int(y): [sr(x), round(float(x.sum()), 4), round(float(shortp[x.index].sum()), 4), round(float(longp[x.index].sum()), 4)] for y, x in ret.groupby(ret.index.year)},
           "top5": by_coin.tail(5).round(4).to_dict(), "bottom5": by_coin.head(5).round(4).to_dict(),
           "top10_share": round(float(by_coin.tail(10).sum() / by_coin.sum()), 2) if by_coin.sum() > 0 else None,
           "n_coins_held": int((win(wf).abs() > 0).any().sum()), "w_o_best10": sr(ret.drop(ret.nlargest(10).index))}
    print(f"{tag}: {json.dumps(out)}", flush=True)
    return out, res


def main():
    out = {}
    hl = data.load_panel("hl", "1d")
    out["hl"], _ = decomp(hl, "HL")
    hl_on = hl["close"].notna()
    bn = data.load_panel("bnall", "1d")
    out["bnall"], _ = decomp(bn, "bnall same dates")
    # bnall restricted point-in-time to coins with an HL close that day (name map: HL k-prefix = BN 1000-prefix)
    m = {}
    for col in bn["close"].columns:
        hc = col
        if col.startswith("1000"):
            hc = "k" + col[4:]
        if hc in hl_on.columns:
            m[col] = hc
    on = pd.DataFrame(False, bn["close"].index, bn["close"].columns)
    for col, hc in m.items():
        on[col] = hl_on[hc].reindex(bn["close"].index).fillna(False).astype(bool)
    bnr = {k: (v.where(on) if k in ("close", "volume") else v) for k, v in bn.items()}
    out["bnall_hl_universe"], _ = decomp(bnr, "bnall restricted to HL-listed coins")
    out["mapped_coins"] = len(m)
    json.dump({"study": "research/studies/is3_lvh.py", "window": [str(LO.date()), str(HI.date())], **out}, open(L.OUT / "lvh_ab.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
