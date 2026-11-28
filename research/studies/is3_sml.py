"""InSilico pass 3, SML: HL main book legs at the $200 band (.05) vs .005. python -m research.studies.is3_sml a|b|c [drop leg]"""
import json, sys
import numpy as np, pandas as pd
from kripto import backtest as bt, data
from kripto.research import bars_per_day
from kripto.strategies import REGISTRY
from research.studies.is3_prb import summary
from research.studies.is3_prl import legs, LEGS

if __name__ == "__main__":
    form = sys.argv[1]
    p = data.load_panel("hl", "1d")
    slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
    out = {}
    if form == "a":
        fin, ref, _ = legs(p)
        for band in (0.005, 0.05):
            for n, w in list(fin.items()) + [("book", ref.fillna(0.0))]:
                r = bt.run(w, p["close"], p.get("funding"), slip, band=band)
                d = w.diff().abs().to_numpy().ravel(); d = d[d > 1e-9]
                o = {str(y): summary(r, f"{y}-01-01", f"{y+1}-01-01") for y in (2023, 2024, 2025, 2026)}
                o["share_changes_below_band"] = float((d < band).mean())
                out[f"{n}_band{band}"] = o
                print(band, n, {y: (round(x["sr"], 2), round(x["ann"], 3), round(x["costs_ann"], 3)) for y, x in o.items() if isinstance(x, dict)}, round(o["share_changes_below_band"], 2), flush=True)
    else:
        drop = sys.argv[2]
        keep = [n for n in LEGS if n != drop]
        yrs = (2023, 2024) if form == "b" else (2025, 2026)
        for lab, comps in (("3leg", LEGS), ("2leg", keep)):
            w = REGISTRY["blend"](p, components={n: {} for n in comps})
            r = bt.run(w, p["close"], p.get("funding"), slip, band=0.05)
            out[lab] = {str(y): summary(r, f"{y}-01-01", f"{y+1}-01-01") for y in yrs}
            out[lab]["all"] = summary(r, f"{yrs[0]}-01-01", f"{yrs[-1]+1}-01-01")
            print(lab, comps, {y: (round(x["sr"], 3), round(x["ann"], 3), round(x["mdd"], 3)) for y, x in out[lab].items()}, flush=True)
    json.dump(out, open(f"research/is3/sml_{form}.json", "w"), indent=1)
