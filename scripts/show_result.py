"""Summarise walk-forward result files: OOS stats, full grid ranking, fold choices.
  .venv/bin/python -m scripts.show_result listing_short hl_1d      # latest result for strategy+dataset
  .venv/bin/python -m scripts.show_result --today                  # one line per result written today (UTC)
"""
import glob, json, sys, time
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "research" / "results"


def line(d):
    o = d.get("oos", {})
    return (f"{d['strategy']:15s} {d['dataset']:7s} OOS SR={o.get('sharpe')} cagr={o.get('cagr')} mdd={o.get('max_dd')} "
            f"yrs={o.get('years')} dsr={o.get('dsr')} | grid med={d['grid_median_sharpe']} >0={d['grid_frac_positive']} n={d['n_configs']}"
            f" | grid avg OOS={d.get('oos_grid_avg')} | worst={(d.get('robust') or {}).get('worst')}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--today"]:
        for f in sorted(OUT.glob(time.strftime("%Y%m%d", time.gmtime()) + "-*.json")):
            print(f.name[:15], line(json.loads(f.read_text())))
        sys.exit()
    strat, ds = sys.argv[1], sys.argv[2]
    files = sorted(OUT.glob(f"*_{strat}_{ds}.json"))
    if not files:
        sys.exit(f"no results for {strat} {ds}")
    d = json.loads(files[-1].read_text())
    print(files[-1].name, "\n" + line(d))
    print("grid (top 10 by full-sample SR; in-sample, for robustness only):")
    for g in d["grid"]:
        p = {k: v for k, v in g.items() if k not in ("i", "sharpe", "cagr", "max_dd", "turnover_yr", "cost_yr", "funding_yr")}
        print(f"  SR={g['sharpe']:6.2f} cagr={g['cagr']:7.3f} mdd={g['max_dd']:6.2f} turn={g['turnover_yr']} "
              f"cost={g['cost_yr']} fund={g['funding_yr']}  {p}")
    rb = d.get("robust") or {}
    if rb:
        print(f"robustness of the latest choice {rb.get('params')} (full-sample SR; the gate reads `worst`):")
        print("  " + "  ".join(f"{k}={rb.get(k)}" for k in ("base", "cost_x2", "delay_1bar", "skip_first_6m",
                                                              "skip_first_12m", "band_tiny", "small_acct", "small_acct_min", "small_deployed", "small_acct_round", "corr_btc", "worst")))
        if rb.get("phases"):
            print(f"  single start days of the schedule: {rb['phases']} (min {rb['phase_min']}, mean {rb['phase_mean']})")
    print("folds (from, oos SR, chosen params):")
    for x in d["folds"]:
        print(f"  {x['from']} {x.get('oos_sharpe')!s:>6} {x['params']}")
