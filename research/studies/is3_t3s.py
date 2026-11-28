"""T3S: HL - Binance funding spread (trailing 7-d mean) as a cross-sectional signal for the coin's next 1/3/7-d HL simple return. Explore 2023-05..2025-03 only
(confirm 2025-04..2026-11 untouched unless a/b pass and a prereg is committed). Placebo: spread shuffled across coins within each day. Not registered.
PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_t3s [explore|confirm] -> research/is3/t3s_<sample>.json"""
import json, sys
import numpy as np, pandas as pd
from kripto import data

SAMPLE = sys.argv[1] if len(sys.argv) > 1 else "explore"
LO, HI = {"explore": ("2023-05-15", "2025-04-01"), "confirm": ("2025-04-01", "2026-11-22")}[SAMPLE]
p = data.load_panel("pair", "1d")
c, f = p["close"], p["funding"]
hl = [x for x in c.columns if x.endswith("@hl") and x[:-3] + "@bn" in c.columns]
bn = [x[:-3] + "@bn" for x in hl]
coins = [x[:-3] for x in hl]
C = c[hl].set_axis(coins, axis=1)
FH, FB = f[hl].set_axis(coins, axis=1), f[bn].set_axis(coins, axis=1)
spread = (FH - FB).rolling(7, min_periods=5).mean()          # known at day t's close
fhl = FH.rolling(7, min_periods=5).mean()
r7 = C / C.shift(7) - 1
dv = (p["volume"][hl].set_axis(coins, axis=1)).rolling(30, min_periods=10).median()
elig = spread.notna() & C.notna() & (dv > 1e6) & fhl.notna() & r7.notna()
fwd = {h: C.shift(-h) / C - 1 for h in (1, 3, 7)}            # simple return from t's close to t+h's close
idx = C.index[(C.index >= pd.Timestamp(LO, tz="UTC")) & (C.index < pd.Timestamp(HI, tz="UTC"))]


def nw_t(x, L):
    x = pd.Series(x).dropna(); n = len(x); m = x.mean(); e = x - m; v = float((e * e).mean())
    for l in range(1, L + 1):
        v += 2 * (1 - l / (L + 1)) * float((e[l:].to_numpy() * e[:-l].to_numpy()).mean())
    return float(m / np.sqrt(v / n)), n


def rank(df):
    return df.rank(axis=1)


def resid(y, Xs):
    """per-day cross-sectional OLS residual of y on the columns of Xs (ranks)."""
    out = pd.DataFrame(np.nan, y.index, y.columns)
    for t in y.index:
        yy = y.loc[t]; X = pd.concat([x.loc[t] for x in Xs], axis=1); m = yy.notna() & X.notna().all(axis=1)
        if m.sum() < 15:
            continue
        A = np.c_[np.ones(m.sum()), X[m].to_numpy()]; b = np.linalg.lstsq(A, yy[m].to_numpy(), rcond=None)[0]
        out.loc[t, m[m].index] = yy[m].to_numpy() - A @ b
    return out


def ic(x, h, rng=None):
    xs = x.where(elig).loc[idx]; ys = fwd[h].where(elig).loc[idx]
    if rng is not None:                                          # placebo: shuffle x across coins within each day
        X = xs.to_numpy().copy()
        for k in range(len(X)):
            m = np.isfinite(X[k]); X[k, m] = rng.permutation(X[k, m])
        xs = pd.DataFrame(X, xs.index, xs.columns)
    xr, yr = rank(xs), rank(ys)
    vals = []
    for t in idx:
        a, b = xr.loc[t], yr.loc[t]; m = a.notna() & b.notna()
        if m.sum() >= 15:
            vals.append(np.corrcoef(a[m], b[m])[0, 1])
    t_, n = nw_t(vals, max(h, 3))
    return {"ic": round(float(np.mean(vals)), 4), "t_nw": round(t_, 2), "days": n, "n_coins": round(float(elig.loc[idx].sum(axis=1).mean()), 1),
            "mde_ic": round(2 * float(np.std(vals)) / np.sqrt(n / max(h, 1)), 4)}


out = {"sample": SAMPLE, "lo": LO, "hi": HI}
for h in (1, 3, 7):
    out[f"ic_h{h}"] = ic(spread, h)
    out[f"placebo_h{h}"] = ic(spread, h, np.random.default_rng(h))
    print(h, out[f"ic_h{h}"], out[f"placebo_h{h}"], flush=True)
# b: partial IC controlling for the HL funding level and the 7-d return (ranks), and quintile dose-response for h=3
sp_r = resid(rank(spread.where(elig)).loc[idx], [rank(fhl.where(elig)).loc[idx], rank(r7.where(elig)).loc[idx]])
for h in (1, 3, 7):
    out[f"partial_ic_h{h}"] = ic(sp_r.reindex(C.index), h)
    out[f"fundlevel_ic_h{h}"] = ic(fhl, h)
print("partial", {h: out[f"partial_ic_h{h}"] for h in (1, 3, 7)}, flush=True)
q = rank(spread.where(elig)).loc[idx].div(elig.loc[idx].sum(axis=1), axis=0)
y3 = fwd[3].where(elig).loc[idx]; y3 = y3.sub(y3.mean(axis=1), axis=0)
bins = np.ceil(q * 5).clip(1, 5)
qt = {}
for k in range(1, 6):
    per_day = y3.where(bins == k).mean(axis=1).dropna()
    qt[k] = {"mean_bp": round(float(per_day.mean() * 1e4), 1), "t_nw": round(nw_t(per_day, 3)[0], 2)}
out["quintiles_h3_demeaned"] = qt
sp = spread.where(elig).loc[idx]
out["spread_ann_pct"] = {"p10": round(float(np.nanpercentile(sp.to_numpy(), 10) * 365 * 100), 1), "p50": round(float(np.nanpercentile(sp.to_numpy(), 50) * 365 * 100), 1),
                         "p90": round(float(np.nanpercentile(sp.to_numpy(), 90) * 365 * 100), 1)}
print(json.dumps(qt), out["spread_ann_pct"], flush=True)
json.dump(out, open(f"research/is3/t3s_{SAMPLE}.json", "w"), indent=1)
