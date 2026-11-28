"""InSilico pass 3, LSX: LSB2 precheck for listing shorts on Binance (bnall). Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_lsx a|b|c     # -> research/is3/lsx_<form>.json

Events as is3_lsb: first traded day t0 (>= 30 d after the panel starts), reaching >= $1M daily dollar volume within d2..d61, entry at the close of d1 (win[0]),
exit at the close of win[-1] (d61). Short the coin, long BTC with the same notional (beta 1). Funding: shorts RECEIVE positive funding, the BTC long pays it.
Path P&L on entry notional at close k: -(a_k/a_0 - 1) + (b_k/b_0 - 1) + sum funding_alt - sum funding_btc. A stop at -x exits at the first CLOSE with P&L <= -x
(the close that crosses it: the gap is paid, the conservative side of a daily path). Costs: per side and leg taker 5 bp + slip (bt.slippage_model) at entry/exit.
"""
from __future__ import annotations

import json
import warnings
import sys

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto import strategies as S

warnings.filterwarnings("ignore")
EV = data.DATA.parent / "research" / "is3"
TAKER = 5e-4


def events():
    p = data.load_panel("bnall", "1d")
    c, v = p["close"], p["volume"]
    fund = p["funding"].reindex(index=c.index, columns=c.columns).fillna(0.0)
    slip = bt.slippage_model(v, 1)
    traded = (v.fillna(0) > 0) & c.notna()
    first = traded.idxmax()[traded.any()]
    t_cut = traded.any(axis=1).idxmax() + pd.Timedelta(days=30)
    dv = S.dollar_volume(p)
    ev = []
    for coin, t0 in first.items():
        if t0 < t_cut or coin == "BTC":
            continue
        i0 = c.index.get_loc(t0)
        if i0 + 62 >= len(c):
            continue
        win = c.index[i0 + 1: i0 + 62]
        if not (dv.loc[win, coin] >= 1e6).any():
            continue
        a = c.loc[win, coin].ffill().to_numpy(float)
        b = c.loc[win, "BTC"].to_numpy(float)
        if not (np.isfinite(a[0]) and a[0] > 0 and np.isfinite(a[-1])):
            continue
        fa = np.concatenate([[0.0], np.cumsum(fund.loc[win[1:], coin].to_numpy(float))])
        fb = np.concatenate([[0.0], np.cumsum(fund.loc[win[1:], "BTC"].to_numpy(float))])
        path = -(a / a[0] - 1) + (b / b[0] - 1) + fa - fb
        s0 = slip.at[win[0], coin]
        s0 = s0 if np.isfinite(s0) else 25e-4
        ev.append({"coin": coin, "t0": win[0], "path": path, "alt": -(a / a[0] - 1) + fa, "btc": (b / b[0] - 1) - fb,
                   "cost": 2 * (TAKER + s0) + 2 * (TAKER + 1.5e-4), "days": win, "dv0_m": float(dv.loc[win[:7], coin].max() / 1e6)})
    return ev, p


def exit_at(path, stop):
    if stop is None:
        return len(path) - 1
    hit = np.nonzero(path[1:] <= -stop)[0]
    return int(hit[0] + 1) if len(hit) else len(path) - 1


def summ(x, day):
    x = pd.Series(np.asarray(x, float)); d = pd.Series(pd.DatetimeIndex(day))
    g = x.groupby(d.values).sum()
    gm = x.groupby(d.dt.to_period("M").values).mean()
    pos = g[g > 0].sort_values(ascending=False)
    return {"n": int(len(x)), "mean": round(float(x.mean()), 3), "median": round(float(x.median()), 3), "win": round(float((x > 0).mean()), 2),
            "t_month": round(float(gm.mean() / (gm.std() / np.sqrt(len(gm)))), 2) if len(gm) > 3 and gm.std() > 0 else None,
            "top3_day_share": round(float(pos.iloc[:3].sum() / x.sum()), 2) if x.sum() > 0 else None}


def form_a():
    ev, _ = events()
    df = pd.DataFrame([{"t0": e["t0"], "year": e["t0"].year, "net": e["path"][-1] - e["cost"], "alt": e["alt"][-1], "btc": e["btc"][-1]} for e in ev])
    out = {"by_year": {}}
    for y, g in df.groupby("year"):
        out["by_year"][int(y)] = {"net": summ(g.net, g.t0), "alt_leg_mean": round(float(g.alt.mean()), 3), "alt_leg_median": round(float(g.alt.median()), 3),
                                  "btc_leg_mean": round(float(g.btc.mean()), 3)}
    out["all"] = summ(df.net, df.t0)
    print(json.dumps(out, indent=1)); json.dump(out, open(EV / "lsx_a.json", "w"), indent=1)


def form_b():
    ev, _ = events()
    out = {}
    for stop in (None, 1.0, 0.5, 0.3):
        rows = []
        for e in ev:
            k = exit_at(e["path"], stop)
            rows.append({"t0": e["t0"], "year": e["t0"].year, "net": e["path"][k] - e["cost"], "k": k, "stopped": k < len(e["path"]) - 1,
                         "gap": float(e["path"][k] + stop) if (stop and k < len(e["path"]) - 1) else 0.0})
        df = pd.DataFrame(rows)
        key = "nostop" if stop is None else f"stop{int(stop*100)}"
        out[key] = {"all": summ(df.net, df.t0), "stopped_share": round(float(df.stopped.mean()), 3),
                    "mean_gap_beyond_stop": round(float(df.loc[df.stopped, "gap"].mean()), 3) if df.stopped.any() else None,
                    "by_year": {int(y): summ(g.net, g.t0) for y, g in df.groupby("year")}}
        if stop is None:
            wo = df.drop(df.net.nsmallest(10).index)
            out["nostop_wo_worst10"] = {"all": summ(wo.net, wo.t0), "by_year_mean": {int(y): round(float(g.net.mean()), 3) for y, g in wo.groupby("year")}}
            out["worst10"] = [[str(e["coin"]), str(ev[i]["t0"].date()), round(float(df.net[i]), 2)] for i, e in
                              ((i, ev[i]) for i in df.net.nsmallest(10).index)]
        print(key, json.dumps({k: v for k, v in out[key].items() if k != "by_year"}),
              {y: (v["mean"], v["median"]) for y, v in out[key]["by_year"].items()}, flush=True)
    # placebo: the stop's exits (share and exit days) assigned to random events; 200 draws. Real stop gain must beat it.
    rng = np.random.default_rng(7)
    paths = [e["path"] for e in ev]; cost = np.array([e["cost"] for e in ev]); yr = np.array([e["t0"].year for e in ev])
    for stop in (1.0, 0.5):
        ks = np.array([exit_at(pa, stop) for pa in paths]); stopped = ks < 60
        real = np.array([pa[k] for pa, k in zip(paths, ks)]) - cost
        pl, ply = [], []
        for _ in range(200):
            pick = rng.permutation(len(ev))[: stopped.sum()]
            kk = np.full(len(ev), 60); kk[pick] = rng.permutation(ks[stopped])
            x = np.array([pa[min(k, len(pa) - 1)] for pa, k in zip(paths, kk)]) - cost
            pl.append(x.mean()); ply.append([x[yr == y].mean() for y in range(2020, 2027)])
        pl, ply = np.array(pl), np.array(ply)
        key = f"placebo_stop{int(stop*100)}"
        out[key] = {"real_mean": round(float(real.mean()), 3), "placebo_mean": round(float(pl.mean()), 3), "pct_rank": round(float((pl < real.mean()).mean()), 3),
                    "by_year_real_minus_placebo": {y: round(float(real[yr == y].mean() - ply[:, i].mean()), 3) for i, y in enumerate(range(2020, 2027))}}
        print(key, out[key], flush=True)
    json.dump(out, open(EV / "lsx_b.json", "w"), indent=1)


def book(ev, idx, slots, stop=None, cost_mult=2.0, order="first"):
    """daily book returns: at most `slots` concurrent events, each 1/slots of equity short + the same long BTC (fixed entry notional).
    Daily P&L = the path increment x notional; entry cost on the entry day, exit cost on the exit day."""
    r = pd.Series(0.0, idx); n_act = pd.Series(0, idx)
    evs = sorted(ev, key=lambda e: (e["t0"], -e["dv0_m"]))
    busy = []          # exit dates of open slots
    taken = 0
    for e in evs:
        busy = [d for d in busy if d > e["t0"]]
        if len(busy) >= slots:
            continue
        k = exit_at(e["path"], stop)
        days = e["days"][: k + 1]
        inc = np.diff(e["path"][: k + 1])
        r.loc[days[1:]] += inc / slots
        r.loc[days[0]] -= e["cost"] / 2 * cost_mult / slots
        r.loc[days[k]] -= e["cost"] / 2 * cost_mult / slots
        n_act.loc[days[1:]] += 1
        busy.append(days[k]); taken += 1
    return r, n_act, taken


def form_c():
    ev, p = events()
    idx = p["close"].index
    sr = lambda x: round(float(x.mean() / x.std() * np.sqrt(365)), 2) if x.std() > 0 else None
    out = {}
    for slots in (5, 10, 1000):
        for stop in (None, 1.0):
            r, n, taken = book(ev, idx, slots, stop)
            r = r.loc["2020-03-01":]
            eq = (1 + r).cumprod()
            key = f"slots{slots}_{'nostop' if stop is None else 'stop100'}"
            out[key] = {"taken": taken, "sr_all": sr(r), "ann_pct": round(float(r.mean() * 365 * 100), 1), "vol_pct": round(float(r.std() * np.sqrt(365) * 100), 1),
                        "mdd": round(float((eq / eq.cummax() - 1).min()), 3), "worst_day": round(float(r.min()), 3), "mean_active": round(float(n.loc[r.index].mean()), 1),
                        "sr_by_year": {int(y): sr(g) for y, g in r.groupby(r.index.year)},
                        "ret_by_year": {int(y): round(float(g.sum()), 3) for y, g in r.groupby(r.index.year)}}
            print(key, json.dumps(out[key]), flush=True)
    json.dump(out, open(EV / "lsx_c.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": form_a, "b": form_b, "c": form_c}[sys.argv[1]]()
