"""InSilico pass 3, L6V: range / HAR vol forecasts (library N6). Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_l6v a    # forecast accuracy of next-7-d realized vol, bnall 1d, top-100 point-in-time, 2021-23 -> research/is3/l6v_a.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data
from research.studies import is3_lib as L

H = 7


def run_a():
    p = data.load_panel("bnall", "1d")
    c, h, l, v = p["close"], p["high"], p["low"], p["volume"]
    r = np.log(c / c.shift(1))
    pk = (np.log(h / l) ** 2) / (4 * np.log(2))                       # Parkinson daily variance
    pk = pk.where(np.isfinite(pk) & (pk > 0))
    top = v.rolling(30, min_periods=10).mean().rank(axis=1, ascending=False) <= 100
    liq = v.rolling(30, min_periods=10).mean().where(top).rank(axis=1, ascending=False)
    # target: realized variance over t+1..t+7 (daily close-to-close, mean of r^2)
    fut = (r ** 2).rolling(H, min_periods=H).mean().shift(-H)
    F = {"cc20": (r ** 2).rolling(20, min_periods=15).mean(), "cc60": (r ** 2).rolling(60, min_periods=40).mean(),
         "ewm20": (r ** 2).ewm(halflife=20, min_periods=15).mean(), "pk20": pk.rolling(20, min_periods=15).mean(), "pk5": pk.rolling(5, min_periods=4).mean()}
    # HAR on Parkinson (log space), pooled fit on 2021-22, liquid top-100 cells only
    lw = {"d": np.log(pk), "w": np.log(pk.rolling(5, min_periods=4).mean()), "m": np.log(pk.rolling(22, min_periods=15).mean())}
    y = np.log(fut)
    mask = top & np.isfinite(y)
    def stack(df):
        return df.where(mask).stack()
    X = pd.concat({k: stack(x) for k, x in lw.items()}, axis=1).join(stack(y).rename("y"), how="inner").dropna()
    tr = X[X.index.get_level_values(0) < pd.Timestamp("2023-01-01", tz="UTC")]
    tr = tr[tr.index.get_level_values(0) >= pd.Timestamp("2021-01-01", tz="UTC")]
    A = np.column_stack([np.ones(len(tr)), tr.d, tr.w, tr.m])
    beta = np.linalg.lstsq(A, tr.y.to_numpy(), rcond=None)[0]
    resid_var = float(np.var(tr.y.to_numpy() - A @ beta))
    har = np.exp(beta[0] + beta[1] * lw["d"] + beta[2] * lw["w"] + beta[3] * lw["m"] + resid_var / 2)
    F["har_pk"] = har
    print("HAR beta (const, d, w, m):", beta.round(3), "resid var", round(resid_var, 3), flush=True)
    # constant scale per estimator fitted on 2021-22 (median ratio), applied to 2023
    out = {"har_beta": beta.round(4).tolist()}
    rows = []
    for nm, f in F.items():
        d = pd.concat({"f": f.where(mask).stack(), "y": fut.where(mask).stack(), "liq": liq.where(mask).stack()}, axis=1).dropna()
        d = d[(d.f > 0) & (d.y > 0)]
        t = d.index.get_level_values(0)
        fit = d[(t >= pd.Timestamp("2021-01-01", tz="UTC")) & (t < pd.Timestamp("2023-01-01", tz="UTC"))]
        k = float(np.exp(np.median(np.log(fit.y / fit.f))))
        for scaled in (False, True):
            for yr in (2021, 2022, 2023):
                g = d[t.year == yr]
                ff = g.f * (k if scaled else 1.0)
                q = g.y / ff
                ql = q - np.log(q) - 1
                le = np.abs(0.5 * np.log(ff / g.y))
                for tl, gg in ((0, g.liq <= 33), (1, (g.liq > 33) & (g.liq <= 66)), (2, g.liq > 66), (-1, g.liq > 0)):
                    rows.append({"est": nm, "scaled": scaled, "k": round(k, 3), "year": yr, "liq": tl, "n": int(gg.sum()),
                                 "qlike": float(ql[gg].mean()), "qlike_med": float(ql[gg].median()), "abs_log_vol_err": float(le[gg].mean())})
    T = pd.DataFrame(rows)
    piv = T[T.liq == -1].pivot_table(index=["est", "scaled"], columns="year", values="qlike").round(4)
    print(piv.to_string(), flush=True)
    piv2 = T[(T.year == 2023) & T.scaled].pivot_table(index="est", columns="liq", values="qlike").round(4)
    print("2023 scaled, by liquidity tercile (0 = most liquid, -1 = all):\n" + piv2.to_string(), flush=True)
    out["table"] = T.round(5).to_dict("records")
    (L.OUT / "l6v_a.json").write_text(json.dumps(out, indent=1, default=float))




def make_vt(var_df):
    """vol_target with the per-coin variances on the diagonal taken from var_df (annualised), correlations from the same trailing 60-d window."""
    from kripto import strategies as S

    def vt(w, panel, target, lookback_days=60, max_gross=3.0):
        r = S.returns(panel).fillna(0.0)
        bpd = S.bars_per_day(r.index)
        lb = lookback_days * bpd
        out = w.copy()
        R, Wn = r.to_numpy(), w.to_numpy()
        V = var_df.reindex(index=w.index, columns=w.columns).to_numpy()
        for i in range(len(w)):
            row = Wn[i]
            if not np.isfinite(row).any():
                continue
            row = np.nan_to_num(row)
            nz = np.flatnonzero(row)
            if len(nz) == 0 or i < bpd * 20:
                out.iloc[i] = 0.0 if i < bpd * 20 else row
                continue
            sub = R[max(0, i - lb + 1): i + 1][:, nz]
            cov = np.atleast_2d(np.cov(sub, rowvar=False) * 365 * bpd)
            sd = np.sqrt(np.clip(np.diag(cov), 1e-12, None))
            v = V[i, nz]
            v = np.where(np.isfinite(v) & (v > 0), v, sd ** 2)
            corr = cov / np.outer(sd, sd)
            cov2 = corr * np.outer(np.sqrt(v), np.sqrt(v))
            pv = float(np.sqrt(max(row[nz] @ cov2 @ row[nz], 1e-12)))
            scaled = row * (target / pv)
            g = np.abs(scaled).sum()
            if g > max_gross:
                scaled *= max_gross / g
            out.iloc[i] = scaled
        return out
    return vt


def track(ret, target, lo, hi):
    r = ret[(ret.index >= lo) & (ret.index < hi)]
    q = r.groupby(r.index.to_period("Q")).std() * np.sqrt(365)
    m = r.groupby(r.index.to_period("M")).sum()
    rv30 = r.rolling(30).std() * np.sqrt(365)
    return {"sr": round(float(r.mean() / r.std() * np.sqrt(365)), 3), "vol": round(float(r.std() * np.sqrt(365)), 4),
            "te_log_q": round(float(np.sqrt(np.mean(np.log(q / target) ** 2))), 4), "q_vol_min_max": [round(float(q.min()), 3), round(float(q.max()), 3)],
            "rv30_p95": round(float(rv30.quantile(0.95)), 3), "worst_month": round(float(m.min()), 4), "worst_day": round(float(r.min()), 4),
            "q_vols": [round(float(x), 3) for x in q]}


def run_b(sample="explore"):
    from kripto import backtest as bt
    from kripto import strategies as S
    from kripto.research import bars_per_day, default_band
    p = data.load_panel("bnall", "1d")
    c, h, l = p["close"], p["high"], p["low"]
    r = np.log(c / c.shift(1))
    pk = ((np.log(h / l) ** 2) / (4 * np.log(2))).where(lambda x: np.isfinite(x) & (x > 0))
    beta = json.loads((L.OUT / "l6v_a.json").read_text())["har_beta"]
    lw = [np.log(pk), np.log(pk.rolling(5, min_periods=4).mean()), np.log(pk.rolling(22, min_periods=15).mean())]
    har = np.exp(beta[0] + beta[1] * lw[0] + beta[2] * lw[1] + beta[3] * lw[2] + 0.88 / 2) * 365
    ests = {"cc60": None, "ewm20": (r ** 2).ewm(halflife=20, min_periods=15).mean() * 365, "har_pk": har}
    lo, hi = (pd.Timestamp(x, tz="UTC") for x in L.SAMPLES[sample])
    slip = bt.slippage_model(p["volume"], bars_per_day(c.index))
    books = {"blend_bn": ("blend", {"components": {"carry_trend": {}, "carry": {}, "xsmom": {}}}, 0.25), "tsmom_bn": ("tsmom", {}, None), "xsmom_bn": ("xsmom", {}, None)}
    orig = S.vol_target
    out = {}
    for bn, (s, prm, tv) in books.items():
        import inspect
        tv = tv or inspect.signature(S.REGISTRY[s]).parameters["target_vol"].default
        out[bn] = {}
        for en, var in ests.items():
            S.vol_target = orig if var is None else make_vt(var)
            try:
                w = S.REGISTRY[s](p, **prm)
            finally:
                S.vol_target = orig
            res = bt.run(w, c, p.get("funding"), slip, band=default_band())
            out[bn][en] = track(res.returns, tv, lo, hi) | {"turnover_yr": round(float(res.turnover[(res.turnover.index >= lo) & (res.turnover.index < hi)].sum() / ((hi - lo).days / 365)), 1)}
            x = out[bn][en]
            print(f"{bn:9s} {en:6s} target {tv} | SR {x['sr']:+.2f} vol {x['vol']:.3f} TE(log, quarterly) {x['te_log_q']:.3f} q-vol {x['q_vol_min_max']} rv30 p95 {x['rv30_p95']} "
                  f"worst month {x['worst_month']:+.3f} day {x['worst_day']:+.3f} turnover {x['turnover_yr']}", flush=True)
    (L.OUT / f"l6v_b_{sample}.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    {"a": run_a, "b": run_b}[sys.argv[1]](*sys.argv[2:])
