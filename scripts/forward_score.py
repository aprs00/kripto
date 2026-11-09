"""Forward ledger: score every walk-forward experiment's frozen choice ONLY on bars after it was registered.

Why: every backtest re-reads the same few years of history, so each new idea raises the multiple-testing bar. Data that
did not exist when a config was chosen is the one clean out-of-sample we have, and it accrues for ALL experiments at once,
DEAD ones included (they are the null distribution: if ALIVE configs don't beat them forward, the "edge" was selection).

  nice -n 19 .venv/bin/python -m scripts.forward_score          # all results -> table + research/forward.json
  nice -n 19 .venv/bin/python -m scripts.forward_score hl_1d    # one dataset only

Config = the parameters the walk-forward's latest fold chose, taken from research/results/*.json; registration time =
the result file's timestamp. Scored with today's code (tranches, band = min order / equity), i.e. as it would trade.
Each run goes through research.evaluate (logged as config kind with tag "forward": no effect on the walk-forward DSR bar).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "research" / "results"
DEST = ROOT / "research" / "forward.json"


def registered(fname: str) -> pd.Timestamp | None:
    """UTC time a result file was written, from its name (YYYYMMDD-HHMM or YYYYMMDD-HHMMSS)."""
    m = re.match(r"(\d{8})-(\d{6}|\d{4})(?!\d)", fname)
    if not m:
        return None
    return pd.Timestamp(pd.to_datetime(m.group(1) + m.group(2), format="%Y%m%d%H%M%S" if len(m.group(2)) == 6
                                       else "%Y%m%d%H%M"), tz="UTC")


def experiments(out: Path = OUT, known: set[str] | None = None) -> list[dict]:
    """Earliest registration of each distinct (strategy, dataset, chosen params)."""
    seen: dict[tuple, dict] = {}
    for f in sorted(out.glob("*.json")):
        ts = registered(f.name)
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        if ts is None or not d.get("folds") or (known is not None and d.get("strategy") not in known):
            continue
        params = d["folds"][-1]["params"]
        key = (d["strategy"], d["dataset"], json.dumps(params, sort_keys=True, default=str))
        if key not in seen:
            seen[key] = {"strategy": d["strategy"], "dataset": d["dataset"], "params": params, "registered": ts,
                         "backtest_oos_sharpe": (d.get("oos") or {}).get("sharpe"), "file": f.name}
    return list(seen.values())


def forward_stats(r: pd.Series, since: pd.Timestamp, ppy: float) -> dict:
    """Stats of the returns of bars that START at or after `since` (those bars lie wholly after registration)."""
    f = r[r.index >= since].dropna()
    days = float(len(f) / ppy * 365) if len(f) else 0.0
    out = {"bars": int(len(f)), "days": round(days, 1), "ret": round(float((1 + f).prod() - 1), 4) if len(f) else 0.0,
           "sharpe": None}
    if days >= 30 and f.std() > 0:   # a Sharpe on less than a month is noise even as a description
        out["sharpe"] = round(float(f.mean() / f.std() * np.sqrt(ppy)), 2)
    return out


def main(only: str | None = None) -> list[dict]:
    from kripto import data, metrics as mx
    from kripto.research import evaluate
    from kripto.strategies import REGISTRY
    loaders = {"hl": lambda: data.load_hl_panel("4h"), "hl_1d": lambda: data.load_hl_panel("1d"),
               "bn": lambda: data.load_bn_panel("4h"), "bn_1d": lambda: data.load_bn_panel("1d"),
               "bnall": data.load_bn_all_panel, "bnall_1d": data.load_bn_all_panel}
    exps = [e for e in experiments(known=set(REGISTRY)) if e["dataset"] in loaders and (not only or e["dataset"] == only)]
    rows, panels = [], {}
    for e in sorted(exps, key=lambda e: (e["dataset"], e["strategy"])):
        ds = e["dataset"]
        if ds not in panels:
            panels = {ds: loaders[ds]()}          # one panel in memory at a time (RAM on the shared server)
        try:
            res, _ = evaluate(e["strategy"], panels[ds], e["params"], ds, tag="forward")
        except Exception as ex:                   # e.g. a dataset without the column a strategy needs
            rows.append({**e, "registered": str(e["registered"]), "error": repr(ex)[:80]})
            continue
        st = forward_stats(res.returns, e["registered"], mx.periods_per_year(res.returns.index))
        rows.append({**e, "registered": str(e["registered"]), "data_end": str(res.returns.index[-1]), **st})
    return rows


if __name__ == "__main__":
    rows = main(sys.argv[1] if len(sys.argv) > 1 else None)
    DEST.write_text(json.dumps({"updated": pd.Timestamp.now("UTC").strftime("%Y-%m-%dT%H:%MZ"), "rows": rows},
                               indent=1, default=str))
    print(f"{'strategy':15s}{'dataset':9s}{'registered':17s}{'days':>6s}{'fwd ret':>9s}{'fwd SR':>8s}{'bt OOS':>8s}")
    for r in sorted(rows, key=lambda r: (-(r.get("days") or 0), r["strategy"])):
        if "error" in r:
            print(f"{r['strategy']:15s}{r['dataset']:9s}{r['registered'][:16]:17s}  {r['error']}")
            continue
        print(f"{r['strategy']:15s}{r['dataset']:9s}{r['registered'][:16]:17s}{r['days']:6.1f}{r['ret']:+9.2%}"
              f"{str(r['sharpe']):>8s}{str(r['backtest_oos_sharpe']):>8s}")
    print(f"{len(rows)} frozen configs -> {DEST.relative_to(ROOT)}. Under 30 days forward nothing can be concluded.")
