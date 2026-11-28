"""X1P: power of the X1f forward judge for fspread_hold@pair (main@pair = same strategy, scaled). Descriptive, NOT registered.
a: backtest daily returns (pair 1d, shipped params): mean, sd, AC1, HAC MDE of the mean at 30/60/90/180 d; rolling-window distributions of 30/60-d vol ratio and
   P(60-d SR < 0) (false-retire rate), on 2024-01+ and full; b: live so far (ledger_decomp) in MDE units.
PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_x1p -> research/is3/x1p_ab.json"""
import json
import numpy as np, pandas as pd
from kripto import backtest as bt, data, paper as P, strategies as S
from kripto.research import bars_per_day, default_band
from scripts.ledger_decomp import decompose

p = data.load_panel("pair", "1d"); c = p["close"]
w = S.REGISTRY["fspread_hold"](p, lookback=14, enter=0.1)
res = bt.run(w, c, p["funding"], bt.slippage_model(p["volume"], bars_per_day(c.index)), band=default_band())
r_all = res.returns.dropna()
r_all = r_all.loc[r_all.ne(0).idxmax():]


def hac_var(x, L):                      # Newey-West long-run variance (copy of is3_fjp.hac_var: importing that script runs it)
    x = x - x.mean(); v = float((x * x).mean())
    for l in range(1, L + 1):
        v += 2 * (1 - l / (L + 1)) * float((x[l:].to_numpy() * x[:-l].to_numpy()).mean())
    return v


def stats(r):
    lrv = hac_var(r, 10); m = float(r.mean()); sd = float(r.std())
    o = {"days": len(r), "start": str(r.index[0].date()), "end": str(r.index[-1].date()), "mean_bp": round(m * 1e4, 3), "ann_ret_pct": round(m * 365 * 100, 2),
         "vol_pct": round(sd * np.sqrt(365) * 100, 2), "sr": round(m / sd * np.sqrt(365), 2), "ac1": round(float(r.autocorr(1)), 3),
         "hac_over_iid": round(lrv / sd ** 2, 2),
         "mde_mean_bp": {n: round(2 * np.sqrt(lrv / n) * 1e4, 3) for n in (30, 60, 90, 180, 365)}}
    o["mde_over_mean"] = {n: round(v / (m * 1e4), 2) for n, v in o["mde_mean_bp"].items()}
    for n in (30, 60, 90):
        rs = r.rolling(n)
        vr = (rs.std() / sd).dropna(); sr = (rs.mean() / rs.std()).dropna()
        o[f"w{n}"] = {"vol_ratio_p05": round(float(vr.quantile(.05)), 2), "p50": round(float(vr.median()), 2), "p95": round(float(vr.quantile(.95)), 2),
                      "p99": round(float(vr.quantile(.99)), 2), "share_vol_ge_3x": round(float((vr >= 3).mean()), 4),
                      "share_sr_lt_0": round(float((sr < 0).mean()), 3), "share_ret_lt_0": round(float((rs.sum().dropna() < 0).mean()), 3)}
    return o


out = {"a_full": stats(r_all), "a_2024": stats(r_all.loc["2024":]), "a_2026": stats(r_all.loc["2026":])}
for k in out: print(k, out[k], flush=True)
# b: live
store = P.Store(); live = {}
for book in ("shadow:fspread_hold@pair", "main@pair"):
    try:
        led = decompose(store, book)
    except SystemExit as e:
        live[book] = str(e); continue
    st = store.q("select start_equity from books where name=?", book)[0][0]
    lr = (led["d_eq"] / st).dropna()
    ref = out["a_2024"]; scale = 0.5 if book == "main@pair" else 1.0
    n = len(lr); lrv_bt = ref["mde_mean_bp"][30] / 2 * np.sqrt(30)  # bp * sqrt(day): HAC sd of the daily mean per sqrt n
    live[book] = {"days": n, "first": str(led.index[0])[:10], "last": str(led.index[-1])[:10], "mean_bp": round(float(lr.mean()) * 1e4, 3),
                  "vol_pct": round(float(lr.std() * np.sqrt(365)) * 100, 2), "sr": round(float(lr.mean() / lr.std() * np.sqrt(365)), 2) if n > 2 else None,
                  "cols": {k: round(float(led[k].sum()), 2) for k in ("funding", "fees", "price") if k in led.columns},
                  "gap_mean_bp_vs_bt2024_scaled": round(float(lr.mean()) * 1e4 - ref["mean_bp"] * scale, 3),
                  "gap_in_mde_units": round((float(lr.mean()) * 1e4 - ref["mean_bp"] * scale) / (2 * lrv_bt * scale / np.sqrt(max(n, 1))), 2),
                  "vol_ratio_vs_bt2024": round(float(lr.std() * np.sqrt(365) * 100) / (ref["vol_pct"] * scale), 2)}
    print(book, live[book], flush=True)
out["b_live"] = live
json.dump(out, open("research/is3/x1p_ab.json", "w"), indent=1)
