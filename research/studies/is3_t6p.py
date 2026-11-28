"""InSilico pass 3, T6P: HL top-account positioning data integrity + signal sizing WITHOUT returns (T6b precheck). Descriptive.
  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_t6p  -> research/is3/t6p_ab.json"""
import json
import numpy as np
import pandas as pd
from kripto.data import DATA

rows = []
for f in sorted((DATA / "hl" / "positions").glob("*.jsonl")):
    for line in open(f):
        try:
            r = json.loads(line)
        except Exception:
            continue
        for p in r.get("pos") or []:
            try:
                rows.append((r["ts"], r["user"], p[0], float(p[1]), float(p[3])))
            except Exception:
                pass
d = pd.DataFrame(rows, columns=["ts", "user", "coin", "szi", "value"])
d["t"] = pd.to_datetime(d.ts, unit="s", utc=True)
d["hour"] = d.t.dt.floor("1h")
snaps = d.groupby("hour").user.nunique()
hrs = pd.date_range(snaps.index.min(), snaps.index.max(), freq="1h")
gaps = hrs.difference(snaps.index)
users_by_day = d.groupby(d.t.dt.floor("D")).user.unique()
days = sorted(users_by_day.index)
stay = [len(set(users_by_day[a]) & set(users_by_day[b])) / max(1, len(set(users_by_day[a]))) for a, b in zip(days[:-1], days[1:])]
d["sv"] = np.sign(d.szi) * d.value
g = d.groupby(["hour", "coin"]).agg(net=("sv", "sum"), gross=("value", "sum"), n=("user", "nunique"))
g = g[g.n >= 3]
g["x"] = g.net / g.gross
day = g.reset_index().assign(day=lambda x: x.hour.dt.floor("D")).groupby(["day", "coin"]).x.mean().unstack()
ncoin = day.notna().sum(axis=1)
disp = day.std(axis=1)
ac = []
for c in day.columns:
    s = day[c].dropna()
    if len(s) > 5:
        ac.append(s.autocorr())
rank_ac = day.rank(axis=1).corrwith(day.rank(axis=1).shift(1), axis=1, method="pearson") if False else None
# daily rank IC MDE: se(IC_day) ~ 1/sqrt(N-1); mean over D days; signal autocorrelation inflates the variance of the mean (n_eff = D (1-rho)/(1+rho))
N = float(ncoin.median()); rho = float(np.nanmedian(ac)) if ac else 0.0
out = {"files": len(list((DATA / "hl" / "positions").glob("*.jsonl"))), "span": [str(d.t.min()), str(d.t.max())], "position_rows": int(len(d)),
       "snapshot_hours": int(len(snaps)), "hours_in_span": int(len(hrs)), "gaps_hours": int(len(gaps)), "gap_list": [str(x) for x in gaps[:30]],
       "accounts_per_snapshot_median": float(snaps.median()), "accounts_total": int(d.user.nunique()),
       "account_overlap_day_to_day_median": round(float(np.median(stay)), 2),
       "coins_with_3plus_accounts_per_day_median": N, "net_x_dispersion_median": round(float(disp.median()), 3),
       "net_x_autocorr_1d_median": round(rho, 2)}
for D, tag in ((14, "explore_or_confirm_14d"), (28, "all_28d_at_12_07"), (60, "60d")):
    neff = D * (1 - rho) / (1 + rho) if rho > 0 else D
    se = 1 / np.sqrt(max(N - 1, 1)) / np.sqrt(max(neff, 1))
    out[f"mde_ic_{tag}"] = round(float(2.8 * se), 3)
print(json.dumps(out, indent=1)); json.dump(out, open("research/is3/t6p_ab.json", "w"), indent=1)
