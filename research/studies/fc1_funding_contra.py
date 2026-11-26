"""FC1 (2026-11-26, PC session; backlog FC1, findings "funding_contra" OPEN one form failed): the untried forms of funding_contra.

THINK-THROUGH (written before any number of this study was looked at)
Tried form (11-08/09): cross-sectional rank of a z-scored 1-day funding jump vs its 14-day history, dollar + beta neutral, daily.
HL -0.81, bnall -0.42 (grid mixed). Diagnosis then: turnover only. That form mixes two opposite stories (crowded longs that unwind vs
crowded longs that keep squeezing) and both tails at once, so it cannot tell which story is true.

Mechanism: funding is the price a crowded side pays to hold its position. Who pays us: (i) the funding itself (the crowded side pays the
other), (ii) the price move IF the crowd is wrong and is forced out (short squeeze / long liquidation). Carry (ALIVE on bnall, pick 1.30)
already harvests (i) across the whole cross-section and LOSES on (ii) (the high-funding names keep rising: 2025-26 squeezes > funding).
So a funding_contra form is new information only if it earns on the PRICE leg, or earns where carry does not. Each form is therefore
judged on hedged price P&L and funding P&L separately, and against the carry tail (same side, same funding extremity, without the extra
condition) and by its daily-P&L correlation with the carry and carry_trend books (picks lb1/7d and lb7/3d).

(a) Extreme NEGATIVE funding, long side only. Shorts paying >= 0.1 %/day (3x the normal +0.03 %/day, opposite sign) are crowded;
    covering pushes price up, and we are paid funding while waiting. Failure modes not about the idea: negative funding on Binance is
    largely HEDGERS (new listings, unlocks, airdrop farmers short the perp against spot/locked tokens) -> informed supply, price keeps
    falling (listing_short is ALIVE: the same names); delisting tails (ffilled to the last price here, i.e. settlement); one-day funding
    spikes revert before we collect them; few events per day (concentration); thin names (liquidity-scaled cost).
    Closest to carry's LONG leg: if (a) only earns funding and its price leg ~ the carry tail's, it is carry relabelled.
(b) Fade HIGH funding only once price has stopped rising (short side). A spike while price still rises is a squeeze in progress (carry's
    loss); once price stalls the late leveraged longs are under water and their unwind is the price leg. Stall definitions: b1 down day,
    b2 7-d up but 3-d down, b3 >= 5 % off the 7-d high, b5 the old z-spike with a down day. Contrast b4 = still rising (should be worse).
    Failure modes: a one-day dip inside a squeeze is noise (trends resume); high-funding names are momentum winners and cross-sectional
    momentum is ALIVE on bnall (shorting winners fights it); costs on thin names. Closest relative: carry_trend (short above-median funding
    with NEGATIVE 14-56 d trend). (b) differs by extremity (absolute threshold) and horizon (1-7 d stall vs 14-56 d trend): must show
    low correlation with carry_trend to count as new.
(c) HL-vs-Binance funding GAP as the crowding measure (= backlog T3). HL's crowd (on-chain, retail, hourly funding) differs from Binance's;
    a coin whose HL funding is far above its Binance funding has crowded HL longs that arbitrage has not closed. Direction: fade the HL
    crowd (short when HL >> BN, long when HL << BN), P&L on Binance prices and funding (the liquid leg, and where history exists).
    Failure modes: the gap is mechanical (HL premium sampling, HL 0.01 %/8h interest floor, caps differ), only ~85 coins and 2.3 years,
    and it may just be BN funding in disguise (check the cross-sectional rank correlation of gap with BN funding). fspread (capturing the
    gap itself, two venues) is a different trade and already tested (DEAD at taker / fspread_hold candidate).
What would change my mind: a form whose hedged PRICE leg is positive in every explore year with day-clustered t > 2 after costs, and whose
book correlates < 0.5 with carry -> pre-register and walk-forward. If every form only earns the funding the carry tail earns, or the
price leg is negative, record the reason.

SAMPLES (fixed before running):
  (a), (b): bnall 1d, top-100 point-in-time universe. EXPLORE 2020-01-01 .. 2023-12-31. CONFIRM 2024-01-01 .. 2026-10-31 (one shot per
            chosen form, `confirm <form>`), and the walk-forward (bnall, its OOS by year) for at most one or two forms.
  (c):      HL funding is held locally only from 2024-07-01. EXPLORE 2024-07-01 .. 2025-06-30. CONFIRM 2025-07-01 .. 2026-10-31.
            No walk-forward possible (too short for 240-d train + 60-d folds to mean anything): descriptive only.
Outcome per event: decision at the close of day t (funding[t] is paid during day t, known at its end). Hold H days. SIMPLE returns.
  price = side * (P[t+H]/P[t]-1 - beta * BTC same), beta = 60-d BTC beta (clip 0..3); funding = -side * sum funding[t+1..t+H] + the
  BTC hedge leg's funding; cost = round trip 2*(5 bp fee + liquidity slippage of the coin) + beta * 2*(5+1.5) bp hedge. net = sum.
  'state' rows: every coin-day the condition holds, H=1 (what a daily-rebalanced book earns). 'entry' rows: first day of an episode
  (condition false the day before), H=7. t = Newey-West (lag H-1) t of the per-day mean (day-clustered). Delisted coins: last price.
  usage: nice -n 19 .venv/bin/python -m research.studies.fc1_funding_contra [explore|diag|confirm <form>[,<form>]]

RESULT (explore only, 2026-11-26; the confirm samples were NOT touched, no walk-forward, no registry line). Forms a7/a7w, the top-30
variants and the (c) controls cX/cY were added after the first explore pass (diagnostics, explore is free).
  (a) price leg <= 0 in every definition (t_price -2.4..+0.4): no squeeze on average. New listings (< 120 d) with extreme negative
      funding fall -84..-96 bp/day (hedged supply = listing_short's premise). Best: a7 (f3 < -0.3 %/d, top-30, age >= 120 d): book net
      SR 1.63 (2020 -0.54), but it is funding (+100 bp/d) not price (+12, t 0.4), event t 1.8, top-3 days 44 % / top-10 days 104 % of
      the net sum (TRB/BLZ 2023, AXS 2021 squeezes), corr 0.46 with carry: a concentrated carry long tail, fails the rule above.
  (b) every short-high-funding form loses (price -35..-60 bp/d); the stall filter changes nothing (down day -60, still rising -74);
      the whole loss is the worst 1 % of events (b0: -61.7 of -61.6): squeezes. The price condition that works is carry_trend's
      14-56 d trend (ALIVE), not a 1-7 d stall.
  (c) the only form whose crowding-fade PRICE leg has the right sign: short gap top-10 % +122..+148 bp/7 d (t_price 1.4-1.8, net t
      1.1-1.2, both explore years +), book net SR 0.46-0.57, corr 0.49 with listing_short, gap ranks corr -0.25 with BN funding.
      12 months of explore: underpowered, not failed. Decision: no form meets the pre-written rule -> no confirm, no walk-forward.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from kripto import backtest as bt, data
from kripto.strategies import REGISTRY, beta_to, universe

EXPLORE = ("2020-01-01", "2024-01-01")
CONFIRM = ("2024-01-01", "2026-11-01")
GAP_EXPLORE = ("2024-07-01", "2025-07-01")
GAP_CONFIRM = ("2025-07-01", "2026-11-01")
FEE = 0.0005


def nw_t(x: pd.Series, lag: int) -> float:
    x = x.dropna()
    n = len(x)
    if n < 10:
        return np.nan
    e = x - x.mean()
    v = (e * e).sum() / n
    for k in range(1, lag + 1):
        v += 2 * (1 - k / (lag + 1)) * (e.iloc[k:].values * e.iloc[:-k].values).sum() / n
    return x.mean() / np.sqrt(v / n)


class Outcomes:
    """Forward hedged price / funding / cost per (day, coin) for side +1, for horizons H, on one panel."""

    def __init__(self, p: dict, ref: str = "BTC"):
        self.c = p["close"]
        self.pf = self.c.ffill()                       # delisted coins keep their last (settlement) price
        self.f = p["funding"].reindex_like(self.c).fillna(0.0)
        self.beta = beta_to(p, ref).clip(0, 3).fillna(1.0)
        slip = bt.slippage_model(p["volume"], 1)
        self.cost = 2 * (FEE + slip) + self.beta * 2 * (FEE + 1.5e-4)
        self.ref = ref
        self.cache = {}

    def get(self, H: int):
        if H not in self.cache:
            r = self.pf.shift(-H) / self.c - 1
            rb = r[self.ref]
            price = r.sub(self.beta.mul(rb, axis=0))
            fsum = self.f[::-1].rolling(H, min_periods=1).sum()[::-1].shift(-1)   # sum f[t+1..t+H]
            fund = -fsum.add(-self.beta.mul(fsum[self.ref], axis=0))               # long coin pays f, short beta*BTC receives
            self.cache[H] = (price, fund)
        return self.cache[H]


def events(mask: pd.DataFrame, side: int, out: Outcomes, H: int, lo: str, hi: str, entry: bool) -> pd.DataFrame:
    m = mask.fillna(False).astype(bool)
    if entry:
        m = m & ~m.shift(1, fill_value=False)
    new = m & ~m.shift(1, fill_value=False)          # state rows pay the round trip only on the first day of an episode
    m = m.loc[(m.index >= lo) & (m.index < hi)]
    price, fund = out.get(H)
    s = m.stack()
    s = s[s]
    idx = s.index
    pr = price.stack().reindex(idx) * side
    fu = fund.stack().reindex(idx) * side
    co = (out.cost * new).stack().reindex(idx)
    e = pd.DataFrame({"price": pr, "fund": fu, "cost": co}).dropna(subset=["price"])
    e["gross"] = e["price"] + e["fund"]
    e["net"] = e["gross"] - e["cost"]
    return e


def row(name: str, e: pd.DataFrame, H: int) -> dict:
    if len(e) == 0:
        return {"form": name, "n": 0}
    d = e.groupby(level=0)["net"].mean()
    dg = e.groupby(level=0)["gross"].mean()
    dp = e.groupby(level=0)["price"].mean()
    yrs = e.groupby(e.index.get_level_values(0).year)["net"].mean()
    return {"form": name, "H": H, "n": len(e), "days": len(d), "price": e["price"].mean() * 1e4, "fund": e["fund"].mean() * 1e4,
            "cost": e["cost"].mean() * 1e4, "net": e["net"].mean() * 1e4, "med": e["net"].median() * 1e4,
            "t": nw_t(d, H - 1), "t_gross": nw_t(dg, H - 1), "t_price": nw_t(dp, H - 1), **{f"y{y % 100}": v * 1e4 for y, v in yrs.items()}}


def book(mask: pd.DataFrame, side: int, out: Outcomes, hold: int, net: bool = False) -> pd.Series:
    """Daily return of an equal-weight hedged book holding every coin whose condition fired in the last `hold` days
    (net: minus the round-trip cost of each newly entered coin, as a share of the equal weight)."""
    act = mask.fillna(False).astype(float).rolling(hold, min_periods=1).max() > 0
    price, fund = out.get(1)
    x = (price + fund).where(act) * side
    if net:
        x = x - (out.cost * (act & ~act.shift(1, fill_value=False))).where(act)
    return x.mean(axis=1)


def strat_returns(name: str, p: dict, params: dict) -> pd.Series:
    w = REGISTRY[name](p, **params)
    slip = bt.slippage_model(p["volume"], 1)
    r = bt.run(w, p["close"], p["funding"], cost=slip, band=0.01, fee=FEE)
    return r.returns


def bn_forms(p: dict):
    c, f = p["close"], p["funding"]
    u = universe(p, 100)
    u30 = universe(p, 30)
    f1 = f.where(u)
    f3 = f.rolling(3, min_periods=2).mean().where(u)
    z = (f - f.rolling(14, min_periods=3).mean()) / f.rolling(14, min_periods=3).std()
    r1, r3, r7 = c / c.shift(1) - 1, c / c.shift(3) - 1, c / c.shift(7) - 1
    hi7 = c.rolling(7, min_periods=3).max()
    age = c.notna().cumsum()
    q05 = f3.quantile(0.05, axis=1)
    hi = f3 > 0.001
    # carry tails (the "relabelled carry" baseline): carry pick lb=1 -> 1-day funding rank within the top-30
    fr30 = f.where(u30).rank(axis=1, pct=True)
    forms = {
        "a1 f3<-0.1%": (+1, f3 < -0.001),
        "a2 f3<-0.3%": (+1, f3 < -0.003),
        "a3 bottom5%&f3<0": (+1, f3.le(q05, axis=0) & (f3 < 0)),
        "a4 z<-2&f1<0": (+1, (z < -2) & (f1 < 0)),
        "a6 a1&up day": (+1, (f3 < -0.001) & (r1 > 0)),
        "A* carry long tail": (+1, fr30 <= 0.1),
        "b0 f3>0.1%": (-1, hi),
        "b1 b0&down day": (-1, hi & (r1 < 0)),
        "b2 b0&r7>0&r3<0": (-1, hi & (r7 > 0) & (r3 < 0)),
        "b3 b0&<=0.95*hi7": (-1, hi & (c <= 0.95 * hi7)),
        "b4 b0&r3>0 (rising)": (-1, hi & (r3 > 0)),
        "b5 z>2&f1>0&down": (-1, (z > 2) & (f1 > 0) & (r1 < 0) & u),
        "B* carry short tail": (-1, fr30 >= 0.9),
        # diagnostics added after the first explore pass: is the top-100 tail just thinner names? (top-30 universe)
        "a2t30 a2 in top30": (+1, (f3 < -0.003) & u30),
        "a3t30 a3 in top30": (+1, f3.le(q05, axis=0) & (f3 < 0) & u30),
        "b3t30 b3 in top30": (-1, hi & (c <= 0.95 * hi7) & u30),
        # added after `diag` (new listings with extreme negative funding fall hard: hedged supply, listing_short's premise):
        "a7 a2t30&age>=120d": (+1, (f3 < -0.003) & u30 & (age >= 120)),
        "a7w a2&age>=120d (top100)": (+1, (f3 < -0.003) & (age >= 120)),
    }
    return forms


def gap_forms(p_hl: dict, p_bn: dict):
    """(c): HL minus Binance funding on the same coin, Binance prices + funding for P&L. Returns (forms, bn sub-panel)."""
    coins = [c for c in p_hl["close"].columns if data.hl_to_bn(c) in p_bn["close"].columns and p_hl["funding"][c].notna().any()]
    bnc = [data.hl_to_bn(c) for c in coins]
    idx = p_bn["close"].index
    hf = p_hl["funding"][coins].reindex(idx).set_axis(bnc, axis=1)
    hc = p_hl["close"][coins].reindex(idx).set_axis(bnc, axis=1)
    sub = {k: p_bn[k][list(dict.fromkeys(bnc + ["BTC"]))] for k in ("close", "volume", "funding")}
    bf = sub["funding"][bnc]
    ok = data._same_asset(hc, sub["close"][bnc]) & hf.notna() & bf.notna()
    u = universe(p_bn, 100)[bnc]
    ok = ok & u
    g3 = (hf.rolling(3, min_periods=2).mean() - bf.rolling(3, min_periods=2).mean()).where(ok)
    rk = g3.rank(axis=1, pct=True)
    enough = (g3.notna().sum(axis=1) >= 20)
    forms = {
        "c1 gap>+0.05% short": (-1, g3 > 0.0005),
        "c2 gap<-0.05% long": (+1, g3 < -0.0005),
        "c3s gap top10% short": (-1, (rk >= 0.9) & enough.values[:, None]),
        "c3l gap bot10% long": (+1, (rk <= 0.1) & enough.values[:, None]),
    }
    bf3 = bf.rolling(3, min_periods=2).mean().where(ok)
    # control added after the first explore pass (gap ranks correlate -0.25 with BN funding): the same short on the BN-funding rank alone
    rb = bf3.rank(axis=1, pct=True)
    forms["cX short BN-f3 bot10% (control)"] = (-1, (rb <= 0.1) & enough.values[:, None])
    forms["cY c3s & not BN-f3 bot30%"] = (-1, (rk >= 0.9) & (rb > 0.3) & enough.values[:, None])
    rc = g3.rank(axis=1).corrwith(bf3.rank(axis=1), axis=1)
    return forms, sub, rc


def show(rows: list[dict]):
    df = pd.DataFrame(rows).set_index("form")
    with pd.option_context("display.width", 250, "display.max_columns", 30, "display.float_format", "{:.1f}".format):
        print(df)


def run_bn(p, out, forms, lo, hi, names=None):
    rows = []
    for name, (side, m) in forms.items():
        if names and name.split()[0] not in names:
            continue
        rows.append(row(name + " [state]", events(m, side, out, 1, lo, hi, False), 1))
        rows.append(row(name + " [entry]", events(m, side, out, 7, lo, hi, True), 7))
    show(rows)


def correlations(p, out, forms, lo, hi, names=None):
    sl = slice(pd.Timestamp(lo, tz="UTC"), pd.Timestamp(hi, tz="UTC") - pd.Timedelta(days=1))
    ref = {"carry": strat_returns("carry", p, {"lookback": 1, "every_days": 7}),
           "carry_trend": strat_returns("carry_trend", p, {"lookback": 7, "every_days": 3})}
    print("\ndaily-P&L correlation of each form's costless equal-weight hedged book (hold 3 d) with the carry books (net):")
    for name, (side, m) in forms.items():
        if names and name.split()[0] not in names:
            continue
        b = book(m, side, out, 3).loc[sl]
        bn_ = book(m, side, out, 3, net=True).loc[sl]
        cs = {k: b.corr(v.shift(-1).loc[sl]) for k, v in ref.items()}   # book uses ret[t+1] at index t; bt.returns at t+1
        sr = b.mean() / b.std() * np.sqrt(365)
        srn = bn_.mean() / bn_.std() * np.sqrt(365)
        yr = bn_.groupby(bn_.index.year).apply(lambda x: x.mean() / x.std() * np.sqrt(365))
        print(f"  {name:24s} SR gross {sr:5.2f} net {srn:5.2f}  corr carry {cs['carry']:5.2f}  carry_trend {cs['carry_trend']:5.2f}  "
              f"days {b.notna().sum()}  net SR by year " + " ".join(f"{y % 100}:{v:.2f}" for y, v in yr.items()))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "explore"
    names = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    p = data.load_panel("bnall", "1d")
    out = Outcomes(p)
    forms = bn_forms(p)
    lo, hi = EXPLORE if mode == "explore" else CONFIRM
    bnames = None if names is None else [n for n in names if not n.startswith("c")]
    gnames = None if names is None else [n for n in names if n.startswith("c")]
    if bnames is None or bnames:
        print(f"== bnall {mode} {lo}..{hi} (bp per event; t = NW day-clustered; yYY = mean net by year)")
        run_bn(p, out, forms, lo, hi, bnames)
        correlations(p, out, forms, lo, hi, bnames)
    if gnames is None or gnames:
        glo, ghi = GAP_EXPLORE if mode == "explore" else GAP_CONFIRM
        h = data.load_panel("hl", "1d")
        gforms, sub, rc = gap_forms(h, p)
        gout = Outcomes(sub)
        print(f"\n== (c) HL-BN funding gap, Binance P&L, {mode} {glo}..{ghi}; cross-sectional rank corr(gap, BN f3) "
              f"mean {rc.loc[glo:ghi].mean():.2f}")
        rows = []
        for name, (side, m) in gforms.items():
            if gnames and name.split()[0] not in gnames:
                continue
            rows.append(row(name + " [state]", events(m, side, gout, 1, glo, ghi, False), 1))
            rows.append(row(name + " [entry]", events(m, side, gout, 7, glo, ghi, True), 7))
        show(rows)




def diag():
    """Diagnostics of the explore failures (explore samples only): (a) price leg by listing age; (b) tail share of the loss;
    (c) the gap book's correlation with carry and its price leg by listing age."""
    p = data.load_panel("bnall", "1d")
    out = Outcomes(p)
    forms = bn_forms(p)
    c = p["close"]
    age = c.notna().cumsum()
    lo, hi = EXPLORE
    print("(a)/(b) explore, state H=1, by listing age (days since first bar; bnall starts 2020-01, so 2020 ages are capped):")
    for k in ("a2", "a3", "a2t30", "b0", "b3"):
        name = next(n for n in forms if n.split()[0] == k)
        side, m = forms[name]
        e = events(m, side, out, 1, lo, hi, False)
        a = age.stack().reindex(e.index)
        for lab, sel in (("age<120d", a < 120), ("age>=120d", a >= 120)):
            x = e[sel.values]
            print(f"  {name:22s} {lab:9s} n {len(x):5d} price {x['price'].mean()*1e4:7.1f} fund {x['fund'].mean()*1e4:6.1f} "
                  f"med price {x['price'].median()*1e4:6.1f}")
        g = e["gross"].sort_values()
        k1 = max(1, len(g) // 100)
        print(f"  {name:22s} gross sum {g.sum():.2f}; worst 1% of events {g.iloc[:k1].sum():.2f}; best 1% {g.iloc[-k1:].sum():.2f}")
    h = data.load_panel("hl", "1d")
    gforms, sub, rc = gap_forms(h, p)
    gout = Outcomes(sub)
    glo, ghi = GAP_EXPLORE
    sl = slice(pd.Timestamp(glo, tz="UTC"), pd.Timestamp(ghi, tz="UTC") - pd.Timedelta(days=1))
    ref = {"carry": strat_returns("carry", p, {"lookback": 1, "every_days": 7}),
           "carry_trend": strat_returns("carry_trend", p, {"lookback": 7, "every_days": 3}),
           "listing_short": strat_returns("listing_short", p, {"skip_days": 1, "hold_days": 60})}
    sage = sub["close"].notna().cumsum()
    for k in ("c1", "c3s", "cY"):
        name = next(n for n in gforms if n.split()[0] == k)
        side, m = gforms[name]
        b = book(m, side, gout, 3).loc[sl]
        bn_ = book(m, side, gout, 3, net=True).loc[sl]
        cs = " ".join(f"{r} {b.corr(v.shift(-1).loc[sl]):.2f}" for r, v in ref.items())
        print(f"  {name:28s} book SR gross {b.mean()/b.std()*np.sqrt(365):.2f} net {bn_.mean()/bn_.std()*np.sqrt(365):.2f}  corr {cs}")
        e = events(m, side, gout, 7, glo, ghi, True)
        a = sage.stack().reindex(e.index)
        for lab, sel in (("age<120d", a < 120), ("age>=120d", a >= 120)):
            x = e[sel.values]
            print(f"     entry H7 {lab:9s} n {len(x):4d} price {x['price'].mean()*1e4:7.1f} med {x['price'].median()*1e4:7.1f} fund {x['fund'].mean()*1e4:6.1f}")


if __name__ == "__main__":
    diag() if len(sys.argv) > 1 and sys.argv[1] == "diag" else main()
