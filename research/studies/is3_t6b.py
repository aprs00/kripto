"""T6b (pre-registered in T6P 2026-11-28; code frozen by insilico T6S before any return was joined). HL top-account positioning -> next UTC day's HL return.
x(coin, d)  = mean over day d's hourly snapshots of sum(sign(szi) x positionValue) / sum(positionValue) over accounts holding the coin (>= 3 accounts that hour).
dx(coin, d) = sum over accounts holding the coin on BOTH d and d-1 of (sv_d - sv_{d-1}) / sum of (value_d + value_{d-1}) / 2 over them (>= 3 such accounts);
              sv, value = the account's sign x value and value averaged over the day's hourly snapshots in which it held the coin.
Outcome: HL 1d simple return close(d+1) / close(d) - 1 (close(d) = end of UTC day d). Statistic: mean daily cross-sectional Spearman IC, t = Newey-West (3 lags) over daily ICs.
EXPLORE 2026-11-10 .. 2026-12-07 (choose the sign, <= 2 variants: x and dx); CONFIRM 2026-12-08 .. 2027-02-05: PASS = same sign as explore, t >= 2 and |IC| >= .03.
  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_t6b dry|explore|confirm  -> research/is3/t6b_<mode>.json"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

EXPLORE = ("2026-11-10", "2026-12-08")      # [lo, hi)
CONFIRM = ("2026-12-08", "2027-02-06")


def load_positions(path_glob) -> pd.DataFrame:
    rows = []
    for f in sorted(path_glob):
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
    return d


def signal_x(d: pd.DataFrame) -> pd.DataFrame:
    d = d.assign(hour=d.t.dt.floor("1h"), sv=np.sign(d.szi) * d.value)
    g = d.groupby(["hour", "coin"]).agg(net=("sv", "sum"), gross=("value", "sum"), n=("user", "nunique"))
    g = g[g.n >= 3]
    g = g.assign(x=g.net / g.gross).reset_index()
    return g.assign(day=g.hour.dt.floor("D")).groupby(["day", "coin"]).x.mean().unstack()


def signal_dx(d: pd.DataFrame) -> pd.DataFrame:
    d = d.assign(day=d.t.dt.floor("D"), sv=np.sign(d.szi) * d.value)
    a = d.groupby(["day", "coin", "user"]).agg(sv=("sv", "mean"), value=("value", "mean")).reset_index()
    prev = a.assign(day=a.day + pd.Timedelta(days=1)).rename(columns={"sv": "sv0", "value": "v0"})
    m = a.merge(prev, on=["day", "coin", "user"], how="inner")
    m = m.assign(dsv=m.sv - m.sv0, avgv=(m.value + m.v0) / 2)
    g = m.groupby(["day", "coin"]).agg(dsv=("dsv", "sum"), avgv=("avgv", "sum"), n=("user", "nunique"))
    g = g[g.n >= 3]
    return (g.dsv / g.avgv).unstack()


def daily_ic(x: pd.DataFrame, nxt: pd.DataFrame, min_coins: int = 10) -> pd.Series:
    out = {}
    for t in x.index:
        if t not in nxt.index:
            continue
        a, b = x.loc[t], nxt.loc[t]
        m = a.notna() & b.notna()
        if m.sum() >= min_coins:
            out[t] = float(np.corrcoef(a[m].rank(), b[m].rank())[0, 1])
    return pd.Series(out, dtype=float)


def nw_t(s: pd.Series, L: int = 3) -> float:
    e = s - s.mean(); n = len(s); v = float((e * e).mean())
    for l in range(1, L + 1):
        v += 2 * (1 - l / (L + 1)) * float((e[l:].to_numpy() * e[:-l].to_numpy()).mean())
    return float(s.mean() / np.sqrt(v / n))


def guard(mode: str, today: pd.Timestamp) -> None:
    lo, hi = EXPLORE if mode == "explore" else CONFIRM
    if today < pd.Timestamp(hi, tz="UTC") + pd.Timedelta(days=1):    # the last day's next-day return must exist
        raise SystemExit(f"{mode}: not before {hi} + 1 day (pre-registration); today {today.date()}")


def main(mode: str):
    from kripto.data import DATA
    d = load_positions((DATA / "hl" / "positions").glob("*.jsonl"))
    X, DX = signal_x(d), signal_dx(d)
    out = {"mode": mode, "x_days": int(X.notna().any(axis=1).sum()), "x_coins_per_day": round(float(X.notna().sum(axis=1).mean()), 1),
           "dx_days": int(DX.notna().any(axis=1).sum()), "dx_coins_per_day": round(float(DX.notna().sum(axis=1).mean()), 1),
           "window": [str(X.index.min()), str(X.index.max())]}
    if mode != "dry":
        guard(mode, pd.Timestamp.now(tz="UTC"))
        from kripto import data
        c = data.load_panel("hl", "1d")["close"]
        nxt = (c.shift(-1) / c - 1)
        lo, hi = (pd.Timestamp(v, tz="UTC") for v in (EXPLORE if mode == "explore" else CONFIRM))
        for k, s in (("x", X), ("dx", DX)):
            s = s[(s.index >= lo) & (s.index < hi)]
            ic = daily_ic(s, nxt)
            out[k] = {"days": len(ic), "ic": round(float(ic.mean()), 4), "t_nw3": round(nw_t(ic), 2) if len(ic) > 4 else None}
    print(json.dumps(out, indent=1))
    json.dump(out, open(DATA.parent / "research" / "is3" / f"t6b_{mode}.json", "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dry")
