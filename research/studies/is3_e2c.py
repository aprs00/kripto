"""InSilico pass 3, E2C: flow@bn (lookback 3, cap .05) with the daily decision anchored at 00 / 16 / 20 UTC. Descriptive, NOT registered.

  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_e2c a     # -> research/is3/e2c_a.json

Prices/volume: bn100 1h (survivorship-free, as is3_e2b) restricted to coins with metrics_full. Hourly taker buy ~ qv_h x mean over the hour's 5-min bars of
taker_ls/(1+taker_ls) (taker_ls = buy/sell taker volume ratio). A day needs all 24 hourly values, else NaN. Known answer: the 00-anchor approximate panel vs the
true daily taker split (klines_1d_all tbqv): imbalance correlation and flow SR side by side.
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
import pandas as pd

from kripto import backtest as bt
from kripto import data
from kripto.data import BN100_DIR, DATA
from kripto.strategies import REGISTRY

warnings.filterwarnings("ignore")
EV = DATA.parent / "research" / "is3"
ANCH = (0, 4, 8, 12, 16, 20)
MET = DATA / "bn" / "metrics_full"
PARAMS = {"lookback": 3, "cap": 0.05}


def panels():
    tf = data.bn_tradfi()
    keys = ("close", "volume", "taker_buy", "funding")
    acc = {h: {k: {} for k in keys} for h in ANCH}
    true_tb = {}
    for f in sorted(BN100_DIR.glob("*.parquet")):
        sym = f.stem; coin = sym.removesuffix("USDT")
        mf = MET / f"{sym}.parquet"
        if not mf.exists():
            continue
        df = pd.read_parquet(f, columns=["t", "c", "qv"])
        t = df["t"].where(df["t"] < 1e14, df["t"] // 1000)
        df.index = pd.to_datetime(t, unit="ms", utc=True)
        df = data.drop_tradfi(df[~df.index.duplicated()], sym, tf)
        df = df[df.index >= "2021-12-01"]
        if df.empty:
            continue
        m = pd.read_parquet(mf, columns=["t", "taker_ls"])
        m = m[np.isfinite(m["taker_ls"]) & (m["taker_ls"] > 0)]
        s = (m["taker_ls"] / (1 + m["taker_ls"])).groupby(pd.DatetimeIndex(m["t"]).floor("1h")).mean()
        df["tb"] = df["qv"] * s.reindex(df.index)
        fp = DATA / "bn" / "funding_all" / f"{sym}.parquet"
        fr = pd.read_parquet(fp) if fp.exists() else None
        for h in ANCH:
            sh = df.set_axis(df.index - pd.Timedelta(hours=h))
            r = sh.resample("1D")
            c_, v_ = r["c"].last(), r["qv"].sum()
            tb_ = r["tb"].sum(min_count=24).where(r["tb"].count() == 24)
            for x in (c_, v_, tb_):
                x.index = x.index + pd.Timedelta(hours=h)
            if coin == "BTC":
                L = c_.index[100]; assert c_.iloc[100] == df["c"].get(L + pd.Timedelta(hours=23)), (h, L)
            acc[h]["close"][coin] = c_.astype("float32"); acc[h]["volume"][coin] = v_.astype("float32"); acc[h]["taker_buy"][coin] = tb_.astype("float32")
            if fr is not None:
                ts = (pd.to_datetime(fr["time"] - 1, unit="ms", utc=True) - pd.Timedelta(hours=h)).dt.floor("1D") + pd.Timedelta(hours=h)
                acc[h]["funding"][coin] = fr.groupby(ts)["fundingRate"].sum().astype("float32")
        kd = DATA / "bn" / "klines_1d_all" / f"{sym}.parquet"
        if kd.exists():
            k = pd.read_parquet(kd, columns=["t", "tbqv", "qv"])
            tt = k["t"].where(k["t"] < 1e14, k["t"] // 1000)
            true_tb[coin] = pd.Series(k["tbqv"].to_numpy(float), pd.to_datetime(tt, unit="ms", utc=True))
    out = {}
    for h in ANCH:
        c = pd.DataFrame(acc[h]["close"]).sort_index()
        v = pd.DataFrame(acc[h]["volume"]).reindex(c.index); v = v.where(v > 0)
        out[h] = {"close": c.where(v.notna()), "volume": v,
                  "taker_buy": pd.DataFrame(acc[h]["taker_buy"]).reindex(index=c.index, columns=c.columns),
                  "funding": pd.DataFrame(acc[h]["funding"]).reindex(index=c.index, columns=c.columns)}
    tt = pd.DataFrame({k: v[~v.index.duplicated()] for k, v in true_tb.items()}).reindex(index=out[0]["close"].index, columns=out[0]["close"].columns)
    return out, tt


def run(p):
    w = REGISTRY["flow"](p, **PARAMS)
    slip = bt.slippage_model(p["volume"], 1)
    return bt.run(w, p["close"], p["funding"], slip, fee=5e-4), w


def yearly(res, start="2022-01-01", end="2026-11-01"):
    r = res.returns.loc[start:end]; g = (res.returns + res.costs).loc[start:end]
    sr = lambda x: round(float(x.mean() / x.std() * np.sqrt(365)), 2) if x.std() > 0 else None
    return {"sr": sr(r), "years": {int(y): [sr(x), round(float(x.mean() * 365 * 100), 1), round(float(g[g.index.year == y].mean() * 365 * 100), 1)]
                                   for y, x in r.groupby(r.index.year)}}


def form_a():
    P, tt = panels()
    p0 = P[0]
    # known answer: approximate vs true daily taker split at the 00 anchor
    v = p0["volume"]
    ia, it = (2 * p0["taker_buy"] - v) / v, (2 * tt - v) / v
    ia, it = ia.replace([np.inf, -np.inf], np.nan), it.replace([np.inf, -np.inf], np.nan)
    ok = ia.notna() & it.notna() & (ia.abs() <= 1) & (it.abs() <= 1)
    out = {"coins": int(p0["close"].shape[1]),
           "imb_corr_pooled": round(float(np.corrcoef(ia[ok].stack(), it[ok].stack())[0, 1]), 3),
           "imb_xs_rank_corr_median": round(float(ia.where(ok).rank(axis=1).corrwith(it.where(ok).rank(axis=1), axis=1).median()), 3)}
    ptrue = dict(p0, taker_buy=tt.where(p0["taker_buy"].notna()))
    rt, _ = run(ptrue)
    out["true00"] = yearly(rt)
    print("known answer", {k: out[k] for k in ("coins", "imb_corr_pooled", "imb_xs_rank_corr_median")}, "true00", out["true00"], flush=True)
    base = None
    for h in ANCH:
        res, w = run(P[h])
        out[f"approx{h:02d}"] = yearly(res)
        r = res.returns.loc["2022-01-01":"2026-11-01"].copy(); r.index = (r.index + pd.Timedelta(hours=h)).floor("D")
        if h == 0:
            base = r
        else:
            d = (r - base).dropna()
            out[f"approx{h:02d}"]["corr_vs_00"] = round(float(r.corr(base)), 3)
            out[f"approx{h:02d}"]["diff_bp_yr_by_year"] = {int(y): round(float(x.mean() * 365 * 1e4), 0) for y, x in d.groupby(d.index.year)}
        print(h, out[f"approx{h:02d}"], flush=True)
    json.dump(out, open(EV / "e2c_a.json", "w"), indent=1)


def form_b():
    """Break execution on flow@bn's own daily target changes (raw, no band), decided at anchor H close T = label + 24 h.
    (1) sell deferral: gain = -dw_sell * r(B -> B+1h), B = 17:00 New York on T's NY date; placebo = the same 1-h sell deferral starting at every other NY hour.
    (2) delay: moving ALL trades from T to B costs -dw * r(T -> B) (per unit turnover). Per year, bp per unit."""
    from research.studies.is3_e2b import hourly
    P, _ = panels()
    out = {}
    hp = None
    for h in (16, 20):
        w = REGISTRY["flow"](P[h], **PARAMS).fillna(0.0)
        dw = w.diff().loc["2022-01-01":"2026-10-31"]
        dw = dw.loc[:, dw.abs().sum() > 0]
        if hp is None:
            hp = hourly(list(P[0]["close"].columns))
        T = dw.index + pd.Timedelta(hours=24)
        ny = T.tz_convert("America/New_York").normalize()
        res = {}
        for H in range(24):
            B = (ny + pd.Timedelta(hours=H)).tz_convert("UTC")
            B = B.where(B >= T, B + pd.Timedelta(days=1))          # the first NY hour H at or after the decision
            g = pd.Series(0.0, dw.index); sold = pd.Series(0.0, dw.index); dl = pd.Series(0.0, dw.index); turn = pd.Series(0.0, dw.index)
            for coin in dw.columns:
                if coin not in hp:
                    continue
                sr_ = hp[coin]
                pT, pB, pB1 = (sr_.reindex(x).to_numpy() for x in (T, B, B + pd.Timedelta(hours=1)))
                d = dw[coin].to_numpy()
                r1, rd = pB1 / pB - 1, pB / pT - 1
                ok1, okd = np.isfinite(r1), np.isfinite(rd)
                sm = ok1 & (d < 0)
                g += np.where(sm, -d * np.nan_to_num(r1), 0.0); sold += np.where(sm, -d, 0.0)
                dl += np.where(okd, -d * np.nan_to_num(rd), 0.0); turn += np.where(okd, np.abs(d), 0.0)
            yr = lambda a, b: {int(y): round(float(a[a.index.year == y].sum() / b[b.index.year == y].sum() * 1e4), 2) for y in range(2022, 2027)}
            res[H] = {"sell_defer_bp": round(float(g.sum() / sold.sum() * 1e4), 2), "sell_defer_by_year": yr(g, sold),
                      "t": round(float(g.mean() / g.std() * np.sqrt(len(g))), 2), "delay_bp": round(float(dl.sum() / turn.sum() * 1e4), 2), "delay_by_year": yr(dl, turn),
                      "turn_yr": round(float(turn.sum() / (len(turn) / 365)), 1)}
        pl = np.array([res[H]["sell_defer_bp"] for H in range(24) if H != 17])
        out[h] = {"break17": res[17], "placebo_mean": round(float(pl.mean()), 2), "placebo_rank_of_17": int((pl < res[17]["sell_defer_bp"]).sum()), "of": len(pl),
                  "all_hours": {H: [res[H]["sell_defer_bp"], res[H]["delay_bp"]] for H in range(24)}}
        print(h, json.dumps({k: v for k, v in out[h].items() if k != "all_hours"}), flush=True)
    json.dump(out, open(EV / "e2c_b.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": form_a, "b": form_b}[sys.argv[1]]()
