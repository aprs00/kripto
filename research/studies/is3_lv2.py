"""LV2 (a)(b): lowvol with the crowded negative-funding shorts removed / ranked on funding-adjusted vol (think-through research/is3/notes.md,
written before this ran). bnall 1d, explore 2020-01..2023-12, gross of trading costs, net of funding, BTC-beta hedged, next-day simple returns.
(a) rank weights on 30-d total vol; short candidates (w < 0) with trailing 7-d mean funding < 0 (known at the close t) dropped, short leg
    re-scaled to the same gross; placebo: the same number of short candidates dropped at random each day (100 draws).
(b) rank on the 30-d vol of (r - funding).  Dose: Q5 (high vol) hedged next-day return by trailing-funding tercile.
usage: nice -n 19 .venv/bin/python -m research.studies.is3_lv2 [--hl]"""
import json
import sys
import numpy as np
import pandas as pd
from kripto import data
from kripto.strategies import beta_to, universe, xs_demean_rank
from research.studies.lv1_lowvol import vols, sr, window

A, B = "2020-01-01", "2023-12-31"


def legs(w):
    """re-scale long and short legs to 0.5 gross each (dollar neutral)."""
    lo = w.clip(lower=0); sh = w.clip(upper=0)
    lo = lo.div(lo.sum(axis=1).replace(0, np.nan), axis=0) * 0.5
    sh = sh.div(-sh.sum(axis=1).replace(0, np.nan), axis=0) * 0.5
    return (lo.fillna(0) + sh.fillna(0))


def pnl(w, r1, f1, beta, m1):
    px = (w * r1.fillna(0)).sum(axis=1)
    fd = (w * f1.fillna(0)).sum(axis=1)
    b = (w * beta.fillna(1.0)).sum(axis=1)
    h = px - fd - b * m1.fillna(0)
    return h, px - b * m1.fillna(0)


def line(lab, h, hpx, a=A, b=B):
    h, hpx = window(h, a, b), window(hpx, a, b)
    yrs = {y: sr(h[h.index.year == y]) for y in sorted(set(h.index.year))}
    print(f"{lab:34s} SR {sr(h):5.2f} ann {h.mean()*365:6.1%} (price-only {sr(hpx):5.2f}) years>0 {sum(s > 0 for s in yrs.values())}/{len(yrs)} "
          + " ".join(f"{y}:{s:5.2f}" for y, s in yrs.items()))
    return sr(h)


def run(p, a=A, b=B, tops=(30, 100)):
    r, tv, _ = vols(p)
    fr = p["funding"]
    r1, f1 = r.shift(-1), fr.shift(-1)
    m1 = r1["BTC"]
    beta = beta_to(p)
    f7 = fr.rolling(7, min_periods=5).mean()
    adj = (r - fr.fillna(0)).rolling(30, min_periods=10).std()
    rng = np.random.default_rng(11)
    for top in tops:
        print(f"\n--- top{top} ---")
        mask = universe(p, top) & tv.notna()
        w0 = legs(xs_demean_rank(-tv, mask).fillna(0.0))
        base = line("base lowvol (rank, total vol)", *pnl(w0, r1, f1, beta, m1), a, b)
        drop = (w0 < 0) & (f7 < 0)
        wa = legs(w0.where(~drop, 0.0))
        sa = line("a drop shorts f7<0", *pnl(wa, r1, f1, beta, m1), a, b)
        share = drop.sum(axis=1) / (w0 < 0).sum(axis=1).replace(0, np.nan)
        print(f"   dropped share of short candidates: mean {window(share, a, b).mean():.0%}")
        # placebo: drop the same count of short candidates at random each day
        neg = (w0 < 0).to_numpy(); k = drop.sum(axis=1).to_numpy()
        ins = (w0.index >= pd.Timestamp(a, tz="UTC")) & (w0.index <= pd.Timestamp(b, tz="UTC"))
        sims = []
        W = w0.to_numpy()
        for s in range(100):
            Wd = W.copy()
            for i in np.where(ins & (k > 0))[0]:
                idx = np.flatnonzero(neg[i]); Wd[i, rng.choice(idx, size=int(k[i]), replace=False)] = 0.0
            h, _ = pnl(legs(pd.DataFrame(Wd, w0.index, w0.columns)), r1, f1, beta, m1)
            sims.append(sr(window(h, a, b)))
        sims = np.array(sims)
        print(f"   placebo random drop SR: median {np.median(sims):.2f}, 95th {np.quantile(sims, .95):.2f}; a at pct {(sims < sa).mean():.0%}")
        # inverse: keep ONLY the negative-funding shorts (is the effect in the dropped names?)
        wi = legs(w0.where(~((w0 < 0) & ~(f7 < 0)), 0.0))
        line("a' shorts ONLY f7<0 (mirror)", *pnl(wi, r1, f1, beta, m1), a, b)
        mb = universe(p, top) & adj.notna()
        wb = legs(xs_demean_rank(-adj, mb).fillna(0.0))
        line("b rank on vol of (r - funding)", *pnl(wb, r1, f1, beta, m1), a, b)
        wab = legs(wb.where(~((wb < 0) & (f7 < 0)), 0.0))
        line("a+b", *pnl(wab, r1, f1, beta, m1), a, b)
        # dose: high-vol quintile next-day hedged return by trailing-funding tercile (pooled coin-days)
        q = tv.where(mask).rank(axis=1, pct=True) > 0.8
        hr = (r1 - f1.fillna(0) - beta.fillna(1).mul(m1, axis=0)).where(q)
        hp = (r1 - beta.fillna(1).mul(m1, axis=0)).where(q)
        ff = f7.where(q)
        st = pd.DataFrame({"h": window(hr, a, b).stack(), "p": window(hp, a, b).stack(), "f": window(ff, a, b).stack()}).dropna()
        st["t"] = pd.qcut(st["f"], [0, 1/3, 2/3, 1], labels=["f7 low", "mid", "high"])
        g = st.groupby("t", observed=True).agg(n=("h", "size"), hedged_bp=("h", lambda x: x.mean() * 1e4), price_bp=("p", lambda x: x.mean() * 1e4),
                                               med_bp=("h", lambda x: x.median() * 1e4), f7_bp=("f", lambda x: x.mean() * 1e4))
        print("   Q5 (short leg) next-day by trailing funding tercile (shorting earns -hedged):\n" + g.round(1).to_string())


def form_c():
    """LV2 c: lowvol (defaults, the HL main book's blend leg) on HL 1d via research.evaluate (logged, tag lv2c): SR by year, price vs funding,
    SR without the best 10 days, and the HL funding coverage (backfilled to 2023-05 by is3_fc1c_fetch)."""
    from kripto import research
    p = data.load_panel("hl", "1d")
    fcov = p["funding"].notna().sum(axis=1)
    print("HL coins with funding by year (median per day):", fcov.groupby(fcov.index.year).median().to_dict())
    res, s = research.evaluate("lowvol", p, {}, "hl", tag="lv2c")
    r = res.returns[res.gross.cumsum() > 0]
    f = res.funding.reindex(r.index).fillna(0); co = res.costs.reindex(r.index).fillna(0)
    out = {"sharpe": s.get("sharpe"), "n_days": int(len(r)), "start": str(r.index[0].date())}
    yrs = {}
    for y, x in r.groupby(r.index.year):
        yrs[int(y)] = {"sr": round(sr(x), 2), "ret": round(float(x.sum()), 4), "funding_received": round(float(f[x.index].sum()), 4), "costs": round(float(co[x.index].sum()), 4)}
    out["years"] = yrs
    top = r.nlargest(10)
    out["sr_wo_best10"] = round(sr(r.drop(top.index)), 2)
    out["best10_share_of_total"] = round(float(top.sum() / r.sum()), 2) if r.sum() != 0 else None
    out["sr_since_2024_07"] = round(sr(r[r.index >= "2024-07-01"]), 2)
    out["sr_before_2024_07"] = round(sr(r[r.index < "2024-07-01"]), 2)
    print(json.dumps(out, indent=1))
    json.dump({"study": "research/studies/is3_lv2.py --hlc", **out}, open("research/is3/lv2_hlc.json", "w"), indent=1)


if __name__ == "__main__" and "--hlc" in sys.argv:
    form_c()
elif __name__ == "__main__":
    if "--hl" in sys.argv:
        p = data.load_panel("hl", "1d")
        print("hl", p["close"].shape)
        run(p, "2023-05-15", "2100-01-01", tops=(30,))
    else:
        p = data.load_panel("bnall", "1d")
        print("bnall", p["close"].shape, p["close"].index[-1].date())
        run(p)
