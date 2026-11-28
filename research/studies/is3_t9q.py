"""InSilico pass 3, T9Q: HL-venue books' live fills replayed as post-only at the HL price of the order minute, fills judged on HL 1-min OHLC
(data/hl/flow), trade-through q, next 24 h from the next minute. Descriptive.   PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_t9q -> research/is3/t9q_ab.json"""
from __future__ import annotations

import json
import sqlite3

import numpy as np
import pandas as pd

from kripto.data import DATA

EV = DATA.parent / "research" / "is3"
TAKER, MAKER = 4.5, 1.5
BOOKS = ("main", "shadow:blend_nested", "shadow:blend", "shadow:tsmom", "shadow:xsmom", "shadow:xsmom_k", "shadow:blend_nested_lam1", "small:main")


def minutes():
    fl = pd.concat([pd.read_parquet(x, columns=["coin", "minute", "h", "l", "c", "buy_ntl", "sell_ntl"]) for x in sorted((DATA / "hl" / "flow").glob("*.parquet"))])
    fl["minute"] = pd.to_datetime(fl["minute"] * 60, unit="s", utc=True)    # minutes since epoch
    return {c: x.set_index("minute").sort_index() for c, x in fl.groupby("coin")}


def replay(g):
    con = sqlite3.connect(DATA.parent / "state" / "paper.db")
    f = pd.read_sql(f"select ts, book, coin, size, px, mid, fee, slip_bps from fills where book in ({','.join('?' * len(BOOKS))})", con, params=BOOKS)
    f["ts"] = pd.to_datetime(f["ts"], utc=True, format="ISO8601")
    end = max(x.index.max() for x in g.values())
    rows = []
    for _, r in f.iterrows():
        x = g.get(r.coin)
        if x is None or r.ts < x.index.min() + pd.Timedelta(minutes=5) or r.ts + pd.Timedelta(hours=24) > end:
            continue
        m0 = r.ts.floor("1min"); ref = x["c"].asof(m0)
        w = x[(x.index > m0) & (x.index < r.ts + pd.Timedelta(hours=24))]
        if not np.isfinite(ref) or len(w) < 600:
            continue
        side = float(np.sign(r["size"]))
        ext = float(w["l"].min()) if side > 0 else float(w["h"].max())
        thru = side * (ref - ext) / ref * 1e4
        hit = w.index[(w["l"] < ref * (1 - 5e-4)) if side > 0 else (w["h"] > ref * (1 + 5e-4))]
        dv = float((x["buy_ntl"] + x["sell_ntl"]).loc[m0 - pd.Timedelta(days=1):m0].sum())
        rows.append({"ts": r.ts, "book": r.book, "coin": r.coin, "side": side, "notional": abs(r["size"] * r.px), "thru_bp": thru,
                     "min_to_fill_q5": float((hit[0] - m0).total_seconds() / 60) if len(hit) else np.nan,
                     "move24": side * (float(w["c"].iloc[-1]) / ref - 1) * 1e4, "slip_bps": float(r.slip_bps or 0.0), "dvol24": dv})
    return f, pd.DataFrame(rows)


def summarize(e, q):
    fill = e.thru_bp > q
    net = np.where(fill, TAKER - MAKER + e.slip_bps, -(e.move24 - TAKER - e.slip_bps)) * e.notional
    nd = pd.DataFrame({"n": e.notional, "net": net, "day": e.ts.dt.normalize()}).groupby("day").sum()
    pdn = nd.net / nd.n
    return {"n": int(len(e)), "fill_share_notional": round(float(e.loc[fill, "notional"].sum() / e.notional.sum()), 3),
            "unfilled_move24_bp": round(float(np.average(e.move24[~fill], weights=e.notional[~fill])), 1) if (~fill).any() else None,
            "slip_bps_wmean": round(float(np.average(e.slip_bps, weights=e.notional)), 2),
            "net_bp_per_unit": round(float(nd.net.sum() / nd.n.sum()), 2),
            "day_t": round(float(pdn.mean() / pdn.std(ddof=1) * np.sqrt(len(pdn))), 2) if len(pdn) > 2 else None, "days": int(len(pdn))}


def main():
    g = minutes()
    f, e = replay(g)
    out = {"fills_hl_books": int(len(f)), "replayed": int(len(e)), "window": [str(e.ts.min()), str(e.ts.max())],
           "minutes_to_fill_q5_median": float(e.min_to_fill_q5.median()), "filled_q5_within_60min": round(float((e.min_to_fill_q5 < 60).mean()), 3),
           "all": {q: summarize(e, q) for q in (0, 3, 5, 10)},
           "by_book_q5": {b: summarize(x, 5) for b, x in e.groupby("book")}}
    e["liq"] = pd.qcut(e.dvol24.rank(method="first"), 3, labels=["thin", "mid", "deep"])
    out["by_liquidity_q5"] = {str(k): summarize(x, 5) for k, x in e.groupby("liq", observed=True)}
    print(json.dumps(out, indent=1, default=str))
    json.dump(out, open(EV / "t9q_ab.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
