"""LD1: inventory skew for the resting ladder (library N13, Gueant 2016 §11; backlog LD1). Descriptive, NOT registered (no walk-forward).

  nice -n 19 .venv/bin/python -m research.studies.ld1_ladder_skew universe          # causal top-20 (is3_ladtop.universe) -> data/is3/ld1_universe.parquet
  nice -n 19 .venv/bin/python -m research.studies.ld1_ladder_skew build [workers]   # k30-crossing minutes, one bar late, NO lock -> data/is3/ld1_cand.parquet
  nice -n 19 .venv/bin/python -m research.studies.ld1_ladder_skew explore           # all forms, 2021-01-01 .. 2023-12-31 only
  nice -n 19 .venv/bin/python -m research.studies.ld1_ladder_skew confirm <form>    # ONE run of the explore pick on 2024-01-01 .. 2026-10-31

THINK-THROUGH (written 2026-11-26 before any run)
(a) Mechanism. The ladder is paid by forced sellers: a liquidation cascade pushes a coin 30 sigma below its last close and our resting bid is
    the liquidity they hit; the bounce is the payment. Avellaneda-Stoikov / Gueant: a market maker with inventory q shifts BOTH quotes away
    from the side he is long (distance ~ static term + (2q+1)/2 * sigma * const), because more inventory = more exposure to the same
    adverse move. Our inventory risk is not per coin but market-wide: fills cluster in flushes (E2c: the largest same-minute batch held 17
    fills, 2025-10-10 and 2024-01-03 marked -17% at the minute low while the booked worst day was -4.6%). Hypothesis: when positions are
    already open the market is in a flush, the NEXT fills are more likely to be the continuation leg, so quote deeper (better price, fewer
    fills) or not at all. Counter-prior (findings T1): "stops, calm filters and don't quote when BTC falls all make it worse; the cascade is
    what pays". So the likely failure is that deepening cuts exactly the fills that pay most.
(b) Source. N13 is a closed form for a continuous two-sided market maker with exponential fill intensity; we run a one-sided, sparse,
    30-sigma ladder that fills only in tails. What transfers is the shape: distance proportional to sigma, shifted linearly in inventory.
(c) Formulations (live-implementable: the quote judging minute t is set from the close of t-2, so state is counted as of q = t-2):
    A  book-wide inventory: k = 30 * (1 + lam * n_open(q)), n_open = ladder positions open at q.        lam in {0.1, 0.25, 0.5}
    B  per-coin inventory. Per-coin n_open is IDENTICALLY 0 under the frozen rule (one position per coin per 60 min lock, positions live 61
       min), so the per-coin form uses the coin's own memory: k = 30 * (1 + lam * fills of this coin in the last 6 h).  lam in {0.25, 0.5, 1.0}
    C  market-wide flush indicator, independent of what WE hold: f(q) = distinct universe coins whose k30 bid was crossed in (q-30m, q].
       C1 f >= 3 -> k = 45;  C2 f >= 5 -> k = 45;  C3 f >= 3 -> no quote.
    D  hard cap on concurrent fills (the base takes the WHOLE same-minute batch while < 5 are open, so 17 can open at once): never more than
       cap open, a batch is truncated in universe-rank order (highest volume first).   cap in {2, 3, 5}
    Closest to the idea: A. D is the blunt control (does any skew beat simply holding less?).
(d) Non-idea failures: (1) A/B/C cannot see a same-minute batch from a flat book (n_open at q=t-2 is 0), which is where the worst day lives;
    D is there for that. (2) Local data: this PC holds minute bars for ~80% of top-20 coin-days (no k1m_top), so concurrency is understated
    and the base differs from the server's E2 numbers; every form is compared with a base built from the SAME candidate set. (3) Too few
    tail days: the worst day is ONE event per sample; the worst-5-day share and the per-year table are there so one day does not decide.
    (4) Deeper quotes beyond the PERCENT_PRICE band are not placed (live rule), which can silently turn "deeper" into "skip".
(e) Fill model = the stressed one-bar-late E2 rule (is3_e2.events_late): quote = close[t-2] * (1 - k sigma[t-2]), fill if low[t] <= quote *
    (1 - 30 bp), entry at the quote, exit at close[t+61], cost 7 bp + slip_per_day, 5% per order, P&L booked on the fill day, simple (not
    compounded); one event per coin per 60 min (lock set by an event even when the account had no slot, as in E2); a slot frees at fill+60.
    The candidate table holds every k30-crossing minute without the lock; any deeper quote's fill is a subset of it (same close, same sigma).
PRE-REGISTERED RULES (before any run)
    Explore 2021-01-01 .. 2023-12-31. Confirm 2024-01-01 .. 2026-10-31 (2026 = the spent vault year of T1/E2; acknowledged).
    Explore pick: eligible if explore daily SR >= base SR - 0.1 AND explore worst day improved by >= 25 % (|worst| <= 0.75 |base worst|);
    among eligible, the largest worst-5-day-sum improvement, ties -> higher SR. If none is eligible, NO confirm is spent and LD1 is recorded
    OPEN with the diagnosis (the confirm sample stays clean for a better-motivated form).
    Confirm PASS: confirm daily SR >= base SR - 0.1 AND confirm worst day improved by >= 25 %. Anything else = FAIL for that form.
    Live ladder changes only on a confirm PASS, and then only by a design decision in a research session, never from this script.
"""
from __future__ import annotations

import json
import sys
from collections import deque
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from kripto import events as ev
from kripto import metrics as mx
from research.studies import is3_e2 as E
from research.studies import is3_ladtop as T

OUT = T.OUT
K, THROUGH, HOLD, SLOTS, SIZE, COST = 30.0, 30e-4, 60, 5, 0.05, 7e-4
LO, HI = pd.Timestamp("2021-01-01", tz="UTC"), pd.Timestamp("2026-11-01", tz="UTC")
SPLIT = pd.Timestamp("2024-01-01", tz="UTC")
MIN = pd.Timedelta(minutes=1)

FORMS = {"base": ("base", None),
         "A_0.1": ("A", 0.1), "A_0.25": ("A", 0.25), "A_0.5": ("A", 0.5),
         "B_0.25": ("B", 0.25), "B_0.5": ("B", 0.5), "B_1.0": ("B", 1.0),
         "C1_f3_k45": ("C", (3, 45.0)), "C2_f5_k45": ("C", (5, 45.0)), "C3_f3_skip": ("C", (3, None)),
         "D_cap2": ("D", 2), "D_cap3": ("D", 3), "D_cap5": ("D", 5)}


def universe():
    u = T.universe()
    u.to_parquet(OUT / "ld1_universe.parquet")
    print(len(u), "coin-days,", u.coin.nunique(), "coins", flush=True)


def cand_one(a):
    """Every minute whose low crosses the one-bar-late k30 bid (no lock), with what any deeper quote needs: kreach = deepest k that fills."""
    coin, days = a
    out = []
    for x in T.series(coin, LO, HI):
        c, l = x["c"].to_numpy(), x["l"].to_numpy()
        r = np.diff(np.log(c), prepend=np.nan)
        sig = pd.Series(r).rolling(1440, min_periods=720).std().to_numpy()
        cp, sp = np.roll(c, 2), np.roll(sig, 2)
        lim = cp * (1 - K * sp)
        n = len(c)
        tt = np.flatnonzero((l <= lim * (1 - THROUGH)) & (sp > 0))
        tt = tt[(tt >= 720) & (tt + 1442 < n)]
        if not len(tt):
            continue
        e = pd.DataFrame({"time": x.index[tt], "sp": sp[tt], "cp": cp[tt], "kreach": (1 - l[tt] / (1 - THROUGH) / cp[tt]) / sp[tt], "c61": c[tt + 61]})
        e["slip"] = ev.slip_per_day(x["qv"].to_frame(coin))[coin].reindex(e.time.dt.floor("D")).to_numpy()
        out.append(e)
    if not out:
        return pd.DataFrame(), 0
    e = pd.concat(out).assign(coin=coin, day=lambda d: d.time.dt.floor("D")).merge(days, on="day")
    e = e[(e.time >= LO) & (e.time < HI)]
    return e, len(e)


def build(workers=3):
    u = pd.read_parquet(OUT / "ld1_universe.parquet")
    jobs = [(c, g[["day", "rank"]]) for c, g in u.groupby("coin")]
    with ProcessPoolExecutor(int(workers)) as ex:
        parts = [x[0] for x in ex.map(cand_one, jobs) if len(x[0])]
    t = pd.concat(parts).sort_values(["time", "rank"]).reset_index(drop=True)
    t["band"] = t.coin.map(E.bands()).fillna(0.15)
    t.to_parquet(OUT / "ld1_cand.parquet")
    print(len(t), "k30 crossing minutes,", t.coin.nunique(), "coins", t.time.min(), t.time.max(), flush=True)


def flush_count(t, window=30):
    """f(q) for every candidate minute t: distinct coins with a k30 crossing in (q - window, q], q = t - 2 min. Causal."""
    times = t.time.to_numpy()
    coins = t.coin.to_numpy()
    out = np.zeros(len(t), dtype=int)
    win = deque()
    cnt: dict[str, int] = {}
    j = 0
    w = np.timedelta64(window, "m")
    two = np.timedelta64(2, "m")
    for i in range(len(t)):
        q = times[i] - two
        while j < len(t) and times[j] <= q:
            win.append(j)
            cnt[coins[j]] = cnt.get(coins[j], 0) + 1
            j += 1
        while win and times[win[0]] <= q - w:
            k = win.popleft()
            cnt[coins[k]] -= 1
            if not cnt[coins[k]]:
                del cnt[coins[k]]
        out[i] = len(cnt)
    return out


def simulate(t, form, par):
    """The account under one form. Returns the taken fills (time, coin, k, net)."""
    rows = t.to_dict("records")
    open_pos: list[pd.Timestamp] = []          # fill minutes of taken positions
    last_evt: dict[str, pd.Timestamp] = {}
    coin_fills: dict[str, deque] = {}
    taken = []
    i, n = 0, len(rows)
    while i < n:
        tm = rows[i]["time"]
        j = i
        while j < n and rows[j]["time"] == tm:
            j += 1
        q = tm - 2 * MIN
        open_pos = [f for f in open_pos if f + 61 * MIN > q]
        n_open_q = sum(1 for f in open_pos if f <= q)                 # what the quote setter knew
        slots_used = sum(1 for f in open_pos if f + HOLD * MIN > tm)  # E2 slot rule
        evts = []
        for r in rows[i:j]:
            c = r["coin"]
            if c in last_evt and tm <= last_evt[c] + HOLD * MIN:
                continue
            k = K
            if form == "A":
                k = K * (1 + par * n_open_q)
            elif form == "B":
                d = coin_fills.get(c, deque())
                while d and d[0] <= q - pd.Timedelta(hours=6):
                    d.popleft()
                k = K * (1 + par * sum(1 for f in d if f <= q))
            elif form == "C":
                m, kk = par
                if r["flush"] >= m:
                    if kk is None:
                        continue
                    k = kk
            if k * r["sp"] > r["band"] or r["kreach"] < k:
                continue
            last_evt[c] = tm
            evts.append((r, k))
        if evts and slots_used < SLOTS:
            if form == "D":
                evts = evts[:max(0, par - slots_used)]
            for r, k in evts:
                p = r["cp"] * (1 - k * r["sp"])
                net = r["c61"] / p - 1 - (COST + r["slip"])
                taken.append({"time": tm, "coin": r["coin"], "k": k, "net": net})
                open_pos.append(tm)
                coin_fills.setdefault(r["coin"], deque()).append(tm)
        i = j
    return pd.DataFrame(taken)


def daily(f, lo, hi):
    idx = pd.date_range(lo, hi, tz="UTC", inclusive="left")
    if not len(f):
        return pd.Series(0.0, idx)
    return (f.net * SIZE).groupby(f.time.dt.floor("D")).sum().reindex(idx, fill_value=0.0)


def card(f, r, base_r=None):
    tot = float(r.sum())
    w5 = float(r.nsmallest(5).sum())
    d = {"n": len(f), "sr": round(mx.sharpe(r, 365), 2), "ret_yr": round(tot / (len(r) / 365), 4), "worst": round(float(r.min()), 4),
         "worst5": round(w5, 4), "w5_share": round(w5 / tot, 2) if tot else None,
         "t_daily": round(float(r.mean() / r.std() * np.sqrt(len(r))), 2), "top3_share": round(float(r.nlargest(3).sum()) / tot, 2) if tot else None,
         "by_year": {str(y): [round(mx.sharpe(x, 365), 2), round(float(x.sum()), 4), round(float(x.min()), 4)] for y, x in r.groupby(r.index.year)}}
    if base_r is not None:
        dd = r - base_r
        d["t_diff"] = round(float(dd.mean() / dd.std() * np.sqrt(len(dd))), 2) if dd.std() > 0 else 0.0
        d["worst_days_base"] = {str(k.date()): [round(float(base_r[k]), 4), round(float(r[k]), 4)] for k in base_r.nsmallest(5).index}
    return d


def load(lo, hi):
    t = pd.read_parquet(OUT / "ld1_cand.parquet")
    t["flush"] = flush_count(t)
    return t[(t.time >= lo) & (t.time < hi)].reset_index(drop=True)


def run(names, lo, hi, tag):
    t = load(lo, hi)
    print(f"{tag}: {len(t)} candidate minutes, {t.coin.nunique()} coins", flush=True)
    res, R = {}, {}
    for nm in names:
        f = simulate(t, *FORMS[nm])
        R[nm] = daily(f, lo, hi)
        res[nm] = card(f, R[nm], None if nm == "base" else R["base"])
        res[nm]["mean_k"] = round(float(f.k.mean()), 1) if len(f) else None
        b = res["base"]
        x = res[nm]
        print(f"{nm:12s} n {x['n']:5d} sr {x['sr']:5.2f} ret/yr {x['ret_yr']:+.3f} worst {x['worst']:+.4f} worst5 {x['worst5']:+.4f} "
              f"w5sh {x['w5_share']} t {x['t_daily']} top3 {x['top3_share']} tdiff {x.get('t_diff')} "
              f"dSR {x['sr'] - b['sr']:+.2f} worst_impr {1 - x['worst'] / b['worst']:+.0%}", flush=True)
    return res


def explore():
    res = run(list(FORMS), LO, SPLIT, "explore")
    b = res["base"]
    elig = [nm for nm, x in res.items() if nm != "base" and x["sr"] >= b["sr"] - 0.1 and x["worst"] >= 0.75 * b["worst"]]
    pick = max(elig, key=lambda nm: (res[nm]["worst5"], res[nm]["sr"])) if elig else None
    out = {"explore": res, "eligible": elig, "pick": pick}
    (OUT / "ld1_explore.json").write_text(json.dumps(out, indent=1, default=str))
    print("eligible", elig, "pick", pick)
    print(json.dumps({k: {kk: v[kk] for kk in ("by_year", "worst_days_base") if kk in v} for k, v in res.items()}, indent=0, default=str))


def confirm(name):
    p = OUT / "ld1_confirm.json"
    if p.exists():
        raise SystemExit(f"confirm already spent: {p}")
    res = run(["base", name], SPLIT, HI, "confirm")
    b, x = res["base"], res[name]
    ok = x["sr"] >= b["sr"] - 0.1 and x["worst"] >= 0.75 * b["worst"]
    p.write_text(json.dumps({"form": name, "pass": ok, **res}, indent=1, default=str))
    print("PASS" if ok else "FAIL", json.dumps(res, indent=0, default=str))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"universe": universe, "build": lambda: build(*a[1:]), "explore": explore, "confirm": lambda: confirm(a[1])}[a[0]]()
