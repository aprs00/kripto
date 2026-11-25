"""W2 first look (2026-11-25 research): does Hyperliquid taker-flow imbalance (our own websocket data, data/hl/flow, non-backfillable,
since 2026-11-11) predict the next returns ACROSS coins, the way Binance taker flow does (flow@bn: continuation, 3-14 d lookback)?
15 days is far too short for a daily book; this only checks the kill rule written in backlog W2 (|IC| < 0.02, or a spread below costs)
at horizons short enough to have samples. Per coin and hour: imb = (taker buy - taker sell) / (buy + sell) notional over the last
L hours; forward return = log close change over the next H hours (closes from the same minute bars). Spearman IC across coins per
decision hour; decision hours spaced H apart (non-overlapping forward windows); t = mean / sd * sqrt(n). Also the top-minus-bottom
quintile spread in bp per H (an HL round trip costs ~10-13 bp on liquid names).
FIRST HALF (decision hours before the median day) vs SECOND HALF reported separately: an effect must show in both.
  usage: nice -n 19 .venv/bin/python -m research.studies.w2_hl_flow
"""
import glob

import numpy as np
import pandas as pd


def load():
    fs = sorted(glob.glob("data/hl/flow/*.parquet"))
    d = pd.concat([pd.read_parquet(f, columns=["coin", "minute", "buy_ntl", "sell_ntl", "c"]) for f in fs])
    d["ts"] = pd.to_datetime(d["minute"], unit="m" if d["minute"].max() < 1e11 else "ms", utc=True)
    d["h"] = d["ts"].dt.floor("h")
    g = d.groupby(["h", "coin"]).agg(buy=("buy_ntl", "sum"), sell=("sell_ntl", "sum"), c=("c", "last"))
    buy, sell, c = (g[k].unstack() for k in ("buy", "sell", "c"))
    full = pd.date_range(buy.index.min(), buy.index.max(), freq="h")
    return buy.reindex(full).fillna(0), sell.reindex(full).fillna(0), c.reindex(full).ffill(limit=2)


def main():
    buy, sell, c = load()
    print(f"W2 HL flow | {c.shape[1]} coins | {c.index.min():%Y-%m-%d %H:%M} .. {c.index.max():%Y-%m-%d %H:%M} | hours {len(c)}")
    lc = np.log(c)
    mid = c.index[len(c) // 2]
    for L in (1, 4, 24, 72):
        b, s = buy.rolling(L).sum(), sell.rolling(L).sum()
        imb = ((b - s) / (b + s)).where((b + s) > 0)
        past = lc - lc.shift(L)
        for H in (1, 4, 24):
            fwd = lc.shift(-H) - lc
            rows = []
            for t in c.index[L::H]:
                x, y, pr = imb.loc[t], fwd.loc[t], past.loc[t]
                ok = x.notna() & y.notna() & pr.notna()
                if ok.sum() < 20:
                    continue
                ic = x[ok].rank().corr(y[ok].rank())
                # flow net of the same-window price move (flow@bn's resid idea): rank IC of the residual
                xr, pr_ = x[ok] - x[ok].mean(), pr[ok] - pr[ok].mean()
                beta = (xr * pr_).sum() / (pr_ * pr_).sum() if (pr_ * pr_).sum() > 0 else 0.0
                icr = (xr - beta * pr_).rank().corr(y[ok].rank())
                q = pd.qcut(x[ok].rank(method="first"), 5, labels=False)
                spread = y[ok][q == 4].mean() - y[ok][q == 0].mean()
                pic = pr[ok].rank().corr(y[ok].rank())
                rows.append((t, ic, icr, spread, pic))
            r = pd.DataFrame(rows, columns=["t", "ic", "icr", "spread", "pic"]).set_index("t")
            if len(r) < 6:
                continue
            out = []
            for lab, rr in (("all", r), ("1st", r[r.index < mid]), ("2nd", r[r.index >= mid])):
                t_ = rr["ic"].mean() / rr["ic"].std() * np.sqrt(len(rr)) if rr["ic"].std() > 0 else np.nan
                out.append(f"{lab} IC {rr['ic'].mean():+.3f} (t {t_:+.1f}, n {len(rr)})")
            print(f" L {L:2d}h H {H:2d}h | " + " | ".join(out) + f" | resid IC {r['icr'].mean():+.3f} | Q5-Q1 {r['spread'].mean() * 1e4:+6.1f} bp"
                  f" | past-return IC {r['pic'].mean():+.3f}")


if __name__ == "__main__":
    main()
