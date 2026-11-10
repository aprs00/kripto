"""T9: same strategy configs under taker vs passive (maker + taker fallback) execution, on the bars that have hourly data.

    nice -n 19 .venv/bin/python -m scripts.exec_study research/batches/2026-11-10-t9-exec.json

Every backtest goes through research.evaluate (registry lines tagged exec / tag "exec"). Prints, per config and policy:
turnover/yr, cost/yr, Sharpe over the hourly-covered window, the turnover-weighted fill rate and the mean drift paid
by unfilled orders. Writes research/results/<ts>_exec_study.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from kripto import data, research
from kripto.execution import MAKER_FEE, maker_fills

ROOT = Path(__file__).resolve().parent.parent


def hourly(ds: str) -> dict:
    p = data.load_hl_panel("1h") if ds in ("hl", "hlx") else data.load_bn_panel("1h")
    return {k: p[k] for k in ("close", "high", "low")}


def fill_stats(res, mk, start: str) -> dict:
    """Turnover-weighted fill rate and mean drift cost of unfilled trades, on cells that have hourly data."""
    w = res.weights[res.weights.index >= start]   # the hourly-covered window only (bug in the first 11-10 run: full history)
    dw = (w.shift(-1) - w).fillna(0.0)      # trade at close t moves held weights from bar t to t+1 (approx: ignores drift)
    fb, fs, dr = (mk[k].reindex(index=w.index, columns=w.columns) for k in ("fill_buy", "fill_sell", "drift"))
    have = fb.notna() & dr.notna()
    buy, sell = dw.clip(lower=0).where(have, 0), (-dw).clip(lower=0).where(have, 0)
    tot = buy.to_numpy().sum() + sell.to_numpy().sum()
    filled = (buy * fb.fillna(0)).to_numpy().sum() + (sell * fs.fillna(0)).to_numpy().sum()
    unf_cost = (buy * (1 - fb.fillna(0)) * dr.fillna(0)).to_numpy().sum() - (sell * (1 - fs.fillna(0)) * dr.fillna(0)).to_numpy().sum()
    allt = np.abs(dw).to_numpy().sum()
    return {"covered": round(tot / allt, 3) if allt else None, "fill_rate": round(filled / tot, 3) if tot else None,
            "unfilled_drift_bp": round(1e4 * unf_cost / max(tot - filled, 1e-12), 1) if tot > filled else None}


def main(path: str):
    spec = json.loads(Path(path).read_text())
    pols = spec["_policies"]
    out = []
    for ds, strats in spec.items():
        if ds.startswith("_"):
            continue
        panel = data.load_panel(ds, "1d")
        hp = hourly(ds)
        start = str(hp["close"].index.min() + pd.Timedelta(days=30))   # leave the strategies a month of hourly-era warm-up
        fee = MAKER_FEE["hl" if ds in ("hl", "hlx") else "bn"]
        # a policy is [horizon_h, through] (taker fallback) or [horizon_h, through, "skip"] (post-only, unfilled = no trade)
        mks = {tuple(p): {**maker_fills(hp, panel["close"].index, p[0], p[1]), "fee": fee,
                          "skip_unfilled": len(p) > 2 and p[2] == "skip"} for p in pols}
        for name, params in strats.items():
            _, s0 = research.evaluate(name, panel, params, f"{ds}_1d", start=start, tag="exec")
            row = {"ds": ds, "strategy": name, "params": params, "start": start[:10],
                   "taker": {k: s0.get(k) for k in ("sharpe", "turnover_yr", "cost_yr", "cagr")}}
            for p, mk in mks.items():
                res, s = research.evaluate(name, panel, params, f"{ds}_1d", start=start, tag="exec", maker=mk,
                                           exec_desc=f"maker_h{p[0]}_x{p[1]*1e4:.0f}bp" + ("_skip" if mk["skip_unfilled"] else ""))
                row[f"h{p[0]}_x{p[1]*1e4:.0f}" + ("_skip" if mk["skip_unfilled"] else "")] = {**{k: s.get(k) for k in ("sharpe", "turnover_yr", "cost_yr", "cagr")},
                                                   **fill_stats(res, mk, start)}
            out.append(row)
            t = row["taker"]
            print(f"{ds:4} {name:14} taker SR={t['sharpe']} cost/yr={t['cost_yr']} turn={t['turnover_yr']}", flush=True)
            for k, v in row.items():
                if k.startswith("h"):
                    print(f"      {k:9} SR={v['sharpe']} cost/yr={v['cost_yr']} fill={v['fill_rate']} "
                          f"cov={v['covered']} unfilled drift={v['unfilled_drift_bp']}bp", flush=True)
    f = ROOT / "research" / "results" / f"{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}_exec_study.json"
    f.write_text(json.dumps(out, indent=1, default=str))
    print("wrote", f)


if __name__ == "__main__":
    main(sys.argv[1])
