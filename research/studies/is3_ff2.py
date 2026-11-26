"""FF2 (a)(b): friday_follow on the excess move over the universe, and shorts only (notes.md FF2, pre-registered before this ran).
bn100 1h (survivorship-free). Cut T = close of the hour ending at H:00 New York (H in 12/15/17/20, tranches) on Friday; placebo Thursday / Saturday.
m = c(T)/c(T-24h)-1; U = equal-weight mean of m over the point-in-time top-N (30-d mean daily quote volume of the days before T, >= 30 days listed);
x = m - U. (a) follow sign(x) for |x| >= thr: outcome side * (r(T->T+24h) - U_fwd). (b) shorts only: raw m <= -thr, outcome -(r_fwd) and hedged -(r_fwd - U_fwd).
    PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_ff2 [confirm]"""
import json, sys
import numpy as np
import pandas as pd
from kripto import data
from kripto.data import BN100_DIR

CUTS = (12, 15, 17, 20)
DOW = {"Thu": 3, "Fri": 4, "Sat": 5}
COST = 14e-4


def times(lo, hi):
    hrs = pd.date_range(lo, hi, freq="1h", tz="America/New_York")
    out = {}
    for d, k in DOW.items():
        out[d] = hrs[(hrs.day_of_week == k) & hrs.hour.isin(CUTS)].tz_convert("UTC")
    return out


def load(T_all):
    tf = data.bn_tradfi()
    need = T_all.union(T_all - pd.Timedelta(hours=24)).union(T_all + pd.Timedelta(hours=24))
    px, dv = {}, {}
    for f in sorted(BN100_DIR.glob("*.parquet")):
        sym = f.stem; coin = sym.removesuffix("USDT")
        df = pd.read_parquet(f, columns=["t", "c", "qv"])
        t = df["t"].where(df["t"] < 1e14, df["t"] // 1000)
        df.index = pd.to_datetime(t, unit="ms", utc=True)
        df = data.drop_tradfi(df[~df.index.duplicated()], sym, tf)
        if df.empty:
            continue
        s = pd.Series(df["c"].to_numpy(), df.index + pd.Timedelta(hours=1))      # price at the hour's close
        s = s.where(df["qv"].to_numpy() > 0)
        px[coin] = s.reindex(need).astype("float32")
        dv[coin] = df["qv"].resample("1D").sum().astype("float32")
    P = pd.DataFrame(px)
    D = pd.DataFrame(dv).sort_index()
    D = D.where(D > 0)
    adv = D.rolling(30, min_periods=30).mean().shift(1)        # known before the day of T
    return P, adv


def events(P, adv, T, top):
    rows = []
    rk = adv.rank(axis=1, ascending=False)
    for t in T:
        day = t.floor("D")
        if day not in rk.index:
            continue
        mem = rk.loc[day] <= top
        c0, cm, c1 = P.loc[t - pd.Timedelta(hours=24)], P.loc[t], P.loc[t + pd.Timedelta(hours=24)]
        m = (cm / c0 - 1)[mem].dropna(); f = (c1 / cm - 1)[mem].reindex(m.index)
        ok = f.notna()
        m, f = m[ok], f[ok]
        if len(m) < 10:
            continue
        U, Uf = m.mean(), f.mean()
        rows.append(pd.DataFrame({"t": t, "coin": m.index, "m": m.values, "x": (m - U).values, "f": f.values, "fh": (f - Uf).values}))
    return pd.concat(rows, ignore_index=True)


def summ(e, side, col):
    if len(e) == 0:
        return {"n": 0}
    o = side * e[col]
    wk = o.groupby(e["t"].dt.to_period("W")).mean()
    t = float(wk.mean() / wk.std() * np.sqrt(len(wk))) if len(wk) > 2 else np.nan
    yrs = o.groupby(e["t"].dt.year).mean() * 1e4
    return {"n": int(len(e)), "weeks": int(len(wk)), "gross_bp": round(float(o.mean() * 1e4), 1), "med_bp": round(float(o.median() * 1e4), 1),
            "t_week": round(t, 2), "net_bp": round(float((o.mean() - COST) * 1e4), 1), "years": {int(k): round(float(v), 1) for k, v in yrs.items()}}


def main():
    conf = "confirm" in sys.argv
    lo, hi = ("2024-01-01", "2026-10-31") if conf else ("2020-02-15", "2023-12-31")
    TT = times(lo, hi)
    T_all = TT["Thu"].union(TT["Fri"]).union(TT["Sat"])
    P, adv = load(T_all)
    print(f"bn100 coins {P.shape[1]}, window {lo}..{hi}", flush=True)
    res = {}
    for top in (30, 100):
        for d, T in TT.items():
            e = events(P, adv, T, top)
            for thr in (0.02, 0.03, 0.04):
                up, dn = e[e.x >= thr], e[e.x <= -thr]
                a = pd.concat([up.assign(s=1), dn.assign(s=-1)])
                a["o"] = a["s"] * a["fh"]
                res[f"top{top} {d} a excess>={thr:.0%} follow hedged"] = summ(a.assign(one=a["o"]), 1, "one")
                res[f"top{top} {d} b short raw m<=-{thr:.0%} unhedged"] = summ(e[e.m <= -thr], -1, "f")
                res[f"top{top} {d} b short raw m<=-{thr:.0%} hedged"] = summ(e[e.m <= -thr], -1, "fh")
                res[f"top{top} {d} b' short excess x<=-{thr:.0%} hedged"] = summ(dn, -1, "fh")
                ab = pd.concat([e[e.m >= thr].assign(s=1), e[e.m <= -thr].assign(s=-1)])
                res[f"top{top} {d} ref abs m>={thr:.0%} follow unhedged"] = summ(ab.assign(one=ab.s * ab.f), 1, "one")
                res[f"top{top} {d} ref abs m>={thr:.0%} LONG only unhedged"] = summ(e[e.m >= thr], 1, "f")
            if d == "Fri":
                q = pd.qcut(e["x"], 10, labels=False)
                dose = e.groupby(q).agg(x_mid=("x", "median"), fh_bp=("fh", lambda z: z.mean() * 1e4), n=("fh", "size"))
                print(f"\ntop{top} Friday dose (excess-move decile -> next-24h hedged return, bp):\n" + dose.round(2).to_string(), flush=True)
                res[f"top{top} Fri dose"] = dose.round(3).to_dict()
    for k, v in res.items():
        if v is not None and "dose" not in k:
            print(f"{k:48s} {v}", flush=True)
    json.dump({"study": "research/studies/is3_ff2.py", "window": [lo, hi], "res": {k: v for k, v in res.items() if v is not None}},
              open(f"research/is3/ff2_{'confirm' if conf else 'explore'}.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
