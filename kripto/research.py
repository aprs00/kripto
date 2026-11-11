"""Research harness: grid evaluation, walk-forward OOS, cost stress, and an append-only trial registry.

Every configuration ever backtested is appended to research/registry.jsonl (append-only). Its counts set
`n_trials` for the deflated Sharpe ratio -- our main defence against data-mining:
* a single-config (in-sample) backtest is deflated by the number of single-config trials ever run;
* a walk-forward OOS record is deflated by the number of walk-forward experiments ever run. Parameter
  selection inside a walk-forward is already out-of-sample (chosen on past data only), so the remaining
  selection bias is picking which experiment to believe among all experiments (design.md changelog 2026-11-09).
"""
from __future__ import annotations

import inspect
import itertools
import json
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import backtest as bt
from . import metrics as mx
from .events import EVENTS
from .strategies import REGISTRY, bars_per_day

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "research" / "registry.jsonl"
RISK = ROOT / "config" / "risk.json"
MIN_ORDER = 10.0   # Hyperliquid minimum order ($); Binance is $5 for most symbols


def default_band() -> float:
    """No-trade band that mirrors the main paper book: a trade smaller than min order / equity cannot be sent.
    $10 / $1,000 = 0.01 since 2026-11-10 (it was 0.05 while the book was $200; registry lines now record `band`)."""
    try:
        eq = float(json.loads(RISK.read_text())["start_equity"])
    except Exception:
        eq = 1000.0
    return MIN_ORDER / eq


def n_trials(kind: str = "config") -> int:
    """Count registry lines of one kind: "walk_forward" experiments or single-"config" backtests."""
    if not REG.exists():
        return 1
    n = 0
    with REG.open() as f:
        for line in f:
            is_wf = '"kind": "walk_forward"' in line
            n += is_wf if kind == "walk_forward" else not is_wf
    return max(1, n)


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


def small_band() -> float | None:
    """Band of the small-account twin (risk.json `small_equity`, $200 → 0.05), or None if there is no twin."""
    try:
        eq = json.loads(RISK.read_text()).get("small_equity")
    except Exception:
        return None
    return MIN_ORDER / float(eq) if eq else None


def evaluate(name: str, panel: dict, params: dict, dataset: str, cost_mult: float = 1.0,
             band: float | None = None, log: bool = True, start: str | None = None, lag: int = 0,
             tag: str | None = None, maker: dict | None = None, exec_desc: str | None = None) -> tuple[bt.BTResult, dict]:
    """One config, full sample. lag = bars of execution delay (weights decided at close t are traded at close t+lag).
    tag marks the purpose of a logged line ("robust", "forward", ...). maker = execution.maker_fills(...) + {"fee"}
    (passive execution with taker fallback, T9); exec_desc names that policy in the registry line."""
    band = default_band() if band is None else band
    if name in EVENTS:
        # intraday order strategies (kripto/events.py) simulate their own fills and return a daily BTResult
        res = EVENTS[name](panel, cost_mult=cost_mult, lag=lag, band=band, **params)
    else:
        w = REGISTRY[name](panel, **params)
        if lag:
            w = w.shift(lag)
        bpd = bars_per_day(panel["close"].index)
        slip = bt.slippage_model(panel["volume"], bpd)
        res = bt.run(w, panel["close"], panel.get("funding"), slip, band=band, cost_mult=cost_mult, maker=maker)
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
        log_trial({"strategy": name, "params": params, "dataset": dataset, "cost_mult": cost_mult, "band": band,
                   **({"lag": lag} if lag else {}), **({"tag": tag} if tag else {}),
                   **({"exec": exec_desc or "maker"} if maker is not None else {}), **s})
    return res, s


def grid(spec: dict) -> list[dict]:
    keys = list(spec)
    return [dict(zip(keys, vals)) for vals in itertools.product(*(spec[k] for k in keys))]


def robustness(name: str, panel: dict, params: dict, dataset: str) -> dict:
    """Standard stress block for ONE config (full-sample Sharpes), computed for every walk-forward so it is never
    skipped: 2x costs, one bar of execution delay, a tiny band (the signal without the min-order constraint), the
    first 6/12 months dropped (start-date luck), correlation to BTC and, for schedules slower than daily, the Sharpe
    of every single start day of the schedule (the default already trades their average as tranches).
    `worst` = min(base, 2x costs, delay, start-date cuts): the gate reads this, not the best case.
    `small_acct` = the same config in the small account (band = min order / small_equity): reported next to `base`
    because the owner may fund $200 rather than $1,000; it is not part of `worst` (the gate is judged at the main size).
    Lines are logged as config kind with tag "robust", so they do not raise the walk-forward DSR bar."""
    def ev(p=params, **kw):
        return evaluate(name, panel, p, dataset, tag="robust", **kw)
    res, s = ev()
    out = {"params": params, "base": s.get("sharpe"), "cost_x2": ev(cost_mult=2.0)[1].get("sharpe"),
           "delay_1bar": ev(lag=1)[1].get("sharpe"), "band_tiny": ev(band=0.001)[1].get("sharpe")}
    sb = small_band()
    if sb:
        out["small_acct"] = ev(band=sb)[1].get("sharpe")
    first = res.gross[res.gross > 0].index.min()
    if not pd.isna(first):
        r = res.returns[res.returns.index >= first]
        ppy = mx.periods_per_year(r.index)
        for m in (6, 12):
            seg = r[r.index >= first + pd.DateOffset(months=m)]
            out[f"skip_first_{m}m"] = round(mx.sharpe(seg, ppy), 3) if len(seg) > 60 else None
        ref = next((x for x in ("BTC", "BTC@bn") if x in panel["close"]), None)
        if ref:
            px = panel["close"][ref]
            if name in EVENTS:                       # event results are daily whatever the panel's bar size
                px = px.resample("1D").last()
            btc = px.pct_change(fill_method=None).reindex(r.index)
            out["corr_btc"] = round(float(r.corr(btc)), 3)
    sig = inspect.signature(EVENTS.get(name) or REGISTRY[name]).parameters
    n = int(params.get("every_days", sig["every_days"].default if "every_days" in sig else 1))
    if 1 < n <= 14 and "phase" in sig:
        ph = [ev({**params, "phase": k})[1].get("sharpe") for k in range(n)]
        out["phases"] = ph
        out["phase_min"], out["phase_mean"], out["phase_max"] = min(ph), round(float(np.mean(ph)), 3), max(ph)
    vals = [out.get(k) for k in ("base", "cost_x2", "delay_1bar", "skip_first_6m", "skip_first_12m")]
    vals = [v for v in vals if v is not None]
    out["worst"] = min(vals) if vals else None
    return out


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
        "oos": mx.summary(oos_r, n_trials=n_trials("walk_forward") + 1) if len(oos_r) > 30 else {},
        "folds": chosen,
        "grid": grid_df.sort_values("sharpe", ascending=False).head(10).to_dict("records"),
        # stress block for the config the walk-forward would trade today (latest fold's choice)
        "robust": robustness(name, panel, chosen[-1]["params"], dataset) if chosen else {},
    }
    log_trial({"kind": "walk_forward", **{k: v for k, v in out.items() if k not in ("grid", "folds")}})
    return out
