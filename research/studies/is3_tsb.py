"""InSilico pass 3, TSB: HL main book, slow legs (tsmom, lowvol) traded only when |leg target - leg held| > 0.02 per coin (listing in full).
python -m research.studies.is3_tsb a|b"""
import json, sys
import numpy as np, pandas as pd
from kripto import backtest as bt, data
from kripto.research import bars_per_day
from research.studies.is3_prb import partial, summary
from research.studies.is3_prl import legs


def banded(w, band):
    T = w.fillna(0.0).to_numpy()
    out = np.zeros_like(T)
    held = np.zeros(T.shape[1])
    for t in range(len(T)):
        hit = np.abs(T[t] - held) > band
        held = np.where(hit, T[t], held)
        out[t] = held
    return pd.DataFrame(out, w.index, w.columns)


if __name__ == "__main__":
    form = sys.argv[1]
    p = data.load_panel("hl", "1d")
    slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
    fin, ref, _ = legs(p)
    slow = fin["lowvol"] + fin["tsmom"]
    books = {"lam1": ref.fillna(0.0), "slow33": fin["listing_short"] + partial(slow, 0.33), "band02": fin["listing_short"] + banded(slow, 0.02)}
    yrs = (2023, 2024) if form == "a" else (2025, 2026)
    out = {}
    for k, w in books.items():
        r = bt.run(w, p["close"], p.get("funding"), slip, band=0.005)
        out[k] = {str(y): summary(r, f"{y}-01-01", f"{y+1}-01-01") for y in yrs}
        out[k]["all"] = summary(r, f"{yrs[0]}-01-01", f"{yrs[-1]+1}-01-01")
        d = w.diff().abs().to_numpy().ravel()
        d = d[d > 0.005]
        out[k]["share_trades_below_10usd_at_1000"] = float((d * 1000 < 10).mean())
        print(k, {y: (round(v["sr"], 3), round(v["costs_ann"], 4), round(v["sr_pre_cost"], 3)) for y, v in out[k].items() if isinstance(v, dict)},
              round(out[k]["share_trades_below_10usd_at_1000"], 3), flush=True)
    json.dump(out, open(f"research/is3/tsb_{form}.json", "w"), indent=1)
