"""Assumption row 19 (2026-11-22 retro): does the live candidate list (top 60 by last-24h volume) change what the books trade?

Live: universe() ranks by 30-d volume only among the coins downloaded that run (top 60 by 24h volume, plus held coins).
Research: universe() ranks among all perps. `vis` = 24h-volume rank <= 60 on the decision bar (daily close), optionally sticky for 3 days as a
proxy for "held coins stay in the list". Reports the share of the research top-n that live sees, the intruders, and the configs both ways.

usage: python -m research.studies.live_universe bnall|hl
"""
import json
import sys

import pandas as pd

from kripto import data, research as R, strategies as st


def visible(p, top=60, sticky=1):
    v = p["volume"].fillna(0)
    vis = (v.rank(axis=1, ascending=False) <= top) & (v > 0)
    return vis if sticky == 1 else vis.rolling(sticky, min_periods=1).max().astype(bool)


def ranked(p, top_n, vis):
    c, v = p["close"], p["volume"]
    dv = v.rolling(30, min_periods=7).mean()
    ok = (c.notna().cumsum() >= 30) & c.notna() & (dv > 0)
    if vis is not None:
        ok &= vis
    return (dv.where(ok).rank(axis=1, ascending=False) <= top_n) & ok


def overlap(p):
    for n in (12, 30):
        full = ranked(p, n, None)
        for s in (1, 3):
            lv = ranked(p, n, visible(p, sticky=s))
            both = (full & lv).sum(axis=1)
            o = (both / full.sum(axis=1).clip(lower=1)).where(full.sum(axis=1) >= n)
            by = o.groupby(o.index.year).mean().round(3).to_dict()
            print(f"top_n={n} sticky={s}: share of the research top-n live also trades: mean {o.mean():.3f} last 30 d {o.iloc[-30:].mean():.3f} by year {by}")


def main(ds):
    p = data.load_panel(ds, "1d")
    p = {k: x.loc[:"2026-10-31"] for k, x in p.items()} if ds == "bnall" else p   # the daily top-up is alphabetical: cut where all files are complete
    overlap(p)
    cfg = json.load(open("config/strategies.json"))
    want = [(k, v) for k, v in cfg.items() if v["status"] != "retired"
            and ((ds == "bnall" and v.get("venue") == "bn") or (ds == "hl" and not v.get("venue")))]
    u0, d0 = st.universe, st.dollar_volume
    rows = []
    for k, v in want:
        fn, params = v.get("strategy", k.split("@")[0]), v.get("params", {})
        out = {"entry": k}
        for label, s in (("research", None), ("live", 1), ("live_sticky3", 3)):
            if s is None:
                st.universe, st.dollar_volume = u0, d0
            else:
                vis = visible(p, sticky=s)

                def uni(panel, top_n=30, min_days=30, vol_days=30, vis=vis):
                    return u0({**panel, "close": panel["close"], "volume": panel["volume"]}, 10**6, min_days, vol_days).pipe(
                        lambda ok: (panel["volume"].rolling(vol_days, min_periods=7).mean().where(ok & vis.reindex_like(ok))
                                    .rank(axis=1, ascending=False) <= top_n) & ok & vis.reindex_like(ok))

                def dvol(panel, days=7, vis=vis):
                    x = d0(panel, days)
                    return x.where(vis.reindex_like(x))
                st.universe, st.dollar_volume = uni, dvol
            for per, start in (("all", None), ("2024+", "2024-01-01")):
                res, m = R.evaluate(fn, p, params, ds + "_1d", tag=f"liveuniv:{label}", start=start, log=(per == "all"))
                out[f"{label}_{per}"] = round(m["sharpe"], 2)
                if per == "all":
                    out[f"{label}_mdd"] = round(m.get("mdd", m.get("max_dd", float("nan"))), 2)
        st.universe, st.dollar_volume = u0, d0
        rows.append(out)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1])
