"""R1 + LV1(c): where do the Binance cross-sectional books lose on the short side? (descriptive; no walk-forward)

Books: xsmom (lookback 28, daily), flow (lookback 3), xsmom_k (28, k 5, every 3) = the live @bn configs, on bnall daily.
Per held (day, coin) P&L = weight held during the day x the day's return (funding excluded; it is small next to squeezes).
For the SHORT leg: (1) the tail: share of the short leg's total P&L lost on its worst 1% coin-days and worst 20 coin-days;
(2) which shorts lose: short-position return (-ret) by bucket of characteristics known at the decision (prior 30-day vol rank
within the day's universe, 30-day dollar-volume rank, days since listing, prior 7-day return rank).
Samples: explore = up to 2023-06-30 (the only part used to choose formulations); confirm = 2023-07-01 onward, printed only
with --confirm, after the formulations are written into the batch file.

usage: python -m research.studies.r1_squeeze [--confirm]
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from kripto import backtest as bt, data
from kripto.strategies import REGISTRY, bars_per_day

SPLIT = pd.Timestamp("2023-07-01", tz="UTC")
BOOKS = {"xsmom": {"lookback": 28, "every_days": 1}, "flow": {"lookback": 3}, "xsmom_k": {"lookback": 28, "k": 5, "every_days": 3}}


def features(panel):
    c, v = panel["close"], panel["volume"]
    r = c.pct_change(fill_method=None)
    vol = r.rolling(30, min_periods=10).std()
    dv = v.rolling(30, min_periods=10).mean()
    age = c.notna().cumsum()
    r7 = c / c.shift(7) - 1
    return {"vol": vol, "dv": dv, "age": age, "r7": r7}, r


def main(confirm: bool):
    panel = data.load_panel("bnall", "1d")
    feats, ret = features(panel)
    slip = bt.slippage_model(panel["volume"], bars_per_day(panel["close"].index))
    for name, params in BOOKS.items():
        w = REGISTRY[name](panel, **params)
        res = bt.run(w, panel["close"], panel.get("funding"), slip, band=0.01)
        held = res.weights
        pnl = held * ret.fillna(0)
        for label, sel in (("explore", pnl.index < SPLIT), ("confirm", pnl.index >= SPLIT)):
            if label == "confirm" and not confirm:
                continue
            P, H = pnl[sel], held[sel]
            short = P.where(H < 0).stack().dropna()
            long_ = P.where(H > 0).stack().dropna()
            s_sorted = short.sort_values()
            k1 = max(1, int(0.01 * len(s_sorted)))
            print(f"\n== {name} {label}: long-leg sum {long_.sum():+.3f}, short-leg sum {short.sum():+.3f} "
                  f"(n short coin-days {len(short)}); short worst 1% sum {s_sorted.iloc[:k1].sum():+.3f}, worst 20 "
                  f"{s_sorted.iloc[:20].sum():+.3f}; short ex-worst-1% {s_sorted.iloc[k1:].sum():+.3f}")
            print("   worst 5 short coin-days:", ", ".join(f"{d.date()} {c} {v:+.3f}" for (d, c), v in s_sorted.iloc[:5].items()))
            # characteristics at the decision (previous day's values), cross-sectional ranks among held+universe coins
            sh = (H < 0)
            rows = []
            for f, X in feats.items():
                Xd = X.shift(1)[sel]
                rk = Xd.where(H.ne(0)).rank(axis=1, pct=True)     # rank among the book's held names that day
                for lo, hi in ((0, 0.5), (0.5, 0.8), (0.8, 0.9), (0.9, 1.01)):
                    m = sh & (rk > lo) & (rk <= hi)
                    rr = (-ret[sel]).where(m).stack().dropna()
                    pp = P.where(m).stack().dropna()
                    rows.append({"feat": f, "rank": f"{lo:.1f}-{min(hi, 1):.1f}", "n": len(rr),
                                 "short_ret_bp": round(1e4 * rr.mean(), 1), "median_bp": round(1e4 * rr.median(), 1),
                                 "pnl_sum": round(pp.sum(), 3), "worst1%_share": round(
                                     (pp < s_sorted.iloc[k1 - 1]).sum() / max(1, k1), 2)})
            print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__" and "forms" not in sys.argv and "cap" not in sys.argv:
    main("--confirm" in sys.argv)


def forms(confirm: bool):
    """The short_filter formulations (kripto.strategies.short_guard) per book: Sharpe, ann. return, max DD, funding share,
    on the exploration sample (and the confirmation sample only with --confirm). Not logged: descriptive."""
    from kripto import metrics as mx
    panel = data.load_panel("bnall", "1d")
    slip = bt.slippage_model(panel["volume"], bars_per_day(panel["close"].index))
    print("has funding:", "funding" in panel and panel["funding"].notna().any().any())
    rows = []
    for name, params in BOOKS.items():
        for mode in ("none", "longonly", "r7", "liq"):
            res = bt.run(REGISTRY[name](panel, **params, short_filter=mode), panel["close"], panel.get("funding"), slip, band=0.01)
            first = res.gross[res.gross > 0].index.min()
            for label, lo, hi in (("explore", first, SPLIT), ("confirm", SPLIT, None)):
                if label == "confirm" and not confirm:
                    continue
                r = res.returns[(res.returns.index >= lo) & ((res.returns.index < hi) if hi is not None else True)]
                eq = (1 + r).cumprod()
                rows.append({"book": name, "mode": mode, "sample": label, "sharpe": round(mx.sharpe(r, 365), 2),
                             "ann%": round(100 * r.mean() * 365, 1), "mdd%": round(100 * (eq / eq.cummax() - 1).min(), 1),
                             "fund%/y": round(100 * res.funding.reindex(r.index).mean() * 365, 1),
                             "cost%/y": round(100 * res.costs.reindex(r.index).mean() * 365, 1),
                             "gross": round(res.gross.reindex(r.index).mean(), 2)})
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__" and "forms" in sys.argv:
    forms("--confirm" in sys.argv)


def cap(confirm: bool):
    """Fourth form: cap each ALT weight (both sides; --oneside = shorts only) after vol targeting at c of equity, BTC hedge uncapped, c in 3/5/8%."""
    from kripto import metrics as mx
    panel = data.load_panel("bnall", "1d")
    slip = bt.slippage_model(panel["volume"], bars_per_day(panel["close"].index))
    rows = []
    for name, params in BOOKS.items():
        w0 = REGISTRY[name](panel, **params)
        print(name, "max |short| per alt (explore, 99th pct of row minima):",
              round(float(w0.drop(columns="BTC").min(axis=1)[w0.index < SPLIT].quantile(0.01)), 3))
        for c in (None, 0.08, 0.05, 0.03):
            w = w0.copy()
            if c:
                alts = [x for x in w.columns if x != "BTC"]
                w[alts] = w[alts].clip(lower=-c, upper=None if "--oneside" in sys.argv else c)
            res = bt.run(w, panel["close"], panel.get("funding"), slip, band=0.01)
            first = res.gross[res.gross > 0].index.min()
            for label, lo, hi in (("explore", first, SPLIT), ("confirm", SPLIT, None)):
                if label == "confirm" and not confirm:
                    continue
                r = res.returns[(res.returns.index >= lo) & ((res.returns.index < hi) if hi is not None else True)]
                eq = (1 + r).cumprod()
                rows.append({"book": name, "cap": c, "sample": label, "sharpe": round(mx.sharpe(r, 365), 2),
                             "ann%": round(100 * r.mean() * 365, 1), "mdd%": round(100 * (eq / eq.cummax() - 1).min(), 1),
                             "worst_day%": round(100 * r.min(), 1)})
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__" and "cap" in sys.argv:
    cap("--confirm" in sys.argv)
