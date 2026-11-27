"""InSilico pass 3, FSM: fspread_hold@pair with maker legs (T9 fill model). Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_fsm      # forms a, b, c -> research/is3/fsm_abc.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data, execution
from kripto import strategies as S
from kripto.research import bars_per_day, default_band
from research.studies import is3_lib as L

LO, HI = pd.Timestamp("2026-04-16", tz="UTC"), pd.Timestamp("2026-10-30", tz="UTC")


def hourly(cols):
    out = {k: {} for k in ("close", "high", "low")}
    for col in cols:
        coin, v = col.split("@")
        f = (data.DATA / "hl" / "candles_1h" / f"{coin}.parquet") if v == "hl" else (data.BN100_DIR / f"{coin}USDT.parquet")
        if not f.exists():
            continue
        x = pd.read_parquet(f, columns=["t", "h", "l", "c"])
        t = x["t"].where(x["t"] < 1e14, x["t"] // 1000)
        x.index = pd.to_datetime(t, unit="ms", utc=True)
        x = x[~x.index.duplicated()].sort_index()
        x = x[(x.index >= LO - pd.Timedelta("2D")) & (x.index < HI + pd.Timedelta("3D"))]
        out["close"][col], out["high"][col], out["low"][col] = x["c"], x["h"], x["l"]
    return {k: pd.DataFrame(v) for k, v in out.items()}


def main():
    p = data.load_panel("pair", "1d")
    c = p["close"]
    w = S.REGISTRY["fspread_hold"](p, lookback=14, enter=0.1)
    slip = bt.slippage_model(p["volume"], bars_per_day(c.index))
    wf = w.ffill().fillna(0.0)
    dw = wf.diff().fillna(0.0)
    traded_cols = [x for x in c.columns if (dw.loc[LO:HI, x].abs() > 0).any()]
    hr = hourly(traded_cols)
    print(f"{len(traded_cols)} traded leg columns in window, hourly data for {hr['close'].shape[1]}", flush=True)
    base = bt.run(w, c, p["funding"], slip, band=default_band())
    win = lambda s: s[(s.index >= LO) & (s.index < HI)]
    yrs = (HI - LO).days / 365
    out = {"window": [str(LO.date()), str(HI.date())], "taker": {"ret_yr": round(float(win(base.returns).sum() / yrs), 4), "cost_yr": round(float(win(base.costs).sum() / yrs), 4),
                                                             "turnover_yr": round(float(win(base.turnover).sum() / yrs), 2)}}
    print("taker", out["taker"], flush=True)
    T = dw.loc[LO:HI, traded_cols]
    for H in (1, 4, 12):
        mk = execution.maker_fills(hr, c.index, horizon_h=H)
        mk = {k: v.reindex(columns=c.columns) for k, v in mk.items()}
        # (a) fill rates on the traded cells, per venue and entry/exit
        fb, fs = mk["fill_buy"].reindex(T.index)[traded_cols], mk["fill_sell"].reindex(T.index)[traded_cols]
        fill = fb.where(T > 0).fillna(fs.where(T < 0))
        prev = wf.shift(1).loc[LO:HI, traded_cols]
        entry = (prev == 0) & (T != 0)
        rates = {}
        for v in ("hl", "bn"):
            cols = [x for x in traded_cols if x.endswith("@" + v)]
            for lab, m in (("entry", entry[cols]), ("exit/resize", (~entry[cols]) & (T[cols] != 0))):
                x = fill[cols].where(m).stack()
                rates[f"{v}_{lab}"] = [int(x.notna().sum()), round(float(x.mean()), 3) if x.notna().any() else None]
        drift_unf = (mk["drift"].reindex(T.index)[traded_cols] * np.sign(T)).where((fill == 0) & (T != 0)).stack()
        res = {}
        for skip in (False, True):
            r = bt.run(w, c, p["funding"], slip, band=default_band(), maker={**mk, "fee": 2e-4, "skip_unfilled": skip})
            res["post_only" if skip else "fallback"] = {"ret_yr": round(float(win(r.returns).sum() / yrs), 4), "cost_yr": round(float(win(r.costs).sum() / yrs), 4),
                                                        "turnover_yr": round(float(win(r.turnover).sum() / yrs), 2),
                                                        "d_ret_yr_vs_taker": round(float((win(r.returns).sum() - win(base.returns).sum()) / yrs), 4)}
        out[f"H{H}"] = {"fill_rates_n_rate": rates, "unfilled_signed_drift_bp_mean_median": [round(float(drift_unf.mean()) * 1e4, 1), round(float(drift_unf.median()) * 1e4, 1), int(len(drift_unf))], **res}
        print(f"H={H}h fills {rates} | unfilled drift (against us +) {out[f'H{H}']['unfilled_signed_drift_bp_mean_median']} | fallback {res['fallback']} | post-only {res['post_only']}", flush=True)
    json.dump({"study": "research/studies/is3_fsm.py", **out}, open(L.OUT / "fsm_abc.json", "w"), indent=1, default=str)


if __name__ == "__main__" and __import__("sys").argv[1:] != ["b"]:
    main()


def form_b(H=4, through=5e-4, maker_fee=2e-4):
    """Maker on ONE leg (the one with the higher modelled taker cost), the other leg taken (taker) at the close of the hour the maker leg fills;
    unfilled after H h -> both legs taker at +H h. Cost per traded pair-event relative to both decision closes (bp of one leg's notional per leg traded)."""
    p = data.load_panel("pair", "1d")
    c = p["close"]
    wf = S.REGISTRY["fspread_hold"](p, lookback=14, enter=0.1).ffill().fillna(0.0)
    slip = bt.slippage_model(p["volume"], bars_per_day(c.index))
    dw = wf.diff().fillna(0.0).loc[LO:HI]
    hlc = [x for x in c.columns if x.endswith("@hl")]
    hr = hourly([x for x in hlc] + [x[:-3] + "@bn" for x in hlc if x[:-3] + "@bn" in c.columns])
    rows = []
    for t, row in dw.iterrows():
        D = t + pd.Timedelta(days=1)                         # decision = close of the daily bar
        for h in hlc:
            b = h[:-3] + "@bn"
            if abs(row.get(h, 0)) < 1e-12 or b not in row or abs(row[b]) < 1e-12 or h not in hr["close"] or b not in hr["close"]:
                continue
            legs = {h: row[h], b: row[b]}
            cost_t = {x: bt.TAKER_FEE + float(slip.at[t, x]) for x in legs}
            A = max(legs, key=lambda x: cost_t[x])           # maker leg = the more expensive one to take
            Bl = b if A == h else h
            sA, sB = np.sign(legs[A]), np.sign(legs[Bl])
            hrs = pd.date_range(D, D + pd.Timedelta(hours=H - 1), freq="1h")
            cA, cB = hr["close"][A], hr["close"][Bl]
            p0A, p0B = cA.get(D - pd.Timedelta(hours=1)), cB.get(D - pd.Timedelta(hours=1))
            if p0A is None or p0B is None or not np.isfinite(p0A) or not np.isfinite(p0B):
                continue
            lo_, hi_ = hr["low"][A].reindex(hrs), hr["high"][A].reindex(hrs)
            hit = (lo_ <= p0A * (1 - through)) if sA > 0 else (hi_ >= p0A * (1 + through))
            base_cost = cost_t[A] + cost_t[Bl]               # taker both at the decision close (the backtest)
            if hit.any():
                k = hit.idxmax()
                pB = cB.get(k)                               # hedge leg taken at the close of the fill hour
                driftB = sB * (pB / p0B - 1)                 # > 0 = price moved against the hedge leg
                cost = maker_fee + cost_t[Bl] + driftB
                filled = True
            else:
                kH = hrs[-1]
                dA, dB = sA * (cA.get(kH) / p0A - 1), sB * (cB.get(kH) / p0B - 1)
                cost = cost_t[A] + cost_t[Bl] + dA + dB      # both taker at +H; drifts of a hedged pair ~ cancel (basis change)
                filled = False
            rows.append({"t": t, "coin": h[:-3], "A": A.split("@")[1], "filled": filled, "base_bp": base_cost * 1e4, "maker_bp": cost * 1e4})
    d = pd.DataFrame(rows)
    d["save_bp"] = d.base_bp - d.maker_bp
    out = {"n_events": int(len(d)), "fill_rate": round(float(d.filled.mean()), 3), "maker_leg_venue": d.A.value_counts().to_dict(),
           "base_bp_mean": round(float(d.base_bp.mean()), 2), "maker_bp_mean": round(float(d.maker_bp.mean()), 2),
           "save_bp_mean": round(float(d.save_bp.mean()), 2), "save_bp_median": round(float(d.save_bp.median()), 2),
           "save_filled_unfilled": [round(float(d[d.filled].save_bp.mean()), 2), round(float(d[~d.filled].save_bp.mean()), 2) if (~d.filled).any() else None]}
    print(f"H={H}: {json.dumps(out)}", flush=True)
    return out, d


if __name__ == "__main__" and __import__("sys").argv[1:] == ["b"]:
    res = {}
    for H in (1, 4, 12):
        res[f"H{H}"], _ = form_b(H)
    json.dump({"study": "research/studies/is3_fsm.py b", **res}, open(L.OUT / "fsm_b.json", "w"), indent=1, default=str)
