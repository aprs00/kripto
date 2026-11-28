"""NPC3: nested selection by the expanding COMBINED Sharpe of the equal-risk set (threshold-free form of NPC's corr cap). Not registered.
python -m research.studies.is3_npc3 hl|<bnall pickle>  -> research/is3/npc3_<venue>.json
Variants: size 2/3/4 (exact max over all sets with every leg's own expanding SR > 0), 'shr3' = size 3 with correlations shrunk 50 % to 0."""
import itertools, json, pickle, sys, inspect
import numpy as np, pandas as pd
from kripto import backtest as bt, data, strategies as S
from kripto.research import bars_per_day
from research.studies.is3_prb import summary

src = sys.argv[1]
p = data.load_panel("hl", "1d") if src == "hl" else pickle.load(open(src, "rb"))
tag = "hl" if src == "hl" else "bnall"
c = p["close"]
comps, sel_std, log_std = S.nested_selection(p)
R = pd.DataFrame({n: S._component_returns(p, n)[1] * (0.20 / inspect.signature(S.REGISTRY[n]).parameters["target_vol"].default) for n in comps})
epoch = pd.Timestamp(0, tz=c.index.tz)
day = np.asarray((c.index - epoch) // pd.Timedelta(days=1), dtype=np.int64)
refit = np.flatnonzero(np.r_[True, np.diff(day // 60) != 0])


def set_sharpe(names, i, start, shrink):
    lo = max(start[n] for n in names)
    X = R[list(names)].iloc[lo: i + 1].to_numpy()
    if len(X) < 240:
        return -np.inf
    mu, cov = X.mean(0), np.cov(X, rowvar=False) if len(names) > 1 else np.array([[X.var(ddof=1)]])
    if shrink and len(names) > 1:
        sd = np.sqrt(np.diag(cov)); corr = cov / np.outer(sd, sd); corr = 0.5 * corr + 0.5 * np.eye(len(names)); cov = corr * np.outer(sd, sd)
    wv = np.full(len(names), 1.0 / len(names))
    return float(wv @ mu / np.sqrt(wv @ cov @ wv) * np.sqrt(365))


def select(size, shrink, exact=False):
    sel = pd.DataFrame(np.nan, c.index, list(comps)); changed = 0; log = []
    for j, i in enumerate(refit):
        cur, start = {}, {}
        for n in comps:
            ri = R[n].iloc[: i + 1]; inv = ri.ne(0).to_numpy()
            if not inv.any():
                continue
            k = int(inv.argmax()); ri = ri.iloc[k:]
            if len(ri) < 240 or ri.std() == 0:
                continue
            s = float(ri.mean() / ri.std() * np.sqrt(365))
            if s > 0:
                cur[n] = s; start[n] = k
        best, bs = [], -np.inf
        for k in ([min(size, len(cur))] if exact and cur else range(1, size + 1)):
            for combo in itertools.combinations(sorted(cur), k):
                v = set_sharpe(combo, i, start, shrink)
                if v > bs:
                    bs, best = v, list(combo)
        std = [n for n, s in sorted(cur.items(), key=lambda x: -x[1])][:3]
        changed += set(std) != set(best)
        sel.iloc[i] = 0.0
        if best:
            sel.iloc[i, [sel.columns.get_loc(n) for n in best]] = 1.0 / len(best)
        log.append((str(c.index[i].date()), std, best, round(bs, 2) if np.isfinite(bs) else None))
    return sel.ffill().fillna(0.0), changed, log


def book(s):
    tot = sum(comps[n].mul(s[n], axis=0) for n in comps)
    tot = tot.where(s.sum(axis=1) > 0, 0.0)
    return S.scheduled(tot, p, 1, 0.25, 3.0, None)


slip = bt.slippage_model(p["volume"], bars_per_day(c.index))
oos0 = sel_std.index[(sel_std.sum(axis=1) > 0).to_numpy()][0]
yrs = range(max(oos0.year, 2021), 2027)
out = {"venue": tag, "refits": len(refit), "oos_start": str(oos0.date())}
variants = {"standard": (sel_std, None, None)}
for k, (size, shr) in {"size2": (2, False), "size3": (3, False), "size4": (4, False), "shr3": (3, True), "exact3": (3, "x"), "exact3_shr": (3, "xs")}.items():
    s, ch, lg = select(size, shr in (True, "xs"), exact=shr in ("x", "xs")); variants[k] = (s, ch, lg)
for k, (s, ch, lg) in variants.items():
    res = bt.run(book(s).fillna(0.0), c, p.get("funding"), slip, band=0.005)
    o = {str(y): round(summary(res, f"{y}-01-01", f"{y+1}-01-01")["sr"], 2) for y in yrs}
    o["pooled"] = round(summary(res, str(oos0.date()), "2027-01-01")["sr"], 2)
    o["pooled_ex2026"] = round(summary(res, str(oos0.date()), "2026-01-01")["sr"], 2)
    if ch is not None:
        o["changed_vs_std"] = ch; o["log_tail"] = lg[-5:]
        o["mean_legs"] = round(float((s.loc[oos0:] > 0).sum(axis=1).mean()), 2)
    out[k] = o
    print(tag, k, json.dumps(o, default=str), flush=True)
json.dump(out, open(f"research/is3/npc3_{tag}.json", "w"), indent=1, default=str)
