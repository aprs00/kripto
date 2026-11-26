"""LV1 (a)/(b): betting against volatility on the survivorship-free Binance daily set, total vs idiosyncratic vol (2026-11-26, PC session).
Descriptive, no registry line. Written BEFORE any number of this study was seen.

THINK-THROUGH
(a) Mechanism. Two textbook stories make high-vol assets earn less per unit of risk: (1) leverage constraints (Frazzini-Pedersen BAB):
    investors who cannot lever buy high-beta/high-vol assets instead, bidding them up; (2) lottery demand (Bali-Cakici-Whitelaw MAX,
    Ang et al. idio-vol puzzle): retail overpays for right-skewed payoffs. Who pays us: the lottery buyer of the high-vol alt, through a
    lower subsequent (risk-adjusted) return. In crypto perps the leverage story is weak (leverage is cheap; a perp holder can lever BTC),
    the lottery story is plausible (memecoin demand) but the payer often pays THROUGH FUNDING (longs pay shorts when crowded), so the short
    leg's return must be measured net of funding. Total vol mixes beta (market exposure, ~priced) and idiosyncratic vol (the lottery part);
    the idio-vol puzzle in equities is stronger than the total-vol one, so (b) is the purer form of the lottery story.
(b) Source: textbook anomaly; the system's form (strategies.lowvol) = rank long low / short high 30-d total vol in the top-30 by volume,
    BTC-beta hedged, weekly tranches. It failed on BN-82 4h (survivor-biased: BN-82 holds coins that survived, so the high-vol losers that
    were later delisted, exactly the short leg's winners, are missing) and on HL (2 y). HL full-sample default 0.90 keeps it in blend_nested.
(c) Formulations (materially different):
    F1 total vol, top-30 universe, rank-weighted beta-hedged (= the live definition) on bnall (survivorship-free)      -> LV1(a)
    F2 idiosyncratic vol (residual of a rolling regression on BTC, same window), top-30, rank-weighted, beta-hedged    -> LV1(b)
    F3 F1/F2 on a wider universe (top-100): the delisted high-vol tail lives outside the top 30, so if survivorship is the story the wider
       universe is where the short leg earns (and where costs are highest)
    F4 quintile Q1-Q5 instead of rank weights (concentration on the extremes; reported for both vol kinds)
    (LV1(c), high-vol exclusion as a filter on the x-sec books' short side, was answered no by R1 2026-11-17.)
(d) Non-idea failure modes: beta hedge error (high-vol alts' beta is unstable and rises in crashes: a 60-d beta under-hedges the short leg
    in a rally and over-hedges in a crash; the hedged spread is reported with the ex-ante beta, which is what a book can use); delisting
    returns (kripto.data: a coin's close is NaN after its last kline and on zero-volume days; kripto.backtest treats a NaN return as 0 and
    keeps the position frozen at its last close, i.e. "exit at the last daily close, no cost"; a settlement price below that close is not
    seen, which UNDER-states a short leg's delisting gain. This study uses the same convention: NaN next-day return = 0); short-leg squeezes
    (fat right tail of high-vol names: mean vs median and the worst 1% are reported); funding (shorting crowded high-vol names earns
    funding; reported separately); costs on thin names (median 30-d $ volume of each quintile is printed; the walk-forward pays the
    liquidity-scaled slippage model).
(e) What would change my mind. For: the hedged spread positive in >= 3 of 4 explore years in a form, and confirm 2024+ positive.
    Against: the spread's sign carried by one year (2021 alt mania) or by funding alone, or the beta-hedged spread negative while the raw
    one is positive (= it is only a market-beta bet).

SAMPLES (fixed now). Explore = bnall 1d, 2020-01-01 .. 2023-12-31 (formation dates). Confirm = 2024-01-01 .. end of data (2026-10-31),
looked at ONCE with `--confirm`, after the walk-forward decision below is written into research/batches/2026-11-26_pc_lv1.json.

PASS RULE (written before running). Measure = the rank-weighted, beta-hedged, dollar-neutral daily spread (the strategy's raw signal without
vol targeting, schedule or trading costs), next-day simple returns, net of funding.
  * A form goes to walk-forward if, on explore: pooled Sharpe >= 0.5 AND positive in >= 3 of the 4 calendar years AND the hedged quintile
    spread Q1-Q5 has the same sign.
  * F1 (total vol, top-30) is the literal backlog question (does the BN-82 failure come from survivorship?) and is the Binance analogue of
    a leg the HL main book trades, so it gets ONE walk-forward on bnall with the UNCHANGED 11-09 grid if its explore pooled Sharpe > 0, even
    if it misses the full rule (that walk-forward is a re-measurement of an existing form on clean data, not a new selection).
  * At most 2 walk-forwards in all (F1 and the best of F2/F3). A top-100 form needs top_n in the grid, so it competes with F2 for the slot.
RESULT 2026-11-26 (gross of trading costs, net of funding; numbers = rank-hedged SR, explore / confirm): total top-30 -0.06 / -0.06,
idio top-30 -0.06 / -0.09, total top-100 0.02 / 0.01, idio top-100 0.11 / -0.08 -> no form passed, NO walk-forward (batch 2026-11-26_pc_lv1.json).
Diagnosis: price-only the spread is positive (explore 0.17-0.31, confirm 0.69-0.92); the short leg pays it back in funding (high-vol names are
crowded shorts: confirm Q5 mean funding -102 %/yr vs median +9.7 %, RIVER/LAB/PIPPIN/MYX squeezes; 10 % of Q5 coin-days < -0.5 %/day). 2021 alt
mania -0.9 in every form. Delistings: 21 (explore) / 144 (confirm) coins, few in the top-100 30 d before (9 / 15): survivorship was not the reason.
LO1 (--lo1, tsmom defaults): long-only excess over vol-matched BTC SR 0.67 explore / -0.06 confirm (alpha 1.19 / 0.16); long-short alpha 1.42 / 0.71.
  usage: nice -n 19 .venv/bin/python -m research.studies.lv1_lowvol [--confirm] [--lo1]
"""
import sys

import numpy as np
import pandas as pd

from kripto import data
from kripto.strategies import beta_to, universe, xs_demean_rank

EXPLORE = ("2020-01-01", "2023-12-31")
CONFIRM = ("2024-01-01", "2100-01-01")


def vols(p, days=30):
    r = p["close"].pct_change(fill_method=None)
    m = r["BTC"]
    tv = r.rolling(days, min_periods=10).std()
    cov = r.rolling(days, min_periods=10).cov(m)
    var_m = m.rolling(days, min_periods=10).var()
    iv = np.sqrt((tv ** 2 - cov.pow(2).div(var_m, axis=0)).clip(lower=0))
    iv["BTC"] = np.nan                     # BTC's residual on itself is 0 by construction: it is the hedge, not a rankable name
    return r, tv, iv


def spread_rank(score, mask, r1, f1, beta, m1):
    """Rank-weighted (long low score), dollar neutral gross 1, BTC-beta hedged; next-day return net of funding."""
    w = xs_demean_rank(-score, mask).fillna(0.0)
    px = (w * r1.fillna(0.0)).sum(axis=1)
    alt = px - (w * f1.fillna(0.0)).sum(axis=1)
    b = (w * beta.fillna(1.0)).sum(axis=1)
    return alt - b * m1.fillna(0.0), alt, px - b * m1.fillna(0.0)


def quintiles(score, mask, r1, f1, beta, m1, med_dv, a, b):
    s = score.where(mask)
    q = s.rank(axis=1, pct=True)
    out = {}
    for k in range(5):
        sel = (q > k / 5) & (q <= (k + 1) / 5)
        n = sel.sum(axis=1).replace(0, np.nan)
        raw = r1.fillna(0.0).where(sel, 0.0).sum(axis=1) / n
        fund = f1.fillna(0.0).where(sel, 0.0).sum(axis=1) / n
        bq = beta.where(sel).mean(axis=1)
        out[f"Q{k + 1}"] = {"raw": raw, "fund": fund, "hedged": raw - fund - bq * m1.fillna(0.0), "beta": bq,
                            "med_dv": med_dv.where(sel).median(axis=1),
                            "fund_med": float(np.nanmedian(window(f1.where(sel), a, b).to_numpy())),
                            "med_r": window(r1.where(sel), a, b).stack().median(),
                            "p99": window(r1.where(sel), a, b).stack().quantile(0.99)}
    return out


def sr(x):
    x = x.dropna()
    return float(x.mean() / x.std() * np.sqrt(365)) if len(x) > 30 and x.std() > 0 else np.nan


def window(x, a, b):
    return x[(x.index >= a) & (x.index <= b)]


def report(p, a, b, label):
    r, tv, iv = vols(p)
    r1 = r.shift(-1)                                  # return earned the day after formation at close t
    f1 = p["funding"].shift(-1)
    m1 = r1["BTC"]
    beta = beta_to(p)
    med_dv = p["volume"].rolling(30, min_periods=7).mean()
    print(f"\n=== {label}: formation {a} .. {b} ===")
    for top in (30, 100):
        mask = universe(p, top)
        for kind, v in (("total", tv), ("idio", iv)):
            msk = mask & v.notna()
            h, raw, hpx = spread_rank(v, msk, r1, f1, beta, m1)
            h, raw, hpx = window(h, a, b), window(raw, a, b), window(hpx, a, b)
            yrs = {y: sr(h[h.index.year == y]) for y in sorted(set(h.index.year))}
            pos = sum(1 for s in yrs.values() if s > 0)
            q = quintiles(v, msk, r1, f1, beta, m1, med_dv, a, b)
            qh = {k: window(d["hedged"], a, b) for k, d in q.items()}
            q15 = qh["Q1"] - qh["Q5"]
            print(f"top{top:3d} {kind:5s} rank-hedged SR={sr(h):5.2f} ann={h.mean() * 365:6.1%} (price only {sr(hpx):5.2f}; unhedged alt-leg {sr(raw):5.2f}) "
                  f"years>0 {pos}/{len(yrs)} " + " ".join(f"{y}:{s:5.2f}" for y, s in yrs.items())
                  + f" | Q1-Q5 hedged SR={sr(q15):5.2f} ann={q15.mean() * 365:6.1%}")
            print("        " + "  ".join(
                f"{k}: hSR {sr(qh[k]):5.2f} raw {window(d['raw'], a, b).mean() * 365:6.1%} fund {window(d['fund'], a, b).mean() * 365:6.1%}"
                f" b {window(d['beta'], a, b).mean():4.2f} dv ${window(d['med_dv'], a, b).median() / 1e6:5.0f}M" for k, d in q.items()))
            if kind == "total" and top == 30:
                print("        Q1 vs Q5 next-day median / p99 (coin-days in the window): "
                      f"Q1 {q['Q1']['med_r'] * 1e4:+.0f} bp / {q['Q1']['p99']:.1%}  Q5 {q['Q5']['med_r'] * 1e4:+.0f} bp / {q['Q5']['p99']:.1%}"
                      f"; median coin-day funding ann. Q1 {q['Q1']['fund_med'] * 365:.1%} Q5 {q['Q5']['fund_med'] * 365:.1%}")


def delistings(p, a, b):
    c = p["close"]
    last = c.apply(lambda s: s.last_valid_index())
    end = c.index[-1]
    gone = last[(last < end - pd.Timedelta(days=10)) & (last >= pd.Timestamp(a, tz="UTC")) & (last <= pd.Timestamp(b, tz="UTC"))]
    _, tv, _ = vols(p)
    rk = tv.rank(axis=1, pct=True)
    u100 = universe(p, 100)
    rows = []
    for coin, t in gone.items():
        s = c[coin].dropna()
        r30 = s.iloc[-1] / s.iloc[-31] - 1 if len(s) > 31 else np.nan
        t30 = t - pd.Timedelta(days=30)
        rows.append({"coin": coin, "last": t.date(), "r_last30": r30, "volrank_t-30": rk[coin].get(t30, np.nan),
                     "in_top100_t-30": bool(u100[coin].get(t30, False))})
    d = pd.DataFrame(rows)
    print(f"\ndelisted in {a}..{b}: {len(d)} coins; in point-in-time top-100 30 d before: {int(d['in_top100_t-30'].sum())}; "
          f"median last-30-d return {d['r_last30'].median():.1%} (in top-100: {d.loc[d['in_top100_t-30'], 'r_last30'].median():.1%}); "
          f"median total-vol pct rank 30 d before {d['volrank_t-30'].median():.2f}")


def lo1(p):
    """LO1 descriptive: tsmom long-only (default params, bnall 1d, the engine with costs) vs BTC held at the same realised vol
    (constant-leverage BTC, leverage = tsmom's full-sample vol / BTC's vol, no costs on the BTC leg: favours BTC slightly).
    Excess = tsmom - vol-matched BTC; also the regression alpha on BTC. By year."""
    from kripto import backtest as bt
    from kripto.research import bars_per_day, default_band
    from kripto.strategies import REGISTRY
    slip = bt.slippage_model(p["volume"], bars_per_day(p["close"].index))
    out = {}
    for lab, prm in (("long_only", {"long_only": True}), ("long_short", {})):
        w = REGISTRY["tsmom"](p, **prm)
        res = bt.run(w, p["close"], p.get("funding"), slip, band=default_band())
        out[lab] = res.returns[res.gross.cumsum() > 0]
    btc = p["close"]["BTC"].pct_change(fill_method=None) - p["funding"]["BTC"].fillna(0.0)
    print("\n=== LO1: tsmom vs vol-matched BTC (bnall 1d, defaults; BTC leg pays funding, no trading cost) ===")
    for lab, r in out.items():
        b = btc.reindex(r.index).fillna(0.0)
        lev = r.std() / b.std()
        ex = r - lev * b
        beta = np.cov(r, b)[0, 1] / b.var()
        alpha = r - beta * b
        yrs = " ".join(f"{y}: {sr(r[r.index.year == y]):5.2f}/{sr((lev * b)[b.index.year == y]):5.2f}/{sr(ex[ex.index.year == y]):5.2f}"
                       for y in sorted(set(r.index.year)))
        print(f"{lab:10s} SR {sr(r):5.2f} | volmatched BTC SR {sr(lev * b):5.2f} (lev {lev:.2f}) | excess SR {sr(ex):5.2f} ann {ex.mean() * 365:6.1%}"
              f" | beta {beta:.2f} alpha SR {sr(alpha):5.2f} ann {alpha.mean() * 365:6.1%} corr {r.corr(b):.2f}")
        print(f"           by year strat/BTCvm/excess: {yrs}")
        for a, bb, nm in (EXPLORE + ("explore",), CONFIRM + ("confirm",)):
            e = window(ex, a, bb)
            al = window(alpha, a, bb)
            print(f"           {nm}: excess SR {sr(e):5.2f} ann {e.mean() * 365:6.1%}; alpha SR {sr(al):5.2f}")


if __name__ == "__main__":
    p = data.load_panel("bnall", "1d")
    print("bnall", p["close"].shape, p["close"].index[0].date(), "..", p["close"].index[-1].date())
    if "--lo1" in sys.argv:
        lo1(p)
        sys.exit()
    a, b = CONFIRM if "--confirm" in sys.argv else EXPLORE
    report(p, a, b, "CONFIRM" if "--confirm" in sys.argv else "EXPLORE")
    delistings(p, a, b)
