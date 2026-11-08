"""Research harness: grid evaluation, walk-forward OOS, cost stress, and an append-only trial registry.

Every configuration ever backtested is appended to research/registry.jsonl. The total count is the
`n_trials` used to deflate Sharpe ratios -- this is our main defence against data-mining.
"""
from __future__ import annotations

import itertools
import json
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import backtest as bt
from . import metrics as mx
from .strategies import REGISTRY, bars_per_day

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "research" / "registry.jsonl"


def n_trials() -> int:
    if not REG.exists():
        return 1
    return max(1, sum(1 for _ in REG.open()))


def _git() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "nogit"


def log_trial(rec: dict):
    REG.parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "git": _git(), **rec}
    with REG.open("a") as f:
        f.write(json.dumps(rec, default=str) + "\n")


def evaluate(name: str, panel: dict, params: dict, dataset: str, cost_mult: float = 1.0,
             band: float = 0.02, log: bool = True, start: str | None = None) -> tuple[bt.BTResult, dict]:
    w = REGISTRY[name](panel, **params)
    bpd = bars_per_day(panel["close"].index)
    slip = bt.slippage_model(panel["volume"], bpd)
    res = bt.run(w, panel["close"], panel.get("funding"), slip, band=band, cost_mult=cost_mult)
    r = res.returns
    if start:
        r = r[r.index >= start]
    # drop warm-up (strategy not yet invested)
    first = res.gross[res.gross > 0].index.min()
    if first is not None and not pd.isna(first):
        r = r[r.index >= first]
    s = mx.summary(r, res.gross.reindex(r.index), res.turnover.reindex(r.index), res.costs.reindex(r.index),
                   res.funding.reindex(r.index), n_trials=n_trials() + 1)
    if log:
        log_trial({"strategy": name, "params": params, "dataset": dataset, "cost_mult": cost_mult, **s})
    return res, s


def grid(spec: dict) -> list[dict]:
    keys = list(spec)
    return [dict(zip(keys, vals)) for vals in itertools.product(*(spec[k] for k in keys))]


def walk_forward(name: str, panel: dict, spec: dict, dataset: str, train_days: int = 240,
                 test_days: int = 60, criterion: str = "sharpe") -> dict:
    """Full grid backtests once (signals are causal), then at each fold pick the params with best
    in-sample `criterion` on ALL prior data and stitch their next-`test_days` returns. Reports the
    stitched out-of-sample series plus grid-robustness stats."""
    configs = grid(spec)
    rets, sums = {}, []
    for i, p in enumerate(configs):
        res, s = evaluate(name, panel, p, dataset)
        rets[i] = res.returns
        sums.append({"i": i, **p, **{k: s.get(k) for k in ("sharpe", "cagr", "max_dd", "turnover_yr", "cost_yr", "funding_yr")}})
    R = pd.DataFrame(rets)
    ppy = mx.periods_per_year(R.index)
    invested = R.ne(0).any(axis=1)
    t0 = R.index[invested.values.argmax()]
    folds, oos, chosen = [], [], []
    start = t0 + pd.Timedelta(days=train_days)
    while start < R.index[-1]:
        end = start + pd.Timedelta(days=test_days)
        ins = R[(R.index >= t0) & (R.index < start)]
        score = ins.mean() / ins.std() * np.sqrt(ppy)
        best = int(score.idxmax())
        seg = R.loc[(R.index >= start) & (R.index < end), best]
        oos.append(seg)
        chosen.append({"from": str(start.date()), "params": configs[best], "is_sharpe": round(float(score[best]), 2),
                       "oos_sharpe": round(mx.sharpe(seg, ppy), 2) if len(seg) > 10 else None})
        start = end
    oos_r = pd.concat(oos) if oos else pd.Series(dtype=float)
    grid_df = pd.DataFrame(sums)
    out = {
        "strategy": name, "dataset": dataset, "n_configs": len(configs),
        "grid_median_sharpe": round(float(grid_df["sharpe"].median()), 3),
        "grid_frac_positive": round(float((grid_df["sharpe"] > 0).mean()), 3),
        "oos": mx.summary(oos_r, n_trials=n_trials()) if len(oos_r) > 30 else {},
        "folds": chosen,
        "grid": grid_df.sort_values("sharpe", ascending=False).head(10).to_dict("records"),
    }
    log_trial({"kind": "walk_forward", **{k: v for k, v in out.items() if k not in ("grid", "folds")}})
    return out
