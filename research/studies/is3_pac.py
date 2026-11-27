"""InSilico pass 3, PAC: per-venue account P&L of a live pair book from the ledger. Descriptive.

  nice -n 19 .venv/bin/python -m research.studies.is3_pac a [book]   # -> research/is3/pac_a.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import paper as P
from kripto import venue_pair as VP


def run_a(book="shadow:fspread_hold@pair"):
    s = P.Store()
    f = pd.DataFrame(s.q("select ts, coin, size, px, fee from fills where book=? order by ts", book), columns=["ts", "coin", "size", "px", "fee"])
    f["ts"] = pd.to_datetime(f.ts, utc=True, format="mixed")
    fu = pd.DataFrame(s.q("select ts, coin, amount from funding where book=?", book), columns=["ts", "coin", "amount"])
    fu["ts"] = pd.to_datetime(fu.ts, utc=True, format="mixed")
    start = s.q("select start_equity from books where name=?", book)[0][0]
    coins = sorted({c[:-3] for c in f.coin})
    panel = VP.live_panel(coins)
    cl = panel["close"]
    days = pd.date_range(f.ts.min().floor("1D"), cl.index[-1], freq="1D")
    out = {"book": book, "start_equity": start, "last_close_bar": str(cl.index[-1].date()), "venues": {}}
    for v in ("hl", "bn"):
        fv = f[f.coin.str.endswith("@" + v)].copy()
        rows = []
        for d in days:
            # trades during day d+1 (00:13) implement bar d; mark the end-of-bar-d position at close(d) (= price at d+1 00:00)
            upto = fv[fv.ts < d + pd.Timedelta(days=1)]
            pos = upto.groupby("coin")["size"].sum()
            cash = -(upto["size"] * upto["px"]).sum() - upto["fee"].sum()
            mark = sum(q * cl.at[d, c] for c, q in pos.items() if c in cl.columns and np.isfinite(cl.at[d, c]) and q != 0)
            fund = fu[(fu.coin.str.endswith("@" + v)) & (fu.ts < d + pd.Timedelta(days=1))].amount.sum()
            rows.append({"day": str(d.date()), "pnl": round(float(cash + mark + fund), 2), "funding": round(float(fund), 2), "fees": round(float(upto["fee"].sum()), 2),
                         "net_notional": round(float(mark), 1)})
        out["venues"][v] = rows
    a, b = out["venues"]["hl"], out["venues"]["bn"]
    out["per_day"] = [{"day": x["day"], "hl_pnl": x["pnl"], "bn_pnl": y["pnl"], "book_pnl": round(x["pnl"] + y["pnl"], 2),
                       "hl_account_pct": round(x["pnl"] / (start / 2) * 100, 2), "bn_account_pct": round(y["pnl"] / (start / 2) * 100, 2)} for x, y in zip(a, b)]
    for r in out["per_day"]:
        print(r)
    eq = s.q("select equity from equity where book=? order by ts desc limit 1", book)[0][0]
    out["ledger_equity_now"] = round(float(eq), 2)
    print("ledger equity now", eq, "start", start)
    json.dump(out, open("research/is3/pac_a.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": run_a}[sys.argv[1]](*sys.argv[2:])
