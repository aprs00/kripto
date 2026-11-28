"""LHT: listing_short by launch heat. a: bnall 2020-23 CAR by first-week $vol decile (raw and relative to BTC's $vol that week); b: HL 2023-24 terciles.
Descriptive, NOT registered. PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_lht a|b|c -> research/is3/lht_<form>.json"""
import json, sys
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from kripto import data, strategies as S

form = sys.argv[1]
B = ((2, 30), (31, 60))


def events(p, lo, hi):
    c, v = p["close"], p["volume"]
    r = c.pct_change(fill_method=None); ab = r.sub(r["BTC"], axis=0)
    traded = (v.fillna(0) > 0) & c.notna(); first = traded.idxmax().where(traded.any())
    t_cut = traded.any(axis=1).idxmax() + pd.Timedelta(days=30); dv = S.dollar_volume(p); usd = c * v
    rows = []
    for coin, t0 in first.dropna().items():
        if coin == "BTC" or t0 < max(t_cut, pd.Timestamp(lo, tz="UTC")) or t0 >= pd.Timestamp(hi, tz="UTC"):
            continue
        i0 = c.index.get_loc(t0) + 1
        if i0 + 61 > len(c) or not (dv[coin].iloc[i0] >= 1e6):
            continue
        a = ab[coin].iloc[i0 + 1:i0 + 61].fillna(0.0).to_numpy()
        fw = float(usd[coin].iloc[i0 - 1:i0 + 6].mean()); fb = float(usd["BTC"].iloc[i0 - 1:i0 + 6].mean())
        rows.append({"coin": coin, "t0": t0, "heat": fw, "heat_rel": fw / fb, "car_2_30": float(a[:29].sum()), "car_31_60": float(a[29:].sum()), "car_2_60": float(a.sum())})
    return pd.DataFrame(rows)


def dose(E, key, nq):
    E = E.copy(); E["q"] = pd.qcut(E[key].rank(method="first"), nq, labels=False)
    g = E.groupby("q")
    tab = {int(q): {"n": len(x), **{f"{col}_mean": round(float(x[col].mean() * 100), 1) for col in ("car_2_30", "car_31_60", "car_2_60")},
                    **{f"{col}_median": round(float(x[col].median() * 100), 1) for col in ("car_2_30", "car_31_60")}} for q, x in g}
    rho = {col: round(float(spearmanr(list(tab), [tab[q][f"{col}_mean"] for q in tab])[0]), 2) for col in ("car_2_30", "car_31_60", "car_2_60")}
    rho_med = {col: round(float(spearmanr(list(tab), [tab[q][f"{col}_median"] for q in tab])[0]), 2) for col in ("car_2_30", "car_31_60")}
    ev_rho = {col: round(float(spearmanr(E[key], E[col])[0]), 3) for col in ("car_2_30", "car_31_60", "car_2_60")}
    return {"table": tab, "spearman_over_bins_mean": rho, "spearman_over_bins_median": rho_med, "spearman_events": ev_rho}


out = {}
if form == "a":
    E = events(data.load_panel("bnall", "1d"), "2020-01-01", "2024-01-01"); E["yr"] = E.t0.dt.year
    for key in ("heat", "heat_rel"):
        out[key] = {"all": dose(E, key, 10), "by_year_events_rho": {int(y): dose(g, key, 3)["spearman_events"] for y, g in E.groupby("yr")}}
        top = E.sort_values("car_31_60", ascending=False)
        out[key]["top5_share_of_quiet_tercile_d31_60_sum"] = None
    q3 = pd.qcut(E.heat_rel.rank(method="first"), 3, labels=["quiet", "mid", "hot"])
    for lab in ("quiet", "hot"):
        x = E[q3 == lab].car_31_60.sort_values(ascending=False)
        out[f"{lab}_rel_d31_60"] = {"sum_pct": round(float(x.sum() * 100), 1), "top5_events": [(E.loc[i, "coin"], round(float(x[i] * 100), 1)) for i in x.index[:5]],
                                    "sum_without_top5_pct": round(float(x.iloc[5:].sum() * 100), 1), "mean_without_top5_pct": round(float(x.iloc[5:].mean() * 100), 1)}
    out["n"] = len(E)
elif form == "b":
    E = events(data.load_panel("hl", "1d"), "2023-01-01", "2025-01-01"); E["yr"] = E.t0.dt.year
    out = {"n": len(E), "heat": dose(E, "heat", 3), "heat_rel": dose(E, "heat_rel", 3),
           "by_year": {int(y): dose(g, "heat_rel", 3)["spearman_events"] for y, g in E.groupby("yr")},
           "mde_pp_tercile_diff_d31_60": round(float(2 * np.sqrt(2) * E.car_31_60.std() / np.sqrt(len(E) / 3) * 100), 1)}
print(json.dumps(out, indent=0, default=str))
json.dump(out, open(f"research/is3/lht_{form}.json", "w"), indent=1, default=str)
