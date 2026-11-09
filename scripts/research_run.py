"""Walk-forward evaluation of registered strategies on HL and/or Binance panels.

  nice -n 19 .venv/bin/python -m scripts.research_run --strategies tsmom carry --datasets hl bn
  nice -n 19 .venv/bin/python -m scripts.research_run --grids research/batches/2026-11-09.json --datasets hl bn
Grids are PRE-REGISTERED below (or passed as JSON via --grid). Results -> research/results/<ts>_<strategy>_<ds>.json
"""
import argparse, json, os, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from kripto import data
from kripto.research import walk_forward

GRIDS = {
    "tsmom": {"lookbacks": [(7, 14, 28, 56), (14, 28, 56), (28, 56, 112)], "every_days": [1, 3],
              "long_only": [False, True]},
    "xsmom": {"lookback": [7, 14, 28, 56], "every_days": [1, 3, 7]},
    "xsrev": {"lookback": [1, 3, 7], "every_days": [1, 3]},
    "carry": {"lookback": [1, 3, 7, 14], "every_days": [1, 3, 7]},
    "lowvol": {"vol_days": [14, 30, 60], "every_days": [3, 7]},
    "funding_contra": {"fast": [1, 3], "slow": [14, 30], "every_days": [1, 3]},
}
OUT = Path(__file__).resolve().parent.parent / "research" / "results"
_PANELS = {}


def panel(ds, since=None, interval="4h"):
    if (ds, interval) not in _PANELS:
        p = data.load_hl_panel(interval) if ds == "hl" else data.load_bn_panel(interval)
        if since:
            p = {k: v[v.index >= since] for k, v in p.items()}
        _PANELS[(ds, interval)] = p
    return _PANELS[(ds, interval)]


def job(args):
    name, ds, grid, since, interval = args
    t = time.time()
    res = walk_forward(name, panel(ds, since, interval), grid, dataset=ds if interval == "4h" else f"{ds}_{interval}")
    res["seconds"] = round(time.time() - t, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{time.strftime('%Y%m%d-%H%M')}_{name}_{res['dataset']}.json").write_text(json.dumps(res, indent=1, default=str))
    return res


def brief(r):
    o = r.get("oos", {})
    return (f"{r['strategy']:15s} {r['dataset']:3s} OOS sharpe={o.get('sharpe')} cagr={o.get('cagr')} "
            f"mdd={o.get('max_dd')} dsr={o.get('dsr')} turn/yr={o.get('turnover_yr')} | grid med sharpe="
            f"{r['grid_median_sharpe']} frac>0={r['grid_frac_positive']} n={r['n_configs']} ({r['seconds']}s)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategies", nargs="+", default=list(GRIDS))
    ap.add_argument("--datasets", nargs="+", default=["hl", "bn"])
    ap.add_argument("--grid", help="JSON grid override (single strategy)")
    ap.add_argument("--grids", help="JSON file {strategy: grid} to test several hypotheses in one parallel batch")
    ap.add_argument("--since", help="e.g. 2021-01-01")
    ap.add_argument("--interval", default="4h", choices=["4h", "1d"], help="bar size (dataset is logged as e.g. hl_1d)")
    ap.add_argument("--workers", type=int, default=3, help="~0.6 GB RAM each; keep <= 3 on the shared server")
    a = ap.parse_args()
    if a.grids:
        spec = json.loads(Path(a.grids).read_text())
        jobs = [(s, d, g, a.since, a.interval) for s, g in spec.items() for d in a.datasets]
    else:
        jobs = [(s, d, json.loads(a.grid) if a.grid else GRIDS[s], a.since, a.interval)
                for s in a.strategies for d in a.datasets]
    with ProcessPoolExecutor(a.workers) as ex:
        for r in ex.map(job, jobs):
            print(brief(r), flush=True)
