"""InSilico pass 3, NPC: H4 nested selection vs the same with a 0.4 correlation cap (prereg NPC_cap04). Descriptive corr at refits + OOS book per venue.
python -m research.studies.is3_npc hl | <bnall pickle path>"""
import json, pickle, sys
import numpy as np, pandas as pd
from kripto import backtest as bt, data, strategies as S
from kripto.research import bars_per_day
from research.studies.is3_prb import summary

src = sys.argv[1]
CAP = float(sys.argv[2]) if len(sys.argv) > 2 else 0.4      # NPS: robustness runs only; the prereg is 0.4
TOP = int(sys.argv[3]) if len(sys.argv) > 3 else 3
p = data.load_panel("hl", "1d") if src == "hl" else pickle.load(open(src, "rb"))
tag = "hl" if src == "hl" else "bnall"
c = p["close"]
comps, sel_std, log_std = S.nested_selection(p)
rets = {n: S._component_returns(p, n)[1] for n in comps}
R = pd.DataFrame(rets)
epoch = pd.Timestamp(0, tz=c.index.tz)
day = np.asarray((c.index - epoch) // pd.Timedelta(days=1), dtype=np.int64)
refit = np.flatnonzero(np.r_[True, np.diff(day // 60) != 0])
sel = pd.DataFrame(np.nan, c.index, list(comps))
log, changed, corr_snap = [], 0, {}
for i in refit:
    cur, start = {}, {}
    for n in comps:
        ri = R[n].iloc[: i + 1]
        inv = ri.ne(0).to_numpy()
        if not inv.any():
            continue
        k = int(inv.argmax()); ri = ri.iloc[k:]
        if len(ri) < 240 or ri.std() == 0:
            continue
        cur[n] = float(ri.mean() / ri.std() * np.sqrt(365)); start[n] = k
    ranked = [n for n, s in sorted(cur.items(), key=lambda x: -x[1]) if s > 0]
    best = []
    for n in ranked:
        ok = True
        for m in best:
            lo = max(start[n], start[m])
            a, b = R[n].iloc[lo: i + 1], R[m].iloc[lo: i + 1]
            if len(a) >= 120 and a.corr(b) > CAP:
                ok = False; break
        if ok:
            best.append(n)
        if len(best) == TOP:
            break
    std = ranked[:3]
    if set(std) != set(best):
        changed += 1
    sel.iloc[i] = 0.0
    if best:
        sel.iloc[i, [sel.columns.get_loc(n) for n in best]] = 1.0 / len(best)
    log.append((str(c.index[i].date()), std, best))
sel = sel.ffill().fillna(0.0)
# corr snapshot at the last refit among the standard choice + capped choice
i = refit[-1]
names = sorted(set(log[-1][1]) | set(log[-1][2]))
corr_snap = R[names].iloc[: i + 1].loc[lambda d: (d != 0).all(axis=1)].corr().round(2).to_dict() if names else {}
def book(s):
    tot = sum(comps[n].mul(s[n], axis=0) for n in comps)
    tot = tot.where(s.sum(axis=1) > 0, 0.0)
    return S.scheduled(tot, p, 1, 0.25, 3.0, None)
slip = bt.slippage_model(p["volume"], bars_per_day(c.index))
oos0 = sel_std.index[(sel_std.sum(axis=1) > 0).to_numpy()][0]
out = {"venue": tag, "refits": len(log), "changed": changed, "log_tail": log[-8:], "corr_last": corr_snap, "oos_start": str(oos0.date())}
yrs = range(max(oos0.year, 2021), 2027)
for k, s in (("standard", sel_std), ("cap04", sel)):
    res = bt.run(book(s).fillna(0.0), c, p.get("funding"), slip, band=0.005)
    out[k] = {str(y): summary(res, f"{y}-01-01", f"{y+1}-01-01") for y in yrs}
    out[k]["pooled"] = summary(res, str(oos0.date()), "2027-01-01")
    print(tag, k, {y: round(v["sr"], 2) for y, v in out[k].items()}, flush=True)
print(tag, "refits", len(log), "changed", changed, flush=True)
for row in log[-6:]:
    print("  ", row, flush=True)
suf = "" if (CAP == 0.4 and TOP == 3) else f"_cap{CAP}_top{TOP}"
json.dump(out, open(f"research/is3/npc_{tag}{suf}.json", "w"), indent=1, default=str)
