"""LFV: listing venue order. (a) HL listings 2023-03-28..2024-12-31 split by when the coin first traded on Binance perps (bnall): BN-first (> 1 d before), same (+-1 d),
HL-first / never on BN. Abnormal simple return (coin - BTC), summed, entry at the close of day 1 (listing_short skip 1), buckets d2-15 / d16-30 / d31-60, min dv $1M at entry.
(b) bnall listings 2020-23 by first-week dollar volume rank (tercile within the calendar year): same buckets. Descriptive, NOT registered. Explore samples only.
PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_lfv -> research/is3/lfv_ab.json"""
import json
import numpy as np, pandas as pd
from kripto import data, strategies as S

B = ((2, 15), (16, 30), (31, 60))
rng = np.random.default_rng(7)


def events(p, lo, hi):
    c, v = p["close"], p["volume"]
    r = c.pct_change(fill_method=None); ab = r.sub(r["BTC"], axis=0)
    traded = (v.fillna(0) > 0) & c.notna(); first = traded.idxmax().where(traded.any())
    t_cut = traded.any(axis=1).idxmax() + pd.Timedelta(days=30); dv = S.dollar_volume(p)
    rows = []
    for coin, t0 in first.dropna().items():
        if coin == "BTC" or t0 < max(t_cut, pd.Timestamp(lo, tz="UTC")) or t0 >= pd.Timestamp(hi, tz="UTC"):
            continue
        i0 = c.index.get_loc(t0) + 1
        if i0 + 61 > len(c) or not (dv[coin].iloc[i0] >= 1e6):
            continue
        a = ab[coin].iloc[i0 + 1:i0 + 61].fillna(0.0).to_numpy()     # day 2..61 after the first traded day = held from the close of day 1
        o = {"coin": coin, "t0": t0, "dv7_entry": float(dv[coin].iloc[i0]), "first_week_dv": float((c[coin] * v[coin]).iloc[i0 - 1:i0 + 6].mean())}
        for a0, a1 in B:
            o[f"car_{a0}_{a1}"] = float(a[a0 - 2:a1 - 1].sum())
        o["car_2_60"] = float(a.sum())
        rows.append(o)
    return pd.DataFrame(rows), first


def summ(df, key):
    out = {}
    for k, g in df.groupby(key):
        out[str(k)] = {"n": len(g), **{f"{col}_mean_pct": round(float(g[col].mean() * 100), 1) for col in g.columns if col.startswith("car_")},
                       **{f"{col}_median_pct": round(float(g[col].median() * 100), 1) for col in g.columns if col.startswith("car_")},
                       "front_share": round(float(g["car_2_15"].mean() + g["car_16_30"].mean()) / float(g["car_2_60"].mean()), 2) if g["car_2_60"].mean() != 0 else None}
    return out


def boot_diff(x, y, n=4000):
    d = [rng.choice(x, len(x)).mean() - rng.choice(y, len(y)).mean() for _ in range(n)]
    return [round(float(np.percentile(d, q)) * 100, 1) for q in (5, 50, 95)]


out = {}
hl = data.load_panel("hl", "1d"); E, _ = events(hl, "2023-01-01", "2025-01-01")
bn = data.load_panel("bnall", "1d"); vb = bn["volume"]; tb = (vb.fillna(0) > 0) & bn["close"].notna(); bfirst = tb.idxmax().where(tb.any())
bn_start = tb.any(axis=1).idxmax()


def cls(row):
    b = bfirst.get(data.hl_to_bn(row.coin))
    if b is None or pd.isna(b):
        return "hl_only"
    gap = (row.t0 - b).days
    return "bn_first" if gap > 1 else ("same" if gap >= -1 else "hl_first")


E["cls"] = E.apply(cls, axis=1)
E["new_to_perps"] = E.cls.isin(["same", "hl_first", "hl_only"])
out["a_hl_2023_24"] = summ(E, "cls"); out["a_hl_new_vs_bnfirst"] = summ(E, "new_to_perps")
x, y = E[E.new_to_perps], E[~E.new_to_perps]
out["a_diff_new_minus_bnfirst_ci90_pct"] = {col: boot_diff(x[col].to_numpy(), y[col].to_numpy()) for col in ("car_2_15", "car_16_30", "car_31_60", "car_2_60")}
out["a_events"] = E.assign(t0=E.t0.astype(str)).round(4).to_dict("records")
print(json.dumps({k: v for k, v in out.items() if k != "a_events"}, indent=0), flush=True)
del hl
# b: bnall 2020-23, first-week dollar volume tercile within the year
F, _ = events(bn, "2020-01-01", "2024-01-01")
F["yr"] = F.t0.dt.year
F["hot"] = F.groupby("yr").first_week_dv.transform(lambda s: pd.qcut(s.rank(method="first"), 3, labels=["quiet", "mid", "hot"])).astype(str)
out["b_bnall_2020_23"] = summ(F, "hot")
out["b_by_year_hot_minus_quiet_car_2_30_pct"] = {int(yv): round(float((g[g.hot == "hot"].car_2_15 + g[g.hot == "hot"].car_16_30).mean() - (g[g.hot == "quiet"].car_2_15 + g[g.hot == "quiet"].car_16_30).mean()) * 100, 1)
                                                 for yv, g in F.groupby("yr")}
out["b_diff_hot_minus_quiet_ci90_pct"] = {col: boot_diff(F[F.hot == "hot"][col].to_numpy(), F[F.hot == "quiet"][col].to_numpy()) for col in ("car_2_15", "car_16_30", "car_31_60", "car_2_60")}
print(json.dumps({k: out[k] for k in out if k.startswith("b_")}, indent=0), flush=True)
json.dump(out, open("research/is3/lfv_ab.json", "w"), indent=1, default=str)
