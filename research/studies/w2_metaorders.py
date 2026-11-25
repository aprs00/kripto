"""W2b first look (2026-11-25 research): visible metaorders on Hyperliquid (library N9/N10, Tóth et al.: order-flow persistence is one
investor splitting a large order; HL publishes the taker address). data/hl/flow `big` = per minute up to 5 [address, signed net taker
notional] with |net| >= the collector's BIG_NTL. Event = (coin, 4-h window, address) where that address took the SAME side in >= `k`
distinct minutes of the window and its net over the window is >= `min_ntl` USD. Direction d = sign(net). Outcomes, in the event's
direction, from the window's last close: forward 4 h and 24 h log return (simple mean too), and the window's own return (did price
already move with it?). t = day-clustered (mean of daily means). Matched baseline: forward return of the same coin's windows with the
same sign of the window return and NO event, signed by that sign (a pure momentum proxy). First look on 13 days: no decision except
the backlog kill rule (|effect| below an HL round trip ≈ 10-13 bp, or t < 2 both halves).
  usage: nice -n 19 .venv/bin/python -m research.studies.w2_metaorders
"""
import glob
import json

import numpy as np
import pandas as pd


def tday(x: pd.Series) -> float:
    d = x.groupby(x.index.floor("D")).mean()
    return float(d.mean() / d.std() * np.sqrt(len(d))) if len(d) > 3 and d.std() > 0 else float("nan")


def main(k=3, min_ntl=100_000):
    fs = sorted(glob.glob("data/hl/flow/*.parquet"))
    d = pd.concat([pd.read_parquet(f, columns=["coin", "minute", "c", "big"]) for f in fs])
    d["ts"] = pd.to_datetime(d["minute"], unit="m" if d["minute"].max() < 1e11 else "ms", utc=True)
    d["w"] = d["ts"].dt.floor("4h")
    close = d.groupby([d["ts"].dt.floor("h"), "coin"])["c"].last().unstack()
    close = close.reindex(pd.date_range(close.index.min(), close.index.max(), freq="h")).ffill(limit=2)
    lc = np.log(close)
    ev = []
    b = d[d["big"].str.len() > 2]
    rows = []
    for coin, w, big in zip(b["coin"], b["w"], b["big"]):
        for a, v in json.loads(big):
            rows.append((coin, w, a, v))
    t = pd.DataFrame(rows, columns=["coin", "w", "addr", "net"])
    g = t.groupby(["coin", "w", "addr"]).agg(net=("net", "sum"), n_pos=("net", lambda x: (x > 0).sum()), n_neg=("net", lambda x: (x < 0).sum()))
    g = g[((g["n_pos"] >= k) & (g["n_neg"] == 0) | (g["n_neg"] >= k) & (g["n_pos"] == 0)) & (g["net"].abs() >= min_ntl)].reset_index()
    print(f"W2b metaorders | {d['ts'].min():%Y-%m-%d} .. {d['ts'].max():%Y-%m-%d} | big rows {len(t)} | events (k={k}, >= ${min_ntl:,.0f}) {len(g)} "
          f"in {g[['coin', 'w']].drop_duplicates().shape[0]} coin-windows, {g['addr'].nunique()} addresses")
    if g.empty:
        return
    # one event per coin-window: the net of all qualifying addresses
    cw = g.groupby(["coin", "w"])["net"].sum()
    out = []
    for (coin, w), net in cw.items():
        end = w + pd.Timedelta(hours=3)                     # last hourly bar of the window (bars indexed by hour start, close = 'last')
        if coin not in lc.columns or end not in lc.index:
            continue
        s = np.sign(net)
        i = lc.index.get_loc(end)
        def ret(h):
            j = i + h
            return s * (lc[coin].iloc[j] - lc[coin].iloc[i]) if j < len(lc) else np.nan
        past = s * (lc[coin].iloc[i] - lc[coin].iloc[i - 4]) if i >= 4 else np.nan
        out.append(dict(ts=end, coin=coin, net=net, past=past, f4=ret(4), f24=ret(24)))
    e = pd.DataFrame(out).set_index("ts").dropna(subset=["f4"])
    mid = e.index.min() + (e.index.max() - e.index.min()) / 2
    for lab, x in (("all", e), ("1st half", e[e.index < mid]), ("2nd half", e[e.index >= mid])):
        print(f" {lab:8s} n {len(x):4d} | window return in its direction {x['past'].mean() * 1e4:+6.1f} bp | fwd 4h {x['f4'].mean() * 1e4:+6.1f} bp "
              f"(t_day {tday(x['f4']):+.2f}) | fwd 24h {x['f24'].mean() * 1e4:+6.1f} bp (t_day {tday(x['f24'].dropna()):+.2f}) | buys {(x['net'] > 0).mean():.0%}")
    # matched baseline: all 4-h windows of the same coins without an event, signed by their own window return
    ws = lc.index[(lc.index.hour % 4) == 3]
    base = []
    evset = set(zip(e["coin"], e.index))
    for coin in e["coin"].unique():
        x = lc[coin]
        for end in ws:
            if (coin, end) in evset:
                continue
            i = lc.index.get_loc(end)
            if i < 4 or i + 24 >= len(lc):
                continue
            pr = x.iloc[i] - x.iloc[i - 4]
            if not np.isfinite(pr) or pr == 0:
                continue
            s = np.sign(pr)
            base.append(dict(ts=end, f4=s * (x.iloc[i + 4] - x.iloc[i]), f24=s * (x.iloc[i + 24] - x.iloc[i]), past=abs(pr)))
    bb = pd.DataFrame(base).set_index("ts")
    print(f" baseline (no-event windows, signed by own move) n {len(bb)} | fwd 4h {bb['f4'].mean() * 1e4:+6.1f} bp | fwd 24h {bb['f24'].mean() * 1e4:+6.1f} bp")
    big_moves = bb[bb["past"] >= e["past"].abs().median()]
    print(f"   same, windows moving >= the events' median |move| ({e['past'].abs().median() * 1e4:.0f} bp) n {len(big_moves)} | fwd 4h {big_moves['f4'].mean() * 1e4:+6.1f} | 24h {big_moves['f24'].mean() * 1e4:+6.1f}")


if __name__ == "__main__":
    main()
    main(k=5, min_ntl=250_000)
