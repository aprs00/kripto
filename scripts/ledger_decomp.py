"""Daily live P&L of one paper book split into funding, fees and price, from the ledger alone (works for every book type,
including the two-venue pair books and main books with an overlay sleeve, which scripts.live_vs_backtest cannot replay).

    .venv/bin/python -m scripts.ledger_decomp main@pair [--since 2026-11-27]

price = equity change - funding + fees (slippage is inside price: fills at worse than mid). The last line gives the annualised
vol of the price part and of the whole equity, on the book's starting equity, to set next to the backtest's vol.
"""
import sys

import numpy as np
import pandas as pd

from kripto import paper as P


def decompose(store: P.Store, book: str, since: str | None = None) -> pd.DataFrame:
    def frame(sql, cols):
        df = pd.DataFrame(store.q(sql, book), columns=cols)
        df["ts"] = pd.to_datetime(df["ts"], utc=True, format="mixed")
        return df.set_index("ts")
    eq = frame("select ts, equity from equity where book=? order by ts", ["ts", "eq"])["eq"]
    if eq.empty:
        return pd.DataFrame()
    first = eq.resample("1D").first()
    days = first.index
    fund = frame("select ts, amount from funding where book=?", ["ts", "a"])["a"].resample("1D").sum()
    fees = frame("select ts, fee from fills where book=?", ["ts", "fee"])["fee"].resample("1D").sum()
    out = pd.DataFrame({"equity": first, "d_eq": first.shift(-1) - first}, index=days)
    out["funding"] = fund.reindex(days).fillna(0.0)
    out["fees"] = fees.reindex(days).fillna(0.0)
    out["price"] = out["d_eq"] - out["funding"] + out["fees"]
    out = out.dropna(subset=["d_eq"])
    return out.loc[since:] if since else out


def main():
    args = sys.argv[1:]
    since = args[args.index("--since") + 1] if "--since" in args else None
    book = args[0]
    store = P.Store()
    d = decompose(store, book, since)
    if d.empty:
        print(f"{book}: no equity rows")
        return
    start = store.q("select start_equity from books where name=?", book)[0][0]
    print(d.round(2).to_string())
    k = np.sqrt(365) / start
    print(f"{book}: {len(d)} days | sum funding ${d.funding.sum():.2f} fees ${d.fees.sum():.2f} price ${d.price.sum():.2f} | "
          f"ann vol: price {d.price.std() * k:.1%}, equity {d.d_eq.std() * k:.1%} | ann mean {d.d_eq.mean() * 365 / start:+.1%}")


if __name__ == "__main__":
    main()
