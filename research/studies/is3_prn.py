"""InSilico pass 3, PRN: per-leg costs and slow-leg partial rebalancing on the Binance blend (carry_trend, carry, xsmom), cached bnall panel.
python -m research.studies.is3_prn a|b|c <pickle> [legs comma-separated for b/c]"""
import inspect, json, pickle, sys
import numpy as np, pandas as pd
from kripto import backtest as bt, strategies as S
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY
from research.studies.is3_prb import partial, summary

LEGS = ("carry_trend", "carry", "xsmom")


def legs(panel):
    cols = panel["close"].columns
    raw = {}
    for n in LEGS:
        tv = inspect.signature(REGISTRY[n]).parameters["target_vol"].default
        raw[n] = S._ffill_targets(REGISTRY[n](panel)).reindex(columns=cols, fill_value=0.0) * (0.20 / tv) / len(LEGS)
    tot = sum(raw.values())
    final = S.scheduled(tot, panel, 1, 0.25, 3.0, None)
    ref = REGISTRY["blend"](panel, components={n: {} for n in LEGS})
    s = (final.fillna(0).abs().sum(1) / tot.abs().sum(1).replace(0, np.nan)).fillna(0.0)
    fin = {n: w.fillna(0.0).mul(s, axis=0) for n, w in raw.items()}
    return fin, ref, float((sum(fin.values()) - ref.fillna(0)).abs().max().max())


if __name__ == "__main__":
    form, pk = sys.argv[1], sys.argv[2]
    p = pickle.load(open(pk, "rb"))
    slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
    fin, ref, err = legs(p)
    print("decomp err", err, flush=True)
    run = lambda w: bt.run(w, p["close"], p.get("funding"), slip, band=0.005)
    out = {"decomp_err": err}
    if form == "a":
        yrs = (2021, 2022, 2023)
        for n, w in list(fin.items()) + [("book", ref.fillna(0.0))]:
            r = run(w)
            out[n] = {y: summary(r, f"{y}-01-01", f"{y+1}-01-01") for y in yrs}
            print(n, {y: (round(v["costs_ann"], 3), round(v["turnover_ann"], 1), round(v["ann"] + v["costs_ann"], 3)) for y, v in out[n].items()}, flush=True)
    else:
        slow = sys.argv[3].split(",")
        yrs = (2021, 2022, 2023) if form == "b" else (2024, 2025, 2026)
        span = ("2021-01-01", "2024-01-01") if form == "b" else ("2024-01-01", "2027-01-01")
        books = {"lam1": ref.fillna(0.0), "slow33": sum(fin[n] for n in LEGS if n not in slow) + partial(sum(fin[n] for n in slow), 0.33)}
        for k, w in books.items():
            r = run(w)
            out[k] = {str(y): summary(r, f"{y}-01-01", f"{y+1}-01-01") for y in yrs}
            out[k]["all"] = summary(r, *span)
            print(k, {y: (round(v["sr"], 3), round(v["costs_ann"], 4), round(v["sr_pre_cost"], 3)) for y, v in out[k].items()}, flush=True)
    json.dump(out, open(f"research/is3/prn_{form}.json", "w"), indent=1, default=str)
