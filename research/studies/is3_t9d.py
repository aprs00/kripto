"""InSilico pass 3, T9D: would post-only orders fill PRB2's slow-leg daily gaps? Descriptive, NOT registered.

  nice -n 19 .venv/bin/python -m research.studies.is3_t9d a|b|c     # -> data/is3/t9d_<form>.json

Legs: is3_prl.legs on BN-82 1d (HL main book's legs, built on Binance where 1h history is long), slow legs tsmom + lowvol at lam .33 (PRB2).
Order at decision D = daily bar open + 1 d (bt.run trades w[t] at close[t]): dw = slow[t] - slow[t-1] per coin (per leg and netted 'net').
Resting post-only limit at L = close[t] * (1 -/+ off) (buy -/sell +). Filled within h hours only if a 1h bar opening in [D, D+h) TRADES THROUGH L
(buy: low < L; sell: high > L). No queue credit, no partial fills. Weight = |dw| (fraction of book).
Samples: explore = decisions in 2021-2023 (form a/b/c); confirm 2024-26 only if c saves >= 1 %/yr (not run here).
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from kripto import data
from research.studies.is3_prb import partial
from research.studies.is3_prl import legs

OUT = data.DATA / "is3"
EV = data.DATA.parent / "research" / "is3"   # evidence JSONs (tracked)
HS = (1, 4, 24)
OFFS = (0.0, 2e-4)
LAM = 0.33


def orders(start="2021-01-01", end="2024-01-01"):
    d = data.load_panel("bn", "1d")
    fin, _, err = legs(d)
    assert err < 1e-9, err
    slow = {n: partial(fin[n], LAM) for n in ("tsmom", "lowvol")}
    slow["net"] = slow["tsmom"] + slow["lowvol"]
    out = {}
    for n, w in slow.items():
        dw = w.diff().fillna(0.0)
        s = dw.stack()
        s = s[s.abs() > 1e-6]
        df = s.rename("dw").reset_index()
        df.columns = ["t", "coin", "dw"]
        df["D"] = df["t"] + pd.Timedelta(days=1)
        df = df[(df["D"] >= start) & (df["D"] < end)]
        df["L0"] = [d["close"].at[t, c] for t, c in zip(df["t"], df["coin"])]
        out[n] = df.reset_index(drop=True)
    return out, d


def fills(df, h1):
    """flags fill_<off>_<h>, plus signed returns from L0 to the close at D+24h and D+48h."""
    hi, lo, cl = h1["high"], h1["low"], h1["close"]
    idx = hi.index
    pos = idx.get_indexer(df["D"])
    assert (pos >= 0).all()
    ci = hi.columns.get_indexer(df["coin"])
    H, Lo, C = hi.to_numpy(), lo.to_numpy(), cl.to_numpy()
    side = np.sign(df["dw"].to_numpy())
    L0 = df["L0"].to_numpy()
    # known answer: the 1h close of the bar before D equals the daily close used as L0
    prev_close = C[pos - 1, ci]
    agree = float(np.nanmax(np.abs(prev_close / L0 - 1)))
    res = {}
    for off in OFFS:
        L = L0 * (1 - side * off)
        first = np.full(len(df), np.inf)
        for k in range(24):
            hk, lk = H[pos + k, ci], Lo[pos + k, ci]
            hit = np.where(side > 0, lk < L, hk > L)
            first = np.where(hit & ~np.isfinite(first), k + 1, first)
        for h in HS:
            res[f"f{int(off*1e4)}_{h}"] = first <= h
        res[f"first{int(off*1e4)}"] = first
    for hh in (24, 48):
        p = C[np.minimum(pos + hh - 1, len(C) - 1), ci]
        res[f"r{hh}"] = side * (p / L0 - 1)
    return pd.DataFrame(res, index=df.index), agree


def form_a():
    od, _ = orders()
    h1 = data.load_panel("bn", "1h")
    out = {}
    for n, df in od.items():
        f, agree = fills(df, h1)
        df = pd.concat([df, f], axis=1)
        df.to_parquet(OUT / f"t9d_orders_{n}.parquet")
        w = df["dw"].abs()
        row = {"n_orders": int(len(df)), "turnover_ann": float(w.sum() / 3), "L0_vs_1h_close_maxdiff": agree}
        for side, m in (("all", slice(None)), ("buy", df["dw"] > 0), ("sell", df["dw"] < 0)):
            sub, ww = df[m], w[m]
            row[side] = {k: round(float((ww * sub[k]).sum() / ww.sum()), 3) for k in f.columns if k.startswith("f")}
        row["by_year_f0_24"] = {int(y): round(float((w[g.index] * g["f0_24"]).sum() / w[g.index].sum()), 3)
                                for y, g in df.groupby(df["D"].dt.year)}
        out[n] = row
        print(n, json.dumps(row), flush=True)
    json.dump(out, open(EV / "t9d_a.json", "w"), indent=1)


QS = (0, 5, 10, 20)          # queue stress: a fill needs a trade-through of q bp beyond the limit
TAKER, MAKER = 5e-4, 2e-4    # Binance VIP0


def first_hit(df, h1, q):
    hi, lo = h1["high"].to_numpy(), h1["low"].to_numpy()
    pos = h1["high"].index.get_indexer(df["D"]); ci = h1["high"].columns.get_indexer(df["coin"])
    side = np.sign(df["dw"].to_numpy()); L = df["L0"].to_numpy() * (1 - side * q * 1e-4)
    first = np.full(len(df), np.inf)
    for k in range(24):
        hit = np.where(side > 0, lo[pos + k, ci] < L, hi[pos + k, ci] > L)
        first = np.where(hit & ~np.isfinite(first), k + 1, first)
    return first


def dayboot(v, w, day, reps=2000, seed=7):
    g = pd.DataFrame({"vw": v * w, "w": w, "d": day}).groupby("d")[["vw", "w"]].sum()
    a, b = g["vw"].to_numpy(), g["w"].to_numpy()
    rng = np.random.default_rng(seed); i = rng.integers(0, len(a), (reps, len(a)))
    bs = a[i].sum(1) / b[i].sum(1)
    return float(a.sum() / b.sum()), [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))]


def form_b():
    from kripto import backtest as bt
    d = data.load_panel("bn", "1d")
    slip = bt.slippage_model(d["volume"], 1)
    h1 = data.load_panel("bn", "1h")
    out = {}
    for n in ("net", "tsmom", "lowvol"):
        df = pd.read_parquet(OUT / f"t9d_orders_{n}.parquet")
        df = df[np.isfinite(df["r24"])]
        w = df["dw"].abs().to_numpy()
        sl = np.array([slip.at[t, c] for t, c in zip(df["t"], df["coin"])])
        sl = np.where(np.isfinite(sl), sl, 25e-4)
        r24 = df["r24"].to_numpy(); day = df["D"].dt.normalize().to_numpy()
        row = {"slip_bp_wmean": round(float((w * sl).sum() / w.sum() * 1e4), 2),
               "r24_all_bp": round(float((w * r24).sum() / w.sum() * 1e4), 1)}
        for q in QS:
            fh = first_hit(df, h1, q)
            f = fh <= 24
            m_f, ci_f = dayboot(r24[f], w[f], day[f])
            m_u, ci_u = dayboot(r24[~f], w[~f], day[~f]) if (~f).sum() > 30 else (float("nan"), None)
            save = np.where(f, TAKER + sl - MAKER, -r24)        # chase unfilled at D+24h as taker
            s_m, s_ci = dayboot(save, w, day)
            yr = {int(y): round(float((w[m] * save[m]).sum() / w[m].sum() * 1e4), 2)
                  for y in (2021, 2022, 2023) for m in [pd.DatetimeIndex(df["D"]).year == y]}
            row[f"q{q}"] = {"fill24": round(float(w[f].sum() / w.sum()), 3), "fill1h": round(float(w[fh <= 1].sum() / w.sum()), 3),
                            "r24_filled_bp": round(m_f * 1e4, 1), "r24_unfilled_bp": round(m_u * 1e4, 1),
                            "r24_unfilled_ci_bp": None if ci_u is None else [round(x * 1e4, 1) for x in ci_u],
                            "save_bp_per_unit": round(s_m * 1e4, 2), "save_ci_bp": [round(x * 1e4, 2) for x in s_ci],
                            "save_pct_yr": round(s_m * w.sum() / 3 * 100, 2), "save_bp_by_year": yr}
        out[n] = row
        print(n, json.dumps(row), flush=True)
    json.dump(out, open(EV / "t9d_b.json", "w"), indent=1)


def sim(W, px, fnd, slip, fb, fs, drift, mode, E=None, maker=MAKER, taker=TAKER):
    """daily book; mode taker | chase (unfilled pays drift + taker) | skip (unfilled dropped, gap carried) | env (taker beyond E, post the rest, skip unfilled)."""
    T, N = px.shape
    w = np.zeros(N); out_r, out_c, out_to = np.zeros(T), np.zeros(T), np.zeros(T)
    for t in range(T):
        r = px[t] / px[t - 1] - 1 if t else np.zeros(N)
        r = np.where(np.isfinite(r), r, 0.0)
        tot = float(w @ r) - float(w @ np.nan_to_num(fnd[t]))
        w = w * (1 + r) / (1 + tot)
        ok = np.isfinite(px[t])
        tgt = np.where(np.isfinite(W[t]) & ok, W[t], 0.0); tgt = np.where(ok, tgt, w)
        dw = tgt - w
        tc = taker + np.where(np.isfinite(slip[t]), slip[t], 25e-4)
        have = np.isfinite(fb[t]) & np.isfinite(drift[t])
        filled = np.where(dw > 0, fb[t] == 1, fs[t] == 1) & have
        if mode == "taker":
            c = np.abs(dw) * tc
        else:
            if mode == "env":
                Et = np.where(np.isfinite(E[t]), E[t], 0.0)
                tk = np.sign(dw) * np.clip(np.abs(dw) - Et, 0, None)
                mk = dw - tk
            else:
                tk, mk = np.where(have, 0.0, dw), np.where(have, dw, 0.0)
            c = np.abs(tk) * tc
            if mode == "chase":
                c = c + np.where(filled, np.abs(mk) * maker, np.abs(mk) * (tc + np.sign(mk) * np.nan_to_num(drift[t])))
            else:   # skip / env: unfilled maker part not done
                c = c + np.where(filled, np.abs(mk) * maker, 0.0)
                mk = np.where(filled, mk, 0.0)
            dw = tk + mk
        ct = float(c.sum())
        w = (w + dw) / (1 - ct); out_c[t] = ct; out_to[t] = np.abs(dw).sum()
        out_r[t] = (1 + tot) * (1 - ct) - 1
    return pd.DataFrame({"r": out_r, "c": out_c, "to": out_to})


def form_c(ds="bn", taker=TAKER, maker=MAKER, win=("2021-01-01", "2023-12-31"), yrs=(2021, 2022, 2023), tag="c", slip_mult=1.0):
    from kripto import backtest as bt
    d = data.load_panel(ds, "1d")
    fin, _, err = legs(d)
    S = partial(fin["tsmom"] + fin["lowvol"], LAM)
    cols, idx = S.columns, S.index
    px = d["close"].reindex(columns=cols).to_numpy(float); fnd = d["funding"].reindex(index=idx, columns=cols).to_numpy(float)
    slip = bt.slippage_model(d["volume"], 1).reindex(index=idx, columns=cols).to_numpy(float) * slip_mult
    h1 = data.load_panel(ds, "1h")
    mn = (h1["low"].rolling(24, min_periods=24).min().shift(-23)).reindex(columns=cols)
    mx = (h1["high"].rolling(24, min_periods=24).max().shift(-23)).reindex(columns=cols)
    D = idx + pd.Timedelta(days=1)
    mn, mx = mn.reindex(D).to_numpy(float) / px, mx.reindex(D).to_numpy(float) / px
    drift = d["close"].reindex(columns=cols).shift(-1).to_numpy(float) / px - 1
    E = S.diff().abs().rolling(20, min_periods=5).mean().shift(1).to_numpy(float)   # 1 x trailing mean daily step, known at t
    W = S.to_numpy(float)
    # known answer: my taker loop == bt.run(S, band 0); my skip == bt.run maker skip_unfilled
    ref = bt.run(S, d["close"], d["funding"], bt.slippage_model(d["volume"], 1) * slip_mult, fee=taker)
    mine = sim(W, px, fnd, slip, mn * 0, mn * 0, drift, "taker", taker=taker)
    chk = {"taker_vs_btrun_maxdiff": float(np.abs(mine["r"].to_numpy() - ref.returns.to_numpy()).max())}
    q = 0
    fb = np.where(np.isfinite(mn), (mn < 1 - q * 1e-4).astype(float), np.nan); fs = np.where(np.isfinite(mx), (mx > 1 + q * 1e-4).astype(float), np.nan)
    mk = {"fill_buy": pd.DataFrame(fb, idx, cols), "fill_sell": pd.DataFrame(fs, idx, cols), "drift": pd.DataFrame(drift, idx, cols), "fee": maker, "skip_unfilled": True}
    ref2 = bt.run(S, d["close"], d["funding"], bt.slippage_model(d["volume"], 1) * slip_mult, maker=mk, fee=taker)
    chk["skip_vs_btrun_maxdiff"] = float(np.abs(sim(W, px, fnd, slip, fb, fs, drift, "skip", maker=maker, taker=taker)["r"].to_numpy() - ref2.returns.to_numpy()).max())
    print(chk, flush=True)
    out = {"check": chk}
    for q in QS[:3]:
        fb = np.where(np.isfinite(mn), (mn < 1 - q * 1e-4).astype(float), np.nan); fs = np.where(np.isfinite(mx), (mx > 1 + q * 1e-4).astype(float), np.nan)
        for mode in ("taker", "chase", "skip", "env"):
            if mode == "taker" and q:
                continue
            res = sim(W, px, fnd, slip, fb, fs, drift, mode, E, maker=maker, taker=taker).set_index(idx)
            row = {}
            for y in yrs + ("all",):
                g = res.loc[win[0]:win[1]] if y == "all" else res.loc[str(y)]
                row[y] = {"ann_pct": round(g["r"].mean() * 365 * 100, 2), "sr": round(g["r"].mean() / g["r"].std() * np.sqrt(365), 2),
                          "cost_pct": round(g["c"].sum() / len(g) * 365 * 100, 2), "to": round(g["to"].sum() / len(g) * 365, 1)}
            out[f"{mode}_q{q}"] = row
            print(mode, q, row["all"], {y: row[y]["sr"] for y in yrs}, flush=True)
    json.dump(out, open(EV / f"t9d_{tag}.json", "w"), indent=1)


def form_e():
    """HL spread (bp) and touch depth per coin from the hourly L2 snapshots, weighted by the slow legs' order notional 2026-04-15..11-26:
    the effective queue stress q for form d is the spread (a post-only buy rests at the bid, about one spread below a close printed at the ask)."""
    import glob
    rows = []
    for f in sorted(glob.glob(str(data.DATA / "hl" / "l2" / "*.jsonl"))):
        for line in open(f):
            j = json.loads(line)
            if j.get("bids") and j.get("asks"):
                b, a = float(j["bids"][0][0]), float(j["asks"][0][0])
                rows.append((j["coin"], (a - b) / ((a + b) / 2) * 1e4, b * float(j["bids"][0][1]), a * float(j["asks"][0][1])))
    sp = pd.DataFrame(rows, columns=["coin", "spread_bp", "bid_usd", "ask_usd"]).groupby("coin").median()
    d = data.load_panel("hl", "1d")
    fin, _, err = legs(d)
    S = partial(fin["tsmom"] + fin["lowvol"], LAM)
    w = S.diff().abs().loc["2026-04-15":"2026-11-26"].sum()
    w = w[w > 0]
    j = sp.reindex(w.index)
    cov = float(w[j["spread_bp"].notna()].sum() / w.sum())
    jj = j.dropna(); ww = w[jj.index]
    out = {"n_snapshots": len(rows), "coins_l2": int(len(sp)), "order_notional_covered": round(cov, 3),
           "spread_bp_wmean": round(float((ww * jj["spread_bp"]).sum() / ww.sum()), 2),
           "spread_bp_wmedian": round(float(jj["spread_bp"].iloc[np.searchsorted((ww / ww.sum())[jj["spread_bp"].argsort()].cumsum().to_numpy(), .5)] if False else
                                     jj.assign(w=ww).sort_values("spread_bp").pipe(lambda x: x["spread_bp"][x["w"].cumsum() >= x["w"].sum() / 2].iloc[0])), 2),
           "share_notional_spread_le5": round(float(ww[jj["spread_bp"] <= 5].sum() / ww.sum()), 3),
           "share_notional_spread_le10": round(float(ww[jj["spread_bp"] <= 10].sum() / ww.sum()), 3),
           "touch_bid_usd_wmedian": round(float(jj.assign(w=ww).sort_values("bid_usd").pipe(lambda x: x["bid_usd"][x["w"].cumsum() >= x["w"].sum() / 2].iloc[0])), 0),
           "top10_by_notional": {c: [round(float(ww[c] / ww.sum()), 3), round(float(jj.at[c, "spread_bp"]), 1)] for c in ww.sort_values().index[::-1][:10]}}
    print(json.dumps(out, indent=1))
    json.dump(out, open(EV / "t9d_e.json", "w"), indent=1)


def form_khl(ks=(0, 5, 10, 20), q=3, slip_mult=0.5):
    """T9K b: HL slow legs, rest k bp beyond the close (filled there: maker fee - k), fill needs k + q through; fitted slip x .5; 2026-04-15..11-26 (seen, descriptive)."""
    from kripto import backtest as bt
    d = data.load_panel("hl", "1d")
    fin, _, err = legs(d)
    S = partial(fin["tsmom"] + fin["lowvol"], LAM)
    cols, idx = S.columns, S.index
    px = d["close"].reindex(columns=cols).to_numpy(float); fnd = d["funding"].reindex(index=idx, columns=cols).to_numpy(float)
    slip = bt.slippage_model(d["volume"], 1).reindex(index=idx, columns=cols).to_numpy(float) * slip_mult
    h1 = data.load_panel("hl", "1h")
    D = idx + pd.Timedelta(days=1)
    mn = h1["low"].rolling(24, min_periods=24).min().shift(-23).reindex(columns=cols).reindex(D).to_numpy(float) / px
    mx = h1["high"].rolling(24, min_periods=24).max().shift(-23).reindex(columns=cols).reindex(D).to_numpy(float) / px
    drift = d["close"].reindex(columns=cols).shift(-1).to_numpy(float) / px - 1
    W = S.to_numpy(float)
    g = lambda res: round(float(res.set_index(idx).loc["2026-04-15":"2026-11-26"]["r"].mean() * 365 * 100), 2)
    base = g(sim(W, px, fnd, slip, mn * 0, mn * 0, drift, "taker", taker=4.5e-4))
    out = {"taker_ann_pct": base}
    rng = np.random.default_rng(5)
    for k in ks:
        th = (k + q) * 1e-4
        fb = np.where(np.isfinite(mn), (mn < 1 - th).astype(float), np.nan); fs = np.where(np.isfinite(mx), (mx > 1 + th).astype(float), np.nan)
        real = g(sim(W, px, fnd, slip, fb, fs, drift, "skip", maker=1.5e-4 - k * 1e-4, taker=4.5e-4))
        share = float(np.nanmean(np.concatenate([fb[np.isfinite(fb)], fs[np.isfinite(fs)]])))
        pn = np.mean([g(sim(W, px, fnd, slip, m, m, drift, "skip", maker=1.5e-4, taker=4.5e-4))
                      for m in [np.where(np.isfinite(mn), (rng.random(mn.shape) < share).astype(float), np.nan) for _ in range(5)]])
        out[f"k{k}"] = {"fill_share": round(share, 3), "real_minus_taker": round(real - base, 2), "placebo_fee_only_minus_taker": round(float(pn) - base, 2)}
        print(k, out[f"k{k}"], flush=True)
    json.dump(out, open(EV / "t9k_b.json", "w"), indent=1)


if __name__ == "__main__":
    {"a": form_a, "b": form_b, "c": form_c,
     "d": lambda: form_c("hl", 4.5e-4, 1.5e-4, ("2026-04-15", "2026-11-26"), (), "d"), "e": lambda: form_e(), "khl": lambda: form_khl(),
     "d2": lambda: form_c("hl", 4.5e-4, 1.5e-4, ("2026-04-15", "2026-11-26"), (), "d_slip05", 0.5)}[sys.argv[1]]()
