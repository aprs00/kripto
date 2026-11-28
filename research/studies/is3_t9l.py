"""InSilico pass 3, T9L: shadow:flow@bn live orders replayed as rest-below k 50 bp post-only orders on live 4h bars. Descriptive.

  PYTHONPATH=. nice -n 19 .venv/bin/python -m research.studies.is3_t9l     # -> research/is3/t9l_ab.json
"""
from __future__ import annotations

import json
import sqlite3

import numpy as np
import pandas as pd

from kripto.data import DATA

EV = DATA.parent / "research" / "is3"
K, Q = 50e-4, 3e-4


def main():
    con = sqlite3.connect(DATA.parent / "state" / "paper.db")
    f = pd.read_sql("select ts, coin, size, px, mid, fee, slip_bps, reason from fills where book = 'shadow:flow@bn'", con)
    f["ts"] = pd.to_datetime(f["ts"], utc=True)
    f["coin"] = f["coin"].str.replace("@bn", "", regex=False)
    bars = {}
    rows = []
    for _, r in f.iterrows():
        c = r["coin"]
        if c not in bars:
            fp = DATA / "bn" / "live_4h" / f"{c}.parquet"
            if not fp.exists():
                bars[c] = None
            else:
                b = pd.read_parquet(fp)
                b.index = pd.to_datetime(b["t"], unit="ms", utc=True)
                bars[c] = b[~b.index.duplicated()].sort_index()
        b = bars[c]
        if b is None or not np.isfinite(r["mid"]) or r["mid"] <= 0:
            continue
        start = r["ts"].ceil("4h")
        w = b[(b.index >= start) & (b.index < r["ts"] + pd.Timedelta(hours=24))]
        if len(w) < 5:
            continue
        side = np.sign(r["size"])
        L = r["mid"] * (1 - side * K)
        filled = bool((w["l"] < L * (1 - Q)).any()) if side > 0 else bool((w["h"] > L * (1 + Q)).any())
        p24 = float(w["c"].iloc[-1])
        rows.append({"ts": r["ts"], "coin": c, "side": side, "notional": abs(r["size"] * r["px"]), "filled": filled,
                     "move24": side * (p24 / r["mid"] - 1), "slip_bps": r["slip_bps"], "fee_bps": r["fee"] / abs(r["size"] * r["px"]) * 1e4 if r["size"] else np.nan,
                     "reason": r["reason"]})
    d = pd.DataFrame(rows)
    wsum = lambda m: float(d.loc[m, "notional"].sum())
    out = {"fills_total": int(len(f)), "replayed": int(len(d)), "days": int(d["ts"].dt.normalize().nunique()), "window": [str(d.ts.min()), str(d.ts.max())],
           "fill_share_notional": round(wsum(d.filled) / wsum(d.index == d.index), 3),
           "fill_share_by_side": {("buy" if s > 0 else "sell"): round(wsum(d.filled & (d.side == s)) / wsum(d.side == s), 3) for s in (1, -1)},
           "fill_share_by_day": {str(k.date()): round(float(g.loc[g.filled, "notional"].sum() / g.notional.sum()), 2) for k, g in d.groupby(d.ts.dt.normalize())},
           "move24_filled_bp": round(float(np.average(d.loc[d.filled, "move24"], weights=d.loc[d.filled, "notional"]) * 1e4), 1),
           "move24_unfilled_bp": round(float(np.average(d.loc[~d.filled, "move24"], weights=d.loc[~d.filled, "notional"]) * 1e4), 1) if (~d.filled).any() else None,
           "live_slip_bps_wmean": round(float(np.average(d["slip_bps"].fillna(0), weights=d["notional"])), 2),
           "live_fee_bps_wmean": round(float(np.average(d["fee_bps"].fillna(0), weights=d["notional"])), 2),
           "reasons": d["reason"].value_counts().to_dict()}
    print(json.dumps(out, indent=1, default=str))
    json.dump(out, open(EV / "t9l_ab.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
