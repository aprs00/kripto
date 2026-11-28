"""InSilico pass 3, TLQ: HL tsmom (as held in the main-book blend) by point-in-time liquidity rank tercile; top_n 10 variant.
python -m research.studies.is3_tlq a|b|c"""
import json, sys, inspect
import numpy as np, pandas as pd
from kripto import backtest as bt, data, strategies as S
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY
from research.studies.is3_prl import legs, LEGS
from research.studies.is3_prb import partial, summary

p = data.load_panel("hl", "1d")
bpd = bars_per_day(p["close"].index)
slip = bt.slippage_model(p["volume"], bpd)
form = sys.argv[1] if len(sys.argv) > 1 else "a"
yrs = (2023, 2024, 2025, 2026)
out = {}
if form == "a":
    fin, ref, err = legs(p)
    out["decomp_err"] = err
    w = fin["tsmom"].fillna(0.0)
    cols = w.columns
    close = p["close"].reindex(columns=cols)
    r = close.pct_change(fill_method=None).fillna(0.0)
    f = p["funding"].reindex(index=w.index, columns=cols).fillna(0.0)
    sl = slip.reindex(index=w.index, columns=cols).fillna(25e-4)
    dv = p["volume"].reindex(columns=cols).rolling(30, min_periods=7).mean()
    rank = dv.where(S.universe(p, 20).reindex(columns=cols, fill_value=False)).rank(axis=1, ascending=False)
    tier = pd.DataFrame(np.select([rank <= 7, rank <= 14, rank <= 20], [1, 2, 3], 0), index=rank.index, columns=cols)
    tier_h = tier.shift(1).fillna(0)            # tier known when the position was set (close t-1)
    wh = w.shift(1).fillna(0.0)
    tr = (w - wh).abs()
    price, fund, cost = wh * r, -wh * f, tr * (bt.TAKER_FEE + sl)
    for k in (1, 2, 3):
        mh, mt = tier_h == k, tier == k             # cost assigned by tier at trade time
        o = {}
        for y in yrs:
            ix = w.index.year == y
            g = float(wh.abs().where(mh, 0).loc[ix].sum(1).mean())
            pr, fu, co = (float(x.where(m, 0).loc[ix].sum(1).mean() * 365) for x, m in ((price, mh), (fund, mh), (cost, mt)))
            o[str(y)] = {"gross_exp": round(g, 3), "price": round(pr, 4), "funding": round(fu, 4), "cost": round(co, 4), "net": round(pr + fu - co, 4),
                         "turn": round(float(tr.where(mt, 0).loc[ix].sum(1).mean() * 365), 1), "net_per_gross": round((pr + fu - co) / g, 3) if g > 0 else None,
                         "cost_bp_per_unit": round(co / max(float(tr.where(mt, 0).loc[ix].sum(1).mean() * 365), 1e-9) * 1e4, 1)}
        out[f"tier{k}"] = o
        print(f"tier{k}", {y: (v["gross_exp"], v["price"], v["funding"], v["cost"], v["net"], v["cost_bp_per_unit"]) for y, v in o.items()}, flush=True)
else:
    cols = p["close"].columns
    def blend(top_n):
        raw = {}
        for n in LEGS:
            kw = {"top_n": top_n} if n == "tsmom" else {}
            tv = inspect.signature(REGISTRY[n]).parameters["target_vol"].default
            raw[n] = S._ffill_targets(REGISTRY[n](p, **kw)).reindex(columns=cols, fill_value=0.0) * (0.20 / tv) / len(LEGS)
        tot = sum(raw.values())
        fin = S.scheduled(tot, p, 1, 0.25, 3.0, None)
        s = (fin.fillna(0).abs().sum(1) / tot.abs().sum(1).replace(0, np.nan)).fillna(0.0)
        return fin.fillna(0.0), {n: x.fillna(0.0).mul(s, axis=0) for n, x in raw.items()}
    run = lambda w: bt.run(w, p["close"], p.get("funding"), slip, band=0.005)
    win = {"b": [("2023-01-01", "2024-01-01"), ("2024-01-01", "2025-01-01"), ("2023-01-01", "2025-01-01")],
           "conf": [("2025-01-01", "2026-01-01"), ("2026-01-01", "2027-01-01"), ("2025-01-01", "2027-01-01")]}[form if form == "b" else "conf"]
    if form in ("b", "conf"):
        books = {}
        for tn in (20, 10):
            fb, fl = blend(tn)
            books[f"blend_top{tn}"] = fb
            books[f"tsmom_top{tn}"] = fl["tsmom"]
    else:   # c: PRB2 interaction on the top-10 book (explore years)
        win = [("2023-01-01", "2024-01-01"), ("2024-01-01", "2025-01-01"), ("2023-01-01", "2025-01-01")]
        fb, fl = blend(10)
        books = {"top10_lam1": fb, "top10_slow33": fl["listing_short"] + partial(fl["lowvol"] + fl["tsmom"], 0.33)}
    for k, w in books.items():
        res = run(w)
        out[k] = {f"{lo[:4]}-{hi[:4]}": summary(res, lo, hi) for lo, hi in win}
        print(k, {a: (round(v["sr"], 3), round(v["ann"], 4), round(v["costs_ann"], 4), round(v["turnover_ann"], 1)) for a, v in out[k].items()}, flush=True)
json.dump(out, open(f"research/is3/tlq_{form}.json", "w"), indent=1, default=str)
