"""InSilico pass 3, T9P: shadow:flow@bn's live Nov orders replayed as post-only at the decision mid (k = 0) on live 4h bars,
trade-through q 0/3/5 bp, the bar containing the order EXCLUDED (conservative: a quick fill inside it is not counted). Descriptive.
  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_t9p   -> research/is3/t9p_ab.json
Net per traded unit vs the live taker fill (bp of notional):
  filled:   + (taker fee 5 - maker fee 2) + live slip (bp, cost paid by the taker)  - selection is NOT a cost here: the fill price is the decision mid,
            better than the taker's fill; what the maker loses is the unfilled residue
  unfilled: skip mode = the order is not executed: we lose the signal's 24-h move on it (move24, signed) and pay nothing; then the next day's decision re-trades
            (approximation: cost = move24 of the unfilled, i.e. what the taker would have earned on it in the first 24 h)
            taker-at-24h mode = buy at the 24-h price as a taker: cost = move24 + 5 bp fee + slip (vs taker at once)
"""
from __future__ import annotations

import json
import sqlite3

import numpy as np
import pandas as pd

from kripto.data import DATA

EV = DATA.parent / "research" / "is3"
TAKER, MAKER = 5.0, 2.0


def load(include_first=False):
    con = sqlite3.connect(DATA.parent / "state" / "paper.db")
    f = pd.read_sql("select ts, coin, size, px, mid, fee, slip_bps, reason from fills where book = 'shadow:flow@bn'", con)
    f["ts"] = pd.to_datetime(f["ts"], utc=True, format="ISO8601")
    f["coin"] = f["coin"].str.replace("@bn", "", regex=False)
    bars, rows = {}, []
    for _, r in f.iterrows():
        c = r["coin"]
        if c not in bars:
            fp = DATA / "bn" / "live_4h" / f"{c}.parquet"
            b = None
            if fp.exists():
                b = pd.read_parquet(fp); b.index = pd.to_datetime(b["t"], unit="ms", utc=True); b = b[~b.index.duplicated()].sort_index()
            bars[c] = b
        b = bars[c]
        if b is None or not np.isfinite(r["mid"]) or r["mid"] <= 0:
            continue
        t0 = r["ts"].floor("4h") if include_first else r["ts"].ceil("4h")    # include_first = optimistic bound: the containing bar's range may predate the order
        w = b[(b.index >= t0) & (b.index < r["ts"] + pd.Timedelta(hours=24))]
        if len(w) < 5:
            continue
        side = float(np.sign(r["size"]))
        ext = float(w["l"].min()) if side > 0 else float(w["h"].max())     # best price reached against the order
        thru = side * (r["mid"] - ext) / r["mid"] * 1e4                       # bp the market traded THROUGH the mid (>0 = through)
        rows.append({"ts": r["ts"], "coin": c, "side": side, "notional": abs(r["size"] * r["px"]), "thru_bp": thru,
                     "move24": side * (float(w["c"].iloc[-1]) / r["mid"] - 1) * 1e4, "slip_bps": float(r["slip_bps"] or 0.0), "reason": r["reason"]})
    return f, pd.DataFrame(rows)


def main():
    res = {}
    for tag, inc in (("exclude_first_bar", False), ("include_first_bar_optimistic", True)):
        res[tag] = one(*load(inc))
    print(json.dumps(res, indent=1, default=str))
    json.dump(res, open(EV / "t9p_ab.json", "w"), indent=1, default=str)


def one(f, d):
    wavg = lambda x, m: float(np.average(x[m], weights=d.loc[m, "notional"])) if m.any() else None
    out = {"fills_total": int(len(f)), "replayed": int(len(d)), "days": int(d.ts.dt.normalize().nunique()), "window": [str(d.ts.min()), str(d.ts.max())],
           "live_slip_bps_wmean": round(wavg(d.slip_bps, d.index == d.index), 2), "by_q": {}}
    day = d.ts.dt.normalize()
    for q in (0, 3, 5):
        fill = d.thru_bp > q
        fs = float(d.loc[fill, "notional"].sum() / d.notional.sum())
        save_f = TAKER - MAKER + d.slip_bps                        # per filled unit vs the taker
        cost_skip = d.move24 - TAKER - d.slip_bps                  # unfilled, skip mode: forgo the 24-h move, but save the taker's cost
        cost_t24 = d.move24 + TAKER + d.slip_bps                   # unfilled, taker at 24 h: late entry + full taker cost; minus what taker-now paid (TAKER+slip) -> move24
        net_skip = np.where(fill, save_f, -cost_skip)
        net_t24 = np.where(fill, save_f, -(cost_t24 - TAKER - d.slip_bps))
        nd = pd.DataFrame({"n": d.notional, "skip": net_skip * d.notional, "t24": net_t24 * d.notional, "day": day})
        g = nd.groupby("day").sum()
        per_day_skip = g["skip"] / g["n"]
        t_day = float(per_day_skip.mean() / per_day_skip.std(ddof=1) * np.sqrt(len(per_day_skip)))
        out["by_q"][q] = {"fill_share_notional": round(fs, 3),
                          "fill_share_by_side": {("buy" if s > 0 else "sell"): round(float(d.loc[fill & (d.side == s), "notional"].sum() / d.loc[d.side == s, "notional"].sum()), 3) for s in (1, -1)},
                          "move24_filled_bp": round(wavg(d.move24, fill), 1), "move24_unfilled_bp": round(wavg(d.move24, ~fill), 1) if (~fill).any() else None,
                          "net_bp_per_unit_skip": round(float(nd.skip.sum() / nd.n.sum()), 2), "net_bp_per_unit_taker24": round(float(nd.t24.sum() / nd.n.sum()), 2),
                          "day_t_skip": round(t_day, 2), "share_days_net_pos_skip": round(float((per_day_skip > 0).mean()), 2)}
    m = d.thru_bp <= 3                                   # who are the unfilled: concentration by day and coin
    u = d[m]
    out["unfilled_top3_days_share_of_cost"] = round(float((u.move24 * u.notional).groupby(u.ts.dt.normalize()).sum().nlargest(3).sum() / (u.move24 * u.notional).sum()), 2) if len(u) else None
    out["unfilled_n"] = int(m.sum()); out["unfilled_coins"] = u.coin.value_counts().head(6).to_dict()
    return out


if __name__ == "__main__":
    main()


def form_b():
    """Minute resolution from HL's per-minute OHLC (data/hl/flow, 11-12..11-27): the BN order is assumed to rest at the HL price of its own minute
    (basis-neutral: HL proxies the path, not the level); fill = an HL trade-through by q within 24 h, from the NEXT minute. Coins not on HL dropped."""
    f, d = load(False)
    fl = pd.concat([pd.read_parquet(x, columns=["coin", "minute", "h", "l", "c"]) for x in sorted((DATA / "hl" / "flow").glob("*.parquet"))])
    fl["minute"] = pd.to_datetime(fl["minute"], utc=True) if not np.issubdtype(fl["minute"].dtype, np.number) else pd.to_datetime(fl["minute"] * 60, unit="s", utc=True)   # minutes since epoch
    end = fl.minute.max()
    g = {c: x.set_index("minute").sort_index() for c, x in fl.groupby("coin")}
    rows = []
    for _, r in d.iterrows():
        x = g.get(r.coin)
        if x is None or r.ts + pd.Timedelta(hours=24) > end or r.ts < x.index.min():
            continue
        m0 = r.ts.floor("1min")
        ref = x["c"].asof(m0)
        w = x[(x.index > m0) & (x.index < r.ts + pd.Timedelta(hours=24))]
        if not np.isfinite(ref) or len(w) < 600:
            continue
        ext = float(w["l"].min()) if r.side > 0 else float(w["h"].max())
        first = w.index[(w["l"] < ref * (1 - 3e-4)) if r.side > 0 else (w["h"] > ref * (1 + 3e-4))]
        rows.append({**r.to_dict(), "thru_hl_bp": r.side * (ref - ext) / ref * 1e4,
                     "minutes_to_fill_q3": float((first[0] - m0).total_seconds() / 60) if len(first) else np.nan,
                     "thru_4h_bp": r.thru_bp})
    e = pd.DataFrame(rows)
    out = {"n": int(len(e)), "days": int(e.ts.dt.normalize().nunique()), "notional_share_of_replayed": round(float(e.notional.sum() / d.notional.sum()), 3), "by_q": {}}
    for q in (0, 3, 5, 10):
        fill = e.thru_hl_bp > q
        save = TAKER - MAKER + e.slip_bps
        net = np.where(fill, save, -(e.move24 - TAKER - e.slip_bps)) * e.notional
        nd = pd.DataFrame({"n": e.notional, "net": net, "day": e.ts.dt.normalize()}).groupby("day").sum()
        pdn = nd.net / nd.n
        out["by_q"][q] = {"fill_share_notional": round(float(e.loc[fill, "notional"].sum() / e.notional.sum()), 3),
                          "move24_unfilled_bp": round(float(np.average(e.move24[~fill], weights=e.notional[~fill])), 1) if (~fill).any() else None,
                          "net_bp_per_unit": round(float(nd.net.sum() / nd.n.sum()), 2),
                          "day_t": round(float(pdn.mean() / pdn.std(ddof=1) * np.sqrt(len(pdn))), 2), "share_days_pos": round(float((pdn > 0).mean()), 2)}
    both = e.thru_4h_bp > 3
    out["same_sample_4h_exclude_first"] = {"fill_share_notional": round(float(e.loc[both, "notional"].sum() / e.notional.sum()), 3)}
    out["minutes_to_fill_q3_median"] = float(e.minutes_to_fill_q3.median()); out["filled_within_4h_share"] = round(float((e.minutes_to_fill_q3 < 240).mean()), 3)
    print(json.dumps(out, indent=1, default=str))
    json.dump(out, open(EV / "t9p_b.json", "w"), indent=1, default=str)
