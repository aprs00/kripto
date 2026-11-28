"""InSilico pass 3, SMY a: the live period (since 11-18) replayed for a $200 account with round-to-minimum vs truncation vs the live big sibling.
Uses scripts.live_vs_backtest's main-book replay (live panels, point-in-time universe). Descriptive.
  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_smy a  -> research/is3/smy_a.json"""
import json
import sys

import numpy as np
import pandas as pd

from kripto import paper as P, research as R
from scripts import live_vs_backtest as L

SINCE = pd.Timestamp("2026-11-18", tz="UTC")


def roundmin(w, m):
    a = w.abs()
    return np.sign(w) * a.where(a >= m, np.where(a >= m / 2, m, 0.0))


def form_a():
    cfg, risk = P.load_cfg(); c = L._db()
    out = {}
    for venue, big in (("hl", "main"), ("bn", "main_bn")):
        live_e = {n: s for n, s in cfg.items() if P.venue_of(s) == venue and s.get("status") in ("incubation", "active") and s.get("alloc", 0) > 0}
        coins = L.live_universe(c, venue); pn = L._panel(venue, coins)
        sb = pd.Timestamp(pd.read_sql("select bar from rebalances where book=? order by bar limit 1", c, params=(f"small:{big}",)).iloc[0, 0])
        w = L.main_targets([(s["alloc"], L.entry_targets(n, s, venue, pn, sb)) for n, s in live_e.items()], float(risk["main_scale"][big]))
        w = w.apply(lambda r: P.apply_risk(r, risk) if r.notna().any() else r, axis=1)
        m = (R.small_minima(w.columns, "bn" if venue == "bn" else "hl") / 200.0).to_numpy()
        live_big = L.daily_live(c, big).pct_change().dropna()
        live_small = L.daily_live(c, f"small:{big}").pct_change().dropna()
        res = {}
        for tag, x, eq in (("usd1000_replay", w, 1000.0), ("trunc_200", w.where((w.abs() >= m) | (w == 0) | w.isna(), 0.0), 200.0),
                           ("roundmin_200", w.where(w.isna(), roundmin(w.fillna(0.0), m)), 200.0)):
            rr, panel = L.run_replay(x, pn, venue, sb, risk, eq)
            r = rr.returns[rr.returns.index >= sb]
            bar = panel["close"].index[1] - panel["close"].index[0]
            r.index = r.index + bar - pd.Timedelta(microseconds=1)
            d = (1 + r).groupby(r.index.floor("D") + pd.Timedelta(days=1)).prod() - 1
            days = d.index.intersection(live_big.index); days = days[days > SINCE]
            held = rr.weights[rr.weights.index >= SINCE]
            res[tag] = {"days": len(days), "ret%": round(100 * float((1 + d.reindex(days)).prod() - 1), 2),
                        "corr_live_big": round(float(d.reindex(days).corr(live_big.reindex(days))), 2),
                        "names": round(float((held.abs() > 0).sum(axis=1).mean()), 1), "gross": round(float(held.abs().sum(axis=1).mean()), 3),
                        "turnover": round(float(rr.turnover[rr.turnover.index >= SINCE].sum()), 2)}
        dd = live_big.index.intersection(live_small.index); dd = dd[dd > SINCE]
        res["live_small"] = {"ret%": round(100 * float((1 + live_small.reindex(dd)).prod() - 1), 2), "corr_live_big": round(float(live_small.reindex(dd).corr(live_big.reindex(dd))), 2)}
        res["live_big_ret%"] = round(100 * float((1 + live_big.reindex(dd)).prod() - 1), 2)
        out[venue] = res
        print(venue, json.dumps(res), flush=True)
    json.dump(out, open("research/is3/smy_a.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": form_a}[sys.argv[1]]()
