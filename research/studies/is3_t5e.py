"""T5E: T5b F3 (3-d OI change against the 3-d move) IC within 3-d winners / losers, split by a FROZEN regime (trend day = |BTC trailing 60-d simple return| >= 20 %).
a = the seen years 2023-03-05..2026-11-20 (does the regime story hold under this split?); b = 2021-01-01..2022-12-31 once (never seen), only if a holds.
Reuses research/studies/t5b_positioning (point-in-time top 60, last 5-min row of day d, target = bar d+1 return). Not registered.
  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_t5e seen|unseen -> research/is3/t5e_<sample>.json"""
import json, sys
import numpy as np, pandas as pd
from kripto import data
from research.studies.t5b_positioning import daily_metrics, ic_series

SAMPLE = sys.argv[1]
start, end = {"seen": ("2023-03-05", "2026-11-20"), "unseen": ("2021-01-01", "2022-12-31")}[SAMPLE]
if SAMPLE == "unseen":
    a = json.load(open("research/is3/t5e_seen.json"))
    if not a.get("H_holds_on_seen"):
        raise SystemExit("form a did not support the regime story on the seen years: the unseen sample stays closed")
p = data.load_bn_all_panel()
close = p["close"]
dv = p["volume"].rolling(30, min_periods=7).mean()
member = (dv.rank(axis=1, ascending=False) <= 60)
lo, hi = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
syms = [c + "USDT" for c in member.columns[member.loc[lo:hi].any()]]
m = daily_metrics(syms, start, end)
coins = [c for c in m["oi"].columns if c in close.columns]
ret3 = (close / close.shift(3) - 1).reindex(columns=coins)
fwd1 = close.pct_change(fill_method=None).shift(-1).reindex(columns=coins)
doi = np.log(m["oi"].reindex(columns=coins)).diff(3)
f3 = doi * -np.sign(ret3.reindex(index=doi.index))
r60 = close["BTC"] / close["BTC"].shift(60) - 1
trend = (r60.abs() >= 0.20)
idx = f3.index[(f3.index >= lo) & (f3.index <= hi)]
mem = member.reindex(columns=coins).reindex(index=idx).fillna(False)
out = {"sample": SAMPLE, "window": [start, end], "coins": len(coins), "days": len(idx), "trend_day_share": round(float(trend.reindex(idx).mean()), 3)}


def nw(s, L=3):
    s = s.dropna(); e = s - s.mean(); n = len(s); v = float((e * e).mean())
    for l in range(1, L + 1):
        v += 2 * (1 - l / (L + 1)) * float((e[l:].to_numpy() * e[:-l].to_numpy()).mean())
    return float(s.mean() / np.sqrt(v / n)) if n > 5 else None


for grp, side in (("winners", 1), ("losers", -1)):
    mm = mem & (np.sign(ret3.reindex(idx)) == side)
    ic = ic_series(f3.reindex(idx), fwd1, mm, None, 1)
    tr = trend.reindex(ic.index).fillna(False)
    o = {}
    for k, msk in (("trend", tr), ("range", ~tr)):
        s = ic[msk]
        o[k] = {"days": int(len(s)), "ic": round(float(s.mean()), 4) if len(s) else None, "t_nw3": round(nw(s), 2) if len(s) > 5 else None}
    d = ic[tr].mean() - ic[~tr].mean()
    se = np.sqrt(ic[tr].var(ddof=1) / max(tr.sum(), 1) + ic[~tr].var(ddof=1) / max((~tr).sum(), 1))
    o["trend_minus_range"] = round(float(d), 4); o["t_diff"] = round(float(d / se), 2) if se > 0 else None
    o["by_year"] = {int(y): {"ic": round(float(v.mean()), 4), "trend_share": round(float(tr[v.index].mean()), 2)} for y, v in ic.groupby(ic.index.year)}
    out[grp] = o
    print(grp, json.dumps(o), flush=True)
w = out["winners"]
# F3 = dOI x -sign(ret3): within winners a POSITIVE F3 IC = OI-building winners FADE. Story (T5c): fade in range, continue in trend
# -> range IC > 0 and trend IC < range IC. (11-28 first run coded this with the wrong sign and printed True; corrected before any unseen look.)
out["H_holds_on_seen"] = bool(SAMPLE == "seen" and w["range"]["ic"] is not None and w["range"]["ic"] > 0 and w["trend_minus_range"] < 0)
if SAMPLE == "unseen":
    out["PASS"] = bool(w["range"]["ic"] is not None and w["range"]["ic"] > 0 and w["trend_minus_range"] < 0 and (w["t_diff"] or 0) <= -2)
json.dump(out, open(f"research/is3/t5e_{SAMPLE}.json", "w"), indent=1)
print("H_holds_on_seen" if SAMPLE == "seen" else "PASS", out.get("H_holds_on_seen", out.get("PASS")))
