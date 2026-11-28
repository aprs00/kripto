"""LSH3: listing_short age weighting: flat 60 d (shipped) vs linear decay (w ∝ 61 - age_days over days 1..60) vs flat 30 d. Same eligibility, beta hedge and
vol-target schedule as strategies.listing_short (the weighting is applied to raw before the hedge). Not registered (descriptive).
PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_lsh3 bnall|hl [check] -> research/is3/lsh3_<ds>[_check].json
explore windows: bnall 2020-23, hl 2023-24; check = bnall 2024-26 (refused unless the explore rule in notes.md passed)."""
import json, sys
import numpy as np, pandas as pd
from kripto import backtest as bt, data
from kripto import strategies as S
from kripto.research import bars_per_day

ds = sys.argv[1]; check = len(sys.argv) > 2 and sys.argv[2] == "check"
if check and ds != "bnall":
    raise SystemExit("check sample is bnall 2024-26 only")
p = data.load_panel(ds, "1d")
lo, hi = {("bnall", False): ("2020-01-01", "2024-01-01"), ("hl", False): ("2023-01-01", "2025-01-01"), ("bnall", True): ("2024-01-01", "2027-01-01")}[(ds, check)]
kw = {"fee": 5e-4} if ds == "bnall" else {"band": 0.005}
c, v = p["close"], p["volume"]
slip = bt.slippage_model(v, bars_per_day(c.index))


def ls_weighted(panel, mode, skip_days=1, min_dv=1e6, target_vol=0.20, max_gross=1.5):
    """strategies.listing_short with hold 60 (or 30) and an age weight; 1d bars only (bpd = 1)."""
    hold = 30 if mode == "flat30" else 60
    traded = (v.fillna(0) > 0) & c.notna(); started = traded.cummax(); age = started.cumsum()
    any_t = traded.any(axis=1); t_cut = any_t.idxmax() + pd.Timedelta(days=30)
    pre = started.loc[started.index < t_cut].any()
    elig = (age > skip_days) & (age <= skip_days + hold) & c.notna() & (S.dollar_volume(panel) >= min_dv)
    elig = elig.loc[:, ~pre].reindex(columns=c.columns, fill_value=False)
    elig = elig & pd.DataFrame(np.broadcast_to((c.index >= t_cut)[:, None], c.shape), c.index, c.columns)
    wt = (skip_days + hold + 1 - age).clip(lower=0).astype(float) if mode == "linear" else pd.DataFrame(1.0, c.index, c.columns)
    raw = -(elig.astype(float) * wt)
    raw = raw.div(raw.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    raw = S.hedge_beta(raw, S.beta_to(panel))
    return S.scheduled(raw, panel, 1, target_vol, max_gross, None)


L, H = pd.Timestamp(lo, tz="UTC"), pd.Timestamp(hi, tz="UTC")
out = {"dataset": ds, "lo": lo, "hi": hi}
w_ref = S.REGISTRY["listing_short"](p, skip_days=1, hold_days=60, min_dv=1e6)
for mode in ("flat60", "linear", "flat30"):
    w = ls_weighted(p, mode)
    if mode == "flat60":   # null check: the local copy must reproduce the registered function
        out["null_check_max_abs_diff"] = float((w.fillna(0) - w_ref.fillna(0)).abs().max().max())
    r = bt.run(w, c, p["funding"], slip, **kw)
    ix = (r.returns.index >= L) & (r.returns.index < H)
    x = r.returns[ix]; vol = float(x.std() * np.sqrt(365))
    yr = {int(y): {"sr": round(float(g.mean() / g.std() * np.sqrt(365)), 2) if g.std() > 0 else None, "ret_per_vol": round(float(g.mean() * 365 / vol), 2)} for y, g in x.groupby(x.index.year)}
    out[mode] = {"sr": round(float(x.mean() / x.std() * np.sqrt(365)), 2), "ann%": round(float(x.mean() * 365 * 100), 1), "vol%": round(vol * 100, 1),
                 "funding%": round(float(r.funding[ix].mean() * 365 * 100), 1), "cost%": round(float(r.costs[ix].mean() * 365 * 100), 1),
                 "turnover_x": round(float(r.turnover[ix].sum() / (len(x) / 365)), 1) if hasattr(r, "turnover") else None,
                 "worst_day_over_vol_daily": round(float(x.min() / (vol / np.sqrt(365))), 1), "by_year": yr,
                 "mean_names": round(float((w.fillna(0).loc[x.index] < 0).sum(axis=1).mean()), 1)}
    print(ds, mode, json.dumps(out[mode]), flush=True)
print("null check", out["null_check_max_abs_diff"])
json.dump(out, open(f"research/is3/lsh3_{ds}{'_check' if check else ''}.json", "w"), indent=1)
