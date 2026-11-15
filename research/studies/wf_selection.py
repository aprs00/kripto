"""Assumption row 9 (2026-11-15 retro): is "pick the in-sample best config" a good walk-forward selection rule?
Descriptive, re-uses the ALREADY pre-registered grids (batch 2026-11-09-h1-recheck-*), so no new hypothesis and no new
walk-forward line (evaluate lines are tagged "wfsel", config kind). Same folds as research.walk_forward (240 d expanding
train from first investment, 60 d test). Rules compared on identical OOS windows:
  best  = the current rule (highest expanding in-sample Sharpe)
  top3  = equal-weight average of the 3 best in-sample configs
  all   = equal-weight average of every config in the grid (no selection at all)
Averaging net returns double-counts trades that would net between configs, so top3/all are slightly cost-pessimistic.
flow is restricted to the continuation half (sign=1): the reversal half is the opposite hypothesis, not a parameter.
Usage: python -m research.studies.wf_selection hl bnall"""
import json, sys
import numpy as np, pandas as pd
from kripto import data, metrics as mx, research as R

GRIDS = {**json.load(open("research/batches/2026-11-09-h1-recheck-1d.json")),
         "flow": {"lookback": [3, 7, 14], "sign": [1], "resid": [False, True]}}
GRIDS.pop("blend", None)                       # one config: nothing to select
ONLY = {"flow": ("bnall",)}


def folds(Rm, train_days=240, test_days=60):
    invested = Rm.ne(0).any(axis=1)
    t0 = Rm.index[invested.values.argmax()]
    start = t0 + pd.Timedelta(days=train_days)
    while start < Rm.index[-1]:
        end = start + pd.Timedelta(days=test_days)
        yield t0, start, end
        start = end


def study(name, ds, panel):
    configs = R.grid(GRIDS[name])
    Rm = pd.DataFrame({i: R.evaluate(name, panel, p, ds, tag="wfsel")[0].returns for i, p in enumerate(configs)})
    ppy = mx.periods_per_year(Rm.index)
    out = {"best": [], "top3": [], "all": []}
    for t0, s, e in folds(Rm):
        ins = Rm[(Rm.index >= t0) & (Rm.index < s)]
        score = (ins.mean() / ins.std() * np.sqrt(ppy)).fillna(-9)
        seg = Rm[(Rm.index >= s) & (Rm.index < e)]
        order = score.sort_values(ascending=False).index
        out["best"].append(seg[order[0]])
        out["top3"].append(seg[order[:3]].mean(axis=1))
        out["all"].append(seg.mean(axis=1))
    row = {"strategy": name, "dataset": ds, "n": len(configs)}
    for k, v in out.items():
        r = pd.concat(v)
        row[k] = round(mx.sharpe(r, ppy), 2)
        yrs = r.groupby(r.index.year).apply(lambda x: mx.sharpe(x, ppy))
        row[k + "_yrs"] = " ".join(f"{y % 100}:{x:+.1f}" for y, x in yrs.items())
    # ex-post median single config over the same OOS span (reference, not a rule)
    span = Rm[Rm.index >= pd.concat(out["best"]).index.min()]
    row["med_cfg"] = round(float(np.median([mx.sharpe(span[c], ppy) for c in span])), 2)
    return row


if __name__ == "__main__":
    rows = []
    for ds in sys.argv[1:] or ["hl", "bnall"]:
        panel = data.load_panel(ds, "1d")
        for name in GRIDS:
            if ds not in ONLY.get(name, (ds,)):
                continue
            row = study(name, ds, panel)
            rows.append(row)
            print(f"{name:14s} {ds:6s} n={row['n']:2d}  best {row['best']:+.2f}  top3 {row['top3']:+.2f}  all {row['all']:+.2f}"
                  f"  (ex-post median cfg {row['med_cfg']:+.2f})", flush=True)
        del panel
    for r in rows:
        print(f"\n{r['strategy']} {r['dataset']}\n  best {r['best_yrs']}\n  top3 {r['top3_yrs']}\n  all  {r['all_yrs']}")
