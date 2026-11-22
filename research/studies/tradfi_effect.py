"""2026-11-22 retro: what the stock / commodity perps in `bnall` did to the Binance candidates (same configs, panel with and without them,
cut at 2026-10-31 where every symbol's archive is complete). Evaluate lines tagged tradfi; no walk-forward.
usage: python -m research.studies.tradfi_effect
"""
import json

import pandas as pd

from kripto import data, research as R

CUT = pd.Timestamp("2026-10-31", tz="UTC")


def panel(clean):
    keep = data.bn_tradfi
    if not clean:
        data.bn_tradfi = lambda: {}
    try:
        p = data.load_panel("bnall", "1d")
    finally:
        data.bn_tradfi = keep
    p = {k: x.loc[:CUT] for k, x in p.items()}
    cols = p["close"].columns[p["close"].notna().any()]
    return {k: x[cols] for k, x in p.items()}


def main():
    cfg = json.load(open("config/strategies.json"))
    want = [(k, v) for k, v in cfg.items() if v.get("venue") == "bn" and v["status"] != "retired"] + [("listing_short", cfg["listing_short"])]
    out = {}
    for clean in (False, True):
        p = panel(clean)
        print("clean" if clean else "with stock perps", p["close"].shape)
        for k, v in want:
            for per, start in (("all", None), ("2025", "2025-01-01"), ("2026", "2026-01-01")):
                _, m = R.evaluate(v.get("strategy", k.split("@")[0]), p, v.get("params", {}), "bnall_1d", start=start,
                                  tag=f"tradfi:{'clean' if clean else 'old'}", log=per == "all")
                out.setdefault(k, {})[f"{'clean' if clean else 'old'}_{per}"] = round(m["sharpe"], 2)
                if per == "all":
                    out[k][f"{'clean' if clean else 'old'}_mdd"] = round(m["max_dd"], 2)
    print(pd.DataFrame(out).T.to_string())


if __name__ == "__main__":
    main()
