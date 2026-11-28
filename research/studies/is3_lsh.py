"""InSilico pass 3, LSH: Binance listing shorts (is3_lsx events) with an HOURLY squeeze stop. Descriptive, NOT registered.

  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_lsh ab     # -> research/is3/lsh_ab.json

Entry at the close of the event's first daily bar (E = t0 + 1 d), exit at the d61 close (X = days[-1] + 1 d). Hourly path on entry notional:
-(a_h / a_E - 1) + (b_h / b_E - 1) + cumulative funding (alt minus BTC, booked per daily bar as in is3_lsx, stepwise). Stop at -x exits at the first FULL HOUR whose price
puts the path at <= -x (fill at that hour's price: the gap inside the hour is paid). Known answer: the hourly path at X equals the daily path's last value.
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
import pandas as pd

from kripto.data import DATA
from research.studies.is3_e2b import hourly
from research.studies.is3_lsx import events, exit_at, summ

warnings.filterwarnings("ignore")
EV = DATA.parent / "research" / "is3"


def hourly_paths(ev):
    hp = hourly(sorted({e["coin"] for e in ev} | {"BTC"}))
    btc = hp["BTC"]
    out = []
    for e in ev:
        s = hp.get(e["coin"])
        E, X = e["t0"] + pd.Timedelta(days=1), e["days"][-1] + pd.Timedelta(days=1)
        if s is None or E not in s.index or X not in s.index:
            continue
        hrs = pd.date_range(E, X, freq="1h")
        a = s.reindex(hrs).ffill().to_numpy(float); b = btc.reindex(hrs).ffill().to_numpy(float)
        if not (np.isfinite(a).all() and np.isfinite(b).all()):
            continue
        dclose = e["days"] + pd.Timedelta(days=1)          # time of each daily close in the path
        out.append((e, hrs, a, b, dclose))
    return out


def build(ev):
    rows = []
    for e, hrs, a, b, dclose in hourly_paths(ev):
        # funding cumulative from the daily path: path = price part + funding part; price part from daily closes
        n = len(e["path"])
        ad = np.array([a[hrs.get_loc(t)] if t in hrs else np.nan for t in dclose])
        bd = np.array([b[hrs.get_loc(t)] if t in hrs else np.nan for t in dclose])
        price_d = -(ad / ad[0] - 1) + (bd / bd[0] - 1)
        fund_d = e["path"] - price_d                              # funding part per daily close (also absorbs tiny price-source differences)
        fh = pd.Series(fund_d, dclose).reindex(hrs, method="ffill").fillna(0.0).to_numpy()
        ph = -(a / a[0] - 1) + (b / b[0] - 1) + fh
        rows.append({"e": e, "hrs": hrs, "ph": ph, "kerr": float(abs(ph[-1] - e["path"][-1])), "dsrc": float(np.nanmax(np.abs(fund_d)))})
    return rows


def exit_h(ph, stop):
    if stop is None:
        return len(ph) - 1
    hit = np.nonzero(ph[1:] <= -stop)[0]
    return int(hit[0] + 1) if len(hit) else len(ph) - 1


def form_ab():
    ev, _ = events()
    R = build(ev)
    out = {"events_all": len(ev), "events_hourly": len(R), "known_answer_max_err": round(max(r["kerr"] for r in R), 6),
           "funding_part_max_abs": round(max(r["dsrc"] for r in R), 3)}
    yr = np.array([r["e"]["t0"].year for r in R]); day = [r["e"]["t0"] for r in R]
    cost = np.array([r["e"]["cost"] for r in R])
    rng = np.random.default_rng(7)
    for stop in (None, 1.0, 0.5):
        ks = np.array([exit_h(r["ph"], stop) for r in R])
        net = np.array([r["ph"][k] for r, k in zip(R, ks)]) - cost
        kd = np.array([exit_at(r["e"]["path"], stop) for r in R])
        netd = np.array([r["e"]["path"][k] for r, k in zip(R, kd)]) - cost
        key = "nostop" if stop is None else f"stop{int(stop * 100)}"
        stopped = ks < np.array([len(r["ph"]) - 1 for r in R])
        row = {"hourly": summ(net, day), "daily_same_events": summ(netd, day), "stopped_share": round(float(stopped.mean()), 3),
               "gap_beyond_hourly": round(float((net[stopped] + cost[stopped] + stop).mean()), 3) if stop and stopped.any() else None,
               "by_year_mean_hourly_vs_daily": {int(y): [round(float(net[yr == y].mean()), 3), round(float(netd[yr == y].mean()), 3)] for y in sorted(set(yr))}}
        if stop:
            pl, ply = [], []
            offs = ks[stopped]
            for _ in range(200):
                pick = rng.permutation(len(R))[: stopped.sum()]
                kk = np.array([len(r["ph"]) - 1 for r in R]); kk[pick] = rng.permutation(offs)
                x = np.array([r["ph"][min(k, len(r["ph"]) - 1)] for r, k in zip(R, kk)]) - cost
                pl.append(x.mean()); ply.append([x[yr == y].mean() for y in sorted(set(yr))])
            pl, ply = np.array(pl), np.array(ply)
            row["placebo"] = {"real_mean": round(float(net.mean()), 3), "placebo_mean": round(float(pl.mean()), 3), "pct": round(float((pl < net.mean()).mean()), 3),
                              "by_year_real_minus_placebo": {int(y): round(float(net[yr == y].mean() - ply[:, i].mean()), 3) for i, y in enumerate(sorted(set(yr)))}}
        out[key] = row
        print(key, json.dumps(row), flush=True)
    print({k: out[k] for k in ("events_all", "events_hourly", "known_answer_max_err", "funding_part_max_abs")})
    json.dump(out, open(EV / "lsh_ab.json", "w"), indent=1)


if __name__ == "__main__":
    {"ab": form_ab}[sys.argv[1]]()
