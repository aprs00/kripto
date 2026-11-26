"""T2b(f) (2026-11-26 research): how much of listing_short (lead leg of HL main's blend_nested) survives realistic listing-day costs?
C1 (11-25): the live XTEN short (HL listing 11-16) cost ~160 bp per trade (slip 39 + close->fill drift 120 bp at the old ~11-min delay)
against the model's 25 bp cap. One event, so the model was not refit; this asks how sensitive the book is, not what the cost is.
Method: the live config's backtest (kripto.backtest, model costs), then an EXTRA charge of x bp on every unit of weight traded in a coin
whose age (days since its first valid close) is <= A days. x in {0, 50, 100, 150, 250}, A in {3, 7}. Also the share of turnover in young coins.
Pre-registered reading (journal 2026-11-26): if listing_short's HL SR at x=150, A=3 stays >= 0.8 x its base SR, the cost risk is noted and
nothing changes; otherwise backlog T2b(f): a pre-registered skip_days walk-forward under an age-dependent cost stress.
Descriptive, no registry line.  usage: nice -n 19 .venv/bin/python -m research.studies.t2b_listing_cost
"""
import numpy as np
import pandas as pd

from kripto import backtest as bt, data
from kripto.research import bars_per_day, default_band
from kripto.strategies import REGISTRY

BOOKS = {"listing_short": ("listing_short", {"skip_days": 1, "hold_days": 60, "min_dv": 1e6}),
         "blend_nested_live": ("blend", {"components": {"listing_short": {}, "lowvol": {}, "tsmom": {}}})}


def sr(r):
    r = r.dropna()
    return r.mean() / r.std() * np.sqrt(365) if r.std() > 0 else np.nan


def main():
    for ds in ("hl", "bnall"):
        p = data.load_panel(ds, "1d")
        c = p["close"]
        slip = bt.slippage_model(p["volume"], bars_per_day(c.index))
        first = c.notna().idxmax()
        age = pd.DataFrame({k: (c.index - first[k]).days for k in c.columns}, index=c.index)
        for name, (fn, prm) in BOOKS.items():
            if ds == "bnall" and name != "listing_short":
                continue
            res = bt.run(REGISTRY[fn](p, **prm), c, p.get("funding"), slip, band=default_band())
            W = res.weights.fillna(0.0)
            dW = W.diff().abs().fillna(W.abs())
            live = res.gross > 0
            start = live[live].index[0]
            r0 = res.returns[res.returns.index >= start]
            tot = dW.sum().sum()
            line = [f"{ds} {name}: base SR {sr(r0):.2f}, model cost/yr {res.costs[res.costs.index >= start].sum() / (len(r0) / 365):.1%}"]
            for A in (3, 7):
                young = dW.where(age <= A, 0.0)
                share = young.sum().sum() / tot if tot > 0 else 0.0
                cells = []
                for x in (50, 100, 150, 250):
                    extra = young.sum(axis=1) * x / 1e4
                    r = (res.returns - extra)[res.returns.index >= start]
                    cells.append(f"+{x}bp {sr(r):.2f}")
                line.append(f"age<={A}d turnover share {share:.0%} (yearly {young.sum().sum() / (len(r0) / 365):.2f}x equity): " + ", ".join(cells))
            print("\n  ".join(line))


if __name__ == "__main__":
    main()
